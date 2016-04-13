#!/bin/bash

#---! only run this from the top level alongside/from makefile

<<notes
notes

here=$(pwd)
codeback=../../../amx
docsdir=amx/docs/build
sourcedir=amx/docs/source

#---if no arguments we bootstrap the docs and make HTML files
if [[ ! -d $docsdir ]]; then 
mkdir $docsdir
cd $docsdir
sphinx-apidoc -F -o . $codeback
cd $here
fi
cd $sourcedir
cp conf.py $here/$docsdir
cp *.png $here/$docsdir
cp *.rst $here/$docsdir
cp style.css $here/$docsdir/_static/
cd $here
echo $@
make -C $docsdir html
echo "[STATUS] docs are ready at file://$(pwd)/amx/docs/build/_build/html/index.html"
