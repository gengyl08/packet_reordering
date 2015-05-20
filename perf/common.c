#include <ctype.h>
#include <fcntl.h>
#include <netinet/tcp.h>
#include <string.h>
#include <unistd.h>
#include "common.h"
#include "hexdump.h"

#ifndef SO_REUSEPORT
#define SO_REUSEPORT 15
#endif

void set_reuseport(int fd)
{
	int optval = 1;
	if (setsockopt(fd, SOL_SOCKET, SO_REUSEPORT, &optval, sizeof(optval)))
		PLOG(ERROR, "setsockopt(SO_REUSEPORT)");
}

void set_nonblocking(int fd)
{
	int flags = fcntl(fd, F_GETFL, 0);
	if (flags == -1)
		flags = 0;
	if (fcntl(fd, F_SETFL, flags | O_NONBLOCK) == -1)
		PLOG(FATAL, "fcntl");
}

int do_close(int fd)
{
	for (;;) {
		int ret = close(fd);
		if (ret == -1 && errno == EINTR)
			continue;
		return ret;
	}
}

int do_connect(int s, const struct sockaddr *addr, socklen_t addr_len)
{
	for (;;) {
		int ret = connect(s, addr, addr_len);
		if (ret == -1 && (errno == EINTR || errno == EALREADY))
			continue;
		if (ret == -1 && errno == EISCONN)
			return 0;
		return ret;
	}
}

struct addrinfo *copy_addrinfo(struct addrinfo *in)
{
	struct addrinfo *out = calloc(1, sizeof(struct addrinfo));
	out->ai_flags = in->ai_flags;
	out->ai_family = in->ai_family;
	out->ai_socktype = in->ai_socktype;
	out->ai_protocol = in->ai_protocol;
	out->ai_addrlen = in->ai_addrlen;
	out->ai_addr = malloc(in->ai_addrlen);
	memcpy(out->ai_addr, in->ai_addr, in->ai_addrlen);
	return out;
}

void reset_port(struct addrinfo *ai, int port)
{
	if (ai->ai_addr->sa_family == AF_INET)
		((struct sockaddr_in *)ai->ai_addr)->sin_port = htons(port);
	else if (ai->ai_addr->sa_family == AF_INET6)
		((struct sockaddr_in6 *)ai->ai_addr)->sin6_port = htons(port);
	else
		LOG(FATAL, "invalid sa_family %d", ai->ai_addr->sa_family);
}

static int try_connect(const char *host, const char *port, struct addrinfo **ai)
{
	struct addrinfo hints, *result, *rp;
	int s, sfd, allowed_retry = 30;

	memset(&hints, 0, sizeof(hints));
	hints.ai_family = AF_UNSPEC;      /* Allow IPv4 or IPv6 */
	hints.ai_socktype = SOCK_STREAM;  /* Stream socket */
	hints.ai_flags = 0;
	hints.ai_protocol = 0;            /* Any protocol */
	s = getaddrinfo(host, port, &hints, &result);
	if (s)
		LOG(FATAL, "getaddrinfo: %s", gai_strerror(s));
retry:
	/* getaddrinfo() returns a list of address structures.
	 * Try each address until we successfully connect().
	 */
	for (rp = result; rp != NULL; rp = rp->ai_next) {
		sfd = socket(rp->ai_family, rp->ai_socktype, rp->ai_protocol);
		if (sfd == -1) {
			if (errno == EMFILE || errno == ENFILE ||
			    errno == ENOBUFS || errno == ENOMEM)
				PLOG(FATAL, "socket");
			/* Other errno's are not fatal. */
			PLOG(ERROR, "socket");
			continue;
		}
		if (do_connect(sfd, rp->ai_addr, rp->ai_addrlen) == 0)
			break;
		PLOG(ERROR, "connect");
		do_close(sfd);
	}
	if (rp == NULL) {
		if (allowed_retry-- > 0) {
			sleep(1);
			goto retry;
		}
		LOG(FATAL, "Could not connect");
	}
	*ai = copy_addrinfo(rp);
	freeaddrinfo(result);
	return sfd;
}

static const char control_port_secret[] = "gperfnet control port secret";
#define SECRET_SIZE (sizeof(control_port_secret))

int ctrl_connect(const char *host, const char *port, struct addrinfo **ai)
{
	int ctrl_conn, optval = 1;
	ctrl_conn = try_connect(host, port, ai);
	if (setsockopt(ctrl_conn, IPPROTO_TCP, TCP_NODELAY, &optval,
		       sizeof(optval)))
		PLOG(ERROR, "setsockopt(TCP_NODELAY)");
	while (write(ctrl_conn, control_port_secret, SECRET_SIZE) == -1) {
		if (errno == EINTR)
			continue;
		PLOG(FATAL, "write");
	}
	return ctrl_conn;
}

int ctrl_listen(const char *host, const char *port, struct addrinfo **ai)
{
	struct addrinfo hints, *result, *rp;
	int s, fd_listen;

	memset(&hints, 0, sizeof(hints));
	hints.ai_family = AF_UNSPEC;      /* Allow IPv4 or IPv6 */
	hints.ai_socktype = SOCK_STREAM;  /* Stream socket */
	hints.ai_flags = AI_PASSIVE;      /* For wildcard IP address */
	hints.ai_protocol = 0;            /* Any protocol */
	s = getaddrinfo(host, port, &hints, &result);
	if (s)
		LOG(FATAL, "getaddrinfo: %s", gai_strerror(s));
	for (rp = result; rp != NULL; rp = rp->ai_next) {
		fd_listen = socket(rp->ai_family, rp->ai_socktype,
				   rp->ai_protocol);
		if (fd_listen == -1) {
			PLOG(ERROR, "socket");
			continue;
		}
		set_reuseport(fd_listen);
		if (bind(fd_listen, rp->ai_addr, rp->ai_addrlen) == 0)
			break;
		PLOG(ERROR, "bind");
		do_close(fd_listen);
	}
	if (rp == NULL)
		LOG(FATAL, "Could not bind");
	*ai = copy_addrinfo(rp);
	freeaddrinfo(result);
	if (listen(fd_listen, 10))
		PLOG(FATAL, "listen");
	return fd_listen;
}

int invalid_secret_count;

int ctrl_accept(int ctrl_port)
{
	char buf[1024], dump[8192], host[NI_MAXHOST], port[NI_MAXSERV];
	struct sockaddr_in cli_addr;
	socklen_t cli_len;
	int ctrl_conn, s;
	ssize_t len;
retry:
	cli_len = sizeof(struct sockaddr_in);
	while ((ctrl_conn = accept(ctrl_port, (struct sockaddr *)&cli_addr,
				   &cli_len)) == -1) {
		if (errno == EINTR || errno == ECONNABORTED)
			continue;
		PLOG(FATAL, "accept");
	}
	s = getnameinfo((struct sockaddr *)&cli_addr, cli_len,
			host, sizeof(host), port, sizeof(port),
			NI_NUMERICHOST | NI_NUMERICSERV);
	if (s) {
		LOG(ERROR, "getnameinfo: %s", gai_strerror(s));
		strcpy(host, "(unknown)");
		strcpy(port, "(unknown)");
	}
	memset(buf, 0, sizeof(buf));
	while ((len = read(ctrl_conn, buf, sizeof(buf))) == -1) {
		if (errno == EINTR)
			continue;
		PLOG(ERROR, "read");
		do_close(ctrl_conn);
		goto retry;
	}
	if (memcmp(buf, control_port_secret, SECRET_SIZE) != 0) {
		++invalid_secret_count;
		if (hexdump(buf, len, dump, sizeof(dump))) {
			LOG(WARNING, "Invalid secret from %s:%s\n%s", host,
			    port, dump);
		} else
			LOG(WARNING, "Invalid secret from %s:%s", host, port);
		do_close(ctrl_conn);
		goto retry;
	}
	return ctrl_conn;
}

void ctrl_wait_client(int ctrl_conn)
{
	char buf[1];
	while (read(ctrl_conn, buf, 1) == -1) {
		if (errno == EINTR)
			continue;
		PLOG(FATAL, "read");
	}
}

void ctrl_notify_server(int ctrl_conn)
{
	char buf[1];
	while (write(ctrl_conn, buf, 1) == -1) {
		if (errno == EINTR)
			continue;
		PLOG(FATAL, "write");
	}
	if (shutdown(ctrl_conn, SHUT_WR))
		PLOG(ERROR, "shutdown");
}
