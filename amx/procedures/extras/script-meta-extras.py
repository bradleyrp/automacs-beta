#!/usr/bin/python

def watch_last_mdrun():

	"""
	Wrapper for a command which tails the oldest mdrun command.
	"""

	cmd = 'find ./ -name "log-mdrun*" | xargs ls -ltrh | '+\
		'tail -n 1 | awk \'{print $9}\' | xargs tail -f'
	#---make sure never to use double quotes to awk
	os.system(cmd)
