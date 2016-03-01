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
			raise Exception("\n[ERROR]".join([
				"wordspace['last'] is not defined",
				"it is likely that you started AMX from a downstream step"]))
		elif key not in self: raise Exception('\n[ERROR] "%s" not found in wordspace'%key)
		return dict.get(self,key)

class WordSpaceLook():
	def __init__(self,d): self.__dict__ = d
	def __getitem__(self,i): return self.__dict__[i]

wordspace = WordSpace()		
import sys,os,importlib
from base.functions import *
from base.mdp import write_mdp
from base.gmxwrap import *
from procedures.toc import procedure_toc

#---custom imports according to the procedure from the script that imported amx
wordspace['script'] = os.path.abspath(os.getcwd()+'/'+sys.argv[0])
#---skip setup if we are only making docs
if not os.path.basename(wordspace['script'])=='sphinx-build':
	with open(wordspace['script'],'r') as fp: original_script_lines = fp.readlines()
	try: 
		procedure = [re.findall('^procedure:\s*([\w,]+)',l)[0] 
			for l in original_script_lines if re.match('^procedure:\s*([\w,]+)',l)]
		if len(procedure)!=1 and len(list(set(procedure)))>1:
			raise Exception('[ERROR] procedure = %s'%str(procedure))
		else: procedure = procedure[0]
	except: raise Exception('[ERROR] could not find "procedure: <name>" in the script')
	#---automatically load the correct function library
	if procedure in procedure_toc:
		libfile = procedure_toc[procedure]
		mod = importlib.import_module('amx.procedures.'+libfile)
		globals().update(vars(mod))
		wordspace['command_library'] = interpret_command(command_library)
		wordspace['mdp_specs'] = mdp_specs
	else: raise Exception('[ERROR] unclear procedure "%s" see procedures.toc'%procedure)

