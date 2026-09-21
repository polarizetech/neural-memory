# R1 — building the authors' reference on macOS (arm64), unmodified

Source: `github.com/jlubo/memory-consolidation-stc` at commit `ac6d2ba` (Apache-2.0), the paper-1 configuration
(`-D MEMORY_CONSOLIDATION_P1 -D CORE_SIZE_CMD=150`), run with the verbatim arguments of the authors'
`simulation-bin/run_binary_paper1/run_recall_varied_size` block for `net150` (`run_trial.sh`) and their fixed
`connections.txt`. `github.com/jlubo/brian_network_plasticity` is a Brian2 port of the same model for a later paper's
comparisons; it was read (neurotape's equations were taken from it) but not run here — the C++ code is the one the
paper's numbers came from.

**No source file was changed.** Three build fixes, all outside the source tree:

1. The authors link `code.zip` and `plotFunctions.py` into the binary with GNU-ld's `-Wl,--format=binary`, which
   Apple's linker lacks. `embed.s` provides the same four symbols with `.incbin`.
2. `get_current_dir_name()` is glibc-only. `macos_shim.h` (force-included with `-include`) defines it as `getcwd(NULL, 0)`.
3. `-static` dropped (unsupported on macOS); `-std=c++14` instead of `c++11` (Homebrew boost 1.92 needs it); Apple clang
   instead of g++ 7.4; boost_serialization from Homebrew.

```sh
cd memory-consolidation-stc/simulation-code
zip -q -D code.zip * -x '*.out' '*.o' '*.txt'
clang -c embed.s -o embed.o
clang++ -std=c++14 -O1 -include macos_shim.h NetworkMain.cpp embed.o -D MEMORY_CONSOLIDATION_P1 -D CORE_SIZE_CMD=150 \
    -w -I/opt/homebrew/include -L/opt/homebrew/lib -lboost_serialization -o net150.out
```

The program's own plotting calls fail at run time (`matplotlib.pyplot.register_cmap` no longer exists); they only draw
figures and do not touch the data files. One trial = 7–14 min for learning + 10 s recall and ~5 min for the
fast-forwarded 8 h run. Scoring: `docs/repro/r1_analyse.py` (the authors' `calculateQ.py` / `calculateMIa.py`).
