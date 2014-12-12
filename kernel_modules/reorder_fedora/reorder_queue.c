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

__u32 seq_next;
__u32 seq;
__u32 length;
struct nf_queue_entry *entry_saved;
__u32 seq_saved;
__u32 length_saved;
bool has_reorder;

int reorder_queue_enqueue_packet(struct nf_queue_entry *entry, unsigned int queuenum)
{
  ip_header = (struct iphdr *)skb_network_header(entry->skb);
  tcp_header = (struct tcphdr *)((unsigned char *)ip_header + (((__u32)(ip_header->ihl))<<2));
  seq = be32_to_cpu(tcp_header->seq);
  length = (__u32)be16_to_cpu(ip_header->tot_len) - (((__u32)ip_header->ihl)<<2) - (((__u32)tcp_header->doff)<<2);

  if (tcp_header->syn) {
    seq_next = seq + 1;
    has_reorder = false;
    nf_reinject(entry, NF_ACCEPT);
    return 0;
  }

  if((__s32)(seq - seq_next) < 0) {
    nf_reinject(entry, NF_ACCEPT);
  }

  if(!has_reorder) {
    if (seq == seq_next) {
        seq_next = seq + length;
        nf_reinject(entry, NF_ACCEPT);
    }
    else {
        entry_saved = entry;
        seq_saved = seq;
        length_saved = length;
        has_reorder = true;
    }
  }
  else {
    if ((__s32)(seq + length - seq_saved - length_saved) < 0) {
      seq_next = seq_saved + length_saved;
    }
    else {
      seq_next = seq + length;
    }

    if ((__s32)(seq - seq_saved) < 0) {
      nf_reinject(entry, NF_ACCEPT);
      nf_reinject(entry_saved, NF_ACCEPT);
    }
    else {
      nf_reinject(entry_saved, NF_ACCEPT);
      nf_reinject(entry, NF_ACCEPT);
    }
    has_reorder = false;
  }

  return 0;
}

int init_module(void)
{
  printk(KERN_INFO "register reorder_queue\n");
  nfqh.outfn = reorder_queue_enqueue_packet;
  nf_register_queue_handler(NFPROTO_IPV4, &nfqh);
  return 0;
}

void cleanup_module(void)
{
  printk(KERN_INFO "unregister reorder_queue\n");
  nf_unregister_queue_handler(NFPROTO_IPV4, &nfqh);
}
