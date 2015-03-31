#!/usr/bin/env python

import time
import subprocess

switch = 'gengyl08@nf3-test6.stanford.edu'
sender = 'gengyl08@chaos1.stanford.edu'
receiver = 'gengyl08@chaos2.stanford.edu'
home = '/home/gengyl08/BalajiGroup/packet_reordering/experiments'

def measure(delay, drop_loop, drop_count, is_new_kernel, flow_num):
	# configure switch
    subprocess.call('ssh -t {0} sudo python {1}/switch/config.py 1 --delay 0 {2} 0 0 0 --dropLoop {3} {3} 0 0 0 --dropCount {4} {4} 0 0 0 --printQueueNum --printDelay'.format(switch, home, delay, drop_loop, drop_count).split())

    # configure old/new kernel on the receiver
    
    # open iperf server on the receiver
    subprocess.call('ssh {0} killall iperf'.format(receiver).split())
    p_receiver = subprocess.Popen('ssh {0} taskset -c 1 iperf -s'.format(receiver).split(), stdout=subprocess.PIPE)

    # open flow_num of iperf flows on the sender
    p_sender = [None] * flow_num
    for i in range(flow_num):
    	p_sender[i] = subprocess.Popen('ssh {0} taskset -c {1} iperf -c 192.168.0.2 -i 1 -t 30 -f g'.format(sender, i).split(), stdout=subprocess.PIPE)
    
    # measure cpu utilization on the receiver
    time.sleep(5)
    p_cpu = subprocess.Popen('ssh {0} mpstat -P ALL 20 1'.format(receiver).split(), stdout=subprocess.PIPE)

    # wait for all senders to complete then kill receiver
    throughput = [None] * flow_num
    err = [None] * flow_num
    for i in range(flow_num):
    	throughput[i], err[i] = p_sender[i].communicate()

    cpu_util, err_cpu = p_cpu.communicate()

    p_receiver.kill()

    # compute results
    result_th = 0
    for i in range(flow_num):
    	result_th += sum([float(line.split()[-2]) for line in throughput[i].split('\n')[-21:-1]])
    result_th = result_th / 20

    result_cpu0 = 100 - float(cpu_util.split('\n')[4].split()[-1])
    result_cpu1 = 100 - float(cpu_util.split('\n')[5].split()[-1])
    
    return result_th, result_cpu0, result_cpu1

if __name__=="__main__":
	f = open('measurements.txt', 'w')
	for flow_num in range(1, 5):
		for drop_loop in [0, 100, 1000, 10000, 100000, 1000000]:
			for delay in [1600*x for x in [0, 1, 4, 8, 10]]:
				th, cpu0, cpu1 = measure(delay, drop_loop, int(drop_loop!=0), True, flow_num)
				f.write('%d %d %d %f %f %f\n' % (flow_num, drop_loop, delay, th, cpu0, cpu1))
	f.close()
