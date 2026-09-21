"""PRIMARY playback: decode to periphery output, then invert the periphery by gradient descent.

Route: the readout is trained (encode phase only) to predict per-stream AUDITORY-NERVE RATE
patterns (``decode.targets: [an_rate]``); a waveform is then optimised so that a DIFFERENTIABLE
periphery reproduces that pattern. The differentiable periphery is CoNNear (Baby, Van Den Broucke
& Verhulst 2021, Nat Mach Intell 3:134; Drakopoulos, Baby & Verhulst 2021, Commun Biol 4:827), a
CNN surrogate of the Verhulst et al. 2018 transmission-line cochlea + IHC + ANF models.

STATUS ON THIS BENCH: NOT RUN. CoNNear needs TensorFlow/Keras and the published weights
(github.com/HearingTechnology/CoNNear_periphery), whose licence is academic / non-commercial --
an operator decision before download. With 13 GB of disk free and Keras-3 incompatibilities in
the published model JSON likely, this module raises StageUnavailable rather than pretending; the
vocoder fallback is reported instead and the report says which one ran.

Two honest caveats that hold even once it runs: (1) CoNNear approximates the Verhulst model while
the forward front end here is Zilany 2014, so the inversion crosses a model mismatch; (2) a
waveform that reproduces a RATE pattern is not unique -- phase is unconstrained above the
phase-locking limit, so this is a reconstruction of what the nerve would report, not of the sound.
"""
from __future__ import annotations

import numpy as np

from ..frontend.base import StageUnavailable


def load_connear(weights_dir):
    try:
        import tensorflow as tf  # noqa: F401
    except ImportError as e:
        raise StageUnavailable("CoNNear inversion needs TensorFlow (not installed on this bench) and the "
                               "CoNNear_periphery weights (academic/non-commercial licence)") from e
    from pathlib import Path
    from tensorflow.keras.models import model_from_json
    wd = Path(weights_dir)
    models = {}
    for name in ("cochlea", "ihc", "anfH", "anfM", "anfL"):
        js, h5 = wd / f"{name}.json", wd / f"{name}.h5"
        if not js.exists():
            raise StageUnavailable(f"CoNNear weights not found at {js}")
        m = model_from_json(js.read_text()); m.load_weights(str(h5)); m.trainable = False
        models[name] = m
    return models


def invert(an_rate_target: np.ndarray, models, fs: float = 20000.0, n_steps: int = 500, lr: float = 1e-3,
           seed: int = 0) -> tuple[np.ndarray, list[float]]:
    """Gradient descent on the waveform. an_rate_target: (T, n_cf) at the model's output rate."""
    import tensorflow as tf
    rng = np.random.default_rng(seed)
    x = tf.Variable(1e-3 * rng.standard_normal((1, an_rate_target.shape[0], 1)).astype("float32"))
    tgt = tf.constant(an_rate_target[None].astype("float32"))
    opt, losses = tf.keras.optimizers.Adam(lr), []
    for _ in range(n_steps):
        with tf.GradientTape() as tape:
            bm = models["cochlea"](x); v = models["ihc"](bm)
            rate = (models["anfH"](v) + models["anfM"](v) + models["anfL"](v)) / 3.0
            n = min(rate.shape[1], tgt.shape[1])
            loss = tf.reduce_mean((rate[:, :n] - tgt[:, :n]) ** 2)
        opt.apply_gradients([(tape.gradient(loss, x), x)])
        losses.append(float(loss))
    return x.numpy()[0, :, 0], losses
