obj-m += dupack_drop.o
obj-m += dupack_drop_queue.o
KDIR = /lib/modules/$(shell uname -r)/build
PWD = $(shell pwd)
all:
	$(MAKE) -C $(KDIR) SUBDIRS=$(PWD) modules
clean:
	$(MAKE) -C $(KDIR) SUBDIRS=$(PWD) clean
insmod:
	sudo insmod dupack_drop.ko
	sudo insmod dupack_drop_queue.ko
rmmod:
	sudo rmmod dupack_drop.ko
	sudo rmmod dupack_drop_queue.ko
