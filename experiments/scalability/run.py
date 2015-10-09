#!/usr/bin/env python

import subprocess
import time
import math

tors_sender = [1, 4]
tor_receiver = 9
servers = {}
for tor in tors_sender:
	with open('/usr/local/google/home/akabbani/yilong_files/bigmac{}servers'.format(tor), 'r') as f:
		servers[tor] = f.readline().split()

servers_all = None
with open('/usr/local/google/home/akabbani/yilong_files/multiflowservers_all', 'r') as f:
	servers_all = f.readline().split()

receiver = 'bigmac-9-2'
receiver_ip = '192.168.9.2'

#init_cmd_gkernel = 'chmod 777 /sys/class/net/eth*/plb_enable; echo 1 > /sys/class/net/eth0/plb_enable; echo 1 > /sys/class/net/eth1/plb_enable; echo 1 > /sys/class/net/eth2/plb_enable; chmod 444 /sys/class/net/eth*/plb_enable; cat /sys/class/net/*/plb_enable; sysctl -w net.ipv4.tcp_congestion_control=dctcp; sysctl -w net.ipv4.tcp_gcn=0; sysctl -w net.ipv4.tcp_ecn=1; /usr/local/bin/container.py run --update --network-max=10000 sys /bin/true; sysctl -w net.ipv4.tcp_recovery=0; service network glag-disable;'

#init_cmd_receiver = 'sysctl -w net.ipv4.tcp_congestion_control=dctcp; echo 13000 > /sys/class/net/eth0/gro_flush_timeout; echo 13000 > /sys/class/net/eth1/gro_flush_timeout; echo 100000 > /sys/class/net/eth0/gro_ofo_timeout; echo 100000 > /sys/class/net/eth1/gro_ofo_timeout; echo 20000 > /sys/class/net/eth0/gro_inseq_timeout; echo 20000 > /sys/class/net/eth1/gro_inseq_timeout; cat /sys/class/net/eth0/gro_flush_timeout; cat /sys/class/net/eth1/gro_flush_timeout; cat /sys/class/net/eth0/gro_ofo_timeout; cat /sys/class/net/eth1/gro_ofo_timeout; cat /sys/class/net/eth0/gro_inseq_timeout; cat /sys/class/net/eth1/gro_inseq_timeout; echo 000010 > /proc/irq/{irq[0]}/smp_affinity; echo 4 > /proc/irq/{irq[0]}/smp_affinity_list; echo 000020 > /proc/irq/{irq[1]}/smp_affinity; echo 5 > /proc/irq/{irq[1]}/smp_affinity_list; echo 000400 > /proc/irq/{irq[2]}/smp_affinity; echo 10 > /proc/irq/{irq[2]}/smp_affinity_list; echo 000800 > /proc/irq/{irq[3]}/smp_affinity; echo 11 > /proc/irq/{irq[3]}/smp_affinity_list; echo 010000 > /proc/irq/{irq[4]}/smp_affinity; echo 16 > /proc/irq/{irq[4]}/smp_affinity_list; echo 020000 > /proc/irq/{irq[5]}/smp_affinity; echo 17 > /proc/irq/{irq[5]}/smp_affinity_list; echo 400000 > /proc/irq/{irq[6]}/smp_affinity; echo 22 > /proc/irq/{irq[6]}/smp_affinity_list; echo 800000 > /proc/irq/{irq[7]}/smp_affinity; echo 23 > /proc/irq/{irq[7]}/smp_affinity_list;'

#netperf = '/usr/local/google/home/ygeng/nettools/netperf -T {receiver_cores[CORE]} -H {receiver} -l 9999 & '

init_cmd = 'echo 13000 > /sys/class/net/eth2/gro_flush_timeout; echo 15000 > /sys/class/net/eth2/gro_inseq_timeout; echo 50000 > /sys/class/net/eth2/gro_ofo_timeout; cat /sys/class/net/eth2/gro_flush_timeout; cat /sys/class/net/eth2/gro_inseq_timeout; cat /sys/class/net/eth2/gro_ofo_timeout;'

def init():
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(' '.join(servers_all)), init_cmd])

def killall_iperf():
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(' '.join(servers_all)), 'killall iperf'])


def start_background():
	receivers_background = []
	for tor in tors_sender:
		for i in range(2):
			receivers_background.append(servers[tor][i])

	p_background_receiver = subprocess.Popen(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d1', '-m {}'.format(' '.join(receivers_background)), 'killall iperf; sleep 1; /data/nettools/iperf -s'])
	
	time.sleep(10)

	p_background_senders = []
	for i in range(len(tors_sender)):
		j = (i + 1) % len(tors_sender)
		for k in range(2):
			sender_tmp = servers[tors_sender[i]][k+2]
			receiver_ip_tmp = '192.168.{}.{}'.format(tors_sender[j], servers[tors_sender[j]][k].split('-')[-1])
			p_tmp = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{0} /data/nettools/iperf -c {1} -i 1 -t 9999'.format(sender_tmp, receiver_ip_tmp).split())
			p_background_senders.append(p_tmp)
		

def measure(kernel, flow_num):

	print '>>>>>>>>>> Kill netperf'
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d1', '-m {}'.format(senders), 'killall netperf'])

        # googledist netperf to senders and receiver
        print '>>>>>>>>>> googledist netperf to senders and receiver'
        print subprocess.check_output(['runlocalssh', 'googledist', '-uroot', '-m {}'.format(senders), '/usr/local/google/home/ygeng/nettools'])
        print subprocess.check_output(['runlocalssh', 'googledist', '-uroot', '-m {}'.format(receiver), '/usr/local/google/home/ygeng/nettools'])


	print '>>>>>>>>>> Measuring with {} flows from {} senders'.format(flow_num * len(senders.split()), len(senders.split()))

	# get ip adress of sender and receiver
	print '>>>>>>>>>> Get IP addresses of sender and receiver'
	sender_ip = subprocess.check_output('runlocalssh googlesh -uroot -corp -d1 -m{0} grep {0} /etc/hosts'.format(senders.split()[0]).split()).split('\n')[1].split()[1]
	receiver_ip = subprocess.check_output('runlocalssh googlesh -uroot -corp -d1 -m{0} grep {0} /etc/hosts'.format(receiver).split()).split('\n')[1].split()[1]
	print sender_ip
	print receiver_ip

	# start receiver
	print '>>>>>>>>>> Start receiver'
	print subprocess.check_output('runlocalssh googlesh -uroot -corp -d1 -m{0} /usr/local/google/home/ygeng/nettools/netserver'.format(receiver).split())

	# start senders
	print '>>>>>>>>>> Start sender'
	netperfs = ''
	for i in range(flow_num):
		netperfs += netperf.replace('CORE', str(i))
	receiver_cores_circle = receiver_cores * int(math.ceil(flow_num * len(senders.split()) / float(16)))
	for i in range(len(senders.split())):
		print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d1', '-m {}'.format(senders.split()[i]), netperfs.format(receiver=receiver, receiver_cores=receiver_cores_circle[flow_num * i : flow_num * (i + 1)])])
	time.sleep(10)

	# measure receiver cpu
	print '>>>>>>>>>> Measure receiver cpu'
	receiver_cpu_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} mpstat -P ALL 60 1'.format(receiver).split(), stdout=subprocess.PIPE)

	# pull receiver's counters
	print '>>>>>>>>>> Measure receiver counters'
	receiver_counter_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} /usr/local/google/home/ygeng/nettools/receiver.py 60 1'.format(receiver).split(), stdout=subprocess.PIPE)

	# pull sender's counters
	print '>>>>>>>>>> Measure sender counters'
	sender_counter_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} /usr/local/google/home/ygeng/nettools/sender.py 60 1'.format(senders.split()[0]).split(), stdout=subprocess.PIPE)

	# wait for experiment to end
	cpu, err = receiver_cpu_thread.communicate()
	counters_receiver, err = receiver_counter_thread.communicate()
	counters_sender, err = sender_counter_thread.communicate()
	print '>>>>>>>>>> End measurement'

	# dump trace
	print '>>>>>>>>>> Start tcpdump'
	receiver_tcpdump_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} /usr/local/google/home/ygeng/nettools/tcpdump -s 128 -c 10000 -w /root/traces/multi_to_one_spray/{} host {}'.format(receiver, kernel + '_' + str(len(senders.split())) + '_' + str(flow_num), sender_ip).split())
	sender_tcpdump_thread = subprocess.Popen('runlocalssh googlesh -uroot -corp -d1 -m{} /usr/local/google/home/ygeng/nettools/tcpdump -s 128 -c 10000 -w /root/traces/multi_to_one_spray/{} host {}'.format(senders.split()[0], kernel + '_' + str(len(senders.split())) + '_' + str(flow_num), receiver_ip).split())
	receiver_tcpdump_thread.communicate()
	sender_tcpdump_thread.communicate()
	print '>>>>>>>>>> End tcpdump'

	print '>>>>>>>>>> Kill netperf'
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d1', '-m {}'.format(senders), 'killall netperf'])

	# calculate results
	print cpu
	print counters_receiver
	print counters_sender

	cpu_result = 100 * 24 - sum([float(x.split()[-2]) for x in cpu.split('\n')[-25:-1]])

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

	return cpu_result, InPkts_receiver, InSegs_receiver, batch_ratio, TCPOFOQueue_receiver, OutSegs_receiver, OutSegs_sender, RetransSegs_sender, TCPDSACKRecv_sender


def main():
	init()
	killall_iperf()
	start_background()
	time.sleep(120)

	"""
	# reset senders
	print '>>>>>>>>>> Reset senders'
	subprocess.call(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(senders), init_cmd_gkernel])
	
	# get irq numbers on receiver
	print '>>>>>>>>>> Get irq numbers on receiver'
	irq = subprocess.check_output('runlocalssh googlesh -uroot -corp -d0.1 -m{} cat /proc/interrupts | grep eth0'.format(receiver).split()).split('\n')
	if len(irq) < 3:
		irq = subprocess.check_output('runlocalssh googlesh -uroot -corp -d0.1 -m{} cat /proc/interrupts | grep eth1'.format(receiver).split()).split('\n')
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

	# enable spraying on senders
	print '>>>>>>>>>> Enable spraying on senders'
	subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(senders), 'sysctl -w net.ipv4.tcp_plb_enabled=4'])

        # create trace directory on senders and receivers
        print '>>>>>>>>>> Create trace directory and senders and receivers'
        print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(senders), 'mkdir -p /root/traces/multi_to_one_spray'])
        print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(receiver), 'mkdir -p /root/traces/multi_to_one_spray'])

	f = open('results', 'a')
	f.write(version + '\n')
	f.write('senders_num\tflow_num\tcpu\tInPkts_receiver\tInSegs_receiver\tbatch_ratio\tTCPOFOQueue_receiver\tOutSegs_receiver\tOutSegs_sender\tRetransSegs_sender\tTCPDSACKRecv_sender\n')
	for flow_num in [128]:
		cpu_result, InPkts_receiver, InSegs_receiver, batch_ratio, TCPOFOQueue_receiver, OutSegs_receiver, OutSegs_sender, RetransSegs_sender, TCPDSACKRecv_sender = measure(version, flow_num)
		f.write('{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(len(senders.split()), flow_num, cpu_result, InPkts_receiver, InSegs_receiver, batch_ratio, TCPOFOQueue_receiver, OutSegs_receiver, OutSegs_sender, RetransSegs_sender, TCPDSACKRecv_sender))

	f.close()
	"""


if __name__ == "__main__":
	main()
