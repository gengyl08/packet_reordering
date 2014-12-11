#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/netfilter.h>
#include <linux/netfilter_ipv4.h>

static struct nf_hook_ops nfho;

unsigned int hook_func(const struct nf_hook_ops *ops, struct sk_buff **skb, const struct net_device *in, const struct net_device *out, int (*okfn)(struct sk_buff *))
{
  printk(KERN_INFO "packet seen\n");
  return NF_QUEUE;
}

int init_module(void)
{
  printk(KERN_INFO "register dupack_drop\n");
  nfho.hook = (nf_hookfn *)hook_func;
  nfho.hooknum = 0;
  nfho.pf = PF_INET;
  nfho.priority = NF_IP_PRI_FIRST;
  nf_register_hook(&nfho);
  return 0;
}

void cleanup_module(void)
{
  printk(KERN_INFO "unregister dupack_drop\n");
  nf_unregister_hook(&nfho);
}
