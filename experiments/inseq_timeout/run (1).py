#!/usr/bin/env python

import time
import subprocess

switch = 'gengyl08@nf3-test6.stanford.edu'
sender = 'gengyl08@chaos1.stanford.edu'
receiver = 'gengyl08@chaos2.stanford.edu'
home = '/home/gengyl08/BalajiGroup/packet_reordering'

def measure(delay):
    time.sleep(2)

    # configure switch
    subprocess.call('ssh -t {0} sudo python {1}/experiments/switch/config.py 1 --delay 0 {2} 0 0 --splitRatio 1 1 0 0 --printDelay --printSplitRatio'.format(switch, home, delay).split())

    # cleanup sender and receiver
    subprocess.call('ssh {0} killall iperf; sleep 1; killall iperf;'.format(sender).split())
    subprocess.call('ssh {0} killall iperf; sleep 1; killall iperf;'.format(receiver).split())

    # open iperf server on the receiver
    p_receiver = subprocess.Popen('ssh {0} taskset -c 2 iperf -s'.format(receiver).split(), stdout=subprocess.PIPE)

    # open iperf on the sender
    p_sender = subprocess.Popen('ssh {0} taskset -c 1 iperf -c 192.168.0.2 -i 1 -t 30 -f g'.format(sender, i).split(), stdout=subprocess.PIPE)
    
    # measure cpu utilization on the sender receiver
    time.sleep(5)
    p_cpu_sender = subprocess.Popen('ssh {0} mpstat -P ALL 10 1'.format(sender).split(), stdout=subprocess.PIPE)
    p_cpu_receiver = subprocess.Popen('ssh {0} mpstat -P ALL 10 1'.format(receiver).split(), stdout=subprocess.PIPE)

    # wait for all senders to complete then kill receiver
    throughput = [None] * flow_num
    err = [None] * flow_num
    for i in range(flow_num):
    	throughput[i], err[i] = p_sender[i].communicate()

    cpu_util_sender, err_cpu = p_cpu_sender.communicate()
    cpu_util_receiver, err_cpu = p_cpu_receiver.communicate()

    p_receiver.kill()

    # compute results
    result_th = 0
    for i in range(flow_num):
    	result_th += sum([float(line.split()[-2]) for line in throughput[i].split('\n')[-11:-1]])
    result_th = result_th / 10

    result_cpu_sender = 100 - sum([float(line.split()[-1]) for line in cpu_util_sender.split('\n')[4:4+flow_num]]) / flow_num

    result_cpu0 = 100 - float(cpu_util_receiver.split('\n')[4].split()[-1])
    result_cpu1 = 100 - float(cpu_util_receiver.split('\n')[5].split()[-1])
    
    return result_th, result_cpu_sender, result_cpu0, result_cpu1

def measure_perf(delay, split_ratio, drop_loop, drop_count, is_new_kernel, flow_num, mice_flows):
    time.sleep(2)

    # configure switch
    print '>>>>>>>>>> Configure Switch'
    subprocess.call('ssh -t {0} sudo python {1}/experiments/switch/config.py --delay {2[0]} {2[1]} {2[2]} {2[3]} --splitRatio {3[0]} {3[1]} {3[2]} {3[3]} --dropLoop {4[0]} {4[1]} {4[2]} {4[3]} --dropCount {5[0]} {5[1]} {5[2]} {5[3]} --printDelay --printSplitRatio'.format(switch, home, delay, split_ratio, drop_loop, drop_count).split())

    # configure old/new kernel on the receiver

    # get statistics before sending packets
    print '>>>>>>>>>> Get TX Packets on Receiver'
    tx_pkts_before = int(subprocess.check_output('ssh {0} ifconfig eth0'.format(receiver).split()).split('\n')[5].split()[1].split(':')[1])
    print '>>>>>>>>>> Get RX Packets on Receiver'
    rx_pkts_before = int(subprocess.check_output('ssh {0} ifconfig eth0'.format(receiver).split()).split('\n')[4].split()[1].split(':')[1])
    print '>>>>>>>>>> Get Segments Received on Receiver'
    segs_received_before = int(subprocess.check_output('ssh {0} netstat -s | grep -m 1 \'segments received\''.format(receiver).split()).split()[0])

    # open perf server on the receiver
    print '>>>>>>>>>> Open Perf on Receiver'
    p_receiver = subprocess.Popen('ssh {0} taskset -c 0 {1}/perf/tcp_stream -H 192.168.0.2 -F {2} -T {3}'.format(receiver, home, flow_num, 1).split(), stdout=subprocess.PIPE)

    # open flow_num of iperf flows on the sender
    print '>>>>>>>>>> Open Perf on Sender'
    p_sender = subprocess.Popen('ssh {0} taskset -c 0 {1}/perf/tcp_stream -c -l 20 -H 192.168.0.2 -F {2} -T {3}'.format(sender, home, flow_num, 1).split(), stdout=subprocess.PIPE)
    
    if mice_flows is not 0:
        # open mice flow receiver
        print '>>>>>>>>>> Open Mice Flow Receiver'
        mice_receiver = subprocess.Popen('ssh {0} python {1}/experiments/receiver/mice.py'.format(receiver, home).split())

        # open mice flow sender
        print '>>>>>>>>>> Open Mice Flow Sender'
        mice_sender = subprocess.Popen('ssh {0} python {1}/experiments/sender/mice.py --num {2}'.format(sender, home, mice_flows).split())


    # measure cpu utilization on the sender receiver
    """
    print '>>>>>>>>>> Sleep for 5 Seconds'
    time.sleep(5)
    print '>>>>>>>>>> Open Mpstat on Receiver'
    p_cpu_receiver = subprocess.Popen('ssh {0} mpstat -P ALL 10 1'.format(receiver).split(), stdout=subprocess.PIPE)
    print '>>>>>>>>>> Open Mpstat on Sender'
    p_cpu_sender = subprocess.Popen('ssh {0} mpstat -P ALL 10 1'.format(sender).split(), stdout=subprocess.PIPE)
    """
    
    print '>>>>>>>>>> Sleep for 10 Seconds'
    time.sleep(10)
    print '>>>>>>>>>> Open Top on Receiver'
    p_cpu_receiver = subprocess.Popen('ssh {0} top -n 1 -b | grep tcp_stream'.format(receiver).split(), stdout=subprocess.PIPE)
    print '>>>>>>>>>> Open Top on Sender'
    p_cpu_sender = subprocess.Popen('ssh {0} top -n 1 -b | grep tcp_stream'.format(sender).split(), stdout=subprocess.PIPE)


    # wait for all threads to complete
    print '>>>>>>>>>> Wait for ALL Processes to Finish'
    cpu_util_receiver, err_cpu = p_cpu_receiver.communicate()
    print '    >>>>>>>>>> Receiver Mpstat Finished'
    cpu_util_sender, err_cpu = p_cpu_sender.communicate()
    print '    >>>>>>>>>> Sender Mpstat Finished'
    p_sender.communicate()
    print '    >>>>>>>>>> Sender Perf Finished'
    throughput, err = p_receiver.communicate()
    print '    >>>>>>>>>> Receiver Perf Finished'
    print throughput

    # close mice flows
    if mice_flows is not 0:
        mice_sender.kill()
        mice_receiver.kill()

    # get statistics after sending packets
    print '>>>>>>>>>> Get TX Packets on Receiver'
    tx_pkts_after = int(subprocess.check_output('ssh {0} ifconfig eth0'.format(receiver).split()).split('\n')[5].split()[1].split(':')[1])
    print '>>>>>>>>>> Get RX Packets on Receiver'
    rx_pkts_after = int(subprocess.check_output('ssh {0} ifconfig eth0'.format(receiver).split()).split('\n')[4].split()[1].split(':')[1])
    print '>>>>>>>>>> Get Segments Received on Receiver'
    segs_received_after = int(subprocess.check_output('ssh {0} netstat -s | grep -m 1 \'segments received\''.format(receiver).split()).split()[0])

    # compute results
    result_th = float(throughput.split('\n')[17].split('=')[1])/1000
    #result_cpu_sender = 100 - float(cpu_util_sender.split('\n')[5].split()[-1])
    #result_cpu_sender_rx_irq = 100 - float(cpu_util_sender.split('\n')[4].split()[-1])
    #result_cpu_sender_tx_irq = 100 - float(cpu_util_sender.split('\n')[16].split()[-1])
    #result_cpu_receiver = 100 - float(cpu_util_receiver.split('\n')[5].split()[-1])
    #result_cpu_receiver_rx_irq = 100 - float(cpu_util_receiver.split('\n')[4].split()[-1])
    #result_cpu_receiver_tx_irq = 100 - float(cpu_util_receiver.split('\n')[16].split()[-1])
    result_cpu_sender = int(cpu_util_sender.split()[8])
    result_cpu_receiver = int(cpu_util_receiver.split()[8])
    result_segs_received = segs_received_after - segs_received_before
    result_rx_pkts = rx_pkts_after - rx_pkts_before
    result_tx_pkts = tx_pkts_after - tx_pkts_before

    print '>>>>>>>>>> Results:'
    print '    >>>>>>>>>> Throughput: ' + str(result_th)
    print '    >>>>>>>>>> Sender CPU: ' + str(result_cpu_sender)
    #print '    >>>>>>>>>> Sender RX IRQ CPU: ' + str(result_cpu_sender_rx_irq)
    #print '    >>>>>>>>>> Sender TX IRQ CPU: ' + str(result_cpu_sender_tx_irq)
    print '    >>>>>>>>>> Receiver CPU: ' + str(result_cpu_receiver)
    #print '    >>>>>>>>>> Receiver RX IRQ CPU: ' + str(result_cpu_receiver_rx_irq)
    #print '    >>>>>>>>>> Receiver TX IRQ CPU: ' + str(result_cpu_receiver_tx_irq)
    print '    >>>>>>>>>> Segments Received by Receiver: ' + str(result_segs_received)
    print '    >>>>>>>>>> Packets Received by Receiver: ' + str(result_rx_pkts)
    print '    >>>>>>>>>> Packets sent by Receiver: ' + str(result_tx_pkts)
    
    return result_th, result_cpu_sender, result_cpu_receiver, result_segs_received, result_rx_pkts, result_tx_pkts

if __name__=="__main__":
    delay = [0, 1600, 0, 0]
    split_ratio = [1, 1, 0, 0]
    drop_loop = [0, 0, 0, 0]
    drop_count = [0, 0, 0, 0]
    f = open('measurements.txt', 'w')
    for flow_num in [1, 2, 4, 8, 16, 32, 48, 64, 128, 256, 512, 1000]:
        result_th, result_cpu_sender, result_cpu_receiver, result_segs_received, result_rx_pkts, result_tx_pkts = measure_perf(delay, split_ratio, drop_loop, drop_count, True, flow_num, 10)
        f.write('{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(flow_num, result_th, result_cpu_sender, result_cpu_receiver, result_segs_received, result_rx_pkts, result_tx_pkts))
    f.close()

    """
    drop_count = [1, 1, 1, 1]
    delay = [0, 1600, 3200, 6400]
    split_ratio = [1, 1, 1, 1]
    flow_num = 1
    f = open('measurements.txt', 'w')
    for drop_loop in [100, 1000, 10000, 100000, 1000000]:
        result_th, result_cpu_sender, result_cpu_receiver, result_segs_received, result_rx_pkts, result_tx_pkts = measure_perf(delay, split_ratio, [drop_loop, drop_loop, drop_loop, drop_loop], drop_count, True, flow_num)
        f.write('{}\t{}\t{}\t{}\t{}\t{}\t{}\n'.format(flow_num, result_th, result_cpu_sender, result_cpu_receiver, result_segs_received, result_rx_pkts, result_tx_pkts))
    f.close()
    """
