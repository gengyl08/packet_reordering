#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/netfilter.h>
#include <linux/netfilter_ipv4.h>
#include <net/netfilter/nf_queue.h>
#include <linux/byteorder/generic.h>
#include <linux/skbuff.h>

struct nf_queue_handler nfqh;

struct iphdr *ip_header;
struct tcphdr *tcp_header;
unsigned long loop_count;

int sender_drop_enqueue_packet(struct nf_queue_entry *entry, unsigned int queuenum)
{
  ip_header = (struct iphdr *)skb_network_header(entry->skb);
  tcp_header = (struct tcphdr *)((unsigned char *)ip_header + (((__u32)(ip_header->ihl))<<2));

  if (tcp_header->syn || tcp_header->fin) {
    loop_count = 0;
    nf_reinject(entry, NF_ACCEPT);
    return 0;
  }

  if (loop_count < 1) {
    nf_reinject(entry, NF_DROP);
  } else {
    nf_reinject(entry, NF_ACCEPT);
  }

  loop_count = (loop_count + 1) % 100;

  return 0;
}

int init_module(void)
{
  printk(KERN_INFO "register sender_drop_queue\n");
  loop_count = 0;
  nfqh.outfn = sender_drop_enqueue_packet;
  nf_register_queue_handler(&nfqh);
  return 0;
}

void cleanup_module(void)
{
  printk(KERN_INFO "unregister sender_drop_queue\n");
  nf_unregister_queue_handler();
}
