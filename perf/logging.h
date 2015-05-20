#ifndef _GPERFNET_LOGGING_H
#define _GPERFNET_LOGGING_H

/* Print in key=value format to stdout and keep track of the line number.
 * Not thread-safe. */
void print(const char *key, const char *value_fmt, ...);

/* Open a file for logging. Must be called before LOG(). Not thread-safe.
 * Logs will be written to the filename
 *     <program name>.<hostname>.<user name>.<date>-<time>.<pid>.log
 * in the current working directory.
 */
void open_log(void);

/* Close the log file. Further LOG()s have no effect. Not thread-safe. */
void close_log(void);

enum LOG_LEVEL {
	/* Use for undesired and unexpected events, that the program cannot
	 * recover from. Use these whenever an event happens from which you
	 * actually want all servers to die and dump a stack trace. */
	FATAL,
	/* Use for undesired and unexpected events that the program can recover
	 * from. All ERRORs should be actionable - it should be appropriate to
	 * file a bug whenever an ERROR occurs in production. */
	ERROR,
	/* Use for undesired but relatively expected events, which may indicate
	 * a problem. For example, the server received a malformed query. */
	WARNING,
	/* Use for state changes or other major events, or to aid debugging. */
	INFO,
};

/* Generic logging function. Thread-safe. */
void logging(const char *file, int line, const char *func, enum LOG_LEVEL level,
	     const char *fmt, ...);

/* Log lines have this form:
 *     Lmmdd hh:mm:ss.uuuuuu nnn thrdid file:line] func: msg...
 * where the fields are defined as follows:
 *   L                A single character, representing the log level
 *   mm               The month (zero padded)
 *   dd               The day (zero padded)
 *   hh:mm:ss.uuuuuu  Time in hours, minutes and fractional seconds
 *   nnn              The number of lines in stdout (space padded)
 *   thrdid           The space-padded thread ID as returned by gettid()
 *   file             The file name
 *   line             The line number
 *   func             The calling function name
 *   msg              The user-supplied message
 */
#define LOG(level, fmt, args...) \
	logging(__FILE__, __LINE__, __func__, level, fmt , ##args)

#define PLOG(level, fmt, args...) \
	LOG(level, fmt ": %s" , ##args, strerror(errno))

#define CHECK(cond, fmt, args...) \
	do { if (cond); else LOG(FATAL, fmt , ##args); } while (0)

#endif
