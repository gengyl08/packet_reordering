import matplotlib.pyplot as plt

f = open('tput_log', 'r')
lines = f.readlines()
f.close()

tput = [int(line.split()[-1]) for line in lines]
timestamp = [float(line.split()[-4][0:-1]) for line in lines]

span = 200
tput_filtered = [None] * len(tput)
for i in range(len(tput)):
	tput_filtered[i] = sum(tput[max(0, i-span) : min(len(tput), i+span)]) / float(len(tput[max(0, i-span) : min(len(tput), i+span)]))

plt.plot(timestamp, tput_filtered)
plt.axvline(x=248.507798, linewidth=2, color='r')
plt.show()
