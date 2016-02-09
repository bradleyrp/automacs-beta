#!/usr/bin/python

settings_cgmd_protein = """
name:               enth
step:               protein
system_name:        CGMD PROTEIN
start_structure:    inputs/1H0A.pdb
procedure:          cgmd,protein
martinize_path:     inputs/martinize.py
structure_name:     protein
"""

settings_cgmd_bilayer = """
system_name:        CGMD BILAYER
lipid_structures:   inputs/cgmd-lipid-structures
step:               bilayer
procedure:          cgmd,bilayer
shape:              flat
lx:                 20
ly:                 20
lz:                 50
height:             6
binsize:            0.9
monolayer_offset:   1.5
lipid:              DOPC
lipid_ready:        lipid-rotated.gro
protein_ready:      protein-rotated.gro
space_scale:        10
ncols:              4
nrows:              4
total_proteins:     14
z_shift:            3.0
lattice_type:       triangle
"""

execfile('inputs/metatools.py')
call('make clean sure')
call('make program cgmd-protein')
script_settings_replace('script-cgmd-protein.py',settings_cgmd_protein)
call('./script-cgmd-protein.py')
call('python inputs/instruct-place-ENTH.py')
call('make program cgmd-bilayer')
script_settings_replace('script-cgmd-bilayer.py',settings_cgmd_bilayer)
call('./script-cgmd-bilayer.py')

"""
/store-delta/worker/SUB2/repo-automacs/automacs-backup-series-collected-2015.11.09/amxdev3-BAR-development
~/store-omicron/membrane-v6xx/membrane-v612-enthx1-12800
"""
