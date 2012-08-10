#!/usr/bin/env python

import sys
from mni import mni
import time
import optparse
import time
import random

parser = optparse.OptionParser()
parser.add_option("-r", "--random",
        action="store",
        type="float",
        dest="random",
        default=-1,
        help="add randomized delays between resets. The supplied parameter\
will the the maximum wait time between consecutive starts.")

(options, args) = parser.parse_args()

m = mni.MNI()

print "Resetting nodes"

if options.random != None and options.random > 0:
    #randomize the startup of the nodes
    for n in m.get_nodes():
        time.sleep(random.random()*options.random)
        print "Starting Node", n.serial, n.id
        n.reset()
else:
    # simply reset all nodes
    for n in m.get_nodes():
        print "Node", n.id
    m.reset_all()

