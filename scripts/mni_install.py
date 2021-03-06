#!/usr/bin/env python
from mni import mni
import sys
import optparse

# Real optparse another day
try:
    config = sys.argv[sys.argv.index("-f") + 1]
    m = mni.MNI(configFile=config)
except ValueError:
    m = mni.MNI()

m.compile()

sys.stdout.write("Installing application on nodes: ")
for n in m.get_nodes():
    sys.stdout.write("%d,%s "%(n.id, n.serial))
sys.stdout.write("\n")
print "Installing on %d nodes"%(len(m.get_nodes()))
sys.stdout.flush()

if m.install_all():
    print "Install Success"
else:
    print "Install Failed!"
