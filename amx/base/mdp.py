#!/usr/bin/python

import re
from copy import deepcopy
from amx import wordspace
from amx.base.journal import *

def delve(o,*k): return delve(o[k[0]],*k[1:]) if len(k)>1 else o[k[0]]

@narrate
def write_mdp(param_file=None,rootdir='./',outdir='',extras=None):

	"""
	Universal MDP file writer which creates input files based on a unified dictionary.
	All MDP parameters should be stored in *mdpdefs* within ``inputs/input_specs_mdp.py``. 
	We assemble MDP files according to rules that can be found in the *mdp* entry for the specs 
	dictionary contained in the ``input_specs_PROCEDURE.py`` file. Other simulation steps may 
	use this function to access the mdp_section entry from the same specs dictionary in order 
	to write more MDP files for e.g. equilibration steps.

	In the ``inputs/input_specs_mdp.py`` file we define the "mdpdefs" (read: Molecular Dynamics 
	Parameter DEFinitionS) dictionary, which is a customizable description of how to run the GROMACS 
	integrator. The mdpdefs variable has a few specific kinds of entries denoted by comments and
	and described here.
	
	The top level of mdpdefs is a "group" set in the *mdp* entry of the specs dictionary. This allows us
	to organize our parameters into distinct groups depending on the task. For example, we might have 
	different groups of parameters for coarse-grained and atomistic simulations. We whittle the full
	mdpspecs dictionary by the group name below.
	
	Our whittled dictionary then contains three kinds of entries.
	
	1. The entry called ``defaults`` is a dictionary which tells you which dictionaries to use if no extra information is provided. Each key in the defaults dictionary describes a type of parameters (e.g. "output" refers to the parameters that specify how to write files). If the associated value is "None" then we assume that the key is found at the top level of mdpdefs. Otherwise the value allows us to descend one more level and choose between competing sets of parameters.
	2. Other entries with keys defined in ``defaults`` contain either a single dictionary for that default (recall that we just use None to refer to these) or multiple dictionaries with names referred to by the defaults. These entries are usually grouped by type e.g. output or coupling parameters.
	3. Override keys at the top level of mdpdefs which do not appear in defaults contain dictionaries which are designed to override the default ones wholesale. They can be used by including their names in the list associated with a particular mdp file name in specs. If they contain a dictionary, then this dictionary will override the default dictionary with that key. Otherwise, they should contain key-value pairs that can lookup a default in the same way that the defaults section does.
	
	Except for the "group" entry, the specs[mdp_section] (remember that this is defined in 
	``input_specs_PROCEDURE.py``should include keys with desired MDP file names pointing to lists that 
	contain override keys and dictionaries. If you include a dictionary in the value for a particular MDP 
	file then its key-value pairs will either override an MDP setting directly or override a key-value
	pair in the defaults.
	"""

	mdpspecs = wordspace['mdp_specs'] if not extras else extras

	if not param_file:
		custom_mdp_parameters = 'inputs/parameters.py'
		if os.path.isfile(custom_mdp_parameters):
			param_file = custom_mdp_parameters
			report('found custom parameters.py in inputs',tag='status')
		else: 
			param_file = 'amx/procedures/parameters.py'
			report('using amx/procedures/parameters.py for mdp parameters',tag='status')

	#---retrieve the master inputs file
	mdpfile = {}
	execfile(param_file,mdpfile)
	mdpdefs = mdpfile['mdpdefs']

	#--topkeys is the root node for our parameters in mdpdict
	mdpdefs = mdpdefs[mdpspecs['group']] if (mdpspecs and 'group' in mdpspecs) else mdpdefs
	mdpspecs = [] if not mdpspecs else mdpspecs
	#---loop over each requested MDP file
	for mdpname in [i for i in mdpspecs if re.match('.+\.mdp$',i)]:
		settings = {}
		#---run through defaults and add them to our MDP file dictionary
		#---the defaults list contains keys that name essential sections of every MDP file
		for key,val in mdpdefs['defaults'].items():
			#---if default says None then we get the parameters for that from the top level
			if val==None: settings[key] = deepcopy(mdpdefs[key])
			else: settings[key] = deepcopy(mdpdefs[key][val])
		#---refinements are given in the mdpspecs dictionary
		if mdpspecs[mdpname] != None:
			for refinecode in mdpspecs[mdpname]:
				#---if the refinement code in the list given at mdpspecs[mdpname] is a string then we
				#---...navigate to mdpdefs[refinecode] and use its children to override settings[key] 
				if type(refinecode) in [str,unicode]:
					for key,val in mdpdefs[refinecode].items():
						#---if the value for an object in mdpdefs[refinecode] is a dictionary, we 
						#---...replace settings[key] with that dictionary
						if type(val)==dict: settings[key] = deepcopy(val)
						#---otherwise the value is really a lookup code and we search for a default value
						#---...at the top level of mdpdefs where we expect mdpdefs[key][val] to be 
						#---...a particular default value for the MDP heading given by key
						elif type(val) in [str,unicode]: settings[key] = deepcopy(mdpdefs[key][val])				
						else: raise Exception('unclear refinecode = '+refinecode+', '+key+', '+str(val))
				#---if the refinement code is a dictionary, we iterate over each rule
				else:
					for key2,val2 in refinecode.items():
						#---if the rule is in the top level of mdpdefs then it selects groups of settings
						if key2 in mdpdefs.keys(): 
							report('using MDP override collection: '+key2+': '+str(val2),tag='note')
							settings[key2] = deepcopy(mdpdefs[key2][val2])
						#---if not, then we assume the rule is meant to override a native MDP parameter
						#---...so we check to make sure it's already in settings and then we override
						elif key2 in [j for k in [settings[i].keys() for i in settings] for j in k]:
							report('overriding MDP parameter: '+key2+': '+str(val2),tag='note')
							for sub in settings:
								if key2 in settings[sub]: settings[sub][key2] = deepcopy(val2)
						else: 
							raise Exception(
								'cannot comprehend one of your overrides: '+
								str(key)+' '+str(val))
		#---completely remove some items if they are set to -1, specifically the flags for trr files
		for key in ['nstxout','nstvout']:
			for heading,subset in settings.items():
				if key in subset and subset[key] == -1: subset.pop(key)
		#---always write to the step directory
		with open(rootdir+'/'+wordspace['step']+'/'+mdpname,'w') as fp:
			for heading,subset in settings.items():
				fp.write('\n;---'+heading+'\n')
				for key,val in subset.items():
					fp.write(str(key)+' = '+str(val)+'\n')
