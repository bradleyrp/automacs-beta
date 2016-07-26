#!/usr/bin/python

class WordSpace(dict):

	"""
	Custom dictionary which holds key variables
	and (inevitable) returns intelligent errors.
	"""
	
	def __getattribute__(self,key):

		"""
		Honestly this is a sick functionality that lets you run e.g. 
		wordspace.step instead of wordspace['step'].
		"""

		if key in self: return self[key]
		else: return dict.__getattribute__(self,key)

	def __setattr__(self,key,value):

		"""
		Assign items as attributes.
		"""

		if key not in dict.__dict__:
			dict.__setitem__(self,key,value)
		else: raise Exception('[ERROR] cannot set the %s key in the wordspace'%key)

	def __getitem__(self,key):

		"""
		Intelligent warnings for some functions.
		"""

		if key=='last' and key not in self:
			raise Exception("".join([
				"[ERROR] wordspace['last'] is not defined ...",
				"[ERROR] it is likely that you started AMX from a downstream step"]))
		elif key not in self:
			if key == 'watch_file':
				print('[ERROR] watch_file not defined yet so returning "WATCHFILE"')
				return "WATCHFILE"
			elif key == 'under_development': return False
		return dict.get(self,key)

class WordSpaceLook():
	def __init__(self,d): self.__dict__ = d
	def __getitem__(self,i): return self.__dict__[i]

#---always import amx into globals
#---assume these variables make it to the global scope 
wordspace = WordSpace()

import sys,os

#---custom imports according to the procedure from the script that imported amx
wordspace['script'] = os.path.basename(os.path.abspath(os.getcwd()+'/'+sys.argv[0]))
#---skip setup if we are only making docs or running a view script
script_call = os.path.basename(wordspace['script'])

#---sphinx requires imports for documentation so we add the right path if compiling docs
if script_call == 'sphinx-build': sys.path.insert(0,os.path.abspath('../../../amx'))

from base.functions import *
from base.mdp import write_mdp
from base.gmxwrap import *
from base.metatools import *
from procedures.common import *

if (not script_call in ['sphinx-build','script-vmd.py'] and 
	not re.match('^script-vmd',script_call)):
	#---instead of running the parent script we pick off the requires list
	regex_requires = '^requires\s*:\s*([\w,]+)$'
	#---search for procedures to import
	with open(wordspace['script'],'r') as fp: original_script_lines = fp.read()
	has_requires = re.search(regex_requires,original_script_lines,re.M)
	if has_requires:
		reqs = has_requires.group(1).split(',')
		#---check for importlib (not available in python versions before 2.7)
		importlib_avail = True
		try: import importlib
		except: 
			importlib_avail = False
			report('cannot import importlib so you are on an old system and we will '+
				'skip loading procedure codes',tag='warning')
		#---loop over required modules and import them
		for libfile in reqs:
			#---use old-school importing if importlib is not available
			if importlib_avail: mod = importlib.import_module('amx.procedures.'+libfile)
			else: mod = __import__('amx.procedures.%s'%libfile,fromlist=['amx.procedures.%s'%libfile])
			#---WARNING functions may be redefined in subsequent requirements
			globals().update(vars(mod))
			#---propagate the last-read command_library and mdp_specs to the wordspace
			if 'command_library' in globals(): 
				wordspace['command_library'] = interpret_command(command_library)
			if 'mdp_specs' in globals(): wordspace['mdp_specs'] = mdp_specs

