#!/usr/bin/python

"""
SOURCES
/store-delta/worker/SUB2/repo-automacs/automacs-backup-series-collected-2015.11.09/amxdev3-BAR-development
~/store-omicron/membrane-v6xx/membrane-v612-enthx1-12800
"""

settings_cgmd_bilayer = """
system name:        CGMD BILAYER
lipid structures:   inputs/cgmd-lipid-structures
step:               bilayer
procedure:          cgmd,bilayer
shape:              flat
lx:                 100
ly:                 100
lz:                 15
height:             6
binsize:            1.0
monolayer offset:   1.5
lipid:              DOPC
solvent thickness:  15
protein water gap:  3
lipid ready:        lipid-ready.gro
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

import sys,os,shutil,subprocess
execfile('amx/base/metatools.py')

call('make clean sure')
call('make program cgmd-bilayer')
script_settings_replace('script-cgmd-bilayer.py',settings_cgmd_bilayer)
call('./script-cgmd-bilayer.py')
subprocess.check_call('./script-continue.sh',cwd='s02-bilayer')
