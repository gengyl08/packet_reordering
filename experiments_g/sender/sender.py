#! /usr/bin/env python

import optparse
import time

parser = optparse.OptionParser()
(options, args) = parser.parse_args()

def stats():
	stats = dict()

	f = open('/proc/net/netstat', 'r')
	legends = f.readline().split()
	values = f.readline().split()
	f.close()
	stats['TCPDSACKRecv'] = int(values[legends.index('TCPDSACKRecv')])
	stats['TCPDSACKOfoRecv'] = int(values[legends.index('TCPDSACKOfoRecv')])

	f = open('/proc/net/snmp', 'r')
	for i in range(6):
		f.readline()
	legends = f.readline().split()
	values = f.readline().split()
	f.close()
	stats['InSegs'] = int(values[legends.index('InSegs')])
	stats['OutSegs'] = int(values[legends.index('OutSegs')])
	stats['RetransSegs'] = int(values[legends.index('RetransSegs')])

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
		for key in stats0:
			print key, stats1[key] - stats0[key]
