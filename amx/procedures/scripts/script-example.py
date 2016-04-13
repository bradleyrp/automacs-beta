#!/usr/bin/python

"""
An example script.
"""

settings = """
step:               bilayer # folder name
system name:        CGMD BILAYER # used by write_top
procedure:          cgmd,bilayer # identifies the necessary codes

#---include files for writing topologies
ff includes:        ['martini-v2.2','martini-v2.0-lipids','martini-v2.2-aminoacids','martini-v2.0-ions']
files:              ['inputs/cgmd-inputs/martini-water.gro']
sources:            ['martini.ff']
"""

from amx import *
init(settings)
try:
	#---the following indent block allows for development without repetition
	if not wordspace['under_development']:
		#---create the folder
		start(wordspace['step']) 
		#---write mdp if mdp_specs is defined in the function library for this procedure
		write_mdp() 
	#---checkpoint writes the wordspace to the log for later
	checkpoint()
	#---write the standard BASH continue script
	write_continue_script()
#---exception handling writes a json file of the wordspace during development even if user cancels
except KeyboardInterrupt as e: exception_handler(e,wordspace,all=True)
except Exception as e: exception_handler(e,wordspace,all=True)
