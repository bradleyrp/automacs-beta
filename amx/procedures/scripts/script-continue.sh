#!/bin/bash

#---SETTINGS: nprocs, maxhours (hours), extend (ps), tpbconv, mdrun
#---SETTINGS OVERRIDES HERE

#---find last CPT
PRUN=0
for file in md.part*.cpt
do
if [ $(echo ${file:7:4} | sed 's/^0*//') -gt $PRUN ]; 
then PRUN=$(echo ${file:7:4} | sed 's/^0*//')
fi
done
NRUN=$(($PRUN+1))

#---log to standard log
step=$(pwd | sed -r 's/.+\/(.+)/\1/')
metalog="../script-$step.log"
echo "[STATUS] continuing simulation from part $PRUN in $step"
echo "[STATUS] logging to $metalog"
echo "[STATUS] running ... "

#---extend TPR
log=$(printf tpbconv-%04d $NRUN)
cmd="$TPBCONV -extend $EXTEND -s $(printf md.part%04d.tpr $PRUN) -o $(printf md.part%04d.tpr $NRUN)"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec

#---continue simulation
BASE=$(printf md.part%04d $NRUN)
BASE_OLD=$(printf md.part%04d $PRUN)
log=$(printf mdrun-%04d $NRUN)
cmd="$MDRUN -deffnm md -s $BASE.tpr -cpi $BASE_OLD.cpt -cpo $BASE.cpt -noappend -maxh $MAXHOURS"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec
echo "[STATUS] done continuation stage"

