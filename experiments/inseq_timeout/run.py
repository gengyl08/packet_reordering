#!/usr/bin/env python

import time
import subprocess

switch = 'gengyl08@nf3-test6.stanford.edu'
sender = 'gengyl08@chaos1.stanford.edu'
receiver = 'gengyl08@chaos2.stanford.edu'
receiver_root = 'root@chaos2.stanford.edu'
home = '/home/gengyl08/BalajiGroup/packet_reordering'

def measure(delay, flush_timeout, inseq_timeout, ofo_timeout):
    time.sleep(2)

    # configure switch
    subprocess.call('ssh -t {0} sudo python {1}/experiments/switch/config.py --delay 0 {2} 0 0 --splitRatio 1 1 0 0 --printDelay --printSplitRatio'.format(switch, home, delay).split())

    # configure receiver timeouts
    print subprocess.check_output('ssh {0} echo {1} > /sys/class/net/eth0/gro_flush_timeout; echo {2} > /sys/class/net/eth0/gro_inseq_timeout; echo {3} > /sys/class/net/eth0/gro_ofo_timeout; cat /sys/class/net/eth0/gro_flush_timeout; cat /sys/class/net/eth0/gro_inseq_timeout; cat /sys/class/net/eth0/gro_ofo_timeout;'.format(receiver_root, flush_timeout, inseq_timeout, ofo_timeout).split())

    # cleanup sender and receiver
    subprocess.call('ssh {0} killall iperf; sleep 1; killall iperf;'.format(sender).split())
    subprocess.call('ssh {0} killall iperf; sleep 1; killall iperf;'.format(receiver).split())
    time.sleep(2)

    # open iperf server on the receiver
    p_receiver = subprocess.Popen('ssh {0} taskset -c 2 iperf -s'.format(receiver).split(), stdout=subprocess.PIPE)
    time.sleep(5)
    # open iperf on the sender
    p_sender = subprocess.Popen('ssh {0} taskset -c 1 iperf -c 192.168.0.2 -i 1 -t 80 -f g'.format(sender).split(), stdout=subprocess.PIPE)
    
    # measure cpu utilization on the sender receiver
    time.sleep(5)
    p_cpu_sender = subprocess.Popen('ssh {0} mpstat -P ALL 60 1'.format(sender).split(), stdout=subprocess.PIPE)
    p_cpu_receiver = subprocess.Popen('ssh {0} mpstat -P ALL 60 1'.format(receiver).split(), stdout=subprocess.PIPE)
    p_stats_receiver = subprocess.Popen('ssh {0} python {1}/experiments_g/receiver/receiver.py 60 1'.format(receiver, home).split(), stdout=subprocess.PIPE)

    # wait for all senders to complete then kill receiver
    throughput, err = p_sender.communicate()

    cpu_util_sender, err_cpu = p_cpu_sender.communicate()
    cpu_util_receiver, err_cpu = p_cpu_receiver.communicate()
    stats_receiver, err = p_stats_receiver.communicate()

    p_receiver.kill()

    # print results
    print throughput
    print cpu_util_sender
    print cpu_util_receiver
    print stats_receiver

    # compute results
    result_th = sum([float(line.split()[-2]) for line in throughput.split('\n')[-61:-1]])
    result_th = result_th / 60

    result_cpu_sender = 100 - float(cpu_util_sender.split('\n')[5].split()[-1])

    result_cpu0 = 100 - float(cpu_util_receiver.split('\n')[5].split()[-1])
    result_cpu1 = 100 - float(cpu_util_receiver.split('\n')[6].split()[-1])
   
    inPkts = int(stats_receiver.split('\n')[1].split()[1])
    inSegs = int(stats_receiver.split('\n')[2].split()[1])
    outPkts = int(stats_receiver.split('\n')[3].split()[1])
    ofoPkts = int(stats_receiver.split('\n')[5].split()[1])
 
    print result_th, result_cpu_sender, result_cpu0, result_cpu1, inPkts, inSegs, outPkts, ofoPkts

    return result_th, result_cpu_sender, result_cpu0 + result_cpu1, float(inPkts) / inSegs, ofoPkts / 60


if __name__=="__main__":
    for i in range(5):
        f = open('measurements_{}.txt'.format(i), 'w')
        for delay in [0, 40000, 80000, 120000]:
            for inseq_timeout in [0, 20000, 40000, 60000, 80000, 100000]:
                result_th, result_cpu_sender, result_cpu_receiver, batching_efficiency, ofoPkts = measure(delay, 10000, inseq_timeout, 1000000)
                print result_th, result_cpu_sender, result_cpu_receiver, batching_efficiency, ofoPkts
                f.write('{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(delay, 10000, inseq_timeout, 1000000, result_th, result_cpu_sender, result_cpu_receiver, batching_efficiency, ofoPkts))
        f.close()
