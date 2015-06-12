ifconfig eth0 192.168.0.1 mask 255.255.255.0
ifconfig eth1 192.168.1.1 mask 255.255.255.0
ifconfig eth2 192.168.2.1 mask 255.255.255.0
ifconfig eth3 192.168.3.1 mask 255.255.255.0
ifconfig eth5 192.168.5.1 mask 255.255.255.0
ifconfig eth6 192.168.6.1 mask 255.255.255.0
ifconfig eth7 192.168.7.1 mask 255.255.255.0

service irqbalance stop

intr0=$(cat /proc/interrupts | grep eth0-rx-0 | grep -oP '[0-9]+' | head -n 1)
intr1=$(cat /proc/interrupts | grep eth0-rx-1 | grep -oP '[0-9]+' | head -n 1)
intr2=$(cat /proc/interrupts | grep eth0-rx-2 | grep -oP '[0-9]+' | head -n 1)
intr3=$(cat /proc/interrupts | grep eth0-rx-3 | grep -oP '[0-9]+' | head -n 1)
intr4=$(cat /proc/interrupts | grep eth0-tx-0 | grep -oP '[0-9]+' | head -n 1)

echo 000001 > /proc/irq/$intr0/smp_affinity
echo 0 > /proc/irq/$intr0/smp_affinity_list
echo 000002 > /proc/irq/$intr1/smp_affinity
echo 1 > /proc/irq/$intr1/smp_affinity_list
echo 000004 > /proc/irq/$intr2/smp_affinity
echo 2 > /proc/irq/$intr2/smp_affinity_list
echo 000008 > /proc/irq/$intr3/smp_affinity
echo 3 > /proc/irq/$intr3/smp_affinity_list
echo 000010 > /proc/irq/$intr4/smp_affinity
echo 4 > /proc/irq/$intr4/smp_affinity_list

sysctl -w net.ipv4.tcp_congestion_control=reno
