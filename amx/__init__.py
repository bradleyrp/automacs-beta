#!/usr/bin/python

#---wordspace tracks and writes all relevant variables
wordspace = {}
from base.functions import *
from base.mdp import write_mdp
from base.gmxwrap import *

#---custom imports according to the procedure from the script that imported amx
import sys,os
wordspace['script'] = os.path.abspath(os.getcwd()+'/'+sys.argv[0])
with open(wordspace['script'],'r') as fp: original_script_lines = fp.readlines()
try: 
	procedure = [re.findall('^procedure:\s*([\w,]+)',l)[0] 
		for l in original_script_lines if re.match('^procedure:\s*([\w,]+)',l)]
	if len(procedure)!=1 and len(list(set(procedure)))>1:
		raise Exception('[ERROR] procedure = %s'%str(procedure))
	else: procedure = procedure[0]
except: raise Exception('[ERROR] could not find "procedure: <name>" in the script')
if procedure == 'aamd,protein':
	#---imports: atomistic protein in water
	from procedures.protein_atomistic import *
	wordspace['command_library'] = interpret_command(command_library)
	wordspace['mdp_specs'] = mdp_specs
elif procedure == 'cgmd,bilayer':
	#---imports: coarse-grained bilayer in water
	from procedures.cgmd_bilayer import *
	wordspace['command_library'] = interpret_command(command_library)
	wordspace['mdp_specs'] = mdp_specs
elif procedure == 'cgmd,protein':
	#---imports: coarse-grained protein in water
	from procedures.cgmd_protein import *
else: raise Exception('[ERROR] unclear procedure %s'%procedure)
