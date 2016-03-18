#!/usr/bin/python

import os,subprocess,re

#---CONSTANTS
#-------------------------------------------------------------------------------------------------------------

gmx_error_strings = [
	'File input/output error:',
	'command not found',
	'Fatal error:',
	'Fatal Error:',
	'Can not open file:',
	]
	
gmx4paths = {
	'grompp':'grompp',
	'mdrun':'mdrun',
	'pdb2gmx':'pdb2gmx',
	'editconf':'editconf',
	'genbox':'genbox',
	'make_ndx':'make_ndx',
	'genion':'genion',
	'genconf':'genconf',
	'trjconv':'trjconv',
	'tpbconv':'tpbconv',
	'vmd':'vmd',
	'gmxcheck':'gmxcheck',
	}

gmx5paths = {
	'grompp':'gmx grompp',
	'mdrun':'gmx mdrun',
	'pdb2gmx':'pdb2gmx',
	'editconf':'editconf',
	'genbox':'gmx solvate',
	'make_ndx':'make_ndx',
	'genion':'gmx genion',
	'trjconv':'gmx trjconv',
	'genconf':'gmx genconf',
	'tpbconv':'gmx convert-tpr',
	'gmxcheck':'gmxcheck',
	'vmd':'vmd',
	}
	
#---SETTINGS
#-------------------------------------------------------------------------------------------------------------

#---load configuration
config_raw = {}
#---look upwards if making docs so no tracebacks
prefix = '../../../' if re.match('.+\/docs\/build$',os.getcwd()) else ''
if os.path.isfile(prefix+'./config.py'): execfile(prefix+'./config.py',config_raw)
else: execfile(os.environ['HOME']+'/.automacs.py',config_raw)
machine_configuration = config_raw['machine_configuration']

#---select a machine configuration
this_machine = 'LOCAL'
hostnames = [key for key in machine_configuration 
	if any([varname in os.environ and (
	re.search(key,os.environ[varname])!=None or re.match(key,os.environ[varname]))
	for varname in ['HOST','HOSTNAME']])]
if len(hostnames)>1: raise Exception('[ERROR] multiple machine hostnames %s'%str(hostnames))
elif len(hostnames)==1: this_machine = hostnames[0]
else: this_machine = 'LOCAL'
print '[STATUS] setting gmxpaths for machine: %s'%this_machine
machine_configuration = machine_configuration[this_machine]

#---modules in LOCAL configuration must be loaded before checking version
module_path = '/usr/share/Modules/default/init/python.py'
if 'modules' in machine_configuration:
	print '[STATUS] found modules in %s configuration'%this_machine
	if 'module_path' in machine_configuration: module_path = machine_configuration['module_path']
	try: execfile(module_path)
	except: raise Exception('could not execute %s'%module_path)
	print '[STATUS] unloading GROMACS'
	#---note that modules that rely on dynamically-linked C-code must use EnvironmentModules
	modlist = machine_configuration['modules']
	if type(modlist)==str: modlist = modlist.split(',')
	for mod in modlist:
		print '[STATUS] module load %s'%mod
		module('load',mod)
	del mod

#---basic check for gromacs version series
suffix = '' if 'suffix' not in machine_configuration else machine_configuration['suffix']
check_gmx = subprocess.Popen('gmx%s'%suffix,shell=True,executable='/bin/bash',
	stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()
if not re.search('command not found',check_gmx[1]): gmx_series = 5
else:
	check_mdrun = ' '.join(subprocess.Popen('mdrun%s -g /tmp/md.log'%suffix,shell=True,
		executable='/bin/bash',stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate())
	if re.search('VERSION 4',check_mdrun): gmx_series = 4
	else: raise Exception('gromacs is absent')
	del check_mdrun
print '[NOTE] using GROMACS %d'%gmx_series

#---select the right GROMACS utilities names
if gmx_series == 4: gmxpaths = dict(gmx4paths)
if gmx_series == 5: gmxpaths = dict(gmx5paths)

#---modify gmxpaths according to hardware configuration
config = machine_configuration
if suffix != '': gmxpaths = dict([(key,val+suffix) for key,val in gmxpaths.items()])
if 'nprocs' in config and config['nprocs'] != None: gmxpaths['mdrun'] += ' -nt %d'%config['nprocs']
#---use mdrun_command for quirky mpi-type mdrun calls on clusters
if 'mdrun_command' in machine_configuration: gmxpaths['mdrun'] = machine_configuration['mdrun_command']
#---if any utilities are keys in config we override it and then perform uppercase substitutions from config
utility_keys = [key for key in gmxpaths if key in config]
if any(utility_keys):
	for name in utility_keys:
		gmxpaths[name] = config[name]
		for key,val in config.items(): gmxpaths[name] = re.sub(key.upper(),str(val),gmxpaths[name])
	del name
#---even if mdrun is customized in config we treat the gpu flag separately
if 'gpu_flag' in config: gmxpaths['mdrun'] += ' -nb %s'%config['gpu_flag']	

#---clean up the namespace
del config,this_machine,gmx5paths,gmx4paths,config_raw,module_path
del check_gmx,gmx_series,hostnames,utility_keys
