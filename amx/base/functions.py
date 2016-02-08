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
			(lastpart,lastpart,lastpart),cwd=dest,shell=True,
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
	proc = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,
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

def start(name):

	"""
	Start a new step and register it.
	"""

	#---register root
	detect_root_directory()
	#---get the most recent step number
	for root,dirnames,filenames in os.walk(os.path.abspath('.')): break
	stepdirs = [d for d in dirnames if re.match('^s[0-9]+',d)]
	if stepdirs == []: last_step = 0
	else: last_step = max([int(re.findall('^s([0-9]+)',d).pop()) for d in stepdirs])
	#---make the new step directory
	step_name = 's%02d-%s'%(last_step+1,name)
	if os.path.exists(step_name): raise Exception('step directory %s already exists'%step_name)
	os.mkdir(step_name)
	os.chmod(step_name,0o2775)
	#---register the step directory in the namespace
	if stepdirs != []: 
		wordspace['last'] = os.path.join(
			next(i for i in stepdirs if int(re.findall('^s([0-9]+)-',i)[0])==last_step),'')
	wordspace['step'] = os.path.join(step_name,'')
	wordspace['watch_file'] = 'script-'+step_name+'.log'
	wordspace['bash_log'] = 'script-'+step_name+'.sh'
	logfile = wordspace['watch_file']
	if os.path.isfile(logfile): raise Exception('logfile %s exists'%logfile)
	with open(wordspace['bash_log'],'a') as fp: 
		fp.write('#!/bin/bash\n\n#---automacs instruction set\n\n')
	#---copy the calling script to this location for posterity
	filecopy(wordspace['script'],wordspace['step']+os.path.basename(wordspace['script']))
	#---files keyword in the settings block refers to files that should be copied from inputs
	if 'files' in wordspace:
		fns = eval(wordspace['files'])
		for fn in fns: 
			if not os.path.isfile(wordspace['step']+fn): filecopy('inputs/'+fn,wordspace['step']+fn)
	#---sources keyword in the settings block refers to directories that should be copied from inputs
	if 'sources' in wordspace:
		source_dirs = eval(wordspace['sources'])
		for dn in source_dirs: 
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
def dircopy(src,dest,permissive=False):

	"""
	Copy any directories that match the glob in src.
	"""

	for folder in [d for d in glob.glob(src) if os.path.isdir(d)]:
		if not os.path.isdir(dest+'/'+os.path.basename(folder)):
			shutil.copytree(folder,dest+'/'+os.path.basename(folder))
		
def resume(init_settings=''):

	"""
	Continue a simulation procedure that was halted by extracting the wordspace 
	from checkpoing lines in the log file.
	"""

	last_step_num = max(map(
		lambda z:int(z),map(
		lambda y:re.findall('^s([0-9]+)',y).pop(),filter(
		lambda x:re.match('^s[0-9]+-\w+$',x),glob.glob('s*-*')))))
	last_step = filter(lambda x:re.match('^s%02d'%last_step_num,x),glob.glob('s*-*')).pop()
	with open('script-%s.log'%last_step,'r') as fp: lines = fp.readlines()
	regex_wordspace = '^\[CHECKPOINT\]\s+wordspace\s*=\s*(.+)'
	add_wordspace = json.loads(re.findall(regex_wordspace,
		filter(lambda x:re.search(regex_wordspace,x),lines[::-1])[0])[0])
	for key,val in add_wordspace.items(): wordspace[key] = val
	
	#---override original settings if available, using code from gmxwrap.init
	if init_settings != '':
		settings = yamlparse(init_settings)
		for key,val in settings.items(): 
			if key not in ['step']:
				wordspace[re.sub(' ','_',key) if key not in ['start_structure'] else key] = val
		
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
def write_continue_script():

	"""
	Uses a template in amx/procedures to write a bash continuation script.
	"""
	
	with open('amx/procedures/scripts/script-continue.sh','r') as fp: lines = fp.readlines()
	#---settings required for continuation script
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
	wordspace['continuation_script'] = script_fn = 'script-continue.sh'
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
	
