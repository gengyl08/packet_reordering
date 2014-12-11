#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/netfilter.h>
#include <linux/netfilter_ipv4.h>
#include <net/netfilter/nf_queue.h>

static struct nf_queue_handler nfqh;

int dupack_drop_enqueue_packet(struct nf_queue_entry *entry, unsigned int queuenum)
{
  printk(KERN_INFO "enqueue\n");
  nf_reinject(entry, NF_ACCEPT);
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
