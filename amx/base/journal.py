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
	
def status(string,i=0,looplen=None,bar_character=None,width=25,tag='',start=None):

	"""
	Show a status bar and counter for a fixed-length operation.
	"""

	#---use unicode if not piping to a log file
	logfile = sys.stdout.isatty()==False
	if not logfile: left,right,bb = u'\u2590',u'\u258C',(u'\u2592' if bar_character==None else bar_character)
	else: left,right,bb = '|','|','='
	string = '[%s] '%tag.upper()+string if tag != '' else string
	if not looplen:
		if not logfile: print string
		else: sys.stdout.write(string+'\n')
	else:
		if start != None:
			esttime = (time.time()-start)/(float(i+1)/looplen)
			timestring = ' %s minutes'%str(abs(round((esttime-(time.time()-start))/60.,1)))
			width = 15
		else: timestring = ''
		countstring = str(i+1)+'/'+str(looplen)
		bar = ' %s%s%s '%(left,int(width*(i+1)/looplen)*bb+' '*(width-int(width*(i+1)/looplen)),right)
		if not logfile: 
			print unicode(u'\r'+string+bar+countstring+timestring+' '),
		else: sys.stdout.write('\r'+string+bar+countstring+timestring+' ')
		if i+1<looplen: sys.stdout.flush()
		else: print '\n',

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

#def register_trajectory 
