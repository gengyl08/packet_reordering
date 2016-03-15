K = 5

f = open('measurements.txt', 'w')
fs = [None] * K
for i in range(K):
	fs[i] = open('measurements_{}.txt'.format(i), 'r')

for i in range(24):
	line = [0] * 9
	for j in range(K):
		line_tmp = [float(x) for x in fs[j].readline().split()]
		line = [line[x] + line_tmp[x] for x in range(9)]
	line = [str(x / K) for x in line]
	line = '\t'.join(line)
	f.write(line + '\n')

f.close()
for i in range(K):
	fs[i].close()
