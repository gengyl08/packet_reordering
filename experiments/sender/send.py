#!/usr/bin/env python

import subprocess
import argparse

interrupt_keys = ['eth0-rx', 'eth0-tx']

ifconfig_keys = ['rx_packets', 'rx_errors', 'rx_dropped', 'rx_bytes',
                 'tx_packets', 'tx_errors', 'tx_dropped', 'tx_bytes']

segment_keys = {'segments received', 'segments send out', 'segments retransmited', 'bad segments received'}

tcpExt_keys = []

parser = argparse.ArgumentParser(description='Argument Parser')
parser.add_argument('core', help='the core iperf runs on', type=int)
parser.add_argument('offload', help='turn on/off various TCP offloads', type=bool)

def read_stats():
    ifconfig_str = subprocess.Popen('ifconfig eth0'.split(), stdout=subprocess.PIPE).communicate()[0]
    netstat_str = subprocess.Popen('netstat -s'.split(), stdout=subprocess.PIPE).communicate()[0]
    tcpExt_str = subprocess.Popen('cat /proc/net/netstat'.split(), stdout=subprocess.PIPE).communicate()[0]

    result = {}

    # interrupt
    result['eth0-rx'] = int(subprocess.Popen('cat /proc/interrupts | grep eth0-rx'.split(), stdout=subprocess.PIPE).communicate()[0].split()[1])
    result['eth0-tx'] = int(subprocess.Popen('cat /proc/interrupts | grep eth0-tx'.split(), stdout=subprocess.PIPE).communicate()[0].split()[1])

    # ifconfig
    lines = ifconfig_str.split('\n')
    result['rx_packets'] = int(lines[4].split()[1].split(':')[1])
    result['rx_errors'] = int(lines[4].split()[2].split(':')[1])
    result['rx_dropped'] = int(lines[4].split()[3].split(':')[1])
    result['tx_packets'] = int(lines[5].split()[1].split(':')[1])
    result['tx_errors'] = int(lines[5].split()[2].split(':')[1])
    result['tx_dropped'] = int(lines[5].split()[3].split(':')[1])
    result['rx_bytes'] = int(lines[7].split()[1].split(':')[1])
    result['tx_bytes'] = int(lines[7].split()[5].split(':')[1])

    # tcp segments
    for line in netstat_str.split('\n'):
    	for key in segment_keys:
    		if line.find(key) >= 0:
    			result[key] = int(line.split()[0])
    			break;

    # netstat
    tcpExt_keys = tcpExt_str.split('\n')[0].split()[1:]
    tcpExt_values = [int(x) for x in tcpExt_str.split('\n')[1].split()[1:]]
    for i in range(len(tcpExt_keys)):
    	result[tcpExt_keys[i]] = tcpExt_values[i]

    return result


if __name__=="__main__":

    args = parser.parse_args()

    if args.offload:
    	subprocess.call('sudo ethtool -K eth0 tso on'.split())
        subprocess.call('sudo ethtool -K eth0 gso on'.split())
        subprocess.call('sudo ethtool -K eth0 gro on'.split())
    else:
        subprocess.call('sudo ethtool -K eth0 tso off'.split())
        subprocess.call('sudo ethtool -K eth0 gso off'.split())
        subprocess.call('sudo ethtool -K eth0 gro off'.split())

    result1 = read_stats()

    subprocess.call(['taskset', '-c', str(args.core), 'iperf', '-c', '192.168.0.2', '-i', '1'], stdout=subprocess.STDOUT, stderr=subprocess.STDOUT)


    result2 = read_stats()
    
    print '========== Interrupts =========='
    for key in interrupt_keys:
        print result2[key] - result1[key], key

    print ''
    print '========== Ifconfig =========='
    for key in ifconfig_keys:
        print result2[key] - result1[key], key
    
    print ''
    print '========== TCP =========='
    for key in segment_keys:
        print result2[key] - result1[key], key

    print ''
    print '========== TcpExt =========='
    for key in TcpExt_keys:
        print result2[key] - result1[key], key
    
