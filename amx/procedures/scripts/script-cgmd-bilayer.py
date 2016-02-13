#!/usr/bin/python -i
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
binsize:            0.9
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
z shift:            4.5
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
init(settings)
start(wordspace['step'])
write_mdp()
build_bilayer(name='vacuum-bilayer')
if 'protein_ready' in wordspace: add_proteins()
write_top('vacuum.top')
solvate_bilayer('vacuum')
write_top('solvate.top')
minimize('solvate')
counterions('solvate-minimized','solvate',resname="W")
counterion_renamer('counterions')
write_top('counterions.top')
minimize('counterions')
bilayer_middle(structure='counterions',gro='system')
bilayer_sorter(structure='system',ndx='system-groups')
write_top('system.top')
equilibrate(groups='system-groups')
