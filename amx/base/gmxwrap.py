#!/usr/bin/python

from amx import wordspace
from amx.base.gromacs import *
from amx.base.journal import *
import os,shutil,re,subprocess,json,glob
try: import yaml
except: print '[WARNING] yaml is missing'

#---FUNCTIONS
#-------------------------------------------------------------------------------------------------------------

@narrate
def queue():
	
	"""
	Queue tells the code whether to execute new commands immediately or queue them in a script for later.
	"""
	
	wordspace['queue'] = True

@narrate
def gmx_run(cmd,log,skip=False,inpipe=None):

	"""
	Run a GROMACS command instantly and log the results to a file.
	"""

	if log == None: raise Exception('[ERROR] gmx_run needs a log file to route output')
	if 'bash_log' in wordspace: 
		with open(wordspace['bash_log'],'a') as fp: fp.write(cmd+' &> log-'+log+'\n')
	else: raise Exception('missing log from wordspace')
	output = open(wordspace['step']+'log-'+log,'w')
	if inpipe == None:
		proc = subprocess.Popen(cmd,cwd=wordspace['step'],shell=True,stdout=output,stderr=output)
		proc.communicate()
	else:
		proc = subprocess.Popen(cmd,cwd=wordspace['step'],shell=True,
			stdout=output,stderr=output,stdin=subprocess.PIPE)
		proc.communicate(input=inpipe)
	#---check for errors
	with open(wordspace['step']+'log-'+log,'r') as logfile:
		for line in logfile:
			for msg in gmx_error_strings:
				if re.search(msg,line)!=None: 
					if skip: report('[NOTE] command failed but nevermind')
					else: raise Exception('[ERROR] %s in log-%s'%(msg.strip(':'),log))

@narrate
def gmx(program ,**kwargs):

	"""
	Construct a GROMACS command and either run it or queue it in a script.
	"""

	#---if a queue was started we wait for execution
	log = kwargs.pop('log') if 'log' in kwargs else None
	#---extra flags let the user add custom flags to the final command
	extra_flags = kwargs.pop('flag') if 'flag' in kwargs else None
	#---if program is interactive we check the inpipe
	inpipe = kwargs.pop('inpipe') if 'inpipe' in kwargs else None
	#---skip copies the incoming file to BASE.gri
	if 'skip' in kwargs and kwargs['skip']: 
		assert 'base' in kwargs
		skip = kwargs.pop('skip')	
	else: skip = False	
	cmd = gmxpaths[program]+' '
	#---check extra_flags for automatic overrides in the flag string
	if extra_flags != None:
		override_keys = [key for key in wordspace['command_library'][program]
			if re.search(key+' ',extra_flags)]
	else: override_keys = []
	#---iterate over each item in the command library entry for a particular gromacs program
	for flag,rule in wordspace['command_library'][program].items():
		value = str(rule)
		for key in kwargs: value = re.sub(key.upper(),kwargs[key],value)
		value = re.sub('NONE','',value)
		if flag not in override_keys: cmd += flag+' '+value+' '
	if extra_flags != None: cmd += extra_flags
	#---! correctly handled below?
	if 'queue' in wordspace and wordspace['queue']:
		if log != None: cmd += ' &> %s'%log
		if 'command_queue' not in wordspace: wordspace['command_queue'] = []
		wordspace['command_queue'].append(cmd)
	else: gmx_run(cmd,log=log,skip=skip,inpipe=inpipe)

@narrate
def gmxscript(script_file):

	"""
	Prepare a local script.
	"""
	
	#---! do not overwrite script?
	with open(wordspace['step']+script_file+'.sh','w') as fp:
		fp.write('#!/bin/bash\n')
		for cmd in wordspace['command_queue']: fp.write(cmd+'\n')
	report('wrote local execution script %s'%script_file)
	wordspace['local_script'] = script_file
	
@narrate
def bash(command,log=None,cwd=None):

	"""
	Run a bash command
	"""
	
	cwd = wordspace['step'] if cwd == None else cwd
	if log == None: 
		subprocess.call(command,cwd=cwd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	else:
		output = open(cwd+log,'w')
		proc = subprocess.Popen(command,cwd=cwd,shell=True,stdout=output,stderr=output)
		proc.communicate()

@narrate
def checkpoint():

	"""
	At the end of a GROMACS procedure, write the wordspace to the log file started by the logger.
	"""

	#---do not try to save modules if they are imported
	for mod in ['re']: 
		if mod in wordspace: wordspace.pop(mod)
	#---clean up step files and hash files
	for root,dirnames,filenames in os.walk(wordspace['step']): break
	useless_files = [i for i in filenames if re.match('^\#?step',i)]
	for fn in useless_files: os.remove(root+'/'+fn)
	with open(wordspace['watch_file'],'a') as fp:
		report('wordspace = '+json.dumps(wordspace),tag='checkpoint')

def init(setting_string):

	"""
	Automatically load settings from the python-amx script into the wordspace for safekeeping.
	"""

	os.umask(002)
	settings = yaml.load(setting_string)
	for key,val in settings.items(): wordspace[re.sub(' ','_',key)] = val
	#---for convenience we automatically substitute a lone PDB file in inputs
	#---! note that this is protein-atomistic specific and may need to be conditional
	if wordspace['start_structure'] == 'inputs/STRUCTURE.pdb': 
		print "DERP"
		pdbs = glob.glob('inputs/*.pdb')
		if len(pdbs)==1: 
			wordspace['start_structure'] = pdbs[0]
			wordspace['system_name'] = re.findall('^inputs/(\w+)\.pdb$',pdbs[0])[0]
		else: report('multiple PDBs in inputs/ and start_structure is still default',tag='warning')

