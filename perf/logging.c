#include "logging.h"
#include <errno.h>
#include <libgen.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/syscall.h>
#include <sys/utsname.h>
#include <time.h>
#include <unistd.h>

static int stdout_lines;
static FILE *log_file;

void print(const char *key, const char *value_fmt, ...)
{
	va_list argp;

	printf("%s=", key);
	va_start(argp, value_fmt);
	vprintf(value_fmt, argp);
	va_end(argp);
	printf("\n");
	fflush(stdout);
	++stdout_lines;
}

void open_log(void)
{
	char *hostname, *user_name, path[1024];
	struct utsname un;
	struct timespec ts;
	struct tm tm;

	uname(&un);
	hostname = un.nodename;
	if (!hostname)
		hostname = "_";
	user_name = getlogin();
	if (!user_name)
		user_name = "_";
	clock_gettime(CLOCK_REALTIME, &ts);
	localtime_r(&ts.tv_sec, &tm);
	snprintf(path, sizeof(path),
		 "%s.%s.%s.%04d%02d%02d-%02d%02d%02d.%d.log",
		 program_invocation_short_name, hostname, user_name,
		 1900 + tm.tm_year, 1 + tm.tm_mon, tm.tm_mday, tm.tm_hour,
		 tm.tm_min, tm.tm_sec, getpid());
	if (log_file)
		fclose(log_file);
	log_file = fopen(path, "w");
}

void close_log(void)
{
	if (log_file) {
		fclose(log_file);
		log_file = NULL;
	}
}

void logging(const char *file, int line, const char *func, enum LOG_LEVEL level,
	     const char *fmt, ...)
{
	char buf[4096], *msg, level_char, *path;
	int size, thread_id;
	struct timespec ts;
	struct tm tm;
	va_list argp;

	if (!log_file)
		return;
	va_start(argp, fmt);
	size = vsnprintf(buf, sizeof(buf), fmt, argp);
	if (size > sizeof(buf)) {
		msg = malloc(size);
		vsnprintf(msg, size, fmt, argp);
	} else
		msg = buf;
	va_end(argp);
	if (level == FATAL)
		level_char = 'F';
	else if (level == ERROR)
		level_char = 'E';
	else if (level == WARNING)
		level_char = 'W';
	else if (level == INFO)
		level_char = 'I';
	else
		level_char = ' ';
	clock_gettime(CLOCK_REALTIME, &ts);
	localtime_r(&ts.tv_sec, &tm);
	thread_id = syscall(SYS_gettid);
	if (thread_id == -1)
		thread_id = getpid();
	path = strdup(file);
	fprintf(log_file,
		"%c%02d%02d %02d:%02d:%02d.%06ld %3d %6d %s:%d] %s: %s\n",
		level_char, tm.tm_mon + 1, tm.tm_mday, tm.tm_hour, tm.tm_min,
		tm.tm_sec, ts.tv_nsec / 1000, stdout_lines, thread_id,
		basename(path), line, func, msg);
	free(path);
	/* TODO dump stack trace if FATAL */
	if (level == FATAL || level == ERROR)
		fprintf(stderr, "%s\n", msg);
	if (size > sizeof(buf))
		free(msg);
	if (level == FATAL || level == ERROR || level == WARNING)
		fflush(log_file);
	if (level == FATAL) {
		fclose(log_file);
		fflush(stdout);
		fflush(stderr);
		fcloseall();
		exit(1);
	}
}
