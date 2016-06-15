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
		raise Exception('\n[ERROR] found %s which must be deleted before continuing '%new_script+
			'(if this was a previous step then there was an automatic copy)')
	elif os.path.isfile(fn): 
		print '[STATUS] copying %s'%fn
		shutil.copy(fn,new_script)
		print '[STATUS] wrote executable to %s'%new_script
		print '[STATUS] check the settings and run via: "./%s"'%new_script
	else: raise Exception('[ERROR] cannot find script at %s'%fn)
	
def clean(sure=False,docs=False):

	"""
	Erases everything to reset the project.
	"""

	docs_dn = 'amx/docs/build'
	for root,dirnames,filenames in os.walk('./'): break
	remove_dirs = [i for i in dirnames if re.match('^[sv][0-9]+-\w+',i)]
	if os.path.isdir(docs_dn): remove_dirs.append(docs_dn)
	remove_files = [i for i in filenames if i != 'config.py' and 
		(re.match('^script-[sv][0-9]+',i) or re.match('^([\w-]+)\.py$',i) or re.match('^serial',i)
		or re.match('^(cluster|gmxjob)',i) or i in [
			'wordspace.json','script-batch-submit.sh'
			])]
	if docs: 
		print '[STATUS] cleaning docs only'
		remove_dirs,remove_files = [],[]
		if os.path.isdir(docs_dn): remove_dirs.append(docs_dn)
		sure = True
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

def upload(sure=False,part=None,bulk=False):

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
	if part: 
		part_num = int(part)
		last_step, = [i for i in glob.glob('s%02d-*'%part_num)]
	if not last_step and not bulk: raise Exception('\n[ERROR] no steps to upload')
	elif last_step and not bulk:
		restart_fns = [last_step+'/md.part%04d.%s'%(part_num,suf) for suf in ['cpt','tpr']]
		restart_fns += [last_step+'/script-continue.sh']
		if not all([os.path.isfile(fn) for fn in restart_fns]):
			error = '[STATUS] could not find necessary upload files (part number %04d)'%part_num
			error += '\n[ERROR] upload only works if there is a TPR for the last CPT part'
			error += "\n[ERROR] missing: %s"%str([fn for fn in restart_fns if not os.path.isfile(fn)])
			raise Exception(error)
		with open('uploads.txt','w') as fp: 
			for fn in restart_fns+default_fns: fp.write(fn+'\n')
	sshname = raw_input('[QUESTION] enter ssh alias for destination machine: ')
	subfolder = raw_input('[QUESTION] enter subfolder on remote machine (default is ~/): ')
	cwd = os.path.basename(os.path.abspath(os.getcwd()))
	if not sure:
		cmd = 'rsync -%s%s ../%s %s:~/%s/%s'%(
			'avin',' --files-from=uploads.txt' if not bulk else ' --exclude=.git',cwd,
			sshname,subfolder,cwd if not bulk else '')
		p = subprocess.Popen(cmd,shell=True,cwd=os.path.abspath(os.getcwd()),executable='/bin/bash')
		log = p.communicate()
	if sure or raw_input('\n[QUESTION] continue [y/N]? ')[:1] not in 'nN':
		cmd = 'rsync -%s%s ../%s %s:~/%s/%s'%(
			'avi',' --files-from=uploads.txt' if not bulk else ' --exclude=.git',cwd,
			sshname,subfolder,cwd if not bulk else '')
		p = subprocess.Popen(cmd,shell=True,cwd=os.path.abspath(os.getcwd()),executable='/bin/bash')
		log = p.communicate()
		if not bulk: os.remove('uploads.txt')
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
	#----infer the log from the number of the last step
	last_step_code = re.search('^([a-z][0-9]+)-',last_step).group(1)
	last_log = [f for f in glob.glob('script-%s-*'%last_step_code)][0]
	with open(last_log) as fp: loglines = fp.readlines()
	upload_records = [i for i in loglines if re.match('^\[FUNCTION]\s+upload',i)]
	if upload_records == []: raise Exception("\n[ERROR] cannot download that which has not been uploaded")
	last_upload = upload_records[-1]
	upload_dict = eval(re.findall(regex_upload,last_upload)[0])
	destination = upload_dict['destination']
	print "[STATUS] log at %s says that this simulation is located at %s"%(last_log,destination)
	try:
		cmd = 'rsync -avin --progress %s/* ./'%destination
		print '[STATUS] running: "%s"'%cmd
		p = subprocess.Popen(cmd,shell=True,cwd=os.path.abspath(os.getcwd()))
		log = p.communicate()
		if p.returncode != 0: raise
		if raw_input('\n[QUESTION] continue [y/N]? ')[:1] not in 'nN':
			cmd = 'rsync -avi --progress %s/* ./'%destination
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

def cluster(**kwargs):

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
		tl = [float(j) if j else 0.0 for j in re.match('^([0-9]+)\:?([0-9]+)?\:?([0-9]+)?',
			machine_configuration['maxhours']).groups()]
		maxhours = tl[0]+float(tl[1])/60+float(tl[2])/60/60
		settings = {
			'maxhours':maxhours,
			'nprocs':machine_configuration['nprocs'],
			'tpbconv':gmxpaths['tpbconv'],
			'mdrun':gmxpaths['mdrun'],
			}
		#---! how should we parse multiple modules from the machine_configuration?
		if 'modules' in machine_configuration:
			need_modules = machine_configuration['modules']
			need_modules = [need_modules] if type(need_modules)==str else need_modules
			for m in need_modules: head += "module load %s\n"%m
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

	valid_meta_globs = glob.glob('inputs/meta*')+glob.glob('inputs/*/meta*')+\
		glob.glob('inputs/*/proc*')
	candidates = [(i,re.findall('^(.+)\.py',os.path.basename(i))[0]) for i in valid_meta_globs]
	if not script:
		print "[USAGE] make metarun <script>"
		print "[USAGE] available scripts: \n > "+'\n > '.join(zip(*candidates)[1])
	else:
		try: target, = [ii for ii,i in enumerate(zip(*candidates)[1]) if re.search(script,i)]
		except: raise Exception('[ERROR] failed to match %s with known scripts'%script)
		execfile(candidates[target][0])

def look(script='',dump=True,step=None):

	"""
	Drop into the wordspace for a script. 
	Useful for adding commands to a procedure without starting from scratch or making a new script.
	Example: after forgetting to add this line, we can make a continuation script from here:
	"from amx.base.functions import write_continue_script;write_continue_script()"
	Any actions you take here will continue to be recorded to the watch_file.
	"""

	#---! this is totally clumsy
	if not script: 
		script = max(glob.iglob('script-*.py'),key=os.path.getctime)
		print 'STATUS] resuming from the last step, apparently creeated by %s'%script
	cmd = '"import sys;sys.argv = [\'%s\'];from amx import *;resume(script_settings=\'%s\',step=%s);%s"'%(
		script,script,
		'None' if not step else step,
		"\nwith open('wordspace.json','w') as fp: json.dump(wordspace,fp);" if dump else '')
	print '[STATUS] running: python -i -c '+cmd
	os.system('python -i -c '+cmd)

def watch():

	"""
	Tail the logfile for the latest step.
	"""

	logfile = max(glob.iglob('script-*.log'),key=os.path.getctime)
	print '[STATUS] watching the last step, apparently written to %s'%logfile
	os.system('cat '+logfile)	

def delstep(number,confident=False,prefix='s'):

	"""
	Delete a step by number.
	Be very careful.
	"""

	target = int(number)
	fns = glob.glob('*%s%02d*'%(prefix,target))
	if not fns: 
		print "[STATUS] cannot find step %d to delete"%target
		return
	assert len(fns)==2
	assert any([re.match('^script-%s%02d-.+\.log$'%(prefix,target),i) for i in fns])
	assert any([re.match('^%s%02d-'%(prefix,target),i) for i in fns])
	extra_delete = ['wordspace.json','WATCHFILE']
	fns.extend([fn for fn in extra_delete if os.path.isfile(fn)])
	#---previously we cleared the associated script but this was not robust
	if False:
		#---try to identify the associated script and clear it too
		script, = glob.glob('%s%02d-*/script*.py'%(prefix,target))
		local_script = os.path.basename(script)
		if os.path.isfile(local_script): fns.append(local_script)
	print "[STATUS] preparing to remove step %d including %s"%(target,str(fns))
	if confident or all(re.match('^(y|Y)',raw_input('[QUESTION] %s (y/N)? '%msg))!=None
		for msg in ['okay to remove this entire step','confirm']):
		for fn in fns: 
			if os.path.isfile(fn): os.remove(fn)
			else: shutil.rmtree(fn)

def back(term=None,command=None):

	"""
	Run a prepared script in the background.
	"""

	if not term and not command:
		print '[STATUS] useage: "make back <name> or command="make metarun <key>" '+\
			'where you supply either the name of a script or a full command'
		return 1
	if term:
		if command: 
			print '[ERROR] you can only supply a name or a command when using "make back"'
			return 1
		finds = [i for i in glob.glob('script-*.py') if re.search(term,i)]
		if len(finds)!=1: print '[STATUS] useage: "make back <name>" '+\
			'where the name is a unique search for the script you want to run in the background'
		else: command = './'+finds[0]
	cmd = "nohup %s > log-back 2>&1 &"%command
	print '[STATUS] running the background via "%s"'%cmd
	job = subprocess.Popen(cmd,shell=True,cwd='./',preexec_fn=os.setsid)
	ask = subprocess.Popen('ps xao pid,ppid,pgid,sid,comm',
		shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	ret = '\n'.join(ask.communicate()).split('\n')
	pgid = next(int(i.split()[2]) for i in ret if re.match('^\s*%d\s'%job.pid,i))
	kill_script = 'script-stop-job.sh'
	term_command = 'pkill -TERM -g %d'%pgid
	with open(kill_script,'w') as fp: fp.write(term_command+'\n')
	os.chmod(kill_script,0744)
	print '[STATUS] if you want to terminate the job, run "%s" or "./%s"'%(term_command,kill_script)
	job.communicate()

def review(source):

	"""
	Retrieve a git repository designed for "inputs".
	"""

	try:
		cmds = ['git init',
			'git remote add origin %s'%source,
			'git fetch',
			'git checkout -t origin/master']
		for cmd in cmds: subprocess.call(cmd,
			cwd='./inputs',shell=True,executable='/bin/bash',stdin=subprocess.PIPE)
		print '[STATUS] loaded inputs with %s'%source
	except:
		print '[ERROR] failed to clone the git repository at "%s"'%source
		print '[USAGE] "make review <path_to_git_repo_for_inputs>"'

def help_review():

	print "[USAGE] make an inputs git repository via:"
	cmds = ['git init',"git commit -m 'initial commit'",'<add,commit files>',
		'git clone . --bare <path_to_new_bare_repo>']
	for cmd in cmds: print '[USAGE] "%s"'%cmd

#---INTERFACE
#-------------------------------------------------------------------------------------------------------------

def makeface(*arglist):

	"""
	Standard interface to makefile.
	"""

	#---stray characters
	arglist = tuple(i for i in arglist if i not in ['w','--','s','ws'])
	#---unpack arguments
	if arglist == []: 
		raise Exception('[ERROR] no arguments to controller')
	args,kwargs = [],{}
	arglist = list(arglist)
	funcname = arglist.pop(0)
	#---regex for kwargs. note that the makefile organizes the flags for us
	regex_kwargs = '^(\w+)\="?([\w:\-\.\/\s]+)"?$'
	while arglist:
		arg = arglist.pop()
		#---note that it is crucial that the following group contains all incoming 
		if re.match(regex_kwargs,arg):
			parname,parval = re.findall(regex_kwargs,arg)[0]
			parname,parval = re.findall('^(\w+)\="?([\w:\-\.\/\s]+)"?$',arg)[0]
			kwargs[parname] = parval
		else:
			argspec = inspect.getargspec(globals()[funcname])
			if arg in argspec.args: kwargs[arg] = True
			else: args.append(arg)
	args = tuple(args)
	if arglist != []: raise Exception('unprocessed arguments %s'%str(arglist))

	#---"command" is a protected keyword
	if funcname != 'back' and 'command' in kwargs: kwargs.pop('command')
	print '[CONTROLLER] calling %s with args="%s" and kwargs="%s"'%(funcname,args,kwargs)

	#---call the function
	globals()[funcname](*args,**kwargs)

#---MAIN
#-------------------------------------------------------------------------------------------------------------

if __name__ == "__main__": 

	#---if the function is not above check extra scripts
	if sys.argv[1] not in globals(): 
		#---execute instead of importing for simplicity
		for fn in glob.glob('./amx/procedures/extras/*.py'): execfile(fn)
		#---assume the target is in one of the extras
		globals()[sys.argv[1]](*[i for i in sys.argv[2:] if i not in ['w','--','s']])
	else: makeface(*sys.argv[1:])
