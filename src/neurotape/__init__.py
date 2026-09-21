"""neurotape -- a falsification testbed for waveform storage by synaptic tagging and capture."""
import os as _os

# One BLAS thread per process. Measured: two pooled workers with default threading spent 1811 s of
# SYSTEM time spinning against each other and took 5.5 min for a job that takes 27 s alone.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS", "NUMEXPR_NUM_THREADS"):
    _os.environ.setdefault(_v, "1")

__version__ = "0.1.0"
