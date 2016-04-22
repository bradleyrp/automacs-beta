#!/usr/bin/python


import sys,os,shutil,subprocess
execfile('amx/base/metatools.py')
settings_collection = {}
execfile('inputs/project-exo70/specs_exo70.py',settings_collection)
settings_cgmd_protein = settings_collection['settings_cgmd_protein']
settings_cgmd_bilayer = settings_collection['settings_cgmd_bilayer']

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
	call('python inputs/project-exo70/instruct-place-EXO70.py')
	call('make program cgmd-bilayer')
elif runtype=='continue':
	shutil.copyfile('amx/procedures/scripts/script-cgmd-bilayer.py','./script-cgmd-bilayer.py')
try:
	script_settings_replace('script-cgmd-bilayer.py',settings_cgmd_bilayer)
	call('./script-cgmd-bilayer.py')
	subprocess.check_call('./script-continue.sh',cwd='s02-bilayer')
except: pass