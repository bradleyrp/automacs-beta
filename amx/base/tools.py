#!/usr/bin/python

import inspect

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
