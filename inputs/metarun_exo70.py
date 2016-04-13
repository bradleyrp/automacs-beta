#!/usr/bin/python

"""
SOURCES
/store-delta/worker/SUB2/repo-automacs/automacs-backup-series-collected-2015.11.09/amxdev3-BAR-development
~/store-omicron/membrane-v6xx/membrane-v612-enthx1-12800
"""

settings_cgmd_protein = """
name:               enth
step:               protein
system_name:        CGMD PROTEIN
start_structure:    inputs/pdbs/exo70_body.pdb
procedure:          cgmd,protein
martinize_path:     inputs/externals/martinize.py
structure_name:     protein
dssp:               ~/libs/dssp-2.0.4-linux-amd64
martinize flags:    -ed
martinize ff:       martini22
"""

settings_cgmd_bilayer = """
system name:        CGMD BILAYER
lipid structures:   inputs/cgmd-lipid-structures
step:               bilayer
procedure:          cgmd,bilayer
shape:              flat
lx:                 60
ly:                 60
lz:                 15
height:             6
binsize:            1.0
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
z shift:            4.95
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

import sys,os,shutil,subprocess
execfile('amx/base/metatools.py')

#---infer run type
if 'start' in sys.argv: runtype = 'start'
if 'more' in sys.argv: runtype = 'continue'
else: runtype = 'start'

#---procedure depends on run type
if runtype=='start':
	try: os.remove('wordspace.pkl')
	except: pass
	call('make clean sure')
	call('make program cgmd-protein')
	script_settings_replace('script-cgmd-protein.py',settings_cgmd_protein)
	call('./script-cgmd-protein.py')
	call('python inputs/instruct-place-EXO70.py')
	call('make program cgmd-bilayer')
elif runtype=='continue':
	shutil.copyfile('amx/procedures/scripts/script-cgmd-bilayer.py','./script-cgmd-bilayer.py')
try:
	script_settings_replace('script-cgmd-bilayer.py',settings_cgmd_bilayer)
	call('./script-cgmd-bilayer.py')
	subprocess.check_call('./script-continue.sh',cwd='s02-bilayer')
except: pass