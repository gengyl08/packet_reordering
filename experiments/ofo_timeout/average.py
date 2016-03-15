f = open('measurements.txt', 'w')
fs = [None] * 5
for i in range(5):
	fs[i] = open('measurements_{}.txt'.format(i), 'r')

for i in range(33):
	line = [0] * 9
	for j in range(5):
		line_tmp = [float(x) for x in fs[j].readline().split()]
		line = [line[x] + line_tmp[x] for x in range(9)]
	line = [str(x / 5) for x in line]
	line = '\t'.join(line)
	f.write(line + '\n')

f.close()
for i in range(5):
	fs[i].close()
