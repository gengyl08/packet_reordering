#ifndef _GPERFNET_COMMON_H
#define _GPERFNET_COMMON_H

#include <errno.h>
#include <netdb.h>
#include <stdlib.h>
#include <string.h>
#include <sys/epoll.h>
#include <sys/socket.h>
#include <time.h>
#include "logging.h"

static inline void epoll_ctl_or_die(int epfd, int op, int fd,
				    struct epoll_event *ev)
{
	if (epoll_ctl(epfd, op, fd, ev))
		PLOG(FATAL, "epoll_ctl");
}

static inline void epoll_del_or_err(int epfd, int fd)
{
	if (epoll_ctl(epfd, EPOLL_CTL_DEL, fd, NULL))
		PLOG(ERROR, "epoll_ctl");
}

static inline double seconds_between(struct timespec *a, struct timespec *b)
{
	return (b->tv_sec - a->tv_sec) + (b->tv_nsec - a->tv_nsec) * 1e-9;
}

static inline int flows_in_thread(int num_flows, int num_threads, int tid)
{
	const int min_flows_per_thread = num_flows / num_threads;
	const int remaining_flows = num_flows % num_threads;
	const int flows_in_this_thread = tid < remaining_flows ?
					 min_flows_per_thread + 1 :
					 min_flows_per_thread;
	return flows_in_this_thread;
}

void set_reuseport(int fd);
void set_nonblocking(int fd);
int do_close(int fd);
int do_connect(int s, const struct sockaddr *addr, socklen_t addr_len);
struct addrinfo *copy_addrinfo(struct addrinfo *in);
void reset_port(struct addrinfo *ai, int port);
int ctrl_connect(const char *host, const char *port, struct addrinfo **ai);
int ctrl_listen(const char *host, const char *port, struct addrinfo **ai);
extern int invalid_secret_count;
int ctrl_accept(int ctrl_port);
void ctrl_wait_client(int ctrl_conn);
void ctrl_notify_server(int ctrl_conn);

#endif
