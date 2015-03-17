obj-m += sender_reorder.o
obj-m += sender_reorder_queue.o
KDIR = /lib/modules/$(shell uname -r)/build
PWD = $(shell pwd)
all: clean compile rmmod insmod
compile:
	$(MAKE) -C $(KDIR) SUBDIRS=$(PWD) modules
clean:
	$(MAKE) -C $(KDIR) SUBDIRS=$(PWD) clean
insmod:
	sudo insmod sender_reorder.ko
	sudo insmod sender_reorder_queue.ko
rmmod:
	sudo rmmod sender_reorder.ko
	sudo rmmod sender_reorder_queue.ko
