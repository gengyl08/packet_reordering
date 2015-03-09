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

struct nf_queue_entry *entry_saved;

int sender_reorder_enqueue_packet(struct nf_queue_entry *entry, unsigned int queuenum)
{
  ip_header = (struct iphdr *)skb_network_header(entry->skb);
  tcp_header = (struct tcphdr *)((unsigned char *)ip_header + (((__u32)(ip_header->ihl))<<2));

  if (tcp_header->syn || tcp_header->fin || tcp_header->urg || tcp_header->rst || tcp_header->psh) {
    if (entry_saved != NULL) {
      nf_reinject(entry_saved, NF_ACCEPT);
    }
    nf_reinject(entry, NF_ACCEPT);
    return 0;
  }

  if (entry_saved == NULL) {
    entry_saved = entry;
  } else {
    nf_reinject(entry, NF_ACCEPT);
    nf_reinject(entry_saved, NF_ACCEPT);
    entry_saved = NULL;
  }

  return 0;
}

int init_module(void)
{
  printk(KERN_INFO "register sender_reorder_queue\n");
  entry_saved = NULL;
  nfqh.outfn = sender_reorder_enqueue_packet;
  nf_register_queue_handler(NFPROTO_IPV4, &nfqh);
  return 0;
}

void cleanup_module(void)
{
  printk(KERN_INFO "unregister sender_reorder_queue\n");
  nf_unregister_queue_handler(NFPROTO_IPV4, &nfqh);
}
