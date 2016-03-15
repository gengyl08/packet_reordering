tmp = range(100)
q0 = [x * 5 for x in tmp]
q1 = [x * 5 + 1 for x in tmp]
q2 = [x * 5 + 2 for x in tmp]
q3 = [x * 5 + 3 for x in tmp]
q4 = [x * 5 + 4 for x in tmp]

q0 = [(x, x+0) for x in q0]
q1 = [(x, x+1) for x in q1]
q2 = [(x, x+2) for x in q2]
q3 = [(x, x+3) for x in q3]
q4 = [(x, x+9) for x in q4]

flow = q0 + q1 + q2 + q3 + q4
flow.sort(key=lambda tup: tup[1])
order = [x[0] for x in flow]
in_order = [1] * 500
for i in range(500):
	for j in range(order[i]):
		if j not in order[:i]:
			in_order[i] = 0
print order
print in_order