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

"""
quickstart guide to pushing docs to github pages

git init .

git commit -am 'initial commit' --allow-empty
touch .nojekyll
git add .
git commit -am 'added'
git remote add origin https://github.com/bradleyrp/amxdocs.git
git push -u origin master

git branch gh-pages
git symbolic-ref HEAD refs/heads/gh-pages  # auto-switches branches to gh-pages
rm .git/index
git clean -fdx
git branch #---check that you are on gh-pages

git push --set-upstream origin gh-pages
"""
