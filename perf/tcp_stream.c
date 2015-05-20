#include <getopt.h>
#include <math.h>
#include <netinet/in.h>
#include <pthread.h>
#include <stdio.h>
#include <sys/eventfd.h>
#include <sys/prctl.h>
#include <sys/resource.h>
#include <sys/time.h>
#include <unistd.h>
#include "common.h"
#include "cpuinfo.h"
#include "logging.h"

static struct {
	/* Is client? */
	int client;
	/* Number of worker threads */
	int num_threads;
	/* Total number of flows */
	int num_flows;
	/* Server hostname or IP address that the client will connect to */
	const char *host;
	/* Control port */
	const char *control_port;
	/* Port for the server to listen on, or for the client to connect to */
	const char *port;
	/* Test length in seconds */
	int test_length;
	/* Number of bytes that each read/write uses as the buffer size */
	int buffer_size;
	/* Nanosecond delay between each send()/write() */
	unsigned long delay;
	/* For how many reads (in each thread) that a sample is generated */
	int sample_rate;
	/* Print all samples or not */
	const char *all_samples;
	/* Turn on writing to flows. Enabled by default on the client side. */
	int enable_write;
	/* Turn on reading from flows. Enabled by default on the server side. */
	int enable_read;
	/* Turn on dry-run mode. */
	int dry_run;
	/* Pin threads to CPU cores */
	int pin_cpu;
	/* Edge-triggered epoll */
	int edge_trigger;
} flags;

static pthread_barrier_t worker_thread_ready_barrier;

struct sample_point {
	int tid;
	int flow_id;
	ssize_t bytes_read;
	struct timespec timestamp;
	struct rusage rusage;
	struct sample_point *next;
};

static void add_sample(int tid, int flow_id, ssize_t bytes_read,
		       struct sample_point **samples)
{
	struct sample_point *sample = calloc(1, sizeof(struct sample_point));
	sample->tid = tid;
	sample->flow_id = flow_id;
	sample->bytes_read = bytes_read;
	clock_gettime(CLOCK_MONOTONIC, &sample->timestamp);
	getrusage(RUSAGE_SELF, &sample->rusage);
	sample->next = *samples;
	*samples = sample;
}

static void print_sample(FILE *csv, struct sample_point *sample)
{
	if (!sample) {
		fprintf(csv, "time,tid,flow_id,bytes_read,utime,stime,");
		fprintf(csv, "maxrss,minflt,majflt,nvcsw,nivcsw\n");
		return;
	}
	fprintf(csv,
		"%ld.%09ld,%d,%d,%zd,%ld.%06ld,%ld.%06ld,%ld,%ld,%ld,%ld,%ld\n",
		sample->timestamp.tv_sec, sample->timestamp.tv_nsec,
		sample->tid, sample->flow_id, sample->bytes_read,
		sample->rusage.ru_utime.tv_sec, sample->rusage.ru_utime.tv_usec,
		sample->rusage.ru_stime.tv_sec, sample->rusage.ru_stime.tv_usec,
		sample->rusage.ru_maxrss,
		sample->rusage.ru_minflt, sample->rusage.ru_majflt,
		sample->rusage.ru_nvcsw, sample->rusage.ru_nivcsw);
}

struct event_info {
	int fd;
	int flow_id;
	ssize_t bytes_read;
};

static void epoll_add_or_die(int epollfd, int fd, uint32_t events)
{
	struct epoll_event ev;
	struct event_info *ei = calloc(1, sizeof(struct event_info));
	ei->fd = fd;
	ev.events = events;
	ev.data.ptr = ei;
	epoll_ctl_or_die(epollfd, EPOLL_CTL_ADD, fd, &ev);
}

static void addflow(int tid, int epollfd, int fd, int flow_id)
{
	struct event_info *ei;
	struct epoll_event ev;

	set_nonblocking(fd);
	ei = calloc(1, sizeof(struct event_info));
	ei->fd = fd;
	ei->flow_id = flow_id;
	ev.events = EPOLLRDHUP;
	if (flags.enable_write)
		ev.events |= EPOLLOUT;
	if (flags.enable_read)
		ev.events |= EPOLLIN;
	if (flags.edge_trigger)
		ev.events |= EPOLLET;
	ev.data.ptr = ei;
	epoll_ctl_or_die(epollfd, EPOLL_CTL_ADD, fd, &ev);
	LOG(INFO, "addflow %d.%d", tid, ei->flow_id);
}

static void delflow(int tid, int epfd, struct event_info *ei)
{
	epoll_del_or_err(epfd, ei->fd);
	do_close(ei->fd);
	LOG(INFO, "delflow %d.%d", tid, ei->flow_id);
	free(ei);
}

static int process_events(int tid, int epfd, struct epoll_event *events,
			  int nfds, int stop_efd, int fd_listen,
			  int *next_flow_id, int *num_reads, char *buf,
			  struct sample_point **samples)
{
	struct sockaddr_in cli_addr;
	struct event_info *ei;
	struct timespec ts;
	socklen_t cli_len;
	ssize_t num_bytes;
	int i, client;

	for (i = 0; i < nfds; i++) {
		ei = events[i].data.ptr;
		if (ei->fd == stop_efd)
			return 1;
		if (ei->fd == fd_listen && next_flow_id) {
			cli_len = sizeof(struct sockaddr_in);
			client = accept(fd_listen, (struct sockaddr *)&cli_addr,
					&cli_len);
			if (client == -1) {
				if (errno == EINTR || errno == ECONNABORTED)
					continue;
				PLOG(ERROR, "accept");
				continue;
			}
			addflow(tid, epfd, client, (*next_flow_id)++);
			continue;
		}
		if (events[i].events & EPOLLRDHUP) {
			delflow(tid, epfd, ei);
			continue;
		}
		if (flags.enable_read && (events[i].events & EPOLLIN)) {
read_again:
			num_bytes = read(ei->fd, buf, flags.buffer_size);
			if (num_bytes == -1) {
				if (errno != EAGAIN)
					PLOG(ERROR, "read");
				continue;
			}
			if (num_bytes == 0) {
				delflow(tid, epfd, ei);
				continue;
			}
			ei->bytes_read += num_bytes;
			(*num_reads)++;
			if (*num_reads % flags.sample_rate == 0) {
				add_sample(tid, ei->flow_id, ei->bytes_read,
					   samples);
			}
			if (flags.edge_trigger)
				goto read_again;
		}
		if (flags.enable_write && (events[i].events & EPOLLOUT)) {
write_again:
			num_bytes = write(ei->fd, buf, flags.buffer_size);
			if (num_bytes == -1) {
				if (errno != EAGAIN)
					PLOG(ERROR, "write");
				continue;
			}
			if (flags.delay) {
				ts.tv_sec = flags.delay / (1000*1000*1000);
				ts.tv_nsec = flags.delay % (1000*1000*1000);
				nanosleep(&ts, NULL);
			}
			if (flags.edge_trigger)
				goto write_again;
		}
	}
	return 0;
}

static void run_client(int tid, struct addrinfo *ai, int stop_efd,
		       struct sample_point **samples)
{
	const int flows_in_this_thread = flows_in_thread(flags.num_flows,
							 flags.num_threads,
							 tid);
	int epfd, i, flow, nfds, num_reads = 0, stop = 0;
	struct epoll_event *events;
	char *buf;

	LOG(INFO, "flows_in_this_thread=%d", flows_in_this_thread);
	epfd = epoll_create(flows_in_this_thread);
	if (epfd == -1)
		PLOG(FATAL, "epoll_create");
	epoll_add_or_die(epfd, stop_efd, EPOLLIN);
	for (i = 0; i < flows_in_this_thread; i++) {
		flow = socket(ai->ai_family, ai->ai_socktype, ai->ai_protocol);
		if (flow == -1)
			PLOG(FATAL, "socket");
		if (do_connect(flow, ai->ai_addr, ai->ai_addrlen))
			PLOG(FATAL, "do_connect");
		addflow(tid, epfd, flow, i);
	}
	events = calloc(flows_in_this_thread, sizeof(struct epoll_event));
	buf = calloc(flags.buffer_size, sizeof(char));
	pthread_barrier_wait(&worker_thread_ready_barrier);
	while (!stop) {
		nfds = epoll_wait(epfd, events, flows_in_this_thread, -1);
		if (nfds == -1) {
			if (errno == EINTR)
				continue;
			PLOG(FATAL, "epoll_wait");
		}
		stop = process_events(tid, epfd, events, nfds, stop_efd, -1,
				      NULL, &num_reads, buf, samples);
	}
	free(buf);
	free(events);
	do_close(epfd);
}

static void run_server(int tid, struct addrinfo *ai, int stop_efd,
		       struct sample_point **samples)
{
	int fd_listen, epfd, nfds, next_flow_id = 0, num_reads = 0, stop = 0;
	struct epoll_event *events;
	char *buf;

	fd_listen = socket(ai->ai_family, ai->ai_socktype, ai->ai_protocol);
	if (fd_listen == -1)
		PLOG(FATAL, "socket");
	set_reuseport(fd_listen);
	if (bind(fd_listen, ai->ai_addr, ai->ai_addrlen))
		PLOG(FATAL, "bind");
	if (listen(fd_listen, flags.num_flows))
		PLOG(FATAL, "listen");
	epfd = epoll_create(flags.num_flows);
	if (epfd == -1)
		PLOG(FATAL, "epoll_create");
	epoll_add_or_die(epfd, stop_efd, EPOLLIN);
	epoll_add_or_die(epfd, fd_listen, EPOLLIN);
	events = calloc(flags.num_flows, sizeof(struct epoll_event));
	buf = calloc(flags.buffer_size, sizeof(char));
	pthread_barrier_wait(&worker_thread_ready_barrier);
	while (!stop) {
		nfds = epoll_wait(epfd, events, flags.num_flows, -1);
		if (nfds == -1) {
			if (errno == EINTR)
				continue;
			PLOG(FATAL, "epoll_wait");
		}
		stop = process_events(tid, epfd, events, nfds, stop_efd,
				      fd_listen, &next_flow_id, &num_reads, buf,
				      samples);
	}
	free(buf);
	free(events);
	do_close(epfd);
}

struct thread_info {
	pthread_t thread_id;
	int thread_index;
	struct addrinfo *ai;
	int stop_efd;
	struct sample_point *samples;
};

static void *worker_thread(void *arg)
{
	struct thread_info *ti = arg;
	reset_port(ti->ai, atoi(flags.port));
	if (flags.client) {
		run_client(ti->thread_index, ti->ai, ti->stop_efd,
			   &ti->samples);
	} else {
		run_server(ti->thread_index, ti->ai, ti->stop_efd,
			   &ti->samples);
	}
	return NULL;
}

static int compare_sample_points(const void *a, const void *b)
{
	const struct sample_point *x = a;
	const struct sample_point *y = b;

	if (x->timestamp.tv_sec < y->timestamp.tv_sec)
		return -1;
	if (x->timestamp.tv_sec > y->timestamp.tv_sec)
		return 1;
	if (x->timestamp.tv_nsec < y->timestamp.tv_nsec)
		return -1;
	if (x->timestamp.tv_nsec > y->timestamp.tv_nsec)
		return 1;
	return 0;
}

static void report_stats(struct thread_info *tinfo)
{
	struct timespec *start_time;
	struct sample_point *p, *samples, *first_sample, *last_sample;
	int num_samples, i, j, tid, flow_id;
	ssize_t start_total, current_total, **per_flow;
	double duration, total_bytes, throughput, correlation_coefficient,
	       avg_xy, avg_xx, avg_yy, sum_xy = 0, sum_xx = 0, sum_yy = 0;

	num_samples = 0;
	for (i = 0; i < flags.num_threads; i++)
		for (p = tinfo[i].samples; p; p = p->next)
			num_samples++;
	if (num_samples == 0) {
		LOG(WARNING, "no sample collected");
		return;
	}
	samples = calloc(num_samples, sizeof(struct sample_point));
	j = 0;
	for (i = 0; i < flags.num_threads; i++)
		for (p = tinfo[i].samples; p; p = p->next)
			samples[j++] = *p;
	qsort(samples, num_samples, sizeof(samples[0]), compare_sample_points);
	if (flags.all_samples) {
		FILE *csv = fopen(flags.all_samples, "w");
		if (csv) {
			LOG(INFO, "successfully opened %s", flags.all_samples);
			print_sample(csv, NULL);
			for (j = 0; j < num_samples; j++)
				print_sample(csv, &samples[j]);
			if (fclose(csv))
				LOG(ERROR, "fclose: %s", strerror(errno));
		} else {
			LOG(ERROR, "fopen(%s): %s", flags.all_samples,
			    strerror(errno));
		}
	}
	print("num_samples", "%d", num_samples);
	if (num_samples < 2) {
		LOG(WARNING, "insufficient number of samples");
		return;
	}
	start_time = &samples[0].timestamp;
	start_total = samples[0].bytes_read;
	current_total = start_total;
	per_flow = calloc(flags.num_threads, sizeof(ssize_t *));
	for (i = 0; i < flags.num_threads; i++)
		per_flow[i] = calloc(flags.num_flows, sizeof(ssize_t));
	per_flow[samples[0].tid][samples[0].flow_id] = start_total;
	for (j = 1; j < num_samples; j++) {
		tid = samples[j].tid;
		flow_id = samples[j].flow_id;
		current_total -= per_flow[tid][flow_id];
		per_flow[tid][flow_id] = samples[j].bytes_read;
		current_total += per_flow[tid][flow_id];
		duration = seconds_between(start_time, &samples[j].timestamp);
		total_bytes = current_total - start_total;
		sum_xy += duration * total_bytes;
		sum_xx += duration * duration;
		sum_yy += total_bytes * total_bytes;
	}
	throughput = sum_xy / sum_xx;
	avg_xy = sum_xy / (num_samples - 1);
	avg_xx = sum_xx / (num_samples - 1);
	avg_yy = sum_yy / (num_samples - 1);
	correlation_coefficient = avg_xy / sqrt(avg_xx * avg_yy);
	print("throughput_Mbps", "%.2f", throughput * 8 / 1e6);
	print("correlation_coefficient", "%.2f", correlation_coefficient);
	for (i = 0; i < flags.num_threads; i++)
		free(per_flow[i]);
	free(per_flow);
	first_sample = &samples[0];
	last_sample = &samples[num_samples - 1];
	print("time_start", "%ld.%09ld", first_sample->timestamp.tv_sec,
	      first_sample->timestamp.tv_nsec);
	print("time_end", "%ld.%09ld", last_sample->timestamp.tv_sec,
	      last_sample->timestamp.tv_nsec);
	print("utime_start", "%ld.%06ld", first_sample->rusage.ru_utime.tv_sec,
	      first_sample->rusage.ru_utime.tv_usec);
	print("utime_end", "%ld.%06ld", last_sample->rusage.ru_utime.tv_sec,
	      last_sample->rusage.ru_utime.tv_usec);
	print("stime_start", "%ld.%06ld", first_sample->rusage.ru_stime.tv_sec,
	      first_sample->rusage.ru_stime.tv_usec);
	print("stime_end", "%ld.%06ld", last_sample->rusage.ru_stime.tv_sec,
	      last_sample->rusage.ru_stime.tv_usec);
	print("maxrss_start", "%ld", first_sample->rusage.ru_maxrss);
	print("maxrss_end", "%ld", last_sample->rusage.ru_maxrss);
	print("minflt_start", "%ld", first_sample->rusage.ru_minflt);
	print("minflt_end", "%ld", last_sample->rusage.ru_minflt);
	print("majflt_start", "%ld", first_sample->rusage.ru_majflt);
	print("majflt_end", "%ld", last_sample->rusage.ru_majflt);
	print("nvcsw_start", "%ld", first_sample->rusage.ru_nvcsw);
	print("nvcsw_end", "%ld", last_sample->rusage.ru_nvcsw);
	print("nivcsw_start", "%ld", first_sample->rusage.ru_nivcsw);
	print("nivcsw_end", "%ld", last_sample->rusage.ru_nivcsw);
	free(samples);
	print("invalid_secret_count", "%d", invalid_secret_count);
}

static void start_worker_threads(struct thread_info *tinfo, int num_cores,
				 const cpu_set_t *cpuset, struct addrinfo *ai)
{
	pthread_attr_t attr;
	int s, i;

	s = pthread_barrier_init(&worker_thread_ready_barrier, NULL,
				 flags.num_threads + 1);
	if (s != 0)
		LOG(FATAL, "pthread_barrier_init: %s", strerror(s));
	s = pthread_attr_init(&attr);
	if (s != 0)
		LOG(FATAL, "pthread_attr_init: %s", strerror(s));
	for (i = 0; i < flags.num_threads; i++) {
		tinfo[i].thread_index = i;
		tinfo[i].ai = copy_addrinfo(ai);
		tinfo[i].stop_efd = eventfd(0, 0);
		if (tinfo[i].stop_efd == -1)
			PLOG(FATAL, "eventfd");
		tinfo[i].samples = NULL;
		if (flags.pin_cpu) {
			s = pthread_attr_setaffinity_np(&attr,
							sizeof(cpu_set_t),
							&cpuset[i % num_cores]);
			if (s != 0) {
				LOG(FATAL, "pthread_attr_setaffinity_np: %s",
				    strerror(s));
			}
		}
		s = pthread_create(&tinfo[i].thread_id, &attr, &worker_thread,
				   &tinfo[i]);
		if (s != 0)
			LOG(FATAL, "pthread_create: %s", strerror(s));
	}
	s = pthread_attr_destroy(&attr);
	if (s != 0)
		LOG(FATAL, "pthread_attr_destroy: %s", strerror(s));
}

static void stop_worker_threads(struct thread_info *tinfo)
{
	int i, s;

	for (i = 0; i < flags.num_threads; i++)
		if (eventfd_write(tinfo[i].stop_efd, 1) == -1)
			LOG(FATAL, "eventfd_write returns -1");
	for (i = 0; i < flags.num_threads; i++) {
		s = pthread_join(tinfo[i].thread_id, NULL);
		if (s != 0)
			LOG(FATAL, "pthread_join: %s", strerror(s));
	}
	s = pthread_barrier_destroy(&worker_thread_ready_barrier);
	if (s != 0)
		LOG(FATAL, "pthread_barrier_destroy: %s", strerror(s));
}

static int get_cpuset(cpu_set_t *cpuset)
{
	int i, j, n, num_cores, physical_id[CPU_SETSIZE], core_id[CPU_SETSIZE];
	struct cpuinfo cpus[CPU_SETSIZE];

	n = get_cpuinfo(cpus, CPU_SETSIZE);
	if (n == -1)
		PLOG(FATAL, "get_cpuinfo");
	if (n == 0)
		LOG(FATAL, "no cpu found in /proc/cpuinfo");
	num_cores = 0;
	for (i = 0; i < n; i++) {
		LOG(INFO, "%d\t%d\t%d\t%d\t%d", cpus[i].processor,
		    cpus[i].physical_id, cpus[i].siblings, cpus[i].core_id,
		    cpus[i].cpu_cores);
		for (j = 0; j < num_cores; j++) {
			if (physical_id[j] == cpus[i].physical_id &&
			    core_id[j] == cpus[i].core_id)
				break;
		}
		if (j == num_cores) {
			num_cores++;
			CPU_ZERO(&cpuset[j]);
			core_id[j] = cpus[i].core_id;
			physical_id[j] = cpus[i].physical_id;
		}
		CPU_SET(cpus[i].processor, &cpuset[j]);
	}
	return num_cores;
}

static void run(void)
{
	int ctrl_conn, ctrl_port, i, num_cores;
	cpu_set_t cpuset[CPU_SETSIZE];
	struct thread_info *tinfo;
	struct addrinfo *ai;

	tinfo = calloc(flags.num_threads, sizeof(struct thread_info));
	if (flags.client) {
		ctrl_conn = ctrl_connect(flags.host, flags.control_port, &ai);
		LOG(INFO, "connected to control port");
	} else {
		ctrl_port = ctrl_listen(NULL, flags.control_port, &ai);
		LOG(INFO, "opened control port");
	}
	if (flags.pin_cpu)
		num_cores = get_cpuset(cpuset);
	start_worker_threads(tinfo, num_cores, cpuset, ai);
	LOG(INFO, "started worker threads");
	pthread_barrier_wait(&worker_thread_ready_barrier);
	LOG(INFO, "worker threads are ready");
	if (flags.client) {
		sleep(flags.test_length);
		LOG(INFO, "finished sleep");
	} else {
		ctrl_conn = ctrl_accept(ctrl_port);
		LOG(INFO, "established control connection");
		ctrl_wait_client(ctrl_conn);
		LOG(INFO, "received client notification");
		do_close(ctrl_conn);
		do_close(ctrl_port);
	}
	stop_worker_threads(tinfo);
	LOG(INFO, "stopped worker threads");
	if (flags.client) {
		ctrl_notify_server(ctrl_conn);
		LOG(INFO, "notified server to exit");
		do_close(ctrl_conn);
	}
	report_stats(tinfo);
	for (i = 0; i < flags.num_threads; i++)
		do_close(tinfo[i].stop_efd);
	free(tinfo);
}

static void print_flags(void)
{
	print("client", "%d", flags.client);
	print("num_threads", "%d", flags.num_threads);
	print("num_flows", "%d", flags.num_flows);
	print("host", "%s", flags.host ?: "");
	print("control_port", "%s", flags.control_port ?: "");
	print("port", "%s", flags.port ?: "");
	print("test_length", "%d", flags.test_length);
	print("buffer_size", "%d", flags.buffer_size);
	print("delay", "%lu", flags.delay);
	print("sample_rate", "%d", flags.sample_rate);
	print("all_samples", "%s", flags.all_samples ?: "");
	print("enable_write", "%d", flags.enable_write);
	print("enable_read", "%d", flags.enable_read);
	print("dry_run", "%d", flags.dry_run);
	print("pin_cpu", "%d", flags.pin_cpu);
	print("edge_trigger", "%d", flags.edge_trigger);
}

static void sanity_check_arguments(void)
{
	CHECK(flags.num_flows >= 1,
	      "There must be at least 1 flow.");
	CHECK(flags.num_threads >= 1,
	      "There must be at least 1 thread.");
	CHECK(flags.num_flows >= flags.num_threads,
	      "There should not be less flows than threads.");
	CHECK(flags.test_length >= 1,
	      "Test length must be at least 1 second.");
	CHECK(flags.buffer_size > 0,
	      "Buffer size must be positive.");
	CHECK(flags.sample_rate > 0,
	      "Sample rate must be positive.");
}

static int usage(void)
{
	puts("usage: tcp_stream [-A|--all-samples] [-B|--buffer-size=<n>]");
	puts("                  [-C|--control-port=<port>] [-D|--delay=<n>]");
	puts("                  [-E|--edge-trigger]");
	puts("                  [-F|--num-flows=<n>] [-H|--host=<addr>]");
	puts("                  [-P|--port=<port>] [-S|--sample-rate=<n>]");
	puts("                  [-T|--num-threads=<n>] [-U|--pin-cpu]");
	puts("                  [-c|--client] [-h|--help]");
	puts("                  [-l|--test-length=<n>] [-n|--dry-run]");
	puts("                  [-r|--enable-read] [-w|--enable-write]");
	return 1;
}

int main(int argc, char **argv)
{
	static struct option long_options[] = {
		{"all-samples",  optional_argument, 0, 'A'},
		{"buffer-size",  required_argument, 0, 'B'},
		{"control-port", required_argument, 0, 'C'},
		{"delay",        required_argument, 0, 'D'},
		{"edge-trigger", no_argument,       0, 'E'},
		{"num-flows",    required_argument, 0, 'F'},
		{"host",         required_argument, 0, 'H'},
		{"port",         required_argument, 0, 'P'},
		{"sample-rate",  required_argument, 0, 'S'},
		{"num-threads",  required_argument, 0, 'T'},
		{"pin-cpu",      no_argument,       0, 'U'},
		{"client",       no_argument,       0, 'c'},
		{"help",         no_argument,       0, 'h'},
		{"test-length",  required_argument, 0, 'l'},
		{"dry-run",      no_argument,       0, 'n'},
		{"enable-read",  no_argument,       0, 'r'},
		{"enable-write", no_argument,       0, 'w'},
		{0,              0,                 0,  0 }
	};
	int c, i;

	flags.control_port = "12866";
	flags.buffer_size = 16384;
	flags.all_samples = NULL;
	flags.sample_rate = 100;
	flags.edge_trigger = 0;
	flags.enable_write = 0;
	flags.test_length = 10;
	flags.enable_read = 0;
	flags.num_threads = 1;
	flags.port = "12867";
	flags.num_flows = 1;
	flags.host = NULL;
	flags.dry_run = 0;
	flags.pin_cpu = 0;
	flags.client = 0;
	flags.delay = 0;

	open_log();
	opterr = 0;
	while ((c = getopt_long(argc, argv, "A::B:C:D:EF:H:P:S:T:Uchl:nrw",
				long_options, NULL)) != -1) {
		switch (c) {
		case 'A':
			if (optarg)
				flags.all_samples = optarg;
			else
				flags.all_samples = "samples.csv";
			break;
		case 'B':
			flags.buffer_size = atoi(optarg);
			break;
		case 'C':
			flags.control_port = optarg;
			break;
		case 'D':
			flags.delay = strtoul(optarg, NULL, 0);
			prctl(PR_SET_TIMERSLACK, 1UL);
			break;
		case 'E':
			flags.edge_trigger = 1;
			break;
		case 'F':
			flags.num_flows = atoi(optarg);
			break;
		case 'H':
			flags.host = optarg;
			break;
		case 'P':
			flags.port = optarg;
			break;
		case 'S':
			flags.sample_rate = atoi(optarg);
			break;
		case 'T':
			flags.num_threads = atoi(optarg);
			break;
		case 'U':
			flags.pin_cpu = 1;
			break;
		case 'c':
			flags.client = 1;
			break;
		case 'h':
			return usage();
		case 'l':
			flags.test_length = atoi(optarg);
			break;
		case 'n':
			flags.dry_run = 1;
			break;
		case 'r':
			flags.enable_read = 1;
			break;
		case 'w':
			flags.enable_write = 1;
			break;
		case '?':
			LOG(WARNING, "Unknown option `-%c'.", optopt);
			return usage();
		default:
			abort();
		}
	}
	for (i = optind; i < argc; i++) {
		LOG(WARNING, "Non-option argument `%s'.", argv[i]);
		return usage();
	}

	if (flags.client)
		flags.enable_write = 1;
	else
		flags.enable_read = 1;

	print_flags();
	sanity_check_arguments();
	if (flags.dry_run)
		return 0;

	run();
	close_log();
	return 0;
}
