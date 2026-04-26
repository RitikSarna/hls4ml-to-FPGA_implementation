# hls4ml Conversion

## Vitis HLS 2023.2 Compatibility Fixes

hls4ml 0.7.1 generates code with 5 pragma patterns that cause
silent failures in Vitis HLS 2023.2. Pre-patched files are in
the `patches/` folder. Copy them to your hls4ml project's
`firmware/nnet_utils/` directory before running synthesis.

| File | Issue | Fix |
|------|-------|-----|
| myproject.cpp | `#pragma HLS DATAFLOW` rejects multi-fanout skip connections | Comment out |
| myproject.cpp | `#pragma HLS ARRAY_PARTITION complete dim=0` on 16K-element arrays crashes scheduler | Remove all intermediate ones |

## Critical Config Flags (build_prj.tcl)

```tcl
config_compile -complex-mul-dsp=1   # enable DSP48E1 inference
config_bind    -effort high         # aggressive DSP mapping
```

Without these, all multiplications fall back to LUT fabric
and LUT utilisation exceeds 160% on A7-100T.

## io_stream is Required

```python
io_type='io_stream'   # NOT io_parallel
```

`io_parallel` causes a depth bug in hls4ml 0.7.1's vivado_writer.py
that crashes during `hls_model.write()`. `io_stream` also reduces
scheduler complexity from O(exponential) to O(linear), cutting
synthesis time from hours to ~4 minutes.

## ReuseFactor

Valid values for 3×3×16=144 MACs: `1, 2, 3, 4, 6, 8, 9, 12, 16, 18, 24, 36, 48, 72, 144`

| RF | DSPs | Synthesis time | Per-patch latency |
|----|------|---------------|-------------------|
| 144 | 5 | ~4 min | ~5.6 ms |
| 9 | ~80 | ~4 min | ~0.88 ms |
| 6 | ~120 | ~4 min | ~0.6 ms |
| 3 | ~240 (at limit) | ~5 min | ~0.3 ms |
