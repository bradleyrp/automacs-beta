#!/usr/bin/python

settings = """
system name:        AAMD BILAYER
lipid structures:   inputs/lipids/charmm36-structs/
step:               bilayer
requires:           bilayer
shape:              flat
height:             6
binsize:            1.2
monolayer offset:   1.5
monolayer top:      144
monolayer bottom:   None
composition top:    {'DOPC':0.8,'DOPS':0.2}
composition bottom: None
aspect:             1.0
solvent thickness:  5
protein water gap:  3
lipid ready:        lipid-ready.gro
force field:        charmm36
cation:             NA
anion:              CL
ionic strength:     0.150
sol:                SOL
ff includes:        ['forcefield','tip3p','ions']
files:              []
water box:          spc216
sol:                SOL
use vmd:            true
sources:            ['lipids/charmm36-tops','inputs/general/spc216.gro']
itp:|               [
					'charmm36-tops/lipid.DOPC.itp','charmm36-tops/restr.DOPC.itp',
					'charmm36-tops/lipid.DOPS.itp','charmm36-tops/restr.DOPS.itp',
					]
equilibration:      npt-bilayer
mdp specs:|         {
					'group':'aamd',
					'input-em-steep-in.mdp':['minimize'],
					'input-em-cg-in.mdp':['minimize',{'integrator':'cg'}],
					'input-md-vacuum-pack1-eq-in.mdp':['vacuum-packing',{'nsteps':10000}],
					'input-md-vacuum-pack2-eq-in.mdp':['vacuum-packing',{'ref_p':'100.0 1.0'}],
					'input-md-vacuum-pack3-eq-in.mdp':['vacuum-packing'],
					'input-md-npt-bilayer-eq-in.mdp':['npt-bilayer-simple',],
					'input-md-in.mdp':['npt-bilayer'],
					}
atom resolution:    aamd
keep continue:      True
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
		vacuum_pack(structure='vacuum-nojump',name='vacuum-pack1',gro='vacuum-packed1')
		vacuum_pack(structure='vacuum-packed1',name='vacuum-pack2',gro='vacuum-packed2')
		vacuum_pack(structure='vacuum-packed2',name='vacuum-pack3',gro='vacuum-packed')
	solvate_bilayer('vacuum-packed')
	write_top('solvate.top')
	minimize('solvate')
	remove_jump(structure='solvate-minimized',tpr='em-solvate-steep',gro='solvate-nojump')
	counterions('solvate-nojump','solvate')
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
	checkpoint()
	write_mdp()
	equilibrate(groups='system-groups')
	write_continue_script()
	if wordspace['keep_continue']: continuation()
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
