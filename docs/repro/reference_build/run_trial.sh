#!/bin/sh
# One reference trial = the authors' run_recall_varied_size block for net150, verbatim arguments.
d="$1"; mkdir -p "$d" && cd "$d" || exit 1
cp ../../memory-consolidation-stc/simulation-bin/run_binary_paper1/connections.txt .
rm -f saved_state.txt
../bin/net150.out -Nl_exc=40 -Nl_inh=20 -t_max=30 -N_stim=25 -pc=0.1 -learn=TRIPLETf100 -recall=F100D1at20.0 -w_ei=2 -w_ie=4.0 -w_ii=4.0 -I_0=0.15 -sigma_WN=0.05 -theta_p=3.0 -theta_d=1.2 -purpose="Learning, 10s-recall" > log_10s.txt 2>&1
mv -f saved_state0.txt saved_state.txt
../bin/net150.out -Nl_exc=40 -Nl_inh=20 -t_max=28820 -N_stim=25 -pc=0.1 -learn= -recall=F100D1at28810.0 -w_ei=2 -w_ie=4.0 -w_ii=4.0 -I_0=0.15 -sigma_WN=0.05 -theta_p=3.0 -theta_d=1.2 -purpose="Consolidation, 8h-recall" > log_8h.txt 2>&1
rm -f saved_state.txt
echo done > DONE
