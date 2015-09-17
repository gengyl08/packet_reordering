import matplotlib.pyplot as plt

f = open('tput_log_3', 'r')
lines = f.readlines()
f.close()

tput = [int(line.split()[-1]) for line in lines]
timestamp = [float(line.split()[-5][0:-1]) for line in lines]
thresh = [int(line.split()[-2]) for line in lines]

span = 200
tput_filtered = [None] * len(tput)
for i in range(len(tput)):
	tput_filtered[i] = sum(tput[max(0, i-span) : min(len(tput), i+span)]) / float(len(tput[max(0, i-span) : min(len(tput), i+span)]))

thresh_filtered = [None] * len(thresh)
for i in range(len(thresh)):
	thresh_filtered[i] = sum(thresh[max(0, i-span) : min(len(thresh), i+span)]) / float(len(thresh[max(0, i-span) : min(len(thresh), i+span)]))

plt.plot(timestamp, tput_filtered)
plt.axvline(x=2676.197458, linewidth=2, color='r')
plt.show()
