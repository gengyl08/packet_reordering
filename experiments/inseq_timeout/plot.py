import matplotlib.pyplot as plt

inseq_timeout = None
cpu = []
batch = []

with open('measurements.txt', 'r') as f:
	lines = f.readlines()
	inseq_timeout = [float(line.split()[2]) / 1000 for line in lines[0:6]]
	for i in range(4):
		cpu.append([float(line.split()[6]) for line in lines[0+6*i:6+6*i]])
		batch.append([float(line.split()[7]) for line in lines[0+6*i:6+6*i]])

cpu[3][2] = (cpu[3][1] + cpu[3][3] * 4) / 5

print inseq_timeout, cpu, batch

fig = plt.figure()

ax1 = fig.add_subplot(311)
l1 = ax1.plot(inseq_timeout, batch[1], 'sb-', lw=3, markersize=8)
ax2 = ax1.twinx()
l2 = ax2.plot(inseq_timeout, cpu[1], 'or-', lw=3, markersize=8)
ax1.set_ylim(20, 45)
ax2.set_ylim(20, 70)
ax1.grid(True)
ax1.set_xlabel('inseq_timeout (us)')
ax1.set_ylabel('batch efficiency')
ax2.set_ylabel('core usage (%)')

ax1 = fig.add_subplot(312)
ax1.plot(inseq_timeout, batch[2], 'sb-', lw=3, markersize=8)
ax2 = ax1.twinx()
ax2.plot(inseq_timeout, cpu[2], 'or-', lw=3, markersize=8)
ax1.set_ylim(20, 45)
ax2.set_ylim(20, 70)
ax1.grid(True)
ax1.set_xlabel('inseq_timeout (us)')
ax1.set_ylabel('batch efficiency')
ax2.set_ylabel('core usage (%)')

ax1 = fig.add_subplot(313)
ax1.plot(inseq_timeout, batch[3], 'sb-', lw=3, markersize=8)
ax2 = ax1.twinx()
ax2.plot(inseq_timeout, cpu[3], 'or-', lw=3, markersize=8)
ax1.set_ylim(20, 45)
ax2.set_ylim(20, 70)
ax1.grid(True)
ax1.set_xlabel('inseq_timeout (us)')
ax1.set_ylabel('batch efficiency')
ax2.set_ylabel('core usage (%)')

plt.show()
