#!/usr/bin/python

"""
Write concise VMD scripts with flexible variables.
Adapted from OMNICALC.
"""

import re,os,sys,time,tempfile,subprocess,shutil,copy

#---SETTINGS
#-------------------------------------------------------------------------------------------------------------

#---common operations
commons = {
'pbc':"package require pbc",
'bonder':"""
source ~/libs/cg_bonds.tcl
cg_bonds -cutoff BOND_CUTOFF_ANGSTROMS -gmx GMXDUMP -tpr TPR
""",
'load':
"""
mol new GRO
animate delete beg 0 end 0 skip 0 0
mol addfile XTC FRAMES step STEP waitfor all 
""",
'load_structure':
"""
mol new GRO
""",
'ortho':
"""
display projection Orthographic
""",
'standard':
"""
display projection Orthographic
color Display Background BACKCOLOR
axes location off
display resize VIEWX VIEWY
mol delrep 0 top
""",
'dev':
"""
mol selection "SELECT"
mol addrep top
""",
'play':'animate forward',
'reset':'display resetview\nafter 3000',
'xview':
"""
mouse stoprotation
rotate x to -90
rotate y by -90
""",
'isoview':
"""
mouse stoprotation
rotate z to -45
rotate x by -60
""",
'yview':
"""
rotate z to 180
rotate x by -90
""",
'zview':
"""
mouse stoprotation
rotate z to 180
""",
'align_backbone':
"""
set reference [atomselect top "name CA" frame 0]
set compare [atomselect top "name CA"]
set num_steps [molinfo top get numframes]
for {set frame 0} {$frame < $num_steps} {incr frame} {
	$compare frame $frame
	set trans_mat [measure fit $compare $reference]
	$compare move $trans_mat
}
"""
}

#---FUNCTIONS
#-------------------------------------------------------------------------------------------------------------

class VMDWrap:

	commons = copy.deepcopy(commons)
	draw_defaults = {
		'beads':'Beads 1.000000 12.000000',
		'vdw':'VDW 0.600000 12.000000',
		'licorice':'Licorice 0.300000 12.000000 12.000000',
		'cartoon':'NewCartoon 0.300000 10.000000 4.100000 0',
		'lines':'Lines 4.000000',
		'points':'Points 20.000000'
		}

	extras = {
		'update':'mol selupdate REP top 1',
		'smooth':'mol smoothrep top REP 5',
		'rainbow':'mol modcolor REP top ResID',
		'resname_color':'mol modcolor REP top ResName',
		'structure_color':'mol modcolor REP top Structure',
		'transparent':'mol modmaterial REP top Transparent',
		'edgyglass':'mol modmaterial REP top EdgyGlass',
		'glass1':'mol modmaterial REP top Glass1',
		'goodsell':'mol modmaterial REP top Goodsell',
		'hide':'mol showrep top REP 0',
		'glass':'mol modmaterial REP top Diffuse',
		'xy':'\n'.join([
			'mol showperiodic top REP x',
			'mol numperiodic top REP 1',
			'mol showperiodic top REP xy',
			'mol numperiodic top REP 1',
			'mol showperiodic top REP xyX',
			'mol numperiodic top REP 1',
			'mol showperiodic top REP xyXY',
			'mol numperiodic top REP 1',
			]),
		'pbcz':'\n'.join([
			'mol showperiodic top REP z',
			'mol numperiodic top REP 1',
			'mol showperiodic top REP zZ',
			'mol numperiodic top REP 1',
			]),
		}

	def __init__(self,name='vmd',**kwargs):

		"""
		Interface with VMD to make videos and execute common rendering functions.
		"""

		#---note that we previously mixed instance variables and kept track of substitutions
		#---...in a single list called subs. we have since converted subs to a dictionary
		#---...instead of using the self.__dict__ to track them. 
		self.subs = {}
		
		#---defaults
		self.step = 1
		self.start_time = time.time()
		#---viewing dimensions
		self.viewx,self.viewy = (800,800)
		#---output resolution
		self.resx,self.resy = kwargs['res'] if 'res' in kwargs else (1000,1000)
		#---background color
		self.backcolor = kwargs['backcolor'] if 'backcolor' in kwargs else 'white'
		self.bond_cutoff_angstroms = 20
		#---native parameters used in the constants which can be regex replaced from kwargs
		#natives = ['resx','resy','viewx','viewy','backcolor']

		#---counters
		self.script = []
		self.selections = {}
		self.selection_order = []
		self.video_script_ready = False
		self.vmd_prepend = "VMDNOCUDA=1"

		"""
		note that previous iterations of vmdwrap.py/lipidlook.py had convoluted paths
		previous iterations of the code used the following paths
			self.rootdir : where to render mp4, holds the subdir which becomes self.cwd
			self.cwd : a subdir of self.rootdir which is either specified or created as a tempdir for snaps
		here we will streamline those paths using the following convention
		paths conventions
			VMDWrap has two paths:
				1. root directory specified by kwargs "output" in the constructor to hold the final mp4
				2. sub-directory 
		"""

		#---root directory for subfolders holding the snapshots
		self.rootdir = os.getcwd() if 'site' not in kwargs else os.path.abspath(kwargs['site'])
		if 'subdir' not in kwargs: self.cwd = tempfile.mkdtemp(dir=self.rootdir)
		elif not kwargs['subdir']: self.cwd = self.rootdir
		else: self.cwd = kwargs['subdir']

		self.molnum = 0 if 'molnum' not in kwargs else kwargs['molnum']
		if 'last' in kwargs and 'frames' not in kwargs: 
			self.subs['frames'] = '' if kwargs['last']==None else 'last %d'%kwargs['last']
		elif 'last' in kwargs: raise Exception('cannot define both LAST and FRAMES')
		#---special kwargs that become substitutions stored in self.__dict__
		#---! note that we removed "root" from the following list because it is not used as a substitution
		for key in ['gro','xtc','tpr','frames','step']:
			if key in kwargs: self.subs[key] = kwargs[key]
		self.script_fn = 'script-%s.tcl'%name
		self.snapshot = False
		#---figure out gmx path for the bonder if necessary
		gmxdump_path = subprocess.check_output('which gmxdump',shell=True).strip()
		self.subs['gmxdump'] = gmxdump_path
		
		#---load subs into the class instance dictionary for substitutions
		for key,val in self.subs.items(): self.__dict__[key] = val

	def do(self,*names):

		"""
		Use a set of prescribed code blocks defined in commons.
		"""

		for name in names:
			chunk = self.commons[name].strip('\n')
			for key,val in self.__dict__.items(): chunk = re.sub(key.upper(),str(val),chunk)
			self.script.append(chunk)

	def write(self):

		"""
		Write the script.
		"""

		with open(self.rootdir+'/'+self.script_fn,'w') as fp:
			for line in self.script: fp.write(line+'\n')

	def review(self,prompt=True):

		"""
		Check over the code before running.
		"""

		for s in self.script: print s
		if prompt: raw_input('run VMD or ctrl+D')
		self.write()

	#---raw commands added to the script
	def command(self,text): self.script.append(text)

	#---interface with the command line
	def call(self,command): subprocess.check_call(command,shell=True,cwd=self.rootdir)

	def select(self,**kwargs):

		"""
		Create a new selection with string substitutions.
		"""

		style = kwargs.pop('style') if 'style' in kwargs else None
		extras = []
		for key,val in kwargs.items():
			if type(kwargs[key]) == bool:
				kwargs.pop(key)
				if val: extras.append(key)
		dynamics = kwargs.pop('dynamics') if 'dynamics' in kwargs else None
		for key in kwargs:
			selstring = str(kwargs[key])
			for sel in self.selections:
				selstring = re.sub(sel.upper(),'(%s)'%self.selections[sel],selstring)
			self.script += ["mol selection \"(%s)\""%selstring,"mol addrep top"]		
			self.script += ['set %s [atomselect top "%s"]'%(key,selstring)]
			self.selection_order.append(key)
			self.selections[key] = kwargs[key]
		if style != None:
			for key in kwargs:
				style = VMDWrap.draw_defaults[style] if style in VMDWrap.draw_defaults else style
				self.script += ['mol modstyle %d top %s'%(self.selection_order.index(key),style)]
		for extra in extras:
			if extra in VMDWrap.extras and extra:
				for key in kwargs:
					instruct = str(VMDWrap.extras[extra])
					instruct = re.sub('REP','%d'%self.selection_order.index(key),instruct)
					#instruct = re.sub('MOLNUM','%d'%self.molnum,instruct)
					self.script += [instruct]
			else: raise Exception('missing extra setting: %s'%extra)

	def video(self,traces=None,snapshot=False,pause=False,cwd=''):

		"""
		Prepare to render a video by writing an add-on script.
		"""

		#---add a "trace" or tail to some elements
		if traces != None:
			trace_commands = []
			if type(traces) != list: raise Exception('traces must be a list or None')
			for key in traces:
				trace_commands.append(
					'    mol drawframes top %d $lag:$lead'%self.selection_order.index(key))
		else: trace_commands = []
		#---generic header for making a video
		video_lines = [
			'set num [molinfo top get numframes]',
			'for {set i 0} {$i < $num} {incr i} {',
			'    animate goto $i',
			'    set lag [expr $i-15]',
			'    set lead [expr $i]',
			]
		video_lines.extend(trace_commands)
		#---snapshot is the cheap/fast method otherwise we render
		if not snapshot:
			video_lines.extend([
				'    set filename '+(os.path.join(os.path.basename(self.cwd),'') 
					if self.cwd else '')+'snap.[format "%04d" $i]',
				'    render TachyonInternal $filename.tga' if False else
				'    render Tachyon $filename "/usr/local/lib/vmd/tachyon_LINUXAMD64"'+\
				' -aasamples 12 %s -format TARGA -o %s.tga -res '+str(self.resx)+' '+str(self.resy),
				'    exec convert $filename.tga $filename.png',
				'    exec rm $filename.tga $filename',
				'}',
				])
		else:
			video_lines.extend([
				'    set filename '+(os.path.join(os.path.basename(self.cwd),'') 
					if self.cwd else '')+'snap.[format "%04d" $i]',
				'    render snapshot $filename.ppm',
				'}',
				])
			self.snapshot = True
		#---write script-video.tcl which will be sourced by script-vmd.tcl
		with open(self.rootdir+'/script-video.tcl','w') as fp:
			for line in video_lines: fp.write(line+'\n')
		if not pause: self.script.append('source %sscript-video.tcl'%os.path.join(cwd,''))
		#---let show know that there is a video ready to render
		self.video_script_ready = True

	def show(self,text=False,quit=False,render='',clean=False,
		safer=True,prompt=False,rate=1.0,review=False): 

		"""
		After preparing a script we write it and run VMD.
		This function has options for text-only, reviewing the code, and rendering the resulting snapshots.
		This script is messy. "Safer" uses VMD in a more reliable way.
		"""

		#---quit after the script is done
		if quit: self.script += ['quit']
		self.write()
		#---review the script and wait for the go-ahead if prompt
		self.review(prompt=prompt)		
		if quit == False:
			os.system('cd %s && %s vmd %s -e %s'%(self.rootdir,self.vmd_prepend,
				'-dispdev text' if text else '',self.script_fn))
		else: 
			if safer:
				text = '\n'.join(self.script)
				proc = subprocess.Popen('vmd -dispdev text',stdin=subprocess.PIPE,
					shell=True,executable='/bin/bash',stdout=sys.stdout,stderr=sys.stdout,
					cwd=self.rootdir)
				proc.communicate(input=text)
			else:
				self.call('%s vmd %s -e %s'%(self.vmd_prepend,'-dispdev text' 
					if text else '',self.script_fn))
		print '[STATUS] time = %.2f minutes'%((float(time.time())-self.start_time)/60.)

		#---render snapshots if there is a video script
		#---! figure out a default rate/speed-up factor for rendered videos
		has_ffmpeg = not re.search('command not found','\n'.join(
			subprocess.Popen('ffmpeg',shell=True,executable='/bin/bash',
			stdout=subprocess.PIPE,stderr=subprocess.PIPE).communicate()))
		if has_ffmpeg:
			if render != '' and not self.snapshot and self.video_script_ready:
				self.call(r"ffmpeg -i "+self.cwd+"/snap.%04d.png -vcodec mpeg4 -q 0 "+
				"-filter:v 'setpts=%.1f*PTS' "%rate+self.rootdir+'/'+render+".mp4")
			elif render != '' and self.video_script_ready:
				self.call(r"ffmpeg -i "+self.cwd+"snap.%04d.ppm -vcodec mpeg4 -q 0"+
				"-filter:v 'setpts=%.1f*PTS' "%rate+
				self.rootdir+'/'+render+".mp4")
		else:
			if render != '' and not self.snapshot and self.video_script_ready:
				self.call(r"avconv -r %.1f -i "%(rate*4)+self.cwd+
					"/snap.%04d.png "+self.rootdir+'/'+render+".mp4")
			elif render != '' and self.video_script_ready:
				self.call(r"avconv -r %.1f -i "%(rate*4)+self.cwd+
					"/snap.%04d.png "+self.rootdir+'/'+render+".mp4")                   
		if clean: shutil.rmtree(self.cwd)
