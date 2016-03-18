#!/usr/bin/python

import os,re,subprocess,sys

def call(cmd):

	"""
	Execute a shell command.
	"""

	try: subprocess.check_call(cmd,shell=True,executable='/bin/bash')
	except Exception as e: sys.exit(1)

def script_settings_replace(script,settings_string):

	"""
	Replace the settings string in a script. 
	Note that we assume that settings starts on the first line with the word and ends with the import amx.
	"""

	with open(script) as fp: lines = fp.readlines()
	cutout = [next(ii for ii,i in enumerate(lines) if re.match(regex,i)) 
		for regex in ['^settings','^(import amx|from amx import)']]
	with open(script,'w') as fp:
		for line in lines[:cutout[0]]: fp.write(line)
		fp.write('settings = """')
		fp.write(settings_string)
		fp.write('"""\n\n')
		for line in lines[cutout[1]:]: fp.write(line)

def concise_error(e,all=False):

	"""
	Report an error concisely to the terminal to avoid overwhelming the user.
	"""

	exc_type, exc_obj, exc_tb = sys.exc_info()
	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	report('%s in %s at line %d'%(str(exc_type),fname,exc_tb.tb_lineno),tag='error')
	report('%s'%e,tag='error')
	if all:
		import traceback
		traceback.print_exc()

