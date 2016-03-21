#!/bin/bash

#---SETTINGS: nprocs, maxhours (hours), extend (ps), tpbconv, mdrun
#---SETTINGS OVERRIDES HERE

#---log to standard log
step=$(pwd | sed -r 's/.+\/(.+)/\1/')
metalog="../script-$step.log"
echo "[STATUS] continuing simulation from part $PRUN in $step"
echo "[STATUS] logging to $metalog"
echo "[STATUS] running ... "

#---modify the mdp via grompp as per manual recommendations
log="grompp-change"
cmd="$GROMPP -f input-md-in.mdp -c system-input.tpr -o md.part0001.tpr -t system-input.cpt"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec

#---run
log="mdrun-change"
cmd="$MDRUN -deffnm md -s md.part0001.tpr -cpi system-input.cpt -cpo md.part0001.cpt -noappend -maxh $MAXHOURS"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec
