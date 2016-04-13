#!/usr/bin/python

"""
BENCHMARKING FUNCTIONS
"""

def get_timings():

	"""
	Collect timings if this is a benchmarking metarun.
	"""

	import re,glob,os
	performances = {}
	step_regex = '^s[0-9]+-continue-([0-9]+)nodes'
	regex_gmx_timings = '^.+\(ns\/day\).+\n\s*Performance:\s*([0-9]+\.?[0-9]*)'
	steps = [fn for fn in glob.glob('s*') if os.path.isdir(fn) and re.match(step_regex,fn)]
	for step in steps:
		parts = glob.glob(os.path.join(step,'md.part*.log'))
		last_part = sorted(parts,key=lambda x:re.search('^md\.part([0-9]+)\.log',
			os.path.basename(x)).groups()[0])[-1]
		with open(last_part) as fp: lines = fp.read()
		try: 
			nsday = float(re.search(regex_gmx_timings,lines,re.MULTILINE).groups()[0])
			name = re.search(step_regex,step).groups()[0]
			performances[name] = nsday
		except: print '[NOTE] no performance data in %s,%s'%(step,last_part)
	if performances == {}: print '[WARNING] could not find performance data'
	else:
		with open('timings.py','w') as fp: fp.write(str(performances))
		print '[NOTE] writting timings data to timings.py (collect these and plot with "make plot_timings"'