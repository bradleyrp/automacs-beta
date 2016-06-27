#!/usr/bin/python

settings = """
step:                protein
procedure:           aamd,protein
equilibration:       nvt,npt
start structure:     inputs/STRUCTURE.pdb
run part two:        no
system name:         SYSTEM
protein water gap:   3.0
water:               tip3p
force field:         charmm27
water buffer:        1.2
solvent:             spc216
ionic strength:      0.150
cation:              NA
anion:               CL
use vmd:             False
"""

print settings
from amx import *
init(settings)
try:
	if not wordspace['under_development']:
		start(wordspace['step'])
		write_mdp()
		dircopy('inputs/*.ff',wordspace['step'])
		filecopy(wordspace['start_structure'],wordspace['step']+'protein-start.pdb')
		gmx('pdb2gmx',base='vacuum',structure='protein-start.pdb',gro='vacuum-alone',
			log='pdb2gmx',water=wordspace['water'],ff=wordspace['force_field'])
		filemove(wordspace['step']+'system.top',wordspace['step']+'vacuum.top')
		extract_itp('vacuum.top')
		write_top('vacuum.top')
		gmx('editconf',structure='vacuum-alone',gro='vacuum',
			log='editconf-vacuum-room',flag='-c -d %.2f'%wordspace['water_buffer'])
	minimize('vacuum',method='steep')
	solvate(structure='vacuum-minimized',top='vacuum')
	minimize('solvate')
	counterions(structure='solvate-minimized',top='solvate',ff_includes='ions')
	minimize('counterions')
	write_structure_pdb(pdb='protein-start.pdb',structure='counterions')
	write_top('system.top')
	checkpoint()
	equilibrate()
	if wordspace['run_part_two']=='yes': continuation() 
	else: write_continue_script()
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
