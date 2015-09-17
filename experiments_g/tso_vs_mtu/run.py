#!/usr/bin/env python

import subprocess
import time
import threading
import numpy

num_flows = 3
senders = 'clha1 clha2 clha3 clha4 clha5 clha6 clha7 clha8 clha9 clha10 clha11 clha12 clha13 clha14 clha15 clha16'
senders = ' '.join(senders.split()[0:num_flows])
receivers = 'clhc1 clhc2 clhc3 clhc4'
receivers = ' '.join(receivers.split()[0:num_flows])

sender_pinger = 'clha20'
receiver_pinger = 'clhc20'

init_cmd_gkernel = 'service assimilator restart; chmod 777 /sys/class/net/eth*/plb_enable; echo 1 > /sys/class/net/eth0/plb_enable; echo 1 > /sys/class/net/eth1/plb_enable; echo 1 > /sys/class/net/eth2/plb_enable; chmod 444 /sys/class/net/eth*/plb_enable; cat /sys/class/net/*/plb_enable; sysctl -w net.ipv4.tcp_congestion_control=reno; sysctl -w net.ipv4.tcp_gcn=0; /usr/local/bin/container.py run --update --network-max=8000 sys /bin/true; sysctl -w net.ipv4.tcp_ecn=0; sysctl -w net.ipv4.tcp_recovery=0; sysctl -w net.ipv4.tcp_cwnd_bound_mincwnd=1350; sysctl -w net.ipv4.tcp_max_reordering=1000; sysctl -w net.ipv4.tcp_reordering=900;'

init_cmd_receiver = 'sysctl -w net.ipv4.tcp_congestion_control=reno; echo 13000 > /sys/class/net/eth0/gro_flush_timeout; echo 13000 > /sys/class/net/eth1/gro_flush_timeout; echo 500000 > /sys/class/net/eth0/gro_ofo_timeout; echo 500000 > /sys/class/net/eth1/gro_ofo_timeout; cat /sys/class/net/eth0/gro_flush_timeout; cat /sys/class/net/eth1/gro_flush_timeout; cat /sys/class/net/eth0/gro_ofo_timeout; cat /sys/class/net/eth1/gro_ofo_timeout; echo 800000 > /proc/irq/{irq[0]}/smp_affinity; echo 23 > /proc/irq/{irq[0]}/smp_affinity_list; echo 800000 > /proc/irq/{irq[1]}/smp_affinity; echo 23 > /proc/irq/{irq[1]}/smp_affinity_list; echo 800000 > /proc/irq/{irq[2]}/smp_affinity; echo 23 > /proc/irq/{irq[2]}/smp_affinity_list; echo 800000 > /proc/irq/{irq[3]}/smp_affinity; echo 23 > /proc/irq/{irq[3]}/smp_affinity_list; echo 800000 > /proc/irq/{irq[4]}/smp_affinity; echo 23 > /proc/irq/{irq[4]}/smp_affinity_list; echo 800000 > /proc/irq/{irq[5]}/smp_affinity; echo 23 > /proc/irq/{irq[5]}/smp_affinity_list; echo 800000 > /proc/irq/{irq[6]}/smp_affinity; echo 23 > /proc/irq/{irq[6]}/smp_affinity_list; echo 800000 > /proc/irq/{irq[7]}/smp_affinity; echo 23 > /proc/irq/{irq[7]}/smp_affinity_list; sysctl -w net.ipv4.tcp_ecn=0;'

def measure(tso_segs):
	# killall iperf
	print '>>>>>>>>>> killall iperf'
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(senders), 'killall iperf'])
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(receivers), 'killall iperf'])
	time.sleep(5)

	# googledist iperf to sender and receivers
	print '>>>>>>>>>> googledist iperf to senders and receivers'
	print subprocess.check_output(['runlocalssh', 'googledist', '-uroot', '-m {}'.format(senders), '/usr/local/google/home/ygeng/nettools'])
	print subprocess.check_output(['runlocalssh', 'googledist', '-uroot', '-m {}'.format(receivers), '/usr/local/google/home/ygeng/nettools'])

	print '>>>>>>>>>> Measuring with tso_segs {}'.format(tso_segs)
	
	# configure tso_segs
	print '>>>>>>>>>> Configure number of segs per tso'
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(senders), 'sysctl -w net.ipv4.tcp_min_tso_segs={}'.format(tso_segs)])

	# start receivers
	print '>>>>>>>>>> Start receivers'
	receiver_thread = subprocess.Popen(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d1', '-m {}'.format(receivers), 'killall iperf; sleep 5; taskset -c 22 /usr/local/google/home/ygeng/nettools/iperf -s -i 1'])
	time.sleep(10)

	# start senders
	sender_threads = [None] * num_flows
	for i in range(num_flows):
		print '>>>>>>>>>> Start sender {}'.format(i)
		sender_threads[i] = subprocess.Popen(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d1', '-m {}'.format(senders.split()[i]), 'killall iperf; sleep 5; /usr/local/google/home/ygeng/nettools/iperf -c {} -t 100'.format(receivers.split()[i])])
	time.sleep(20)

	# measure receiver cpu
	print '>>>>>>>>>> Measure receiver cpu'
	receiver_cpu_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} mpstat -P ALL 60 1'.format(receivers.split()[0]).split(), stdout=subprocess.PIPE)

	# pull receiver's counters
	print '>>>>>>>>>> Measure receiver counters'
	receiver_counter_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} /usr/local/google/home/ygeng/nettools/receiver.py 60 1'.format(receivers.split()[0]).split(), stdout=subprocess.PIPE)

	# pull sender's counters
	print '>>>>>>>>>> Measure sender counters'
	sender_counter_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} /usr/local/google/home/ygeng/nettools/sender.py 60 1'.format(senders.split()[0]).split(), stdout=subprocess.PIPE)
	"""
	# start monitoring queue size
	print '>>>>>>>>>> Start monitoring queue size'
	qsize = subprocess.check_output('runlocalssh googlesh -uroot -corp -d0.1 -mju1u1t6.mtv99.net killall telnet; echo \'loop 500 \"sleep 0 100000; g OP_BUFFER_TOTAL_COUNT_CELL(0);\"; sleep 1; quit\' | nc -q100000 localhost 5020'.split())
	qsize = [int(x.split()[1].split('=')[1].split(':')[0], 16) for x in qsize.split('\n')[-1001:-2:2]]
	print qsize
	"""
	
	# start pinger
	print '>>>>>>>>>> Start pinger'
	rtt = subprocess.check_output('runlocalssh googlesh -uroot -corp -d0.1 -m{} ping -c 500 -i 0.1 {}'.format(sender_pinger, receiver_pinger).split())
	print '>>>>>>>>>> Pinger completes'
	print rtt
	

	# wait for experiment to end
	cpu, err = receiver_cpu_thread.communicate()
	counters_receiver, err = receiver_counter_thread.communicate()
	counters_sender, err = sender_counter_thread.communicate()
	print '>>>>>>>>>> End measurement'

	# dump trace
	print '>>>>>>>>>> Start tcpdump'
	receiver_tcpdump_threads = [None] * num_flows
	sender_tcpdump_threads = [None] * num_flows
	for i in range(num_flows):
		receiver_tcpdump_threads[i] = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} tcpdump -s 128 -c 1000 -w /root/traces/tso_vs_mtu/{} {}'.format(receivers.split()[i], str(tso_segs), senders.split()[i]).split())
		sender_tcpdump_threads[i] = subprocess.Popen(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d1', '-m {}'.format(senders.split()[i]), 'tcpdump -s 128 -c 1000 -w /root/traces/tso_vs_mtu/{} host {}'.format(str(tso_segs), receivers.split()[i])])

	for i in range(num_flows):
		receiver_tcpdump_threads[i].communicate()
		sender_tcpdump_threads[i].communicate()
	print '>>>>>>>>>> End tcpdump'

	for i in range(num_flows):
		sender_threads[i].communicate()
	receiver_thread.communicate()


	# calculate results
	print cpu
	print counters_receiver
	print counters_sender

	cpu_result = 200 - sum([float(x.split()[-2]) for x in cpu.split('\n')[-3:-1]])

	InPkts_receiver = sum([int(x.split()[-1]) for x in counters_receiver.split('\n') if 'InPkts' in x]) / float(60)
	InSegs_receiver = sum([int(x.split()[-1]) for x in counters_receiver.split('\n') if 'InSegs' in x]) / float(60)
	OutSegs_receiver = sum([int(x.split()[-1]) for x in counters_receiver.split('\n') if 'OutSegs' in x]) / float(60)
	TCPOFOQueue_receiver = sum([int(x.split()[-1]) for x in counters_receiver.split('\n') if 'TCPOFOQueue' in x]) / float(60)
	batch_ratio = InPkts_receiver / InSegs_receiver

	OutSegs_sender = sum([int(x.split()[-1]) for x in counters_sender.split('\n') if 'OutSegs' in x]) / float(60)
	RetransSegs_sender = sum([int(x.split()[-1]) for x in counters_sender.split('\n') if 'RetransSegs' in x]) / float(60)
	TCPDSACKRecv_sender = sum([int(x.split()[-1]) for x in counters_sender.split('\n') if 'TCPDSACKRecv' in x]) / float(60)

	print cpu_result
	print InPkts_receiver
	print InSegs_receiver
	print OutSegs_receiver
	print TCPOFOQueue_receiver
	print batch_ratio
	print OutSegs_sender
	print RetransSegs_sender
	print TCPDSACKRecv_sender

	
	rtt = [float(x.split()[-2].split('=')[-1]) for x in rtt.split('\n')[-505:-5]]
	rtt_min = min(rtt)
	rtt_max = max(rtt)
	rtt_mean = sum(rtt) / len(rtt)
	rtt_50 = numpy.percentile(rtt, 50)
	rtt_70 = numpy.percentile(rtt, 70)
	rtt_90 = numpy.percentile(rtt, 90)
	rtt_99 = numpy.percentile(rtt, 99)

	print rtt_min
	print rtt_max
	print rtt_mean
	print rtt_50
	print rtt_70
	print rtt_90
	print rtt_99

	#return rtt_min, rtt_max, rtt_mean, rtt_50, rtt_70, rtt_90, rtt_99
	"""
	q_min = min(qsize)
	q_max = max(qsize)
	q_mean = sum(qsize) / float(len(qsize))
	q_50 = numpy.percentile(qsize, 50)
	q_70 = numpy.percentile(qsize, 70)
	q_90 = numpy.percentile(qsize, 90)
	q_99 = numpy.percentile(qsize, 99)

	print q_min
	print q_max
	print q_mean
	print q_50
	print q_70
	print q_90
	print q_99
	"""
	return rtt_min, rtt_max, rtt_mean, rtt_50, rtt_70, rtt_90, rtt_99, cpu_result, InPkts_receiver, InSegs_receiver, OutSegs_receiver, TCPOFOQueue_receiver, batch_ratio, OutSegs_sender, RetransSegs_sender, TCPDSACKRecv_sender


def reset_receiver(i):
	# get irq numbers of receiver
	print '>>>>>>>>>> Get irq numbers of receiver {}'.format(i)
	irq = subprocess.check_output('runlocalssh googlesh -uroot -corp -d0.1 -m{} cat /proc/interrupts | grep eth0'.format(receivers.split()[i]).split()).split('\n')
	if len(irq) < 3:
		irq = subprocess.check_output('runlocalssh googlesh -uroot -corp -d0.1 -m{} cat /proc/interrupts | grep eth1'.format(receivers.split()[i]).split()).split('\n')
	irq_num = [None] * 8
	for line in irq:
		tokens = line.split()
		if len(tokens)!=0 and tokens[-1].startswith('eth'):
			irq_num[int(tokens[-1].split('-')[1])] = int(tokens[1].split(':')[0])
	print irq_num

	# get receiver kernel version
	print '>>>>>>>>>> Get kernel version of receiver'
	version = subprocess.check_output('runlocalssh googlesh -uroot -corp -d0.1 -m{} uname -r'.format(receivers.split()[i]).split()).split('\n')[1].split()[1]
	print version
	is_gkernel = False
	if '3.11.10' in version:
		is_gkernel = True

	# reset receiver
	print '>>>>>>>>>> Reset receiver'
	if is_gkernel:
		subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m{}'.format(receivers.split()[i]), init_cmd_gkernel])
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m{}'.format(receivers.split()[i]), init_cmd_receiver.format(irq=irq_num)])

def main():

	# reset senders, sender_pinger and receiver_pinger
	print '>>>>>>>>>> Reset senders, sender_pinger and receiver_pinger'
	subprocess.call(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {} {} {}'.format(senders, sender_pinger, receiver_pinger), init_cmd_gkernel])
	
	# reset receivers
	reset_receiver_threads = [None] * num_flows
	for i in range(num_flows):
		reset_receiver_threads[i] = threading.Thread(target=reset_receiver, args=(i,))
		reset_receiver_threads[i].start()

	for i in range(num_flows):
		reset_receiver_threads[i].join()

	# enable spraying on senders
	print '>>>>>>>>>> Enable spraying on sender'
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(senders), 'sysctl -w net.ipv4.tcp_plb_enabled=4'])

	# create trace directory on senders and receivers
	print '>>>>>>>>>> Create trace directory and senders and receivers'
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(senders), 'mkdir -p /root/traces/tso_vs_mtu'])
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(receivers), 'mkdir -p /root/traces/tso_vs_mtu'])


	f = open('results', 'a')
	f.write('num_flows\ttso_segs\trtt_min\trtt_max\trtt_mean\trtt_50\trtt_70\trtt_90\trtt_99\tcpu_result\tInPkts_receiver\tInSegs_receiver\tOutSegs_receiver\tTCPOFOQueue_receiver\tbatch_ratio\tOutSegs_sender\tRetransSegs_sender\tTCPDSACKRecv_sender\n')
	for tso_segs in [4]:
		rtt_min, rtt_max, rtt_mean, rtt_50, rtt_70, rtt_90, rtt_99, cpu_result, InPkts_receiver, InSegs_receiver, OutSegs_receiver, TCPOFOQueue_receiver, batch_ratio, OutSegs_sender, RetransSegs_sender, TCPDSACKRecv_sender = measure(tso_segs)
		f.write('{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(num_flows, tso_segs, rtt_min, rtt_max, rtt_mean, rtt_50, rtt_70, rtt_90, rtt_99, cpu_result, InPkts_receiver, InSegs_receiver, OutSegs_receiver, TCPOFOQueue_receiver, batch_ratio, OutSegs_sender, RetransSegs_sender, TCPDSACKRecv_sender))
	f.close()

if __name__ == "__main__":
	main()
