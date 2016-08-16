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
	
def yamlparse(text,style=None):

	"""
	A function which reads the settings files in yaml format.
	DEVELOPMENT NOTE: this will ignore lines if your forget a colon. Needs better error checking.
	"""
	
	unpacked = {}
	#---evaluate code blocks first
	regex_block_standard = r"^\s*([^\n]*?)\s*(?:\s*:\s*\|)\s*([^\n]*?)\n(\s+)(.*?)\n(?!\3)"
	regex_block_tabbed = r"^\s*([^\n]*?)\s*(?:\s*:\s*\|)\s*\n(.*?)\n(?!\t)"
	if style == 'tabbed': regex_block = regex_block_tabbed
	else: regex_block = regex_block_standard
	regex_line = r"^\s*(.*?)\s*(?:\s*:\s*)\s*(.+)$"
	while True:
		blockoff = re.search(regex_block,text,re.M+re.DOTALL)
		if not blockoff: break
		if style == 'tabbed': key,block = blockoff.groups()[:2]
		else: 
			#---collect the key, indentation for replacement, and value
			key,indent,block = blockoff.group(1),blockoff.group(3),''.join(blockoff.groups()[1:])
		#---alternate style does multiline blocks with a single tab character
		if style == 'tabbed': compact = re.sub("(\n\t)",r'\n',block.lstrip('\t'),re.M)
		#---remove indentations and newlines (default)
		else: compact = re.sub('\n','',re.sub(indent,'',block))
		unpacked[re.sub(' ','_',key)] = compact
		#---remove the block
		text = re.sub(re.escape(text[slice(*blockoff.span())]),'',text)
	while True:
		line = re.search(regex_line,text,re.M)
		if not line: break
		key,val = line.groups()
		assert key not in unpacked
		unpacked[re.sub(' ','_',key)] = val
		text = re.sub(re.escape(text[slice(*line.span())]),'',text)
	#---evaluate rules to process the results
	for key,val in unpacked.items():
		#---store according to evaluation rules
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

def detect_last(steplist=False):

	"""
	Find the last step number and part number (if available).
	"""

	step_regex = '^s([0-9]+)-[\w-]+$'
	part_regex = '^[^\/]+\/md\.part([0-9]{4})\.cpt' 
	possible_steps = [i for i in glob.glob('s*-*') if os.path.isdir(i)]
	try:
		last_step_num = max(map(
			lambda z:int(z),map(
			lambda y:re.findall(step_regex,y).pop(),filter(
			lambda x:re.match(step_regex,x),possible_steps))))
		last_step = os.path.join(filter(lambda x:re.match('^s%02d.'%last_step_num,x),possible_steps).pop(),'')
	except: last_step = None
	part_num = None
	try:
		possible_parts = glob.glob(last_step+'/*.cpt')
		part_num = max(map(lambda y:int(re.findall(part_regex,y)[0]),filter(
			lambda x:re.match(part_regex,x),possible_parts)))
	except: pass
	#---sometimes we want a list of all step folders so this returns one, without parts
	if steplist: return sorted(possible_steps)
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

def ask_user(*msgs):

	return all(re.match('^(y|Y)',raw_input('[QUESTION] %s (y/N)? '%msg))!=None for msg in msgs)

def ready_to_continue(sure=False):

	"""
	Use this function at the beginning of a continuation step e.g. the multiply procedure which takes a
	previous simulation and increases the size of the unit cell. This function checks for a previous 
	wordspace and asks the user if they want to delete it before continuing. Note that using the add=True flag
	to the resume function will ask AUTOMACS to retrieve the previous wordspace from a checkpoint in the log
	file of the last step. This obviates the need to open the pickled wordspace, which is intended purely
	for rapid development purposes and is not necessary in a production environment.
	"""

	if os.path.isfile('wordspace.json'):
		msgs = [
			"detected wordspace.json but this must be deleted if this is a follow-up. delete? ",
			"confirm"]
		if sure or ask_user(*msgs): os.remove('wordspace.json')
		else: print '[WARNING] wordspace.json remains despite ready_to_continue check'

def nospaces(text):

	"""
	Working with keys processed by yamlparse enforces a no-spaces rule.
	"""

	return re.sub(' ','_',text)