#!/usr/bin/python

def docs(clean=False):

	"""
	Make or delete the documentation.
	"""

	docs_dn = os.path.join(os.getcwd(),'amx/docs/build')
	source_dn = os.path.join(os.getcwd(),'amx/docs/source/')
	import subprocess
	import shutil
	import glob
	if clean:
		if os.path.isdir(docs_dn):
			print '[STATUS] cleaning documentation'
			shutil.rmtree(docs_dn)
	else:
		print '[STATUS] building docs and logging to amx/docs/build/log-docs-build'
		if not os.path.isdir(docs_dn): os.mkdir(docs_dn)
		docslog = 'amx/docs/build/log-docs-build'
		subprocess.call('sphinx-apidoc -F -o %s amx'%docs_dn,shell=True,cwd=os.getcwd(),
			stdout=open(docslog,'w'),stderr=subprocess.PIPE)
		shutil.copy(source_dn+'conf.py',docs_dn)
		shutil.copy(source_dn+'style.css',docs_dn+'/_static')
		for suffix in ['png','rst','py']:
			for fn in glob.glob(source_dn+'*.%s'%suffix): shutil.copy(fn,docs_dn)
		subprocess.call('make html',shell=True,cwd=docs_dn,
			stdout=open(docslog,'a'),stderr=subprocess.PIPE)
		index_fn = os.path.join(os.path.abspath(os.getcwd()),'amx/docs/build/_build/html/index.html')
		if not os.path.isfile(index_fn): raise Exception('\n[ERROR] failed to make docs. see "%s"'%docslog)
		print '[STATUS] docs are ready at "file://%s"'%index_fn
