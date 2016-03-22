#!/bin/bash

#---SETTINGS: nprocs, maxhours (hours), extend (ps), tpbconv, mdrun
#---SETTINGS OVERRIDES HERE

#---log to standard log
step=$(pwd | sed -r 's/.+\/(.+)/\1/')
metalog="../script-$step.log"
echo "[STATUS] continuing simulation from part $LAST_PART"
echo "[STATUS] logging to $metalog"
echo "[STATUS] running ... "

#---! note that system-groups.ndx is not optional
#---modify the mdp via grompp as per manual recommendations
PARTNUM=$(($LAST_PART+1))
log="grompp-change"
<<<<<<< HEAD
cmd="$GROMPP -f input-md-in.mdp -c system-input.tpr -o system-input-modify.tpr -t system-input.cpt -p system.top -n system-groups.ndx $EXTEND_FLAG"
=======
cmd="$TPBCONV -f input-md-in.mdp -c system-input.tpr -o md.part0001.tpr -t system-input.cpt"
>>>>>>> 120a249a5f5954ddf542be280813fbe054098fac
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec

#---if write_continue_script gets continue_extend then we intervene to extend the simulation timewise
if ! [[ -z "$CONTINUE_EXTEND" ]]; then 
log="tpbconv-extend"
cmd="$TPBCONV -s system-input-modify.tpr -o $(printf md.part%04d.tpr $PARTNUM) -extend $CONTINUE_EXTEND"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec
else
cp system-input-modify.tpr $(printf md.part%04d.tpr $PARTNUM)
fi

#---run
log="mdrun-change"
cmd="$MDRUN -deffnm md -s $(printf md.part%04d.tpr $PARTNUM) -cpi system-input.cpt -cpo $(printf md.part%04d.tpr $PARTNUM) -noappend -maxh $MAXHOURS"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec
