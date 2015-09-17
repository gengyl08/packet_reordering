#!/usr/bin/env python

import subprocess
import time

sender = 'clha19'
receiver = 'clhc15'
sender_cross = 'clha20'
receiver_cross = 'clhc20'

init_cmd_gkernel = 'chmod 777 /sys/class/net/eth*/plb_enable; echo 1 > /sys/class/net/eth0/plb_enable; echo 1 > /sys/class/net/eth1/plb_enable; echo 1 > /sys/class/net/eth2/plb_enable; chmod 444 /sys/class/net/eth*/plb_enable; cat /sys/class/net/*/plb_enable; sysctl -w net.ipv4.tcp_congestion_control=reno; sysctl -w net.ipv4.tcp_gcn=0; /usr/local/bin/container.py run --update --network-max=10000 sys /bin/true'

init_cmd_receiver = 'sysctl -w net.ipv4.tcp_congestion_control=reno; echo 13000 > /sys/class/net/eth0/gro_flush_timeout; echo 13000 > /sys/class/net/eth1/gro_flush_timeout; echo 150000 > /sys/class/net/eth0/gro_ofo_timeout; echo 150000 > /sys/class/net/eth1/gro_ofo_timeout; cat /sys/class/net/eth0/gro_flush_timeout; cat /sys/class/net/eth1/gro_flush_timeout; cat /sys/class/net/eth0/gro_ofo_timeout; cat /sys/class/net/eth1/gro_ofo_timeout; echo 000040 > /proc/irq/{irq[0]}/smp_affinity; echo 6 > /proc/irq/{irq[0]}/smp_affinity_list; echo 000080 > /proc/irq/{irq[1]}/smp_affinity; echo 7 > /proc/irq/{irq[1]}/smp_affinity_list; echo 000100 > /proc/irq/{irq[2]}/smp_affinity; echo 8 > /proc/irq/{irq[2]}/smp_affinity_list; echo 000200 > /proc/irq/{irq[3]}/smp_affinity; echo 9 > /proc/irq/{irq[3]}/smp_affinity_list; echo 000400 > /proc/irq/{irq[4]}/smp_affinity; echo 10 > /proc/irq/{irq[4]}/smp_affinity_list; echo 000800 > /proc/irq/{irq[5]}/smp_affinity; echo 11 > /proc/irq/{irq[5]}/smp_affinity_list; echo 040000 > /proc/irq/{irq[6]}/smp_affinity; echo 18 > /proc/irq/{irq[6]}/smp_affinity_list; echo 080000 > /proc/irq/{irq[7]}/smp_affinity; echo 19 > /proc/irq/{irq[7]}/smp_affinity_list;'

def measure(kernel, cross_flow):

	print '>>>>>>>>>> Measuring with cross flow {}'.format(cross_flow)

	# get ip adress of sender and receiver
	print '>>>>>>>>>> Get IP addresses of sender and receiver'
	sender_ip = subprocess.check_output('runlocalssh googlesh -uroot -corp -d1 -m{0} grep {0} /etc/hosts'.format(sender).split()).split('\n')[1].split()[1]
	receiver_ip = subprocess.check_output('runlocalssh googlesh -uroot -corp -d1 -m{0} grep {0} /etc/hosts'.format(receiver).split()).split('\n')[1].split()[1]
	print sender_ip
	print receiver_ip

	# start cross flow
	if cross_flow != 0:
		print '>>>>>>>>>> Start cross flow'
		subprocess.check_output('runlocalssh googlesh -uroot -corp -d1 -m{} /usr/local/bin/container.py run --update --network-max={} sys /bin/true'.format(sender_cross, cross_flow).split())
		receiver_cross_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} killall iperf; /home/akabbani/nettools/iperf -s -i 1'.format(receiver_cross).split())
		time.sleep(1)
		sender_cross_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} killall iperf; /home/akabbani/nettools/iperf -c {} -i 1 -t 90'.format(sender_cross, receiver_cross).split(), stdout=subprocess.PIPE)
	
	# start receiver
	print '>>>>>>>>>> Start receiver'
	receiver_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} killall iperf; taskset -c 20 /home/akabbani/nettools/iperf -s -i 1'.format(receiver).split())
	time.sleep(5)

	# start sender
	print '>>>>>>>>>> Start sender'
	sender_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} killall iperf; /home/akabbani/nettools/iperf -c {} -i 1 -t 80'.format(sender, receiver).split(), stdout=subprocess.PIPE)
	time.sleep(10)

	# measure receiver cpu
	print '>>>>>>>>>> Measure receiver cpu'
	receiver_cpu_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} mpstat -P ALL 60 1'.format(receiver).split(), stdout=subprocess.PIPE)

	# pull receiver's counters
	print '>>>>>>>>>> Measure receiver counters'
	receiver_counter_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} /root/receiver.py 60 1'.format(receiver).split(), stdout=subprocess.PIPE)

	# pull sender's counters
	print '>>>>>>>>>> Measure sender counters'
	sender_counter_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} /root/sender.py 60 1'.format(sender).split(), stdout=subprocess.PIPE)

	# wait for experiment to end
	cpu, err = receiver_cpu_thread.communicate()
	counters_receiver, err = receiver_counter_thread.communicate()
	counters_sender, err = sender_counter_thread.communicate()
	print '>>>>>>>>>> End measurement'

	# dump trace
	print '>>>>>>>>>> Start tcpdump'
	receiver_tcpdump_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} /home/akabbani/nettools/tcpdump -s 128 -c 1000 -w /root/traces/single_flow/{} host {}'.format(receiver, kernel + '_' + str(cross_flow), sender_ip).split())
	sender_tcpdump_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} /home/akabbani/nettools/tcpdump -s 128 -c 1000 -w /root/traces/single_flow/{} host {}'.format(sender, kernel + '_' + str(cross_flow), receiver_ip).split())
	receiver_tcpdump_thread.communicate()
	sender_tcpdump_thread.communicate()
	print '>>>>>>>>>> End tcpdump'

	throughput, err = sender_thread.communicate()
	receiver_thread.communicate()

	throughput_cross = None
	if cross_flow != 0:
		throughput_cross, err = sender_cross_thread.communicate()
		receiver_cross_thread.communicate()

	# calculate results
	print throughput
	print throughput_cross
	print cpu
	print counters_receiver
	print counters_sender

	tmp = [float(x.split()[-2]) for x in throughput.split('\n')[-31:-1]]
	th_result = sum(tmp) / float(len(tmp))
	th_cross_result = 0
	if cross_flow != 0:
		tmp = [float(x.split()[-2]) for x in throughput_cross.split('\n')[-31:-1]]
		th_cross_result = sum(tmp) / float(len(tmp))
	cpu_result = 200 - sum([float(x.split()[-2]) for x in cpu.split('\n')[-3:-1]])

	InPkts_receiver = sum([int(x.split()[-1]) for x in counters_receiver.split('\n') if 'InPkts' in x]) / float(60)
	InSegs_receiver = sum([int(x.split()[-1]) for x in counters_receiver.split('\n') if 'InSegs' in x]) / float(60)
	OutSegs_receiver = sum([int(x.split()[-1]) for x in counters_receiver.split('\n') if 'OutSegs' in x]) / float(60)
	TCPOFOQueue_receiver = sum([int(x.split()[-1]) for x in counters_receiver.split('\n') if 'TCPOFOQueue' in x]) / float(60)
	batch_ratio = InPkts_receiver / InSegs_receiver

	OutSegs_sender = sum([int(x.split()[-1]) for x in counters_sender.split('\n') if 'OutSegs' in x]) / float(60)
	RetransSegs_sender = sum([int(x.split()[-1]) for x in counters_sender.split('\n') if 'RetransSegs' in x]) / float(60)
	TCPDSACKRecv_sender = sum([int(x.split()[-1]) for x in counters_sender.split('\n') if 'TCPDSACKRecv' in x]) / float(60)

	print th_result
	print th_cross_result
	print cpu_result
	print InPkts_receiver
	print InSegs_receiver
	print OutSegs_receiver
	print TCPOFOQueue_receiver
	print batch_ratio
	print OutSegs_sender
	print RetransSegs_sender
	print TCPDSACKRecv_sender

	return th_cross_result, th_result, cpu_result, InPkts_receiver, InSegs_receiver, batch_ratio, TCPOFOQueue_receiver, OutSegs_receiver, OutSegs_sender, RetransSegs_sender, TCPDSACKRecv_sender


def main():

	# reset sender, sender_cross and receiver_cross
	print '>>>>>>>>>> Reset sender, sender_cross and receiver_cross'
	subprocess.call(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {} {} {}'.format(sender, sender_cross, receiver_cross), init_cmd_gkernel])
	
	# get irq numbers on receiver
	print '>>>>>>>>>> Get irq numbers on receiver'
	irq = subprocess.check_output('runlocalssh googlesh -uroot -corp -d0.1 -mclhc15 cat /proc/interrupts | grep eth0'.split()).split('\n')
	if len(irq) < 3:
		irq = subprocess.check_output('runlocalssh googlesh -uroot -corp -d0.1 -mclhc15 cat /proc/interrupts | grep eth1'.split()).split('\n')
	irq_num = [None] * 8
	for line in irq:
		tokens = line.split()
		if len(tokens)!=0 and tokens[-1].startswith('eth'):
			irq_num[int(tokens[-1].split('-')[1])] = int(tokens[1].split(':')[0])
	
	# get receiver kernel version
	print '>>>>>>>>>> Get kernel version of receiver'
	version = subprocess.check_output('runlocalssh googlesh -uroot -corp -d0.1 -m{} uname -r'.format(receiver).split()).split('\n')[1].split()[1]
	print version
	is_gkernel = False
	if '3.11.10' in version:
		is_gkernel = True

	# reset receiver
	print '>>>>>>>>>> Reset receiver'
	if is_gkernel:
		subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m{}'.format(receiver), init_cmd_gkernel])
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m{}'.format(receiver), init_cmd_receiver.format(irq=irq_num)])

	# enable spraying on sender
	print '>>>>>>>>>> Enable spraying on sender'
	subprocess.check_output('runlocalssh googlesh -uroot -corp -d0.1 -m{} sysctl -w net.ipv4.tcp_plb_enabled=4'.format(sender).split())

	f = open('results', 'a')
	f.write(version + '\n')
	f.write('throughput_cross\tthroughput\tcpu\tInPkts_receiver\tInSegs_receiver\tbatch_ratio\tTCPOFOQueue_receiver\tOutSegs_receiver\tOutSegs_sender\tRetransSegs_sender\tTCPDSACKRecv_sender\n')
	for cross_flow in [0, 2000, 4000, 6000]:
		th_cross_result, th_result, cpu_result, InPkts_receiver, InSegs_receiver, batch_ratio, TCPOFOQueue_receiver, OutSegs_receiver, OutSegs_sender, RetransSegs_sender, TCPDSACKRecv_sender = measure(version, cross_flow)
		f.write('{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(th_cross_result, th_result, cpu_result, InPkts_receiver, InSegs_receiver, batch_ratio, TCPOFOQueue_receiver, OutSegs_receiver, OutSegs_sender, RetransSegs_sender, TCPDSACKRecv_sender))

	f.close()

if __name__ == "__main__":
	main()
