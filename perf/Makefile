TARGETCFLAGS_tcp_stream.o := -D_GNU_SOURCE
TARGETCFLAGS_logging.o := -D_GNU_SOURCE

tcp_stream-objs := tcp_stream.o common.o hexdump.o logging.o cpuinfo.o

tcp_stream-ext-libs := -lm -lpthread -lrt

# Link statically so that it can run on vanilla/non-Google systems.
TARGETLOADLIBES_tcp_stream := -static $(tcp_stream-ext-libs)

targetprogs-y := tcp_stream

always := $(targetprogs-y)

clean-files := modules.order
