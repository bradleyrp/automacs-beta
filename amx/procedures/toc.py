#!/usr/bin/python 

"""
Table of contents for available procedures. 
Note that this should be implemented more carefully with a dictionary which is read by amx/__init__.py
"""

procedure_toc = {
	'aamd,protein':'protein_atomistic',
	'cgmd,bilayer':'cgmd_bilayer',
	'cgmd,protein':'cgmd_protein',
	'homology':'homology',
	}

if 0:
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

