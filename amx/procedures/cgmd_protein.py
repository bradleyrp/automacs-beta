#!/usr/bin/python

from amx import wordspace
from amx.base.gmxwrap import bash,gmx_run
from amx.base.gromacs import gmxpaths
from amx.base.journal import *

#---common command interpretations
command_library = """"""
mdp_specs = {}

def build_cgmd_protein():

	"""
	Use martinize to generate a coarse-grained protein.
	"""

	name = 'protein'
	cwd = wordspace['step']
	#---this function is run from the step but martinize_path is relative to root
	cmd = 'python ../'+wordspace['martinize_path']
	cmd += ' -f protein-start.pdb -o %s.top -x %s.pdb'%(name,name)
	bash(cmd,cwd=wordspace['step'],log='martinize')
	gmx_run(gmxpaths['editconf']+' -f %s.pdb -o %s.gro'%(name,name),log='editconf-convert-pdb')
