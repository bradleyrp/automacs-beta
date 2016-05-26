#!/usr/bin/python

settings_cgmd_bilayer = """
system name:        CGMD BILAYER
lipid structures:   inputs/cgmd-inputs
step:               bilayer
procedure:          cgmd,bilayer
shape:              flat
height:             6
binsize:            1.0
monolayer offset:   1.5
monolayer top:     	400 
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

settings_multiply = """
step:               large
procedure:          multiply
equilibration:      npt-bilayer
proceed:            True
genconf gap:        0.3
nx:                 2
ny:                 2
"""

import sys,os,shutil,subprocess
from base.metatools import *

call('make -s clean sure')
call('make -s program cgmd-bilayer')
script_settings_replace('script-cgmd-bilayer.py',settings_cgmd_bilayer)
call('./script-cgmd-bilayer.py')
call('make -s program multiply')
script_settings_replace('script-multiply.py',settings_multiply)
call('./script-multiply.py')
