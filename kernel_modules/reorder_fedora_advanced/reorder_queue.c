#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/netfilter.h>
#include <linux/netfilter_ipv4.h>
#include <net/netfilter/nf_queue.h>
#include <linux/byteorder/generic.h>
#include <linux/skbuff.h>
#include <linux/spinlock.h>
#include <linux/slab.h>
#include <linux/hrtimer.h>
#include <linux/ktime.h>

#define MAX_REORDER_COUNT 10
#define REORDER_QUEUE_TIMEOUT 1E6

struct nf_queue_handler nfqh;

struct iphdr *ip_header;
struct tcphdr *tcp_header;

__u32 seq;
__u32 length;
__u32 seq_next_tmp;

struct nf_queue_entry_node {
  struct nf_queue_entry *entry;
  __u32 seq;
  __u32 seq_next;
  struct nf_queue_entry_node *prev;
  struct nf_queue_entry_node *next;
};

spinlock_t reorder_queue_lock;
unsigned long reorder_queue_lock_flags;
struct nf_queue_entry_node *reorder_queue_head = NULL;
struct nf_queue_entry_node *reorder_queue_tail = NULL;
unsigned reorder_count = 0;
__u32 seq_next = 0;

struct hrtimer hr_timer;
ktime_t ktime;

void flush_reorder_queue(struct nf_queue_entry_node *stop) {
  struct nf_queue_entry_node *tmp;

  while (reorder_queue_head!=stop && reorder_queue_head != NULL) {
    nf_reinject(reorder_queue_head->entry, NF_ACCEPT);
    seq_next = reorder_queue_head->seq_next;
    tmp = reorder_queue_head;
    reorder_queue_head = reorder_queue_head->next;
    kfree(tmp);
    reorder_count--;
  }

  if (reorder_queue_head == NULL) {
    reorder_queue_tail = NULL;
  }
}

enum hrtimer_restart hrtimer_callback(struct hrtimer *timer) {

  spin_lock_irqsave(&reorder_queue_lock, reorder_queue_lock_flags);

  flush_reorder_queue(NULL);

  spin_unlock_irqrestore(&reorder_queue_lock, reorder_queue_lock_flags);
  return HRTIMER_NORESTART;
}

int reorder_queue_enqueue_packet(struct nf_queue_entry *entry, unsigned int queuenum)
{

  struct nf_queue_entry_node *node_tmp;
  struct nf_queue_entry_node *node_tmp1;

  ip_header = (struct iphdr *)skb_network_header(entry->skb);
  tcp_header = (struct tcphdr *)((unsigned char *)ip_header + (((__u32)(ip_header->ihl))<<2));
  seq = be32_to_cpu(tcp_header->seq);
  length = (__u32)be16_to_cpu(ip_header->tot_len) - (((__u32)ip_header->ihl)<<2) - (((__u32)tcp_header->doff)<<2);
  seq_next_tmp = seq + length;
  //nf_reinject(entry, NF_ACCEPT);
  //printk(KERN_INFO "seq: %u\n", seq);
  //printk(KERN_INFO "len: %u\n", length);

  //hrtimer_cancel(&hr_timer);
  hrtimer_start(&hr_timer, ktime, HRTIMER_MODE_REL);

  spin_lock_irqsave(&reorder_queue_lock, reorder_queue_lock_flags);

  if (tcp_header->syn) {
    flush_reorder_queue(NULL);
    seq_next = seq + 1;
    nf_reinject(entry, NF_ACCEPT);
    //printk(KERN_INFO "syn\n");
    spin_unlock_irqrestore(&reorder_queue_lock, reorder_queue_lock_flags);
    return 0;
  }

  if (length == 0) {
    flush_reorder_queue(NULL);
    if ((__s32)(seq_next - seq_next_tmp) < 0) {
      seq_next = seq_next_tmp;
    }
    nf_reinject(entry, NF_ACCEPT);
    //printk(KERN_INFO "fin\n");
    spin_unlock_irqrestore(&reorder_queue_lock, reorder_queue_lock_flags);
    return 0;
  }

  if((__s32)(seq_next_tmp - seq_next) <= 0) {

    //printk(KERN_INFO "lost\n");
    nf_reinject(entry, NF_ACCEPT);

  } else if ((__s32)(seq - seq_next) <= 0) {

    nf_reinject(entry, NF_ACCEPT);
    seq_next = seq_next_tmp;

    while (reorder_queue_head != NULL && (__s32)(reorder_queue_head->seq - seq_next) <= 0) {
      if ((__s32)(seq_next - reorder_queue_head->seq_next) < 0) {
        seq_next = reorder_queue_head->seq_next;
      }
      nf_reinject(reorder_queue_head->entry, NF_ACCEPT);
      node_tmp = reorder_queue_head;
      reorder_queue_head = reorder_queue_head->next;
      kfree(node_tmp);
      reorder_count--;
    }

    if (reorder_queue_head == NULL) {
      reorder_queue_tail = NULL;
    }

  } else {

    if (reorder_count > MAX_REORDER_COUNT) {
      flush_reorder_queue(NULL);
      nf_reinject(entry, NF_ACCEPT);
      if ((__s32)(seq_next - seq_next_tmp) < 0) {
        seq_next = seq_next_tmp;
      }
    } else {

      if (reorder_queue_head == NULL) {

        reorder_queue_head = kmalloc(sizeof(struct nf_queue_entry_node), GFP_ATOMIC);
        reorder_queue_tail = reorder_queue_head;
        reorder_count = 1;
        reorder_queue_head->entry = entry;
        reorder_queue_head->seq = seq;
        reorder_queue_head->seq_next = seq_next_tmp;
        reorder_queue_head->prev = NULL;
        reorder_queue_head->next = NULL;

      } else {

        node_tmp = reorder_queue_head;
        while (node_tmp != NULL) {
          if ((__s32)(seq_next_tmp - node_tmp->seq) <= 0) {
            break;
          } else {
            node_tmp = node_tmp->next;
          }
        } 

        if (node_tmp == NULL) {
          if ((__s32)(seq - reorder_queue_tail->seq_next) < 0) {
            flush_reorder_queue(NULL);
            nf_reinject(entry, NF_ACCEPT);
            if ((__s32)(seq_next - seq_next_tmp) < 0) {
              seq_next = seq_next_tmp;
            }
          } else {  
            node_tmp1 = kmalloc(sizeof(struct nf_queue_entry_node), GFP_ATOMIC);
            node_tmp1->entry = entry;
            node_tmp1->seq = seq;
            node_tmp1->seq_next =seq_next_tmp;
            node_tmp1->prev = reorder_queue_tail;
            node_tmp1->next = NULL;

            reorder_queue_tail->next = node_tmp1;

            reorder_queue_tail = node_tmp1;
            reorder_count++;
          }
        } else {
          if (node_tmp->prev == NULL) {
            node_tmp1 = kmalloc(sizeof(struct nf_queue_entry_node), GFP_ATOMIC);
            node_tmp1->entry = entry;
            node_tmp1->seq = seq;
            node_tmp1->seq_next =seq_next_tmp;
            node_tmp1->prev = NULL;
            node_tmp1->next = reorder_queue_head;

            reorder_queue_head->prev = node_tmp1;

            reorder_queue_head = node_tmp1;
            reorder_count++;
          } else {
            if ((__s32)(seq - node_tmp->prev->seq_next) < 0) {
              flush_reorder_queue(node_tmp);
              nf_reinject(entry, NF_ACCEPT);
              if ((__s32)(seq_next - seq_next_tmp) < 0) {
                seq_next = seq_next_tmp;
              }
            } else {
              node_tmp1 = kmalloc(sizeof(struct nf_queue_entry_node), GFP_ATOMIC);
              node_tmp1->entry = entry;
              node_tmp1->seq = seq;
              node_tmp1->seq_next =seq_next_tmp;
              node_tmp1->prev = node_tmp->prev;
              node_tmp1->next = node_tmp;

              node_tmp1->prev->next = node_tmp1;
              node_tmp1->next->prev = node_tmp1;

              reorder_count++;
            }
          }
        }
      }
    }
  }

  spin_unlock_irqrestore(&reorder_queue_lock, reorder_queue_lock_flags);
  return 0;
}

int init_module(void)
{
  printk(KERN_INFO "register reorder_queue\n");
  nfqh.outfn = reorder_queue_enqueue_packet;
  nf_register_queue_handler(NFPROTO_IPV4, &nfqh);

  spin_lock_init(&reorder_queue_lock);

  ktime = ktime_set(0, REORDER_QUEUE_TIMEOUT);
  hrtimer_init(&hr_timer, CLOCK_MONOTONIC, HRTIMER_MODE_REL);
  hr_timer.function = hrtimer_callback;

  return 0;
}

void cleanup_module(void)
{
  printk(KERN_INFO "unregister reorder_queue\n");

  hrtimer_cancel(&hr_timer);

  nf_unregister_queue_handler(NFPROTO_IPV4, &nfqh);

}

MODULE_LICENSE("GPL");
