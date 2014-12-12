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

__u32 ack_seq_old;
__u32 ack_seq_new;
struct nf_queue_entry *entry_saved;
unsigned dupack_count;

int dupack_drop_enqueue_packet(struct nf_queue_entry *entry, unsigned int queuenum)
{
  ip_header = (struct iphdr *)skb_network_header(entry->skb);
  tcp_header = (struct tcphdr *)((unsigned char *)ip_header + (((__u32)(ip_header->ihl))<<2));
  ack_seq_new = be32_to_cpu(tcp_header->ack_seq);

  if (tcp_header->syn) {
    ack_seq_old = ack_seq_new;
    dupack_count = 0;
    nf_reinject(entry, NF_ACCEPT);
    return 0;
  }

  if (ack_seq_new > ack_seq_old) {

    ack_seq_old = ack_seq_new;
    if (dupack_count == 1) {
      nf_reinject(entry_saved, NF_DROP);
    }
    dupack_count = 0;
    nf_reinject(entry, NF_ACCEPT);

  }
  else if (ack_seq_new == ack_seq_old) {
    if (dupack_count == 0) {
      entry_saved = entry;
      dupack_count = 1;
    }
    else if (dupack_count == 1) {
      nf_reinject(entry_saved, NF_ACCEPT);
      nf_reinject(entry, NF_ACCEPT);
      dupack_count = 2;
      printk(KERN_INFO "drop\n");
    }
    else {
      nf_reinject(entry, NF_ACCEPT);
    }
  }
  else {
    nf_reinject(entry, NF_ACCEPT);
  }
  return 0;
}

int init_module(void)
{
  printk(KERN_INFO "register dupack_drop_queue\n");
  nfqh.outfn = dupack_drop_enqueue_packet;
  nf_register_queue_handler(NFPROTO_IPV4, &nfqh);
  return 0;
}

void cleanup_module(void)
{
  printk(KERN_INFO "unregister dupack_drop_queue\n");
  nf_unregister_queue_handler(NFPROTO_IPV4, &nfqh);
}
