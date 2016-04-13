#!/usr/bin/python

settings = """
step:               continue
system name:        system
procedure:          continue
hostname:           kraken
walltime:           24:00
nnodes:             1
"""

from amx import *
init(settings)
from amx.base.gromacs import prepare_machine_configuration,prepare_gmxpaths
machine_configuration,this_machine = prepare_machine_configuration(hostname=wordspace.hostname)
machine_configuration['walltime'] = wordspace.walltime
gmxpaths = prepare_gmxpaths(machine_configuration,override=True)
assert wordspace.hostname!='LOCAL'
#---assume that we write the cluster script on the last step
last_step,part_num = detect_last()
head = machine_configuration['cluster_header']
machine_configuration['nnodes'] = wordspace.nnodes
machine_configuration['nprocs'] = machine_configuration['nnodes']*machine_configuration['ppn']
#---in case script-continue.sh is not ready we read it
with open('amx/procedures/scripts/script-continue.sh','r') as fp: lines = fp.readlines()
#---if this machine_configuration uses minutes we compute maxhours for gromacs 
regex_walltime_minutes = '([0-9]+)\:([0-9]+)'
if re.match(regex_walltime_minutes,machine_configuration['walltime']):
	hoursplit = re.findall('([0-9]+)\:([0-9]+)',machine_configuration['walltime'])[0]
	maxhours = int(hoursplit[1])/60.+int(hoursplit[0])	
else: maxhours = machine_configuration['walltime']
#---outgoing settings for the cluster script
script_settings = {
	'maxhours':maxhours,
	'nprocs':machine_configuration['nprocs'],
	'tpbconv':str(gmxpaths['tpbconv']),
	'mdrun':str(gmxpaths['mdrun']),
	}
for key,val in script_settings.items(): 
	for subkey,subval in machine_configuration.items(): 
		if type(script_settings[key])==str: 
			script_settings[key] = re.sub(subkey.upper(),str(subval),script_settings[key])
setting_text = '\n'.join([
	str(key.upper())+'='+('"' if type(val)==str else '')+str(val)+('"' if type(val)==str else '') 
	for key,val in script_settings.items()])
lines = map(lambda x: re.sub('#---SETTINGS OVERRIDES HERE$',setting_text,x),lines)
script_fn = 'script-continue.sh'
cont_fn = os.path.join(last_step,script_fn)
print '[STATUS] %swriting %s'%('over' if os.path.isfile(last_step+script_fn) else '',cont_fn)
with open(cont_fn,'w') as fp: fp.write(''.join(lines))
os.chmod(cont_fn,0744)
with open(cont_fn,'r') as fp: continue_script = fp.read()
continue_script = re.sub('#!/bin/bash\n','',continue_script)
cluster_continue = os.path.join(last_step,'cluster-continue-%s.sh'%wordspace.hostname)
print '[STATUS] writing %s'%cluster_continue
#---we must substitute script_settings first
for key,val in script_settings.items(): head = re.sub(key.upper(),str(val),head)
for key,val in machine_configuration.items(): head = re.sub(key.upper(),str(val),head)
cluster_script = head+continue_script
with open(cluster_continue,'w') as fp: fp.write(cluster_script)
assert 'submit_command' in [wordspace,machine_configuration]
submit_command = False
if 'submit_command' in wordspace: submit_command = wordspace.submit_command
elif 'submit_command' in machine_configuration: submit_command = machine_configuration['submit_command']
if not submit_command: print '[STATUS] cannot infer the submit command so you must submit manually'
else:
	#---add this cluster to the batch list if it exists
	batch_script = 'script-batch-submit.sh'
	if os.path.isfile(batch_script):
		with open(batch_script,'a') as fp: 
			fp.write('cd %s\n%s cluster-continue-%s.sh\ncd ..\n'%(
				last_step,wordspace.submit_command,wordspace.hostname))
