ifconfig eth0 192.168.0.1 mask 255.255.255.0
ifconfig eth1 192.168.1.1 mask 255.255.255.0
ifconfig eth2 192.168.2.1 mask 255.255.255.0
ifconfig eth3 192.168.3.1 mask 255.255.255.0
ifconfig eth5 192.168.5.1 mask 255.255.255.0
ifconfig eth6 192.168.6.1 mask 255.255.255.0
ifconfig eth7 192.168.7.1 mask 255.255.255.0

intr=$(cat /proc/interrupts | grep -m 1 eth0 | grep -oP '[0-9]+' | head -n 1)

echo 000001 > /proc/irq/$intr/smp_affinity
echo 000002 > /proc/irq/$[$intr+1]/smp_affinity
echo 000004 > /proc/irq/$[$intr+2]/smp_affinity
echo 000008 > /proc/irq/$[$intr+3]/smp_affinity
echo 000010 > /proc/irq/$[$intr+4]/smp_affinity
sysctl -w net.ipv4.tcp_congestion_control=reno
