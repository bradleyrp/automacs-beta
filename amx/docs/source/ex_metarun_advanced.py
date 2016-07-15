#!/usr/bin/python

#---settings
specs_fn = 'specs_enth.py'

#---set the environment
import sys,os,shutil,subprocess
execfile('amx/base/metatools.py')
settings_collection = {}
execfile('inputs/specs/'+specs_fn,settings_collection)
settings_cgmd_protein = settings_collection['settings_cgmd_protein']
settings_cgmd_bilayer = settings_collection['settings_cgmd_bilayer']

call('make clean sure')
call('make program cgmd-protein')
script_settings_replace('script-cgmd-protein.py',settings_cgmd_protein)
call('./script-cgmd-protein.py')
#---place the protein
from codes.lib_place_proteins import place_protein
place_protein(settings_collection['instruct'])
call('make program cgmd-bilayer')
shutil.copyfile('amx/procedures/scripts/script-cgmd-bilayer.py',
	'./script-cgmd-bilayer.py')
script_settings_replace('script-cgmd-bilayer.py',settings_cgmd_bilayer)
call('./script-cgmd-bilayer.py')
subprocess.check_call('./script-continue.sh',cwd='s02-bilayer')
