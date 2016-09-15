#!/usr/bin/python

from amx import wordspace
from amx.base.gmxwrap import report,bash
from amx.base.journal import *
from amx.base.tools import *
import os,shutil,re,subprocess,glob,json

#---LANGUAGE FUNCTIONS
#-------------------------------------------------------------------------------------------------------------

@narrate
def continue_simulation_from(path,needs_topology=True):

	"""
	Continuation receives the path of the last known production run and collects necessary files.
	"""

	#---deposit the necessary files here unless 'active_step_directory' is in the wordspace
	dest = wordspace['step']+'/' if 'step' in wordspace else './'

	report('collecting continuation files')
	fullpath = os.path.abspath(os.path.expanduser(path))
	#---if path follows the step format then we grap the latest CPT and TPR otherwise we get the latest step
	step_regex = '^([a-z][0-9]+)-'
	if re.match(step_regex,fullpath): 
		cwd = fullpath
		step_list = []
		raise Exception('DEV DEV DEV')
	else:
		#---get list of steps
		for root,dirnames,filenames in os.walk(fullpath): break
		steps = dict([(re.findall(step_regex,i).pop(),i) for i in dirnames if re.match(step_regex,i)])
		cwd = fullpath+'/'+steps[sorted(steps.keys())[-1]]
	for root,dirnames,filenames in os.walk(cwd): break
	#---get the latest step number from the CPT file list
	lastpart = max([int(a[0]) if a else None for a in filter(None,
		[re.findall('^md.part([0-9]{4}).cpt',f) for f in filenames])])
	#---copy CPT and TPR
	incoming = ['md.part%04d.%s'%(lastpart,s) for s in ['cpt','tpr']]
	for fn in incoming: shutil.copy(cwd+'/%s'%fn,dest+fn)
	if os.path.isfile(cwd+'/md.part%04d.gro'%lastpart):
		shutil.copy(cwd+'/md.part%04d.gro'%lastpart,dest+'md.part%04d.gro'%lastpart)
	else:
		report('converting CPT to GRO')
		#---convert CPT to GRO
		proc = subprocess.Popen(
			'gmx trjconv -f md.part%04d.cpt -o md.part%04d.gro -s md.part%04d.tpr'%
			(lastpart,lastpart,lastpart),cwd=dest,shell=True,executable='/bin/bash',
			stdout=subprocess.PIPE,stdin=subprocess.PIPE,stderr=subprocess.PIPE)
		back = proc.communicate(input='0\n')
	#---get ITP and TOP
	found_top,found_itp = False,False
	if needs_topology:
		report('retrieving topology files')
		for stepkey in sorted(steps.keys())[::-1]:
			print '[STATUS] checking %s'%steps[stepkey]
			cwd = fullpath+'/'+steps[stepkey]+'/'
			for root,dirnames,filenames in os.walk(cwd): break
			if 'system.top' in filenames: 
				shutil.copy(cwd+'system.top',dest+'system.top')
				found_top = True
			itps = [fn for fn in filenames if re.match('^.+.itp',fn)]
			if any(itps):
				for itp in itps: shutil.copy(cwd+itp,dest+itp)
				found_itp = True
			if found_top and found_itp: break

@narrate
def get_last_part(suffix='cpt'):

	"""
	Find the most recent GRO file in the current directory.
	"""

	cwd = wordspace['step'] if 'step' in wordspace else './'
	for root,dirnames,filenames in os.walk(os.path.abspath(cwd)): break
	lastpart = max([int(a[0]) if a else None for a in filter(None,
		[re.findall('^md.part([0-9]{4}).%s'%suffix,f) for f in filenames])])
	return 'md.part%04d.%s'%(lastpart,suffix)

@narrate
def get_next_part(suffix='tpr'):

	cwd = wordspace['step'] if 'step' in wordspace else './'
	for root,dirnames,filenames in os.walk(os.path.abspath(cwd)): break
	lastpart = max([int(a[0]) if a else None for a in filter(None,
		[re.findall('^md.part([0-9]{4}).%s'%suffix,f) for f in filenames])])
	return lastpart+1

@narrate
def script(script,*args,**kwargs):

	"""
	Execute a python script using the script keyword in automacs lingo.
	"""

	if 'cwd' in kwargs: cwd = kwargs['cwd']
	else: cwd = wordspace['root_directory']
	kwargs['cwd'] = cwd
	cmd = 'python %s %s %s'%(
		wordspace['root_directory']+'/'+script,' '.join(args),
		' '.join([key+'='+val for key,val in kwargs.items()]))
	report('running python script via "%s"'%cmd)
	proc = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,executable='/bin/bash',
		stdin=subprocess.PIPE,stderr=subprocess.PIPE,cwd=cwd)
	back = proc.communicate()
	for std in back:
		if std != '': report(std,tag='')

def detect_root_directory():

	"""
	Save the root directory to the wordspace.
	"""

	if 'root_directory' not in wordspace:
		wordspace['root_directory'] = os.path.abspath('.')+'/'

def start_decide_stepname():

	"""
	Local wordspaces require access to the inferred stepname.
	"""

def start(name,prefix='s'):

	"""
	Start a new step and register it.
	"""

	if wordspace['under_development']: 
		report('looks like we are developing so skipping start',tag='warning')
		return

	#---register root
	detect_root_directory()
	#---get the most recent step number
	for root,dirnames,filenames in os.walk(os.path.abspath('.')): break
	stepdirs = [d for d in dirnames if re.match('^%s[0-9]+'%prefix,d)]
	if stepdirs == []: last_step = 0
	else: last_step = max([int(re.findall('^%s([0-9]+)'%prefix,d).pop()) for d in stepdirs])

	#---if the step name follows the format then we use it verbatim
	regex_generic_step = '^[a-z][0-9]{2,}\-\w+'
	if re.match(regex_generic_step,name): step_name = name
	else: step_name = '%s%02d-%s'%(prefix,last_step+1,name)
	if not os.path.exists(step_name): 
		os.mkdir(step_name)
		os.chmod(step_name,0o2775)

	wordspace['step'] = os.path.join(step_name,'')
	#---register the step directory in the namespace
	if stepdirs != []: 
		wordspace['last'] = os.path.join(
			next(i for i in stepdirs if int(re.findall('^%s([0-9]+)-'%prefix,i)[0])==last_step),'')
	wordspace['watch_file'] = 'script-'+step_name+'.log'
	#---write the bash log inside each step
	wordspace['bash_log'] = os.path.join(wordspace['step'],'script-'+step_name+'.sh')
	logfile = wordspace['watch_file']
	#---disabled the following so that we could route error logs here from tasks.py by inferring the log
	#---....if os.path.isfile(logfile): raise Exception('logfile %s exists'%logfile)
	with open(wordspace['bash_log'],'a') as fp: 
		fp.write('#!/bin/bash\n\n#---automacs instruction set\n\n')
	#---copy the calling script to this location for posterity
	filecopy(wordspace['script'],wordspace['step']+os.path.basename(wordspace['script']))
	#---files keyword in the settings block refers to files that should be copied from inputs
	if 'files' in wordspace:
		for fn in wordspace['files']: 
			if not os.path.isfile(wordspace['step']+os.path.basename(fn)): 
				#---files in subfolders in the inputs folder are elevated here
				filecopy('inputs/'+fn,wordspace['step']+os.path.basename(fn))
	#---sources keyword in the settings block refers to directories that should be copied from inputs
	if 'sources' in wordspace:
		for dn in wordspace['sources']: 
			if not os.path.isdir(wordspace['step']+dn): dircopy('inputs/'+dn,wordspace['step'])
			
@narrate
def filecopy(src,dest):

	"""
	Wrap shutil.copy for copying files.
	"""

	shutil.copy(src,dest)

@narrate
def filemove(src,dest):

	"""
	Wrap shutil.move for renaming files.
	"""

	shutil.move(src,dest)

@narrate
def dircopy(src,dest):

	"""
	Copy any directories that match the glob in src.
	"""

	for folder in [d for d in glob.glob(src) if os.path.isdir(d)]:
		if not os.path.isdir(dest+'/'+os.path.basename(folder)):
			shutil.copytree(folder,dest+'/'+os.path.basename(folder))
		
def resume(script_settings='',add=False,read_only=False,step=None):

	"""
	Continue a simulation procedure that was halted by extracting the wordspace 
	from checkpoing lines in the log file. Set add flag to remove the step from the wordspace
	in order to load the wordspace before an additional step. 
	Always run resume before start.
	Use the read flag to get data from the previous wordspace without writing to the new one.
	"""

	#---preserve settings in case we are doing an additional step
	if add: new_step = wordspace['step']
	if not step:
		try:
			last_step_num = max(map(
				lambda z:int(z),map(
				lambda y:re.findall('^s([0-9]+)',y).pop(),filter(
				lambda x:re.match('^s[0-9]+-\w+$',x),glob.glob('s*-*')))))
		except: raise Exception('[ERROR] could not find the last step')
	else: last_step_num = step
	last_step = filter(lambda x:re.match('^s%02d'%last_step_num,x),glob.glob('s*-*')).pop()
	status('[STATUS] resuming from %s'%last_step)
	with open('script-%s.log'%last_step,'r') as fp: lines = fp.readlines()
	regex_wordspace = '^\[CHECKPOINT\]\s+wordspace\s*=\s*(.+)'
	try:
		add_wordspace = {}
		add_wordspace = json.loads(re.findall(regex_wordspace,
			filter(lambda x:re.search(regex_wordspace,x),lines[::-1])[0])[0])
		if not read_only:
			for key,val in add_wordspace.items(): wordspace[key] = val
	except: pass	
	if read_only: return add_wordspace
	#---override original settings if available, using code from gmxwrap.init
	#---! does this block need to be modified for read_only?
	#---note that step overrides script_settings
	if script_settings != '' and not step:
		settings = yamlparse(script_settings)
		for key,val in settings.items(): 
			if key not in ['step']:
				wordspace[re.sub(' ','_',key) if key not in ['start_structure'] else key] = val
	#---if we wish to use resume to get the checkpoint from a previous step, we remove the step variable
	#---...so that start makes a new directory with the correct naming scheme. this allows us to retain
	#---...the previous wordspace on a new step
	if add: wordspace['step'] = new_step
	#---! reset the under_development flag on resume (NEEDS CHECKED)
	wordspace['under_development'] = False
			
def interpret_command(block):

	"""
	A function which converts a raw command library into a nested dictionary for use by "amx.gmx".
	"""

	commands = {}
	for line in block.split('\n'):
		if not re.match('^\s*$',line):
			utility = re.findall('^([gmx\s+]?\w+)',line).pop() 
			flags_string = re.findall('^[gmx\s+]?\w+\s*(.+)',line).pop() 
			flags = flags_string.split()
			specs = dict([flags[2*i:2*i+2] for i in range(len(flags)/2)])
			commands[utility] = specs
	return commands

@narrate
def write_continue_script(script='script-continue.sh',machine_configuration=None,**kwargs):

	"""
	Uses a template in amx/procedures to write a bash continuation script.
	"""

	#---assume that the scripts are in the scripts folder
	with open(os.path.join('amx/procedures/scripts',script),'r') as fp: lines = fp.readlines()
	#---settings required for continuation script
	#---! get these from the proper setup
	from amx.base.gromacs import gmxpaths,machine_configuration
	settings = {
		'maxhours':24,
		'extend':100000,
		'start_part':1,
		'tpbconv':gmxpaths['tpbconv'],
		'mdrun':gmxpaths['mdrun'],
		'grompp':gmxpaths['grompp'],
		'maxwarn':0,
		}

	settings.update(**kwargs)
	setting_text = '\n'.join([
		str(key.upper())+'='+('"' if type(val)==str else '')+str(val)+('"' if type(val)==str else '') 
		for key,val in settings.items()])
	modules = machine_configuration.get('modules',None)
	if modules:
		modules = [modules] if type(modules)==str else modules
		#---if gromacs is in any of the modules we try to unload gromacs
		if any([re.search('gromacs',i) for i in modules]):
			setting_text += '\nmodule unload gromacs'
		for m in modules: setting_text += '\nmodule load %s'%m
	lines = map(lambda x: re.sub('#---SETTINGS OVERRIDES HERE$',setting_text,x),lines)
	wordspace['continuation_script'] = script_fn = script
	with open(wordspace['step']+script_fn,'w') as fp:
		for line in lines: fp.write(line)
	os.chmod(wordspace['step']+script_fn,0744)
	
@narrate
def continuation():

	"""
	Execute the continuation script.
	"""

	write_continue_script()
	bash('./'+wordspace['continuation_script'])
	
def get_last_wordspace(step,*args):

	"""
	Retrieve the last wordspace from a previous step.
	"""

	caught = {}
	for arg in args:
		regex_catch = '>>>([^\s]+)'
		cmd = 'make look step=%d'%int(re.findall('s([0-9]+)',step)[0])
		proc = subprocess.Popen(cmd,cwd='./',shell=True,
			stdout=subprocess.PIPE,stderr=subprocess.PIPE,stdin=subprocess.PIPE)
		catch = '\n'.join(proc.communicate(input="print '>>>'+str(wordspace['%s'])\n"%arg))
		values = [re.findall(regex_catch,i)[0] for i in catch.split('\n') if re.match(regex_catch,i)][0]
		caught[arg] = values
	import pdb;pdb.set_trace()
	return values