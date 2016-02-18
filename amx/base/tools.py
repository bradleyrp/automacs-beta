#!/usr/bin/python

import inspect,re,glob,os

def asciitree(obj,depth=0,wide=2,last=[],recursed=False):

	"""
	Print a dictionary as a tree to the terminal.
	Includes some simuluxe-specific quirks.
	"""

	corner = u'\u251C'
	horizo = u'\u2500'
	vertic = u'\u2502'

	spacer = {0:'\n',
		1:' '*(wide+1)*(depth-1)+corner+horizo*wide,
		2:' '*(wide+1)*(depth-1)
		}[depth] if depth <= 1 else (
		''.join([(vertic if d not in last else ' ')+' '*wide for d in range(1,depth)])
		)+corner+horizo*wide
	if type(obj) in [str,float,int,bool]:
		if depth == 0: print spacer+str(obj)+'\n'+horizo*len(obj)
		else: print spacer+str(obj)
	elif type(obj) == dict and all([type(i) in [str,float,int,bool] for i in obj.values()]) and depth==0:
		asciitree({'HASH':obj},depth=1,recursed=True)
	elif type(obj) == list:
		for ind,item in enumerate(obj):
			if type(item) in [str,float,int,bool]: print spacer+str(item)
			elif item != {}:
				print spacer+'('+str(ind)+')'
				asciitree(item,depth=depth+1,
					last=last+([depth] if ind==len(obj)-1 else []),
					recursed=True)
			else: print 'unhandled tree object'
	elif type(obj) == dict and obj != {}:
		for ind,key in enumerate(obj.keys()):
			if type(obj[key]) in [str,float,int,bool]: print spacer+key+' = '+str(obj[key])
			#---special: print single-item lists of strings on the same line as the key
			elif type(obj[key])==list and len(obj[key])==1 and type(obj[key][0]) in [str,float,int,bool]:
				print spacer+key+' = '+str(obj[key])
			#---special: skip lists if blank dictionaries
			elif type(obj[key])==list and all([i=={} for i in obj[key]]):
				print spacer+key+' = (empty)'
			elif obj[key] != {}:
				#---fancy border for top level
				if depth == 0:
					print '\n'+corner+horizo*(len(key)+0)+corner+spacer+vertic+str(key)+vertic+'\n'+\
						corner+horizo*len(key)+corner+'\n'+vertic
				else: print spacer+key
				asciitree(obj[key],depth=depth+1,
					last=last+([depth] if ind==len(obj)-1 else []),
					recursed=True)
			elif type(obj[key])==list and obj[key]==[]:
				print spacer+'(empty)'
			else: print 'unhandled tree object'
	else: print 'unhandled tree object'
	if not recursed: print '\n'
	
def yamlparse(string):

	"""
	A function which reads the settings files in yaml format.
	"""
	
	unpacked = {}
	regex = '^\s*([^:]+)\s*:\s*(.+)'
	for s in string.split('\n'):
		if re.match(regex,s):
			key,val = re.findall(regex,s)[0]
			#---allow lists in our pseudo-yaml format
			try: val = eval(val)
			except: pass
			if type(val)==list: unpacked[key] = val
			elif type(val)==str:
				if re.match('^(T|t)rue$',val): unpacked[key] = True
				elif re.match('^(F|f)alse$',val): unpacked[key] = False
				#---! may be redundant with the eval command above
				elif re.match('^[0-9]+$',val): unpacked[key] = int(val)
				elif re.match('^[0-9]*\.[0-9]*$',val): unpacked[key] = float(val)
				else: unpacked[key] = val
			else: unpacked[key] = val
	return unpacked

def detect_last():

	"""
	Find the last step number and part number (if available).
	"""

	step_regex = '^s([0-9]+)-\w+$'
	part_regex = '^[^\/]+\/md\.part([0-9]{4})\.cpt' 
	possible_steps = glob.glob('s*-*')
	try:
		last_step_num = max(map(
			lambda z:int(z),map(
			lambda y:re.findall(step_regex,y).pop(),filter(
			lambda x:re.match(step_regex,x),possible_steps))))
		last_step = os.path.join(filter(lambda x:
			re.match('^s%02d'%last_step_num,x),possible_steps).pop(),'')
	except: last_step = None
	part_num = None
	try:
		possible_parts = glob.glob(last_step+'/*.cpt')
		part_num = max(map(lambda y:int(re.findall(part_regex,y)[0]),filter(
			lambda x:re.match(part_regex,x),possible_parts)))
	except: pass
	return last_step,part_num

def serial_number():

	"""
	Add a random serial number to the simulation.
	"""

	import random
	serial_prefix = 'serial-'
	if not glob.glob('./'+serial_prefix+'*'):
		print "[STATUS] branding your simulation"
		serial = random.randint(0,10**7)
		with open('./'+serial_prefix+'%d'%serial,'w') as fp: pass
		last_step,part_num = detect_last()
		with open('script-%s.log'%last_step.rstrip('/'),'a') as fp:
			fp.write("[FUNCTION] serial_number (%d) {}\n"%serial)
	else: 
		serial_fn, = glob.glob('./'+serial_prefix+'*')
		serial, = re.findall('^'+re.escape(serial_prefix)+'([0-9]+)$',os.path.basename(serial_fn))
	print "[STATUS] serial no. %s"%serial
	return serial
