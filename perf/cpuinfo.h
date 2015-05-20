#ifndef _GPERFNET_CPUINFO_H
#define _GPERFNET_CPUINFO_H

struct cpuinfo {
	int processor;
	int physical_id;
	int siblings;
	int core_id;
	int cpu_cores;
};

/* Parse /proc/cpuinfo to get CPU topology.  cpus is a user-provided buffer to
 * be filled in.  max_cpus is the maximum number of items that can be filled in
 * cpus.  On success, the number of items filled in is returned.  Otherwise, -1
 * is returned and errno is set.
 */
int get_cpuinfo(struct cpuinfo *cpus, int max_cpus);

#endif
