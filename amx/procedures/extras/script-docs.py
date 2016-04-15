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
		print '[STATUS] cleaning documentation'
		shutil.rmtree(docs_dn)
	else:
		print '[STATUS] building docs and logging to amx/docs/build/log-docs-build'
		if not os.path.isdir(docs_dn): os.mkdir(docs_dn)
		subprocess.call('sphinx-apidoc -F -o . ../../../amx',shell=True,cwd=docs_dn,
			stdout=open('amx/docs/build/log-docs-build','w'),stderr=subprocess.PIPE)
		shutil.copy(source_dn+'conf.py',docs_dn)
		shutil.copy(source_dn+'style.css',docs_dn+'/_static')
		for fn in glob.glob(source_dn+'*.png'): shutil.copy(fn,docs_dn)
		for fn in glob.glob(source_dn+'*.rst'): shutil.copy(fn,docs_dn)
		subprocess.call('make html',shell=True,cwd=docs_dn,
			stdout=open('amx/docs/build/log-docs-build','a'),stderr=subprocess.PIPE)
		print '[STATUS] docs are ready at "file://%s"'%os.path.join(
			os.path.abspath(os.getcwd()),'amx/docs/build/_build/html/index.html')
