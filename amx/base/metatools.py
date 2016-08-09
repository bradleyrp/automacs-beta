#!/usr/bin/python

import os,re,subprocess,sys,json,shutil

#---we often require imports from inputs from the root
if 'inputs' not in sys.path: sys.path.insert(0,'inputs')

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

def write_wordspace(wordspace,outfile='wordspace.json'):

	"""
	In addition to saving checkpoints permanently in the log, we also drop the wordspace into a json file
	for rapid development.
	"""

	with open(outfile,'w') as fp: json.dump(wordspace,fp)

def exception_handler(e,wordspace,all=False):

	"""
	Report an error concisely to the terminal to avoid overwhelming the user.
	"""

	exc_type, exc_obj, exc_tb = sys.exc_info()
	fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
	from amx.base.journal import report
	report('%s in %s at line %d'%(str(exc_type),fname,exc_tb.tb_lineno),tag='error')
	report('%s'%e,tag='error')
	if all:
		import traceback
		report(re.sub('\n','\n[TRACEBACK] ',traceback.format_exc()),tag='traceback')
	write_wordspace(wordspace)
	sys.exit(1)

def call(cmd,cwd='./'):

	"""
	Execute a shell command.
	Note that we don't handle any exceptions here because we assume that the commands run herein have their
	own error-handling. Further handling would be redundant, but it's important to make sure all codes that
	run through here are carefully excepted.
	"""

	try: subprocess.check_call(cmd,shell=True,executable='/bin/bash',cwd=cwd)
	except: 
		print '[STATUS] failing quietly on "%s" which must self-report its errors'%cmd
		sys.exit(1)

def copyfile(src,dest):

	"""
	Wrap shutil for copying files (must specify the full destination path) along with permission bits.
	"""

	dest_full = os.path.join(dest,os.path.basename(src)) if os.path.isdir(dest) else dest
	shutil.copyfile(src,dest_full)
	shutil.copymode(src,dest_full)