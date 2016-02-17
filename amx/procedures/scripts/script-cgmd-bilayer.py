#!/usr/bin/python
execfile('/etc/pythonstart')

settings = """
system name:        CGMD BILAYER
lipid structures:   inputs/cgmd-lipid-structures
step:               bilayer
procedure:          cgmd,bilayer
shape:              flat
lx:                 20
ly:                 30
lz:                 50
height:             6
binsize:            0.95
monolayer offset:   1.5
lipid:              DOPC
solvent thickness:  15
protein water gap:  3
lipid ready:        lipid-ready.gro
protein ready:      protein-ready.gro
ncols:              1
nrows:              1
total proteins:     1
space scale:        20
z shift:            4.85
lattice type:       square
force field:        martini
cation:             NA+
anion:              CL-
ionic strength:     0.150
sol:                W
ff includes:        ['martini-v2.2','martini-v2.0-lipids','martini-v2.2-aminoacids','martini-v2.0-ions']
files:              ['cgmd-tops/PIP2.itp','martini-water.gro']
sources:            ['martini.ff']
equilibration:      npt-bilayer
"""

from amx import *
#---development
import os,pickle;dev = os.path.isfile('wordspace.pkl')
init(settings,dev=dev)
try:
	if not dev:
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
		#---periodically save for continuation
		pickle.dump(wordspace,open('wordspace.pkl','w'))
	if 'protein_ready' in wordspace: 
		for key in ['groups','temperature']:
			wordspace['mdp_specs']['input-md-npt-bilayer-eq-in.mdp'].append({key:'protein'})
			if wordspace['mdp_specs']['input-md-in.mdp'] == None:
				wordspace['mdp_specs']['input-md-in.mdp'] = []
			wordspace['mdp_specs']['input-md-in.mdp'].append({key:'protein'})
		write_mdp()
	equilibrate(groups='system-groups')
	write_continue_script()
#---development
except Exception as e: print e
pickle.dump(wordspace,open('wordspace.pkl','w'))
