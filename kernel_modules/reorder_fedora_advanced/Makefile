obj-m += reorder.o
obj-m += reorder_queue.o
KDIR = /lib/modules/$(shell uname -r)/build
PWD = $(shell pwd)
all: clean compile rmmod insmod
compile:
	$(MAKE) -C $(KDIR) SUBDIRS=$(PWD) modules
clean:
	$(MAKE) -C $(KDIR) SUBDIRS=$(PWD) clean
insmod:
	sudo insmod reorder.ko
	sudo insmod reorder_queue.ko
rmmod:
	sudo rmmod reorder.ko
	sudo rmmod reorder_queue.ko
