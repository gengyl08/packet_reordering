#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/netfilter.h>
#include <linux/netfilter_ipv4.h>

static struct nf_hook_ops nfho;
struct sk_buff *sock_buff;
struct tcphdr *tcp_header;
struct iphdr *ip_header;

unsigned int hook_func(const struct nf_hook_ops *ops, struct sk_buff **skb, const struct net_device *in, const struct net_device *out, int (*okfn)(struct sk_buff *))
{
  sock_buff = *skb;
  if (!sock_buff) {
    return NF_ACCEPT;
  }

  ip_header = (struct iphdr *)skb_network_header(sock_buff);
  if (ip_header->protocol == 6) {
    tcp_header = (struct tcphdr *)skb_transport_header(sock_buff);
    if (tcp_header->source == 5001) {
      return NF_QUEUE;
    }
  }
  return NF_ACCEPT;
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
