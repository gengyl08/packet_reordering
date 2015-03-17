obj-m += sender_drop.o
obj-m += sender_drop_queue.o
KDIR = /lib/modules/$(shell uname -r)/build
PWD = $(shell pwd)
all: clean compile rmmod insmod
compile:
	$(MAKE) -C $(KDIR) SUBDIRS=$(PWD) modules
clean:
	$(MAKE) -C $(KDIR) SUBDIRS=$(PWD) clean
insmod:
	sudo insmod sender_drop.ko
	sudo insmod sender_drop_queue.ko
rmmod:
	sudo rmmod sender_drop.ko
	sudo rmmod sender_drop_queue.ko
