#!/usr/bin/python

settings = """
system name:        CGMD BILAYER
lipid structures:   inputs/cgmd-inputs/
step:               cgmd-bilayer
requires:           cgmd_bilayer
shape:              flat
height:             6
binsize:            1.0
monolayer offset:   1.5
monolayer top:      400
monolayer bottom:   None
composition top:    {'DOPC':0.8,'DOPS':0.2}
composition bottom: None
aspect:             1.0
solvent thickness:  20
protein water gap:  3
lipid ready:        lipid-ready.gro
force field:        martini
cation:             NA+
anion:              CL-
ionic strength:     0.150
sol:                W
ff includes:        ['martini-v2.2','martini-v2.0-lipids','martini-v2.2-aminoacids','martini-v2.0-ions']
files:              ['cgmd-inputs/martini-water.gro']
sources:            ['martini.ff']
equilibration:      npt-bilayer
"""

from amx import *
init(settings)
try:
	if not wordspace['under_development']:
		start(wordspace['step'])
		write_mdp()
		build_bilayer(name='vacuum-bilayer')
		if 'protein_ready' in wordspace: add_proteins()
		else: filecopy(wordspace['step']+'vacuum-bilayer.gro',wordspace['step']+'vacuum.gro')
		write_top('vacuum.top')
		minimize('vacuum')
		remove_jump(structure='vacuum-minimized',tpr='em-vacuum-steep',gro='vacuum-nojump')
		vacuum_pack(structure='vacuum-nojump',name='vacuum-pack',gro='vacuum-packed')
	solvate_bilayer('vacuum-packed')
	write_top('solvate.top')
	minimize('solvate')
	remove_jump(structure='solvate-minimized',tpr='em-solvate-steep',gro='solvate-nojump')
	counterions('solvate-nojump','solvate',resname="W")
	counterion_renamer('counterions')
	write_top('counterions.top')
	minimize('counterions')
	remove_jump(structure='counterions-minimized',tpr='em-counterions-steep',gro='counterions-nojump')
	bilayer_middle(structure='counterions-nojump',gro='system')
	write_mdp()
	bilayer_sorter(structure='system',ndx='system-groups')
	write_top('system.top')
	#---add proteins
	if 'protein_ready' in wordspace: 
		for key in ['groups','temperature']:
			wordspace['mdp_specs']['input-md-npt-bilayer-eq-in.mdp'].append({key:'protein'})
			if wordspace['mdp_specs']['input-md-in.mdp'] == None:
				wordspace['mdp_specs']['input-md-in.mdp'] = []
			wordspace['mdp_specs']['input-md-in.mdp'].append({key:'protein'})
		write_mdp()
	equilibrate(groups='system-groups')
	write_continue_script()
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
