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
if [[ ! -z $EXTEND  ]]; then EXTEND_FLAG="-extend $EXTEND";
elif [[ ! -z $UNTIL ]]; then EXTEND_FLAG="-until $UNTIL";
else EXTEND_FLAG="-nsteps -1"; fi
log=$(printf tpbconv-%04d $NRUN)
cmd="$TPBCONV $EXTEND_FLAG -s $(printf md.part%04d.tpr $PRUN) -o $(printf md.part%04d.tpr $NRUN)"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec

#---continue simulation
log=$(printf mdrun-%04d $NRUN)
cmd="$MDRUN -s $(printf md.part%04d.tpr $NRUN) \
-cpi $(printf md.part%04d.cpt $PRUN) \
-cpo $(printf md.part%04d.cpt $NRUN) \
-g $(printf md.part%04d.log $NRUN) \
-e $(printf md.part%04d.edr $NRUN) \
-o $(printf md.part%04d.trr $NRUN) \
-x $(printf md.part%04d.xtc $NRUN) \
-c $(printf md.part%04d.gro $NRUN) -maxh $MAXHOURS"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec
echo "[STATUS] done continuation stage"
