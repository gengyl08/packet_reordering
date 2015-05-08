#! /usr/bin/env python

################################################################################
#
#  NetFPGA-10G http://www.netfpga.org
#
#  Author:
#        Yilong Geng
#
#  Description:
#        Code to config delay modules and rate limiters
#
#  Copyright notice:
#        Copyright (C) 2010, 2011 The Board of Trustees of The Leland Stanford
#                                 Junior University
#
#  Licence:
#        This file is part of the NetFPGA 10G development base package.
#
#        This file is free code: you can redistribute it and/or modify it under
#        the terms of the GNU Lesser General Public License version 2.1 as
#        published by the Free Software Foundation.
#
#        This package is distributed in the hope that it will be useful, but
#        WITHOUT ANY WARRANTY; without even the implied warranty of
#        MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#        Lesser General Public License for more details.
#
#        You should have received a copy of the GNU Lesser General Public
#        License along with the NetFPGA source package.  If not, see
#        http://www.gnu.org/licenses/.
#
#

import os
from axi import *
from time import sleep
from math import ceil
import argparse

DATAPATH_FREQUENCY = 160000000

REORDER_OUTPUT_QUEUES_BASE_ADDR = "0x76000000"

DELAY_BASE_ADDR = {0 : "0x79c60000",
                   1 : "0x79c40000",
                   2 : "0x79c20000",
                   3 : "0x79c00000"}

parser = argparse.ArgumentParser(description='Argument Parser')
parser.add_argument('--delay', help='delay values for each queue', nargs=4, default=[0, 0, 0, 0], type=int)
parser.add_argument('--dropLoop', help='drop_loop for each queue', nargs=4, default=[0, 0, 0, 0], type=int)
parser.add_argument('--dropCount', help='drop_count for each queue', nargs=4, default=[0, 0, 0, 0], type=int)
parser.add_argument('--splitRatio', help='split_ratio for each queue', nargs=4, default=[1, 0, 0, 0], type=int)
parser.add_argument('--printDrop', help='print drop counters', action='store_true')
parser.add_argument('--printDelay', help='print delays', action='store_true')
parser.add_argument('--printSplitRatio', help='print split ratios', action='store_true')

class ReorderOutputQueues:

    def __init__(self):
        self.module_base_addr = REORDER_OUTPUT_QUEUES_BASE_ADDR
        self.drop_counts_reg_offset = ["0x3", "0x4", "0x5", "0x6"]
        self.split_ratios_reg_offset = ["0x0", "0x1", "0x2"]

        self.drop_counts = [0, 0, 0, 0]
        self.split_ratios = [0, 0, 0, 0]

        self.get_drop_counts()
        self.get_split_ratios()

    def get_drop_counts(self):
        for i in range(4):
            drop_count = rdaxi(self.reg_addr(self.drop_counts_reg_offset[i]))
            self.drop_counts[i] = int(drop_count, 16)

    def get_split_ratios(self):
        for i in range(3):
            split_ratio = rdaxi(self.reg_addr(self.split_ratios_reg_offset[i]))
            self.split_ratios[i] = float(int(split_ratio, 16))

        self.split_ratios = [x/4294967295 for x in self.split_ratios]
        self.split_ratios[3] = 1.0

        for i in range(1, 3):
            self.split_ratios[i] = max(0, self.split_ratios[i] - sum(self.split_ratios[:i]))

    def set_split_ratios(self, split_ratios):
        tmp = sum(split_ratios)
        split_ratios = [float(x)/tmp for x in split_ratios]

        for i in range(1, 4):
            split_ratios[i] = split_ratios[i-1] + split_ratios[i]

        for i in range(3):
            split_ratios[i] = int(split_ratios[i] * 4294967295)

        for i in range(3):
            wraxi(self.reg_addr(self.split_ratios_reg_offset[i]), hex(split_ratios[i]))
        self.get_split_ratios()

    def reg_addr(self, offset):
        return add_hex(self.module_base_addr, offset)

    def print_drop(self):
        for i in range(5):
            print "Queue " + str(i) + " Drop Count: " + str(self.drop_counts[i])

    def printSplitRatio(self):
        for i in range(5):
            print "Queue " + str(i) + " Split Ratio: " + str(self.split_ratios[i])

class Delay:

    def __init__(self, queue):
        self.queue = queue
        self.module_base_addr = DELAY_BASE_ADDR[queue]
        self.delay_reg_offset = "0x0"
        self.drop_loop_reg_offset = "0x1"
        self.drop_count_reg_offset = "0x2"

        # The internal delay_length is in ticks (integer)
        self.delay = 0
        self.drop_loop = 0
        self.drop_count = 0
        self.get_delay()
        self.get_drop_loop()
        self.get_drop_count()

    # delay is stored as an integer value
    def get_delay(self):
        delay = rdaxi(self.reg_addr(self.delay_reg_offset))
        self.delay = int(delay, 16)

    def get_drop_loop(self):
        drop_loop = rdaxi(self.reg_addr(self.drop_loop_reg_offset))
        self.drop_loop = int(drop_loop, 16)

    def get_drop_count(self):
        drop_count = rdaxi(self.reg_addr(self.drop_count_reg_offset))
        self.drop_count = int(drop_count, 16)

    def to_string(self):
        return '{:,}'.format(int(self.delay*1000000000/DATAPATH_FREQUENCY))+'ns'

    # delay is an interger value in nano second
    def set_delay(self, delay):
        wraxi(self.reg_addr(self.delay_reg_offset), hex(delay))
        self.get_delay()

    def set_drop_loop(self, drop_loop):
        wraxi(self.reg_addr(self.drop_loop_reg_offset), hex(drop_loop))
        self.get_drop_loop()

    def set_drop_count(self, drop_count):
        wraxi(self.reg_addr(self.drop_count_reg_offset), hex(drop_count))
        self.get_drop_count()

    def reg_addr(self, offset):
        return add_hex(self.module_base_addr, offset)

    def print_status(self):
        print 'queue: '+str(self.queue)+' delay: '+str(self.delay)+' drop_loop: '+str(self.drop_loop)+' drop_count: '+str(self.drop_count)



if __name__=="__main__":
    #print "begin"
    #rateLimiters = {}
    args = parser.parse_args()

    reorderOutputQueues = ReorderOutputQueues()

    delays = {}
    for i in range(4):
        delays.update({i : Delay(i)})

    reorderOutputQueues.set_split_ratios(args.splitRatio)

    if args.printDrop:
        reorderOutputQueues.print_drop()
    if args.printSplitRatio:
        reorderOutputQueues.printSplitRatio()

    # configure delay modules
    for iface, d in delays.iteritems():
        d.set_delay(args.delay[iface])
        d.set_drop_loop(args.dropLoop[iface])
        d.set_drop_count(args.dropCount[iface])
        if args.printDelay:
            d.print_status()

        
