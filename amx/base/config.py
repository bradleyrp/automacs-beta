#!/usr/bin/python

import re,os,sys

def bootstrap_configuration(local=False):

	"""
	Create a new configuration from the default and explain to the user.
	"""

	#---read the default configuration from the standard location
	with open('amx/base/default_config.py') as fp: default_configuration = fp.read()
	#---we skip the bootstrap if we are only making docs from its subfolder
	if re.match('.+\/docs\/build$',os.getcwd()): return
	print "[STATUS] bootstrapping a configuration now"
	if not local: fn = os.environ['HOME']+'/.automacs.py'
	else: fn = 'config.py'
	with open(fn,'w') as fp: fp.write(default_configuration)
	print "[STATUS] default configuration file:\n|"
	for line in default_configuration.split('\n'): print '|  '+re.sub('\t','  ',line)
	print "[STATUS] edit this file at %s"%fn
