#!/usr/bin/python

import sys,os,re,shutil,glob,inspect,subprocess,datetime,time
from base.config import bootstrap_configuration
from base.metatools import script_settings_replace
from base.tools import detect_last,serial_number

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

	os.umask(002)
	fn = 'amx/procedures/scripts/script-%s.py'%script
	new_script = 'script-%s.py'%script
	if os.path.isfile(fn) and os.path.isfile(new_script): 
		raise Exception('[ERROR] found %s which must be deleted before continuing '%new_script+
			'(if this was a previous step then there was an automatic copy)')
	elif os.path.isfile(fn): 
		print '[STATUS] copying %s'%fn
		shutil.copy(fn,new_script)
		print '[STATUS] wrote executable to %s'%new_script
		print '[STATUS] check the settings and run via: "./%s"'%new_script
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
		or re.match('^(cluster|gmxjob)',i) or i=='wordspace.json')]
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

def upload(sure=False,part=None):

	"""
	Upload the most recent CPT and TPR file to a cluster for continuation.
	Need to re-write the step/part-specific uploader.
	"""

	serial_number()
	default_fns,default_dirs = ['makefile'],['amx']
	default_fns += [os.path.join(root,fn) for root,dirnames,fns 
		in os.walk('./amx') for fn in fns for dn in default_dirs
		if not re.match('.+\.pyc$',fn)!=None]
	default_fns = [i for i in default_fns if not re.match('.+\/amx\/docs',i)]
	last_step,part_num = detect_last()
	if part: part_num = int(part)
	if not last_step: raise Exception('\n[ERROR] no steps to upload')
	restart_fns = [last_step+'/md.part%04d.%s'%(part_num,suf) for suf in ['cpt','tpr']]
	restart_fns += [last_step+'/script-continue.sh']
	if not all([os.path.isfile(fn) for fn in restart_fns]):
		error = '[STATUS] could not find latest CPT or TPR for part%04d'%part_num
		error += '\n[ERROR] upload only works if there is a TPR for the last CPT part'
		print error
		import pdb;pdb.set_trace()
		raise Exception(error)
	else:
		with open('uploads.txt','w') as fp:
			for fn in restart_fns+default_fns: fp.write(fn+'\n')
		sshname = raw_input('[QUESTION] enter ssh alias for destination machine: ')
		subfolder = raw_input('[QUESTION] enter subfolder on remote machine (default is ~/): ')
		cwd = os.path.basename(os.path.abspath(os.getcwd()))
		if not sure:
			cmd = 'rsync -%s --files-from=uploads.txt ../%s %s:~/%s/%s'%('avin',cwd,sshname,subfolder,cwd)
			p = subprocess.Popen(cmd,shell=True,cwd=os.path.abspath(os.getcwd()),executable='/bin/bash')
			log = p.communicate()
		if sure or raw_input('\n[QUESTION] continue [y/N]? ')[:1] not in 'nN':
			cmd = 'rsync -%s --files-from=uploads.txt ../%s %s:~/%s/%s'%('avi',cwd,sshname,subfolder,cwd)
			p = subprocess.Popen(cmd,shell=True,cwd=os.path.abspath(os.getcwd()),executable='/bin/bash')
			log = p.communicate()
			os.remove('uploads.txt')
		if p.returncode == 0:
			with open('script-%s.log'%last_step.rstrip('/'),'a') as fp:
				destination = '%s:~/%s/%s'%(sshname,subfolder,cwd)
				ts = datetime.datetime.fromtimestamp(time.time()).strftime('%Y.%m.%d.%H%M')
				fp.write("[FUNCTION] upload () {'destination': '%s', 'time': '%s', 'sure': %s}\n"%(
					destination,ts,str(sure)))
		else: 
			print "[STATUS] upload failure (not logged)"
			sys.exit(1)

def download():

	"""
	Synchronize uploaded files according to log-uploads.
	"""

	regex_upload = '^\[FUNCTION]\s+upload\s+\(\)\s+(\{[^\}]+\})'
	last_step,part_num = detect_last()
	last_log = 'script-%s.log'%last_step
	with open(last_log) as fp: loglines = fp.readlines()
	upload_records = [i for i in loglines if re.match('^\[FUNCTION]\s+upload',i)]
	if upload_records == []: raise Exception("\n[ERROR] cannot download that which has not been uploaded")
	last_upload = upload_records[-1]
	upload_dict = eval(re.findall(regex_upload,last_upload)[0])
	destination = upload_dict['destination']
	print "[STATUS] log at %s says that this simulation is located at %s"%(last_log,destination)
	try:
		cmd = 'rsync -avin --progress %s ./'%destination
		p = subprocess.Popen(cmd,shell=True,cwd=os.path.abspath(os.getcwd()))
		log = p.communicate()
		if p.returncode != 0: raise
		if raw_input('\n[QUESTION] continue [y/N]? ')[:1] not in 'nN':
			cmd = 'rsync -avi --progress %s:%s/ ./'%(sshname,subfolder)
			print '[STATUS] running "%s"'%cmd
			p = subprocess.Popen(cmd,shell=True,cwd=os.path.abspath(os.getcwd()))
			log = p.communicate()
	except Exception as e:
		import traceback
		#---from omnicalc
		s = traceback.format_exc()
		print "[TRACE] > "+"\n[TRACE] > ".join(s.split('\n'))
		print "[ERROR] failed to find simulation"
		print "[NOTE] find the data on the remote machine via \"find ./ -name serial-%s\""%serial_number()
		sys.exit(1)

def cluster():

	"""
	Write a cluster header according to the machine configuration.
	Note that we do not log this operation because it only changes the BASH scripts
	"""

	if not 'cluster_header' in machine_configuration: 
		print '[STATUS] no cluster information'
		return
	head = machine_configuration['cluster_header']
	for key,val in machine_configuration.items(): head = re.sub(key.upper(),str(val),head)
	with open('cluster-header.sh','w') as fp: fp.write(head)
	print '[STATUS] wrote cluster-header.sh'
	#---get the most recent step (possibly duplicate code from base)
	last_step,part_num = detect_last()
	if last_step:
		#---code from base.functions.write_continue_script to rewrite the continue script
		with open('amx/procedures/scripts/script-continue.sh','r') as fp: lines = fp.readlines()
		settings = {
			'maxhours':machine_configuration['walltime'],
			'nprocs':machine_configuration['nprocs'],
			'tpbconv':gmxpaths['tpbconv'],
			'mdrun':gmxpaths['mdrun'],
			}
		for key in ['extend','until']: 
			if key in machine_configuration: settings[key] = machine_configuration[key]
		#---! must intervene above to come up with the correct executables
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
			fp.write('python script-%s.py &> log-%s\n'%(name,name))
		print '[STATUS] wrote cluster-%s.sh'%name

def metarun(script=None,more=False):

	"""
	Run a series of commands via a meta script in the inputs folder.
	May be deprecated due to execution problems and "moving to directory" weirdness.
	"""

	candidates = [re.findall('^(.+)\.py',os.path.basename(i))[0] for i in glob.glob('inputs/meta*')]
	if not script:
		print "[USAGE] make metarun <script>"
		print "[USAGE] available scripts: \n > "+'\n > '.join(candidates)
	else:
		try: target, = [i for i in candidates if re.search(script,i)]
		except: raise Exception('[ERROR] failed to match %s with known scripts'%script)
		execfile('inputs/%s.py'%target)

def look(script='',dump=True,step=None):

	"""
	Drop into the wordspace for a script. 
	Useful for adding commands to a procedure without starting from scratch or making a new script.
	Example: after forgetting to add this line, we can make a continuation script from here:
	"from amx.base.functions import write_continue_script;write_continue_script()"
	Any actions you take here will continue to be recorded to the watch_file.
	"""

	if not script: 
		script = max(glob.iglob('script-*.py'),key=os.path.getctime)
		print 'STATUS] resuming from the last step, apparently creeated by %s'%script
	cmd = '"import sys;sys.argv = [\'%s\'];from amx import *;resume(script_settings=\'%s\');%s"'%(
		script,script,"\nwith open('wordspace.json','w') as fp:\n\tjson.dump(wordspace,fp);" if dump else '')
	print '[STATUS] running: python -i -c '+cmd
	os.system('python -i -c '+cmd)

def watch():

	"""
	Tail the logfile for the latest step.
	"""

	logfile = max(glob.iglob('script-*.log'),key=os.path.getctime)
	print '[STATUS] watching the last step, apparently written to %s'%logfile
	os.system('cat '+logfile)	

def delstep(number,confident=False):

	"""
	Delete a step by number.
	Be very careful.
	"""

	target = int(number)
	fns = glob.glob('s*%02d-*'%target)
	assert len(fns)==3
	assert any([re.match('^script-s%02d-.+\.sh$'%target,i) for i in fns])
	assert any([re.match('^script-s%02d-.+\.log$'%target,i) for i in fns])
	assert any([re.match('^s%02d-'%target,i) for i in fns])
	extra_delete = ['wordspace.json','WATCHFILE']
	for fn in extra_delete:
		if os.path.isfile(fn): fns.append('wordspace.json')
	try:
		#---try to identify the associated script and clear it too
		script, = glob.glob('s%02d-*/script*.py'%target)
		local_script = os.path.basename(script)
		if os.path.isfile(local_script): fns.append(local_script)
	except: pass
	print "[STATUS] preparing to remove step %d including %s"%(target,str(fns))
	if confident or all(re.match('^(y|Y)',raw_input('[QUESTION] %s (y/N)? '%msg))!=None
		for msg in ['okay to remove this entire step','confirm']):
		for fn in fns: 
			if os.path.isfile(fn): os.remove(fn)
			else: shutil.rmtree(fn)

#---INTERFACE
#-------------------------------------------------------------------------------------------------------------

def makeface(*arglist):

	"""
	Standard interface to makefile.
	"""

	#---stray characters
	arglist = tuple(i for i in arglist if i not in ['w','--','s'])
	#---unpack arguments
	if arglist == []: 
		raise Exception('[ERROR] no arguments to controller')
	args,kwargs = [],{}
	arglist = list(arglist)
	funcname = arglist.pop(0)
	while arglist:
		arg = arglist.pop()
		if re.match('^\w+\=([\w\.\/]+)',arg):
			parname,parval = re.findall('^(\w+)\=([\w\.\/]+)$',arg)[0]
			kwargs[parname] = parval
		else:
			argspec = inspect.getargspec(globals()[funcname])
			if arg in argspec.args: kwargs[arg] = True
			else: args.append(arg)
	args = tuple(args)
	if arglist != []: raise Exception('unprocessed arguments %s'%str(arglist))

	#---call the function
	globals()[funcname](*args,**kwargs)

#---MAIN
#-------------------------------------------------------------------------------------------------------------

if __name__ == "__main__": makeface(*sys.argv[1:])
