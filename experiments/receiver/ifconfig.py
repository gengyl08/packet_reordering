#!/usr/bin/env python

import subprocess

subprocess.call('ifconfig eth0 192.168.0.1 mask 255.255.255.0'.split())
subprocess.call('ifconfig eth1 192.168.1.1 mask 255.255.255.0'.split())
subprocess.call('ifconfig eth2 192.168.2.1 mask 255.255.255.0'.split())
subprocess.call('ifconfig eth3 192.168.3.1 mask 255.255.255.0'.split())
subprocess.call('ifconfig eth5 192.168.5.1 mask 255.255.255.0'.split())
subprocess.call('ifconfig eth6 192.168.6.1 mask 255.255.255.0'.split())
subprocess.call('ifconfig eth7 192.168.7.1 mask 255.255.255.0'.split())

intr = int(subprocess.check_output('grep -m 1 eth0 /proc/interrupts'.split()).split()[0][:-1])

subprocess.call('echo 000001 > /proc/irq/{}/smp_affinity'.format(intr).split())
subprocess.call('echo 000002 > /proc/irq/{}/smp_affinity'.format(intr+1).split())
subprocess.call('echo 000004 > /proc/irq/{}/smp_affinity'.format(intr+2).split())
subprocess.call('echo 000008 > /proc/irq/{}/smp_affinity'.format(intr+3).split())
subprocess.call('echo 000010 > /proc/irq/{}/smp_affinity'.format(intr+4).split())

subprocess.call('sysctl -w net.ipv4.tcp_congestion_control=reno')