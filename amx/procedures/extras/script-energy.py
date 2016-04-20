#!/usr/bin/python

import re,os,subprocess,tempfile,glob,random
from numpy import *
import matplotlib as mpl
import matplotlib.pylab as plt
import matplotlib.gridspec as gridspec

def plot_energy(edr_fn):

	"""
	Plot the energy data to a large panel plot.
	"""

	print "processing %s"%edr_fn
	proc = subprocess.Popen('gmxdump -e %s'%edr_fn,shell=True,cwd='./',
		stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	readout,commentary = proc.communicate()

	reflag = re.MULTILINE|re.DOTALL
	scientific = r"-?[0-9]+.?[0-9]*e-?\+?[0-9]+"
	integer = r"[0-9]+"

	#---read the header to extract the group names
	header_text, = re.search("^energy components:(.*?)(?=\n\n)",readout,flags=reflag).groups()
	parse_header = ''.join([
		'^\s*(?P<index>[0-9]+)\s+',
		'(?P<name>[\w\-0-9\.\#\*]+(?:\s[\w\-0-9\.\#\*]+)?(?:\s\(\w+\))?)',
		'\s+\((.+)\)$'])
	header = {int(i):{'name':j,'units':k} for i,j,k in [l.groups() for l in 
		re.compile(parse_header,re.MULTILINE).finditer(header_text)]}
	#---get each timestep
	parse_body = '^\s*(time:.*?)(?=Component)[^\n]+\n(.*?)(?=\n\n)'
	body = re.compile(parse_body,reflag).finditer(readout)
	chunks = [i.groups() for i in body]
	parse_body_header = re.compile((
		'^\s*time:\s*(?P<time>%s)\s*'+
		'step:\s*(?P<step>%s)\s*\n\s*nsteps:\s*(?P<nsteps>%s)\s*\n\s*'+
		'delta_t:\s*(?P<delta_t>%s)\s*sum steps:\s*(?P<sum_steps>%s)\s*')%
		(scientific,integer,integer,scientific,integer)
		,flags=reflag)

	#---extract
	energy = [{} for step in chunks]
	for step_num,(body_header,body_step) in enumerate(chunks):
		parse_body_header.match(body_header).groups()
		energy[step_num] = {key:float(val) 
			for key,val in parse_body_header.match(body_header).groupdict().items()}
		for name,details in header.items():
			parse_entry = '^\s*%s\s+(%s)\s*(?:(%s)\s+(%s)\s*)?'%(
				re.escape(details['name']),scientific,scientific,scientific)
			energy[step_num][name] = [float(j) if j else None for j in 
				re.search(parse_entry,body_step,flags=reflag).groups()]

	def ticktock(values,cutoff=3,nbins=5,ax=None):
		locator = mpl.ticker.MaxNLocator(nbins=nbins)
		#---determine an appropriate exponent
		exponent = int(log10(max([abs(i) for i in [values.min(),values.max()]])))
		exponent = None if exponent<cutoff else exponent
		if not exponent or len(list(set(values)))==1:
			def tickformatter_custom(x,p):
				return "%.f"%(x)
		else:
			#---ensure unique tick marks for ticks without decimal points
			decimal_shift = 0
			ax.get_yaxis().set_major_locator(locator)
			ticks = ax.get_yticks()
			while len(set(['%d'%int(i) for i in ticks/10**exponent*10**decimal_shift]))<nbins: 
				decimal_shift += 1
			exponent -= decimal_shift
			def tickformatter_custom(x,p):
				return ('%.f')%(x*(10**(-1.*exponent)))
		formatter = mpl.ticker.FuncFormatter(tickformatter_custom)
		return formatter,locator,exponent

	#---plot
	base_size = 20.
	wide_factor = 1.5
	color_map_name = 'Paired'
	color_map = [mpl.cm.__dict__[color_map_name](i/float(len(header))) for i in range(len(header))]
	random.shuffle(color_map)
	timeseries = array([e['time'] for e in energy])
	ncols = int(ceil(sqrt(len(header))))
	nrows = int(ceil(float(len(header))/ncols))
	fig = plt.figure(figsize=(base_size,base_size*(float(nrows)/ncols)/wide_factor))
	gs = gridspec.GridSpec(nrows,ncols,hspace=0.65,wspace=0.8)
	axes = [plt.subplot(gs[plot_num/ncols,plot_num%ncols]) for plot_num in range(len(header))]
	for plot_num,ax in enumerate(axes):
		index = sorted(header.keys())[plot_num]
		details = header[index]
		print "plotting %s"%details['name']
		values = array([e[index][0] for e in energy])
		ax.plot(timeseries,values,color=color_map[plot_num])
		ax.set_title(details['name'])
		ax.tick_params(axis='y',which='both',left='off',right='off',labelleft='on')
		ax.tick_params(axis='x',which='both',bottom='off',top='off',labelbottom='on')
		formatter,locator,exponent = ticktock(values,ax=ax)
		ax.get_yaxis().set_major_formatter(formatter)
		ax.get_yaxis().set_major_locator(locator)
		ax.set_ylabel('(%s)'%details['units']+('x10e%d'%exponent if exponent else ''))
		ax.set_xticklabels([])
	plt.savefig(edr_fn.rstrip('.edr')+'.png',dpi=200)
	plt.close()
