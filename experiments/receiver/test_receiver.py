import subprocess
import argparse

interrupts_keys = ['interrupts']
ifconfig_keys = ['rx_packets', 'rx_segments', 'rx_errors', 'rx_dropped',
                 'tx_packets', 'tx_segments', 'tx_errors', 'tx_dropped']
prune_keys = ['pruned_from_rx_q_overrun', 'pruned_from_rx_q', 'dropped_from_out_of_order_q_overrun',
              'pkts_dropped_from_prequeue']
ack_keys = ['delayed_acks', 'further_delayed_acks', 'quick_ack_mode_activated']
receive_queue_keys = ['pkts_directly_queued_to_recvmsg_prequeue', 'pkts_received_from_backlog',
                      'pkts_received_from_prequeue']
header_prediction_keys = ['pkts_header_predicted', 'pkts_header_predicted_and_directly_queued_to_user']

parser = argparse.ArgumentParser(description='Argument Parser')
parser.add_argument('core', help='the core iperf runs on', type=int)
parser.add_argument('--lro_off', help='turn off large receive offload', action='store_true')

def read_stats():
    netstat = subprocess.check_output('netstat -s'.split())
    ifconfig = subprocess.check_output('ifconfig eth1'.split())
    interrupts = subprocess.check_output('grep eth1 /proc/interrupts'.split())

    result = {}
    # ifconfig
    lines = ifconfig.split('\n')
    result['rx_packets'] = int(lines[3].split()[1].split(':')[1])
    result['rx_errors'] = int(lines[3].split()[2].split(':')[1])
    result['rx_dropped'] = int(lines[3].split()[3].split(':')[1])
    result['tx_packets'] = int(lines[4].split()[1].split(':')[1])
    result['tx_errors'] = int(lines[4].split()[2].split(':')[1])
    result['tx_dropped'] = int(lines[4].split()[3].split(':')[1])

    # interrupts
    result['interrupts'] = int(interrupts.split()[1])

    # netstat
    lines = netstat.split('\n')
    for i in range(len(lines)):
        print i, lines[i]
    result['rx_segments'] = int(lines[35].split()[0])
    result['tx_segments'] = int(lines[36].split()[0])
    result['rx_segments_bad'] = int(lines[38].split()[0])
    result['pruned_from_rx_q_overrun'] = int(lines[49].split()[0])
    result['pruned_from_rx_q'] = int(lines[50].split()[0])
    result['dropped_from_out_of_order_q_overrun'] = int(lines[51].split()[0])
    result['delayed_acks'] = int(lines[55].split()[0])
    result['further_delayed_acks'] = int(lines[56].split()[0])
    result['quick_ack_mode_activated'] = int(lines[57].split()[5])
    result['pkts_directly_queued_to_recvmsg_prequeue'] = int(lines[60].split()[0])
    result['pkts_received_from_backlog'] = int(lines[61].split()[0])
    result['pkts_received_from_prequeue'] = int(lines[62].split()[0])
    result['pkts_dropped_from_prequeue'] = int(lines[63].split()[0])
    result['pkts_header_predicted'] = int(lines[64].split()[0])
    result['pkts_header_predicted_and_directly_queued_to_user'] = int(lines[65].split()[0])

    return result


if __name__=="__main__":

    args = parser.parse_args()

    if args.lro_off:
        subprocess.call('sudo ethtool -K eth1 lro off'.split())
        subprocess.call('sudo ethtool -K eth1 gro off'.split())
    else:
        subprocess.call('sudo ethtool -K eth1 lro on'.split())
        subprocess.call('sudo ethtool -K eth1 gro on'.split())

    #result1 = read_stats()

    p = subprocess.Popen(['taskset', '-c', str(args.core), 'iperf', '-s'], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(p.stdout.readline, b''):
        print line
        if 'Interval' in line:
            break
    p.kill()

    #result2 = read_stats()
    """
    print '========== Interrupts =========='
    for key in interrupts_keys:
        print result2[key] - result1[key], ' '.join(key.split('_'))

    print ''
    print '========== Ifconfig =========='
    for key in ifconfig_keys:
        print result2[key] - result1[key], ' '.join(key.split('_'))

    print ''
    print '========== ACKs =========='
    for key in ack_keys:
        print result2[key] - result1[key], ' '.join(key.split('_'))

    print ''
    print '========== Drops =========='
    for key in prune_keys:
        print result2[key] - result1[key], ' '.join(key.split('_'))

    print ''
    print '========== Receive Queues =========='
    for key in receive_queue_keys:
        print result2[key] - result1[key], ' '.join(key.split('_'))

    print ''
    print '========== Header Prediction =========='
    for key in header_prediction_keys:
        print result2[key] - result1[key], ' '.join(key.split('_'))
    """
