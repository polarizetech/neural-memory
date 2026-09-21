# 20260921-015407_codec_comparison

_time compression 60x (slow processes only: early-phase decay, protein, late phase, CREB)_

## Stored size and quality vs Opus / AAC at matched bitrate

Network: encode held-out r +0.820 [+0.786, +0.854] (n=10); RECALL r after the last delay -0.107 [-0.191, -0.023] (n=10).
Stored size: synaptic state 3.17 kbps; with readout 13.41 kbps.

| codec @ budget | bitrate actually used (kbps) | floor hit | envelope r | network recall - codec |
|---|---|---|---|---|
| libopus@state | 6.88 | True | +0.905 [+0.886, +0.923] (n=10) | -1.012 [-1.091, -0.933] (n=10) network LOSES or ties |
| libopus@full | 12.03 | False | +0.935 [+0.926, +0.943] (n=10) | -1.042 [-1.122, -0.962] (n=10) network LOSES or ties |
| aac@state | 11.60 | True | +0.987 [+0.984, +0.989] (n=10) | -1.094 [-1.178, -1.010] (n=10) network LOSES or ties |
| aac@full | 14.97 | False | +0.996 [+0.995, +0.997] (n=10) | -1.103 [-1.187, -1.019] (n=10) network LOSES or ties |

Where `floor hit` is True the codec could not go as low as the network's budget, so it was given MORE bits than the network.

Video / event-camera encoding: **unavailable** -- no retina front end is built (later milestone).
