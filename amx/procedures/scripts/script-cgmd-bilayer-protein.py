#!/usr/bin/python

settings = """ """

import amx
amx.init(settings)
amx.start(amx.wordspace['step'])
cwd = amx.wordspace['step']
cmd = '../inputs/martinize.py'
cmd += ' -f ../inputs/1H0A.pdb'
cmd += ' -o protein.top'
cmd += ' -x protein.pdb'
amx.bash(cmd,cwd=amx.wordspace['step'])
amx.gmx_run(amx.gmxpaths['editconf']+' -f protein.pdb -o protein.gro',log='editconf-convert-pdb')
execfile('inputs/instruct-place-ENTH.py')
