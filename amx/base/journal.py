#!/usr/bin/python

from amx import wordspace
import os,sys
from functools import wraps

#---always print to stdout without a buffer
unbuffered = os.fdopen(sys.stdout.fileno(),'w',0)

def report(text,tag='status',newline=False,newline_trail=False,watch_file=None):

	"""
	Tell the user something useful?
	"""

	message = ('\n' if newline else '')+'[%s] %s'%(tag.upper(),text)+('\n' if newline_trail else '')
	with open(wordspace['watch_file'],'a') as fp: fp.write(message+'\n')
	unbuffered.write(message+'\n')

def narrate(func):

	"""
	Narrate a function call.
	"""
	
	argnames = func.func_code.co_varnames[:func.func_code.co_argcount]
	name = func.func_name
	if 'function_history' not in wordspace: wordspace['function_history'] = []
	wordspace['function_history'].append(name)
	@wraps(func)
	def func_narrate(*args,**kwargs):
		report(' '.join([str(i) for i in [name,args,kwargs]]),tag='function')
		return func(*args,**kwargs)
	return func_narrate
