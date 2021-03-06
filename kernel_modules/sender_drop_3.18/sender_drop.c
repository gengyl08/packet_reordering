#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/netfilter.h>
#include <linux/netfilter_ipv4.h>
#include <linux/ip.h>
#include <linux/tcp.h>
#include <linux/skbuff.h>
#include <linux/byteorder/generic.h>

static struct nf_hook_ops nfho;
struct sk_buff *sock_buff;
struct tcphdr *tcp_header;
struct iphdr *ip_header;

unsigned int hook_func(const struct nf_hook_ops *ops, struct sk_buff *skb, const struct net_device *in, const struct net_device *out, int (*okfn)(struct sk_buff *))
{
  sock_buff = skb;

  if (!sock_buff) {
    return NF_ACCEPT;
  }

  ip_header = (struct iphdr *)skb_network_header(sock_buff);
  if (ip_header->protocol == 6) {
    tcp_header = (struct tcphdr *)((unsigned char *)ip_header + (((__u32)ip_header->ihl)<<2));
    if (tcp_header->dest == 0x8913) {
      return NF_QUEUE;
    }
  }
  return NF_ACCEPT;
}

int init_module(void)
{
  printk(KERN_INFO "register sender_drop\n");
  nfho.hook = (nf_hookfn *)hook_func;
  nfho.hooknum = 4;
  nfho.pf = NFPROTO_IPV4;
  nfho.priority = NF_IP_PRI_FIRST;
  nf_register_hook(&nfho);
  return 0;
}

void cleanup_module(void)
{
  printk(KERN_INFO "unregister sender_drop\n");
  nf_unregister_hook(&nfho);
}
