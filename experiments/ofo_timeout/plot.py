import matplotlib.pyplot as plt
import math

ofo_timeout = None
tput = []

with open('measurements.txt', 'r') as f:
	lines = f.readlines()
	ofo_timeout = [float(line.split()[3]) / 1000 for line in lines[0:11]]
	for i in range(3):
		tput.append([float(line.split()[4]) * math.pow(2, 30) / 1e9 for line in lines[0+11*i:11+11*i]])

plt.subplot(3, 1, 1)
plt.plot(ofo_timeout, tput[0], 'bs-', lw=3, markersize=8)
plt.axvline(x=250, color='r', ls='--', lw=3)
plt.ylim(0, 11)
plt.xlabel('ofo_timeout (us)')
plt.ylabel('Throughput (Gb/s)')
plt.xticks(range(0, 1001, 100))
plt.grid(True)

plt.subplot(3, 1, 2)
plt.plot(ofo_timeout, tput[1], 'bs-', lw=3, markersize=8)
plt.axvline(x=500, color='r', ls='--', lw=3)
plt.ylim(0, 11)
plt.xlabel('ofo_timeout (us)')
plt.ylabel('Throughput (Gb/s)')
plt.xticks(range(0, 1001, 100))
plt.grid(True)

plt.subplot(3, 1, 3)
plt.plot(ofo_timeout, tput[2], 'bs-', lw=3, markersize=8)
plt.axvline(x=750, color='r', ls='--', lw=3)
plt.ylim(0, 11)
plt.xlabel('ofo_timeout (us)')
plt.ylabel('Throughput (Gb/s)')
plt.xticks(range(0, 1001, 100))
plt.grid(True)

plt.show()
#plt.plot(ofo_timeout, tput[0], 'bs-', ofo_timeout, tput[1], 'go--', ofo_timeout, tput[2], 'rD-.', lw=3, markersize=8)
