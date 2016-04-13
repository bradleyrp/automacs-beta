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

def plot_benchmarks(title=''):

	"""
	Plot speed vs processors.
	Save timings from "make get_timings" to the inputs folder.
	Save timings.py as timings-.+-(.+)\.py where the second regex is the hostname in the 
	machine_configuration dictionary in the configuration file (config.py or ~/.automacs.py).
	This allows the plotting script to figure out NPROCS from NNODES.
	"""

	import glob,re
	import numpy as np
	import matplotlib as mpl
	import matplotlib.pylab as plt

	colormap = 'nipy_spectral'
	ylabel = 'speed (ns/day)'
	xlabel = 'processors'
	#---always need a title and we must strip the kwargs
	if not title: raise Exception('rerun with a title: make plot_benchmarks title="my title"')
	else: title = re.findall('^title?\=?(.+)',title)[0]
	config_fn = os.path.expanduser('~/.automacs.py') if os.path.isfile('~/.automacs.py') else 'config.py'
	if not os.path.isfile(config_fn): 
		raise Exception('cannot find a configuration so run "make config local"')
	config = {}
	execfile(config_fn,config)
	performance,text = {},"system,ppn,nodes,nprocs,ns/day\n"
	#---read timings files from inputs
	regex_timing_fn = '^timings-.+-(.+)\.py$'
	timings = [fn for fn in glob.glob('inputs/*') if re.match(regex_timing_fn,os.path.basename(fn))]
	for timing in timings:
		fn = os.path.basename(timing)
		key = re.search(regex_timing_fn,fn).groups()[0]
		with open(timing) as fp:performance[key] = eval(fp.read())
	#---get ppn from machine_configuration
	ppn = dict([(system,config['machine_configuration'][system]['ppn']) for system in performance])
	xmaxval,ymaxval = 0,0
	colors = [mpl.cm.__dict__[colormap](j) for j in (np.arange(len(performance))+0.5)/len(performance)]
	fig = plt.figure(figsize=(5,5))
	ax = plt.subplot(111)
	systems = performance.keys()
	for sysnum,system in enumerate(performance):
		color = colors[sysnum]
		keys = sorted([int(i) for i in performance[system].keys()])
		xvals = np.array(keys)*ppn[system]
		vals = np.array([performance[system][str(key)] for key in keys])
		ax.plot(xvals,vals,lw=2,zorder=1,c=color,label=system+'\n'+'(%dppn)'%ppn[system])
		ax.scatter(xvals,vals,c=color,s=50,zorder=3,lw=0)
		ax.scatter(xvals,vals,c='w',s=100,zorder=2,lw=0)
		ymaxval = max([ymaxval,max(vals)])
		xmaxval = max([xmaxval,max(xvals)])
		for keynum,nprocs in enumerate(xvals):
			text += '%s,%d,%d,%d,%.3f\n'%(system,ppn[system],keys[keynum],nprocs,vals[keynum])
	ax.set_ylabel(ylabel,fontsize=14)
	ax.set_xlabel(xlabel,fontsize=14)
	ax.set_title(title,fontsize=14)
	ax.set_ylim(0,1.1*ymaxval)
	ax.set_xlim(0,1.1*xmaxval)
	ax.tick_params(axis='y',which='both',left='off',right='off')
	ax.tick_params(axis='x',which='both',bottom='off',top='off')
	ax.grid(True,linestyle='-',zorder=0,alpha=0.35)
	ax.set_axisbelow(True)
	h,l = ax.get_legend_handles_labels()
	legend = ax.legend(loc='lower right',fontsize=12)
	plt.tight_layout()
	plt.savefig('inputs/benchmarks.png',dpi=150)
	plt.close()
	with open('inputs/benchmarks.txt','w') as fp: fp.write(text)
	print '[STATUS] wrote inputs/benchmarks.png and inputs/benchmarks.txt'
