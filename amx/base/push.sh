#!/bin/bash
#---clean is run by make
#---clean may be unnecessary if .gitignore is set correctly
echo "[NOTE] directory size = $(du -h -d 0)"
timestamp=$(date +%Y.%m.%d.%H%M)
echo "pushing code to local repository via"
echo "> git commit -a -m \"${@:2}\""
read -p "okay to commit and push (no password step so be careful) y/N? " -r
if [[ $REPLY =~ ^[Yy]$ ]]
then
	commit_message=${@:2}
	git add . --all
  	git commit -a -m "$commit_message"
    git push
fi

