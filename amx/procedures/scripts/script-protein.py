#!/usr/bin/python

settings = """
step:                protein
procedure:           aamd,protein
equilibration:       nvt,npt
start structure:     inputs/STRUCTURE.pdb
system name:         SYSTEM
protein water gap:   3.0
water:               tip3p
force field:         charmm27
water buffer:        1.2
solvent:             spc216
ionic strength:      0.150
cation:              NA
anion:               CL
"""

import amx
amx.init(settings)
amx.start(amx.wordspace['step'])
amx.write_mdp()
amx.dircopy('inputs/*.ff',amx.wordspace['step'])
amx.filecopy(amx.wordspace['start_structure'],amx.wordspace['step']+'protein-start.pdb')
amx.gmx('pdb2gmx',base='vacuum',structure='protein-start.pdb',gro='vacuum-alone',
	log='pdb2gmx',water=amx.wordspace['water'],ff=amx.wordspace['force_field'])
amx.filemove(amx.wordspace['step']+'system.top',amx.wordspace['step']+'vacuum.top')
amx.extract_itp('vacuum.top')
amx.write_top('vacuum.top')
amx.gmx('editconf',structure='vacuum-alone',gro='vacuum',
	log='editconf-vacuum-room',flag='-c -d %.2f'%amx.wordspace['water_buffer'])
amx.minimize('vacuum',method='steep')
amx.solvate(structure='vacuum-minimized',top='vacuum')
amx.minimize('solvate')
amx.counterions(structure='solvate-minimized',top='solvate')
amx.minimize('counterions')
amx.write_structure_pdb(pdb='protein-start.pdb',structure='counterions')
amx.write_top('system.top')
amx.checkpoint()
amx.equilibrate()
amx.continuation()
