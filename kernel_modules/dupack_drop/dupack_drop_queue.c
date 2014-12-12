#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/tcp.h>
#include <linux/netfilter.h>
#include <linux/netfilter_ipv4.h>
#include <net/netfilter/nf_queue.h>
#include <linux/byteorder/generic.h>

struct nf_queue_handler nfqh;

struct tcphdr *tcp_header;

__u32 ack_seq_old;
__u32 ack_seq_new;
struct nf_queue_entry *entry_saved;
unsigned dupack_count;

int dupack_drop_enqueue_packet(struct nf_queue_entry *entry, unsigned int queuenum)
{
  tcp_header = tcp_hdr(entry->skb);
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
  nf_register_queue_handler(&nfqh);
  return 0;
}

void cleanup_module(void)
{
  printk(KERN_INFO "unregister dupack_drop_queue\n");
  nf_unregister_queue_handler();
}
