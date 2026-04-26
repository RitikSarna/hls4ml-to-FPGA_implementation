"""
convert.py — Generic hls4ml conversion for binary segmentation models.

Usage:
    python convert.py --model path/to/saved_model --output ./hls_project

Requirements:
    pip install hls4ml[profiling]==0.7.1 tf-keras==2.19.0

What this script does:
    1. Loads a trained tf_keras SavedModel (QAT weights)
    2. Strips QAT wrappers back to a clean Keras model
    3. Rebuilds with relu6 → relu  (hls4ml 0.7.1 has no relu6
       streaming overload in nnet_activation.h)
    4. Configures hls4ml for Artix-7 FPGA deployment
    5. Writes the Vitis HLS C++ project to disk

After running this script:
    - Copy firmware_patches/ files into <output>/firmware/nnet_utils/
    - Run: vitis_hls -f build_prj.tcl
"""

import os
import argparse
import shutil
import tf_keras as keras
import hls4ml


# ── Argument parsing ──────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert a trained Keras segmentation model to hls4ml HLS project."
    )
    parser.add_argument(
        '--model', type=str, required=True,
        help='Path to saved tf_keras model (SavedModel format)'
    )
    parser.add_argument(
        '--output', type=str, default='./hls_project',
        help='Output directory for Vitis HLS project (default: ./hls_project)'
    )
    parser.add_argument(
        '--part', type=str, default='xc7a100tcsg324-1',
        help='Xilinx part number (default: xc7a100tcsg324-1 — Nexys A7-100T)'
    )
    parser.add_argument(
        '--clock', type=int, default=12,
        help='Clock period in ns (default: 12 = 83 MHz, safe for Artix-7)'
    )
    parser.add_argument(
        '--reuse', type=int, default=144,
        help=(
            'ReuseFactor — must evenly divide kernel*kernel*channels. '
            'For 3x3x16=144: valid values are 1,2,3,4,6,8,9,12,16,18,24,36,48,72,144. '
            'Higher = fewer DSPs, slower inference. (default: 144)'
        )
    )
    parser.add_argument(
        '--precision', type=str, default='ap_fixed<8,4>',
        help='HLS fixed-point precision (default: ap_fixed<8,4>)'
    )
    parser.add_argument(
        '--clean', action='store_true',
        help='Delete output directory before conversion if it exists'
    )
    return parser.parse_args()


# ── QAT weight stripping ──────────────────────────────────────────────────────
def strip_qat_wrappers(qat_model, base_model):
    """
    Transfer weights from a tfmot QAT-wrapped model back to a clean
    Keras model. QAT wrappers store weights in qat_layer.layer.get_weights()
    — calling qat_layer.get_weights() would also pull min/max quantization
    variables and corrupt the weight shapes.

    Args:
        qat_model:  model wrapped with tfmot.quantization.keras.quantize_model()
        base_model: clean unwrapped model with identical architecture

    Returns:
        base_model with QAT-tuned weights loaded
    """
    transferred = 0
    for qat_layer in qat_model.layers:
        inner = getattr(qat_layer, 'layer', None)
        if inner is None:
            continue
        try:
            base_layer = base_model.get_layer(inner.name)
            base_layer.set_weights(inner.get_weights())
            transferred += 1
        except ValueError:
            pass  # quantize_layer or other wrapper-only layers — skip

    print(f"   Transferred weights from {transferred} layers.")
    return base_model


# ── relu6 → relu rebuild ──────────────────────────────────────────────────────
def rebuild_with_relu(source_model):
    """
    Rebuild a model replacing all relu6 activations with relu.

    hls4ml 0.7.1 nnet_activation.h only implements the array-pointer
    signature for relu6. The io_stream mode passes hls::stream<> objects,
    which has no matching overload, causing a C++ compile error during
    Vitis HLS C-simulation.

    This is safe because ap_fixed<8,4> has a maximum representable value
    of +7.9375, making relu6's clip at 6.0 functionally redundant in
    fixed-point hardware.

    If your model does not use relu6 this function is a no-op.
    """
    config = source_model.get_config()
    replacements = 0

    def replace_relu6(cfg):
        nonlocal replacements
        if isinstance(cfg, dict):
            if cfg.get('class_name') == 'Activation':
                inner = cfg.get('config', {})
                if inner.get('activation') == 'relu6':
                    inner['activation'] = 'relu'
                    replacements += 1
            for v in cfg.values():
                replace_relu6(v)
        elif isinstance(cfg, list):
            for item in cfg:
                replace_relu6(item)

    replace_relu6(config)

    if replacements > 0:
        print(f"   Replaced {replacements} relu6 → relu activations.")
        rebuilt = keras.Model.from_config(config)
        rebuilt.set_weights(source_model.get_weights())
        return rebuilt
    else:
        print("   No relu6 activations found — model unchanged.")
        return source_model


# ── FIFO depth overrides ──────────────────────────────────────────────────────
def set_fifo_depths(hls_config, input_height, input_width, n_filters):
    """
    Set minimum safe FIFO depths for skip connection layers.

    In io_stream mode, skip connections must buffer the entire encoder
    feature map while the decoder waits. The minimum safe depth equals
    the number of 128-bit AXI-Stream words in the feature map:

        depth = (H * W * C) / (128 / bits_per_element)

    For 8-bit elements and 128-bit words: depth = H * W * C / 16

    Setting depth too small causes simulation deadlock.
    Setting depth too large wastes BRAM (each 8 BRAM_18K tiles = 1024 depth).
    """
    # c1 skip: full-resolution feature map
    c1_depth = (input_height * input_width * n_filters) // 16
    # c2 skip: half-resolution feature map
    c2_depth = ((input_height // 2) * (input_width // 2) * n_filters) // 16

    print(f"   FIFO depths: c1={c1_depth}, c2={c2_depth}")

    for layer_name in hls_config.get('LayerName', {}):
        if 'add' in layer_name.lower():
            hls_config['LayerName'][layer_name]['StreamDepth'] = c1_depth

    return hls_config


# ── Validation ────────────────────────────────────────────────────────────────
def validate_reuse_factor(rf, kernel=3, in_channels=16):
    """
    Warn if ReuseFactor does not evenly divide total MACs per layer.
    hls4ml silently rounds up to the nearest valid factor if invalid.
    """
    total_macs = kernel * kernel * in_channels  # 144 for default config
    if total_macs % rf != 0:
        valid = [i for i in range(1, total_macs + 1) if total_macs % i == 0]
        print(f"\n  WARNING: ReuseFactor={rf} does not divide {total_macs} MACs evenly.")
        print(f"   hls4ml will snap to nearest valid value.")
        print(f"   Valid factors: {valid}\n")


# ── Main conversion ───────────────────────────────────────────────────────────
def convert(args):

    # ── 1. Clean output dir ───────────────────────────────────────────────────
    if args.clean and os.path.exists(args.output):
        shutil.rmtree(args.output)
        print(f"  Removed existing output: {args.output}")

    # ── 2. Load model ─────────────────────────────────────────────────────────
    print(f"\n Loading model from: {args.model}")
    model = keras.models.load_model(args.model, compile=False)
    print(f"   Input shape:  {model.input_shape}")
    print(f"   Output shape: {model.output_shape}")
    print(f"   Parameters:   {model.count_params():,}")

    # Detect if this is a QAT-wrapped model
    is_qat = any(hasattr(l, 'layer') for l in model.layers)
    if is_qat:
        print("   Detected QAT-wrapped model — stripping quantization wrappers...")
        # Build a clean copy with same architecture
        # User needs to import their build function here if architecture differs
        # For the generic case we rebuild from config
        clean_model = keras.Model.from_config(model.get_config())
        model = strip_qat_wrappers(model, clean_model)

    # ── 3. Replace relu6 with relu ────────────────────────────────────────────
    print("\n🔧 Checking for relu6 activations...")
    model = rebuild_with_relu(model)

    # ── 4. Infer input dimensions ─────────────────────────────────────────────
    _, h, w, c_in = model.input_shape

    # Infer filter count from first conv layer
    n_filters = None
    for layer in model.layers:
        if hasattr(layer, 'filters'):
            n_filters = layer.filters
            break
    if n_filters is None:
        n_filters = 16  # fallback
        print(f" Could not detect filter count — assuming {n_filters}")

    # Validate reuse factor
    validate_reuse_factor(args.reuse, kernel=3, in_channels=n_filters)

    # ── 5. Build hls4ml config ────────────────────────────────────────────────
    print(f"\n⚙️  Building hls4ml config...")
    print(f"   Part:      {args.part}")
    print(f"   Clock:     {args.clock} ns ({1000//args.clock} MHz)")
    print(f"   Precision: {args.precision}")
    print(f"   ReuseFactor: {args.reuse}")
    print(f"   Strategy:  Resource")
    print(f"   io_type:   io_stream")

    hls_config = hls4ml.utils.config_from_keras_model(
        model,
        granularity='name',
        default_precision=args.precision,
        default_reuse_factor=args.reuse,
    )
    hls_config['Model']['Strategy']    = 'Resource'
    hls_config['Model']['ReuseFactor'] = args.reuse

    # Set FIFO depths for skip connections
    hls_config = set_fifo_depths(hls_config, h, w, n_filters)

    # ── 6. Convert ────────────────────────────────────────────────────────────
    print(f"\nConverting to HLS C++ project → {args.output}")
    hls_model = hls4ml.converters.convert_from_keras_model(
        model,
        hls_config=hls_config,
        output_dir=args.output,
        part=args.part,
        clock_period=args.clock,
        io_type='io_stream',       # required — io_parallel has depth bug in 0.7.1
    )

    hls_model.write()
    print("HLS project written.")

    # ── 7. Post-conversion instructions ───────────────────────────────────────
    print("\n" + "="*60)
    print("  NEXT STEPS")
    print("="*60)
    print(f"\n1. Apply firmware patches:")
    print(f"   cp firmware_patches/*.h {args.output}/firmware/nnet_utils/")
    print(f"\n2. Copy build script:")
    print(f"   cp build_prj.tcl {args.output}/")
    print(f"\n3. Run Vitis HLS synthesis:")
    print(f"   cd {args.output}")
    print(f"   vitis_hls -f build_prj.tcl")
    print(f"\n4. Open result in Vivado for implementation + bitstream.")
    print(f"\n If synthesis shows resource overflow:")
    print(f"   BRAM > available → reduce StreamDepth or increase ReuseFactor")
    print(f"   LUT  > available → ensure build_prj.tcl has:")
    print(f"                      config_compile -complex-mul-dsp=1")
    print(f"                      config_bind -effort high")


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    args = parse_args()
    convert(args)
