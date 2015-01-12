re='^[0-9]+$'
if ! [[ $1 =~ $re ]] ; then
    echo "error: Max Queue Num must be an integer"
    exit 1
fi

#seg_retrans0=$(netstat -s | grep 'segments retransmit' | grep -oP '[0-9]+')
#lost_retrans0=$(netstat -s | grep 'TCPLostRetransmit' | grep -oP '[0-9]+')
#fast_retrans0=$(netstat -s | grep 'fast retransmit' | grep -oP '[0-9]+')
#forward_retrans0=$(netstat -s | grep 'forward retransmit' | grep -oP '[0-9]+')
#transit_timeout0=$(netstat -s | grep 'timeout in transit' | grep -oP '[0-9]+')
#tcp_other_timeout0=$(netstat -s | grep 'other TCP timeouts' | grep -oP '[0-9]+')

sudo python config.py $1 --resetDrop --printQueueNum --printDelay
iperf -c 192.168.10.2 -i 1 -t 10

#seg_retrans1=$(netstat -s | grep 'segments retransmit' | grep -oP '[0-9]+')
#lost_retrans1=$(netstat -s | grep 'TCPLostRetransmit' | grep -oP '[0-9]+')
#fast_retrans1=$(netstat -s | grep 'fast retransmit' | grep -oP '[0-9]+')
#forward_retrans1=$(netstat -s | grep 'forward retransmit' | grep -oP '[0-9]+')
#transit_timeout1=$(netstat -s | grep 'timeout in transit' | grep -oP '[0-9]+')
#tcp_other_timeout1=$(netstat -s | grep 'other TCP timeouts' | grep -oP '[0-9]+')

sudo python config.py $1 --printDrop

#echo $[$seg_retrans1-$seg_retrans0] 'segments retransmited'
#echo $[$lost_retrans1-$lost_retrans0] 'TCPLostRetransmit'
#echo $[$fast_retrans1-$fast_retrans0] 'fast retransmits'
#echo $[$forward_retrans1-$forward_retrans0] 'forward retransmits'
#echo $[$transit_timeout1-$transit_timeout0] 'timeout in transit'
#echo $[$tcp_other_timeout1-$tcp_other_timeout0] 'other TCP timeouts'
