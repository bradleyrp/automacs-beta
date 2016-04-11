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
#---we send the cpt to grompp (not mdrun) as per instructions from gromacs
PARTNUM=$(($LAST_PART+1))
if [[ -f system-groups.ndx ]]; then HAS_GROUPS="-n system-groups.ndx"; else HAS_GROUPS=""; fi
log="grompp-change"
cmd="$GROMPP -f input-md-in.mdp -c system-input.tpr -o system-input-modify.tpr -t system-input.cpt -p system.top $EXTEND_FLAG -po system-input-new.mdp -maxwarn $MAXWARN"
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
cmd="$MDRUN -e $(printf md.part%04d.edr $PARTNUM) -g $(printf md.part%04d.log $PARTNUM) -s $(printf md.part%04d.tpr $PARTNUM) -x $(printf md.part%04d.xtc $PARTNUM) -o $(printf md.part%04d.trr $PARTNUM) -c $(printf md.part%04d.gro $PARTNUM) -cpo $(printf md.part%04d.cpt $PARTNUM) -maxh $MAXHOURS"
cmdexec=$cmd" &> log-$log"
echo "[FUNCTION] gmx_run ('"$cmd"',) {'skip': False, 'log': '$log', 'inpipe': None}" >> $metalog
eval $cmdexec
