#!/usr/bin/python

import re

def script_settings_replace(script,settings_string):

	"""
	Replace the settings string in a script. 
	Note that we assume that settings starts on the first line with the word and ends with the import amx.
	"""

	with open(script) as fp: lines = fp.readlines()
	cutout = [next(ii for ii,i in enumerate(lines) if re.match(regex,i)) 
		for regex in ['^settings','^import amx']]
	with open(script,'w') as fp:
		for line in lines[:cutout[0]]: fp.write(line)
		fp.write('settings = """')
		fp.write(settings_string)
		fp.write('"""\n\n')
		for line in lines[cutout[1]:]: fp.write(line)