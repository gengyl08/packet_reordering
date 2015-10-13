#!/usr/bin/env python

import subprocess
import time
import math

tors_sender = [1, 2, 3, 4, 7 ,8 ,9, 12]
tor_receiver = 5
servers = {}
for tor in tors_sender:
	with open('bigmac-{}-servers'.format(tor), 'r') as f:
		servers[tor] = f.readline().split()

servers_all = None
with open('bigmacservers_all', 'r') as f:
	servers_all = f.readline().split()

receiver = 'bigmac-5-4'
receiver_ip = '192.168.5.4'

init_cmd = 'echo 13000 > /sys/class/net/eth2/gro_flush_timeout; echo 15000 > /sys/class/net/eth2/gro_inseq_timeout; echo 50000 > /sys/class/net/eth2/gro_ofo_timeout; cat /sys/class/net/eth2/gro_flush_timeout; cat /sys/class/net/eth2/gro_inseq_timeout; cat /sys/class/net/eth2/gro_ofo_timeout; tc qdisc del root dev eth2; tc qdisc add dev eth2 root handle 1: htb default 12; tc class add dev eth2 parent 1: classid 1:1 htb rate {0}kbps ceil {0}kbps; tc class add dev eth2 parent 1:1 classid 1:10 htb rate {0}kbps ceil {0}kbps; tc filter add dev eth2 protocol ip parent 1:0 prio 1 u32 match ip dst 192.168.5.0/24 flowid 1:10;'.format(70000)

def init():
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(' '.join(servers_all)), init_cmd])

def killall_iperf():
	print subprocess.check_output(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(' '.join(servers_all)), 'killall iperf; sleep 2; killall iperf;'])
	time.sleep(2)

def start_background():
	receivers_background = []
	for tor in tors_sender:
		for i in range(2):
			receivers_background.append(servers[tor][i])

	p_background_receiver = subprocess.Popen(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(' '.join(receivers_background)), '/data/nettools/iperf -s'])
	
	time.sleep(10)

	p_background_senders = []
	for i in range(len(tors_sender)):
		j = (i + 1) % len(tors_sender)
		for k in range(2):
			sender_tmp = servers[tors_sender[i]][k+2]
			receiver_ip_tmp = '192.168.{}.{}'.format(tors_sender[j], servers[tors_sender[j]][k].split('-')[-1])
			p_tmp = subprocess.Popen('runlocalssh googlesh -uroot -corp -d0.1 -m{0} /data/nettools/iperf -c {1} -i 1 -t 9999'.format(sender_tmp, receiver_ip_tmp).split())
			p_background_senders.append(p_tmp)
	time.sleep(10)		


def start_traffic(flow_num):
	p_receivers = []
	for i in range(len(tors_sender)):
		p_tmp = subprocess.Popen('runlocalssh googlesh -uroot -corp -d0.1 -m{} taskset -c {} /data/nettools/iperf -s -p {}'.format(receiver, 24+i, 5001+i).split())
		p_receivers.append(p_tmp)
	time.sleep(10)

	p_senders = []
	for i in range(len(tors_sender)):
		p_tmp = subprocess.Popen(['runlocalssh', 'googlesh', '-uroot', '-corp', '-d0.1', '-m {}'.format(' '.join(servers[tors_sender[i]][0:8])),
			'/data/nettools/iperf -c {} -i 1 -t 9999 -p {} -P {}'.format(receiver_ip, 5001+i, flow_num)])
		p_senders.append(p_tmp)
	time.sleep(10)

def start_measurement():
	p_cpu = subprocess.Popen('runlocalssh googlesh -uroot -corp -d0.1 -m{} mpstat -P ALL 10 1'.format(receiver).split(), stdout=subprocess.PIPE)
	p_tput = subprocess.Popen('runlocalssh googlesh -uroot -corp -d0.1 -m{} sar -n DEV 10 1'.format(receiver).split(), stdout=subprocess.PIPE)

	cpu, err = p_cpu.communicate()
	tput, err = p_tput.communicate()
	cpu = 100 - float([line for line in cpu.split('\n') if 'all' in line][-1].split()[-2])
	tput = float([line for line in tput.split('\n') if 'eth2' in line][-1].split()[5]) * 8 * math.pow(2, 10)
	print cpu
	print tput

def main():
	init()
	killall_iperf()
	#start_background()
	start_traffic(1)
	time.sleep(120)
	killall_iperf()
	#start_measurement()

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
