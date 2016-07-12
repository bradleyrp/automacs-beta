#!/usr/bin/python

import os,sys

#---when compiling documentation we have to manually add the paths
script_call = os.path.basename(sys.argv[0])
if script_call == 'sphinx-build': sys.path.insert(0,os.path.abspath('../../../amx/base'))

from config import *