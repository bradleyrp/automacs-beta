#!/usr/bin/python

from amx import wordspace
from amx.base.gmxwrap import bash,gmx_run
from amx.base.gromacs import gmxpaths
from amx.base.journal import *

def build_cgmd_protein(name):

	"""
	Use martinize to generate a coarse-grained protein.
	"""

	cwd = wordspace['step']
	cmd = '../'+wordspace['martinize_path']
	cmd += ' -f ../%s'%wordspace['start_structure']
	cmd += ' -o %s.top'%name
	cmd += ' -x %s.pdb'%name
	bash(cmd,cwd=wordspace['step'])
	gmx_run(gmxpaths['editconf']+' -f %s.pdb -o %s.gro'%(name,name),log='editconf-convert-pdb')
