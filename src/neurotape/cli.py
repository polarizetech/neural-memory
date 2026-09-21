"""neurotape CLI.

  neurotape encode a.wav b.wav c.csv --config cfg.yaml      one full run: encode -> consolidate -> recall
  neurotape encode --demo 2 --config cfg.yaml               ... on labelled synthetic streams
  neurotape exp <name> --config cfg.yaml --seeds 10 --workers 4
      names: delay streams ablations baselines lehr population attention codec salience recall_modes recall_drive binaural completion storage_diagnostic all
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .config import load_config


def cmd_encode(a) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from .decode import readout as ro
    from .decode.connear import load_connear
    from .decode.vocoder import vocode, write_reconstruction
    from .experiments import common as C
    from .frontend.base import StageUnavailable
    from .frontend.io import load_streams, synthetic_streams
    from .network import build_inputs, simulate
    from .recall.evaluate import evaluate

    cfg = load_config(a.config)
    if a.seed is not None:
        cfg.seed = a.seed
    streams = synthetic_streams(a.demo, cfg.protocol.encode_s, seed=cfg.seed) if a.demo else load_streams(a.files, cfg.frontend.csv_rate_hz)
    if any(not s.source.lower().endswith((".wav", ".flac", ".ogg")) and not s.source.startswith("synthetic") for s in streams) \
            and cfg.frontend.kind == "an":
        raise SystemExit("CSV / sensor streams are not sound: set frontend.kind: filterbank (and filterbank: logbp)")
    out = C.results_dir("encode")
    inputs = build_inputs(streams, cfg, keep_fine=False)
    res = simulate(cfg, inputs)
    ev, dec = evaluate(res, inputs, cfg)
    S, B = inputs.env.shape[:2]
    playback = []
    try:
        load_connear(a.connear_weights or "connear_weights")
        playback.append("connear: weights found, but an_rate-target inversion must be run via decode/connear.py:invert")
    except StageUnavailable as e:
        playback.append(f"PRIMARY playback (CoNNear inversion) UNAVAILABLE: {e}")
    for k, seg in enumerate(res.timeline.recalls()):
        Xr = ro.activity_features(*res.spikes_e, res.n_exc, seg.t0, seg.t1, cfg.decode.rate_hz, cfg.decode.filter_tau_ms)
        pred = dec.predict(Xr)
        for s in range(S):
            an = inputs.analyses[s]
            x = vocode(pred[:, s * B:(s + 1) * B], an.fcs, an.env_scale, cfg.frontend, cfg.decode.rate_hz, seed=cfg.seed)
            write_reconstruction(out / f"reconstruction_vocoder_stream{s}_delay{seg.delay_s:g}s.wav", x)
    playback.append("FALLBACK playback (noise vocoder) written: reconstruction_vocoder_*.wav -- never auditioned by this code")

    fig, axs = plt.subplots(4, 1, figsize=(9, 8), sharex=True)
    i, t = res.spikes_e
    axs[0].plot(t, i, ",k"); axs[0].set_ylabel("E cell")
    axs[1].plot(res.nm.t, res.nm.nm); axs[1].set_ylabel("NM(t)")
    axs[2].plot(res.lfp_t, np.abs(res.lfp_Ie) + 1.65 * np.abs(res.lfp_Ii), lw=0.4); axs[2].set_ylabel("LFP proxy (pA)")
    axs[3].plot(res.w_t, res.h_log.mean(0), label="mean early h"); axs[3].plot(res.w_t, 1 + res.z_log.mean(0), label="1 + mean late z")
    axs[3].legend(fontsize=7); axs[3].set_xlabel("simulated time (s)")
    for seg in res.timeline.segments:
        for ax in axs:
            ax.axvline(seg.t0, color="0.8", lw=0.6)
    C.stamp_figure(fig, cfg, f"front end: {res.extra['front_end']}"); fig.tight_layout(rect=(0, 0.02, 1, 1))
    fig.savefig(out / "overview.png", dpi=130); plt.close(fig)
    np.savez_compressed(out / "states_and_ranks.npz", state_t=res.state_t, state_e=res.state_e, state_i=res.state_i,
                        rank_t=res.rank_t, drive_nS=res.drive, spikes_e_i=i, spikes_e_t=t)
    rep = ("## Single run\n\nEvery audio file here is a RECONSTRUCTION decoded from network activity by a linear readout "
           "trained on the encode phase only.\n\n" + "".join(f"- {p}\n" for p in playback) +
           f"\n```json\n{json.dumps(ev, indent=1, default=float)[:6000]}\n```\n")
    C.save(out, cfg, [dict(ok=True, tag="encode", seed=cfg.seed, **ev)], ev, rep)
    print(out)


def cmd_exp(a) -> None:
    from .experiments import diagnostic, diagnostic2, lehr, storage, suite
    cfg = load_config(a.config)
    seeds = list(range(a.seeds))
    table = dict(delay=suite.exp_delay, streams=suite.exp_streams, ablations=suite.exp_ablations,
                 baselines=suite.exp_baselines, lehr=lehr.exp_lehr, population=suite.exp_population,
                 attention=suite.exp_attention, codec=storage.exp_codec, salience=storage.exp_salience,
                 recall_modes=suite.exp_recall_modes, recall_drive=suite.exp_recall_drive, binaural=suite.exp_binaural, completion=suite.exp_completion, storage_diagnostic=diagnostic.exp_storage_diagnostic, residual_decode=diagnostic2.exp_residual_decode, storage_A=diagnostic2.exp_storage_A, storage_B=diagnostic2.exp_storage_B)
    names = [n for n in table if n not in ("recall_drive", "binaural", "completion", "storage_diagnostic", "residual_decode", "storage_A", "storage_B")] if a.name == "all" else [a.name]
    if a.seeds < 10:
        print(f"NOTE: {a.seeds} seeds requested; the reporting standard for this project is >= 10.")
    for n in names:
        kw = dict(n_exc=160, n_inh=40, consolidate_s=8.0) if (a.smoke and n == "lehr") else {}
        print(n, "->", table[n](cfg, seeds, a.workers, **kw), flush=True)


def main(argv=None) -> None:
    import os, sys
    if os.environ.get("NEUROTAPE_HASH_PINNED") != "1":      # the running interpreter's own hash seed is fixed
        os.environ.update(PYTHONHASHSEED="0", NEUROTAPE_HASH_PINNED="1")   # at startup, so re-exec once
        os.execv(sys.executable, [sys.executable, "-m", "neurotape.cli", *(sys.argv[1:] if argv is None else argv)])
    p = argparse.ArgumentParser(prog="neurotape", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("encode"); e.add_argument("files", nargs="*"); e.add_argument("--config"); e.add_argument("--demo", type=int, default=0)
    e.add_argument("--seed", type=int); e.add_argument("--connear-weights"); e.set_defaults(fn=cmd_encode)
    x = sub.add_parser("exp"); x.add_argument("name"); x.add_argument("--config"); x.add_argument("--seeds", type=int, default=10)
    x.add_argument("--workers", type=int, default=4); x.add_argument("--smoke", action="store_true", help="plumbing check only: shrinks the Lehr sweep")
    x.set_defaults(fn=cmd_exp)
    a = p.parse_args(argv)
    if a.cmd == "encode" and not a.files and not a.demo:
        p.error("give input files or --demo N")
    a.fn(a)


if __name__ == "__main__":
    main()
