#! /usr/bin/env python2.7

import optparse
import time
import subprocess

parser = optparse.OptionParser()
(options, args) = parser.parse_args()

def stats():
	stats = dict()

	f = open('/proc/net/netstat', 'r')
	legends = f.readline().split()
	values = f.readline().split()
	f.close()
	stats['TCPOFOQueue'] = int(values[legends.index('TCPOFOQueue')])

	f = open('/proc/net/snmp', 'r')
	for i in range(6):
		f.readline()
	legends = f.readline().split()
	values = f.readline().split()
	f.close()
	stats['InSegs'] = int(values[legends.index('InSegs')])
	stats['OutSegs'] = int(values[legends.index('OutSegs')])

	f = open('/proc/net/dev', 'r')
	values = None
	for line in f:
		if 'eth0' in line:
			values = line.split()
			break;
	f.close()
	if values is None:
		print 'Cannot find eth0 in /proc/net/dev'
	else:
		stats['InPkts'] = int(values[2])
		stats['OutPkts'] = int(values[10])

	values = subprocess.check_output('ethtool -S eth1'.split())
	for line in values.split('\n'):
		if 'gro_complete:' in line:
			stats['gro_complete'] = int(line.split()[1])
		elif 'gro_overflows:' in line:
			stats['gro_overflows'] = int(line.split()[1])
		elif 'gro_nogro:' in line:
			stats['gro_nogro'] = int(line.split()[1])
		elif 'gro_msgs:' in line:
			stats['gro_msgs'] = int(line.split()[1])
		elif 'gro_segs:' in line:
			stats['gro_segs'] = int(line.split()[1])

	return stats

if __name__ == "__main__":

	args = [int(x) for x in args]

	if len(args) < 2:
		args = [1, 1]

	for i in range(args[1]):
		stats0 = stats()
		time.sleep(args[0])
		stats1 = stats()
		print '===================='
		for key in sorted(stats0.keys()):
			print key, stats1[key] - stats0[key]
