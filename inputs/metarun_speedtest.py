#!/usr/bin/python

import sys,os,shutil,subprocess
from base.metatools import *

settings = """
step:               continueNODESPEC
system name:        system
procedure:          continue
hostname:           gordon
walltime:           00:30
nnodes:             NNODES
"""

#---loop over number of nodes
nnodes = [1,2,4,8,10,16]
batch_submit_script = 'script-batch-submit.sh'

call('make -s clean sure')
with open(batch_submit_script,'w') as fp: fp.write('#!/bin/bash\n')
#---one short run for each number of nodes
for key in nnodes:
	if os.path.isfile('script-continue.py'): os.remove('script-continue.py')
	call('make -s program continue')
	named_settings = re.sub('NODESPEC','-%dnodes'%key,settings)
	named_settings = re.sub('NNODES','%d'%key,named_settings)
	script_settings_replace('script-continue.py',named_settings)
	#---the continue procedure copies the CPT/TPR files into place and prepares a script-continue.sh
	call('./script-continue.py')
	#---the cluster procedure prepares the cluster script with overrides to machine_configuration
	if os.path.isfile('script-cluster.py'): os.remove('script-cluster.py')
	call('make -s program cluster')
	script_settings_replace('script-cluster.py',named_settings)
	call('./script-cluster.py')
os.chmod(batch_submit_script,0744)

"""
development notes:
	typically simulations are started locally and continued after moving to the cluster
		we run "make upload" to send the data and then "make cluster" once it's situated on the cluster
		the "make cluster" picks up the hostname, reads config.py, and writes the header in the most recent step directory
		the user has to run it
	for the speedtest we modify this procedure
		first we specify the remote machine
		then the metarun_speedtest.py (this script) prepares each continuation
		it also reads config.py and prepares the cluster script in the same manner as "make cluster" from controller.py 
		everything should be uploaded via "make upload all" to the target machine
		once it's uploaded the user can run ./script-batch-submit.sh
"""
