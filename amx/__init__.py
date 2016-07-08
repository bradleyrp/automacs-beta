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
from base.functions import *
from base.mdp import write_mdp
from base.gmxwrap import *
from procedures.toc import procedure_toc
from base.metatools import *

#---custom imports according to the procedure from the script that imported amx
wordspace['script'] = os.path.basename(os.path.abspath(os.getcwd()+'/'+sys.argv[0]))
#---skip setup if we are only making docs or running a view script
script_call = os.path.basename(wordspace['script'])
if (not script_call in ['sphinx-build','script-vmd.py'] and 
	not re.match('^script-vmd',script_call)):
	with open(wordspace['script'],'r') as fp: original_script_lines = fp.readlines()
	try: 
		procedure = [re.findall('^procedure\s*:\s*([\w,]+)',l)[0] 
			for l in original_script_lines if re.match('^procedure\s*:\s*([\w,]+)',l)]
		if len(procedure)!=1 and len(list(set(procedure)))>1:
			raise Exception('[ERROR] procedure = %s'%str(procedure))
		else: procedure = procedure[0]
	except: raise Exception('[ERROR] could not find "procedure: <name>" in the script')
	importlib_avail = True
	try: import importlib
	except: 
		importlib_avail = False
		report('cannot import importlib so you are on an old system and we will '+
			'skip loading procedure codes',tag='warning')
	libfile = False
	if procedure in procedure_toc: libfile = procedure_toc[procedure]
	#---pass if you only find scripts without warning the user
	elif any(glob.glob('amx/procedures/scripts/script-%s*'%procedure)): pass
	else: raise Exception('[ERROR] unclear procedure "%s" with no corresponding scripts'%procedure)
	if not libfile: libfile = 'common'
	if importlib_avail: mod = importlib.import_module('amx.procedures.'+libfile)
	else: mod = __import__('amx.procedures.%s'%libfile,fromlist=['amx.procedures.%s'%libfile])
	globals().update(vars(mod))
	if 'command_library' in globals(): 
		if 'command_library' not in wordspace:
			wordspace['command_library'] = interpret_command(command_library)
	if 'mdp_specs' in globals(): wordspace['mdp_specs'] = mdp_specs
