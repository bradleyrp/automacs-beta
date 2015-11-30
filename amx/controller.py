#!/usr/bin/python

import sys,os,re,shutil,glob,inspect,subprocess,datetime,time
from base.config import bootstrap_configuration

#---CONFIGURE
#-------------------------------------------------------------------------------------------------------------

def config(local=False):

	"""
	Load configuration from a central location.
	"""

	config_file = os.environ['HOME']+'/.automacs.py'
	config_file_local = './config.py'
	if os.path.isfile(config_file_local): local = True
	if local and not os.path.isfile(config_file_local): 
		print '[STATUS] cannot find configuration at %s'%config_file_local
		bootstrap_configuration(local=True)
	elif not local and not os.path.isfile(config_file):
		print '[STATUS] cannot find configuration at %s'%config_file
		bootstrap_configuration()
	else: 
		print '[STATUS] reading configuration from %s'%(config_file_local if local else config_file)
		print '[STATUS] edit the file manually to change settings'

#---configure unless cleaning or configuring
if 'clean' not in sys.argv and 'config' not in sys.argv:
	config()
	from base.gromacs import *

#---FUNCTIONS
#-------------------------------------------------------------------------------------------------------------

def program(script,flag=False):

	"""
	Prepare a script for a particular AUTOMACS program.
	"""

	#---multiple naming schemes
	lookups = {'protein':'script-protein','cgmd-bilayer':'script-cgmd-bilayer'}
	os.umask(002)

	if script not in lookups: raise Exception('[ERROR] invalid program, select from %s'%str(lookups.keys()))
	fn = 'amx/procedures/scripts/%s.py'%lookups[script]
	new_script = '%s.py'%lookups[script]
	if os.path.isfile(fn) and os.path.isfile(new_script): raise Exception('[DEV_ERROR] found %s'%new_script)
	elif os.path.isfile(fn): 
		print '[STATUS] copying %s'%fn
		shutil.copy(fn,new_script)
		print '[STATUS] wrote executable to %s'%new_script
		print '[STATUS] check the settings and run via: "./%s.py"'%lookups[script]
	else: raise Exception('[ERROR] cannot find script at %s'%fn)
	
def clean(sure=False):

	"""
	Erases everything to reset the project.
	"""

	for root,dirnames,filenames in os.walk('./'): break
	remove_dirs = [i for i in dirnames if re.match('^s[0-9]+-\w+',i)]
	if os.path.isdir('amx/docs/build'): remove_dirs.append('amx/docs/build')
	remove_files = [i for i in filenames if i != 'config.py' and 
		(re.match('^script-s[0-9]+',i) or re.match('^([\w-]+)\.py$',i) 
		or re.match('^(cluster|gmxjob)',i))]
	print '[STATUS] preparing to remove directories:'
	for fn in remove_dirs: print '[STATUS] >> %s'%fn
	print '[STATUS] preparing to remove files:'
	for fn in remove_files: print '[STATUS] >> %s'%fn
	if sure or all(re.match('^(y|Y)',raw_input('[QUESTION] %s (y/N)? '%msg))!=None
		for msg in ['okay to remove','confirm']):
		print '[STATUS] resetting'
		for fn in remove_files: os.remove(fn)
		for fn in remove_dirs: shutil.rmtree(fn)
	else: print '[STATUS] doing nothing'

def upload(sure=False):

	"""
	Upload the most recent CPT and TPR file to a cluster for continuation.
	"""

	default_fns,default_dirs = ['makefile'],['amx']
	default_fns += [os.path.join(root,fn) for root,dirnames,fns 
		in os.walk('./amx') for fn in fns for dn in default_dirs
		if not re.match('.+\.pyc$',fn)!=None]
	part_regex = '^[^\/]+\/md\.part([0-9]{4})\.cpt' 
	last_step_num = max(map(
		lambda z:int(z),map(
		lambda y:re.findall('^s([0-9]+)',y).pop(),filter(
		lambda x:re.match('^s[0-9]+-\w+$',x),glob.glob('s*-*')))))
	last_step = filter(lambda x:re.match('^s%02d'%last_step_num,x),glob.glob('s*-*')).pop()
	part_num = max(map(
		lambda y:int(re.findall(part_regex,y)[0]),filter(
		lambda x:re.match(part_regex,x),
		glob.glob(last_step+'/*.cpt'))))
	restart_fns = [last_step+'/md.part%04d.%s'%(part_num,suf) for suf in ['cpt','tpr']]
	restart_fns += [last_step+'/script-continue.sh']
	if not all([os.path.isfile(fn) for fn in restart_fns]):
		error = '[STATUS] could not find latest CPT or TPR for part%04d'%part_num
		error += '\n[ERROR] upload only works if there is a TPR for the last CPT part'
		raise Exception(error)
	else:
		with open('uploads.txt','w') as fp:
			for fn in restart_fns+default_fns: fp.write(fn+'\n')
		sshname = raw_input('[QUESTION] enter ssh alias for destination machine: ')
		subfolder = raw_input('[QUESTION] enter subfolder on remote machine (default is ~/): ')
		cwd = os.path.basename(os.path.abspath(os.getcwd()))
		if not sure:
			cmd = 'rsync -%s --files-from=uploads.txt ../%s %s:~/%s/%s'%('avin',cwd,sshname,subfolder,cwd)
			p = subprocess.Popen(cmd,shell=True,cwd=os.path.abspath(os.getcwd()))
			log = p.communicate()
		if sure or raw_input('\n[QUESTION] continue [y/N]? ')[:1] not in 'nN':
			cmd = 'rsync -%s --files-from=uploads.txt ../%s %s:~/%s/%s'%('avi',cwd,sshname,subfolder,cwd)
			p = subprocess.Popen(cmd,shell=True,cwd=os.path.abspath(os.getcwd()))
			log = p.communicate()
			os.remove('uploads.txt')
		with open('script-%s.log'%last_step,'a') as fp:
			destination = '%s:~/%s/%s'%(sshname,subfolder,cwd)
			ts = datetime.datetime.fromtimestamp(time.time()).strftime('%Y.%m.%d.%H%M')
			fp.write("[FUNCTION] upload () {'destination': '%s', 'time': '%s', 'sure': %s}\n"%(
				destination,ts,str(sure)))

def cluster():

	"""
	Write a cluster header according to the machine configuration.
	"""

	if not 'cluster_header' in machine_configuration: print '[STATUS] no cluster information'
	else:
		head = machine_configuration['cluster_header']
		for key,val in machine_configuration.items(): head = re.sub(key.upper(),str(val),head)
		with open('cluster-header.sh','w') as fp: fp.write(head)
		print '[STATUS] wrote cluster-header.sh'
		#---get the most recent step (possibly duplicate code from base)
		if len(filter(lambda x:re.match('^s[0-9]+-\w+',x),glob.glob('s*-*')))>0:
			last_step_num = max(map(
				lambda z:int(z),map(
				lambda y:re.findall('^s([0-9]+)',y).pop(),filter(
				lambda x:re.match('^s[0-9]+-\w+$',x),glob.glob('s*-*')))))
			last_step = filter(lambda x:re.match('^s%02d'%last_step_num,x),glob.glob('s*-*')).pop()+'/'
			#---code from base.functions.write_continue_script to rewrite the continue script
			with open('amx/procedures/scripts/script-continue.sh','r') as fp: lines = fp.readlines()
			settings = {
				'maxhours':24,
				'extend':100000,
				'tpbconv':'gmx convert-tpr',
				'mdrun':'gmx mdrun',
				}
			setting_text = '\n'.join([
				str(key.upper())+'='+('"' if type(val)==str else '')+str(val)+('"' if type(val)==str else '') 
				for key,val in settings.items()])
			lines = map(lambda x: re.sub('#---SETTINGS OVERRIDES HERE$',setting_text,x),lines)
			script_fn = 'script-continue.sh'
			cont_fn = last_step+script_fn
			print '[STATUS] %swriting %s'%('over' if os.path.isfile(last_step+script_fn) else '',cont_fn)
			with open(last_step+script_fn,'w') as fp:
				for line in lines: fp.write(line)
			os.chmod(last_step+script_fn,0744)
			#---code above from base.functions.write_continue_script		
			with open(cont_fn,'r') as fp: continue_script = fp.read()
			continue_script = re.sub('#!/bin/bash\n','',continue_script)
			cluster_continue = last_step+'/cluster-continue.sh'
			print '[STATUS] writing %s'%cluster_continue
			with open(cluster_continue,'w') as fp: fp.write(head+continue_script)
		#---for each python script in the root directory we write an equivalent cluster script
		pyscripts = glob.glob('script-*.py')
		if len(pyscripts)>0: 
			with open('cluster-header.sh','r') as fp: header = fp.read()
		for script in pyscripts:
			name = re.findall('^script-([\w-]+)\.py$',script)[0]
			with open('cluster-%s.sh'%name,'w') as fp:
				fp.write(header+'\n')
				fp.write('python script-%s.py\n'%name)
			print '[STATUS] wrote cluster-%s.sh'%name
		#---note that we do not log this operation because it only changes the BASH scripts

#---INTERFACE
#-------------------------------------------------------------------------------------------------------------

def makeface(*arglist):

	"""
	Standard interface to makefile.
	"""

	#---unpack arguments
	if arglist == []: 
		raise Exception('[ERROR] no arguments to controller')
	args,kwargs = [],{}
	arglist = list(arglist)
	funcname = arglist.pop(0)
	for arg in arglist:
		if re.match('^\w+\=(\w+)',arg):
			parname,parval = re.findall('^(\w+)\=(\w+)$',arg)[0]
			kwargs[parname] = parval
			arglist.remove(arg)
		else:
			argspec = inspect.getargspec(globals()[funcname])
			if arg in argspec.args: kwargs[arg] = True
			else: args.append(arg)
			arglist.remove(arg)
	args = tuple(args)
	if arglist != []: raise Exception('unprocessed arguments %s'%str(arglist))

	#---call the function
	globals()[funcname](*args,**kwargs)

#---MAIN
#-------------------------------------------------------------------------------------------------------------

if __name__ == "__main__": makeface(*sys.argv[1:])
