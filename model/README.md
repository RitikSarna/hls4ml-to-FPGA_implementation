# Model

This folder contains a **generic** binary segmentation architecture
designed for FPGA deployment via hls4ml.

## Bring Your Own Dataset

This repo does **not** include training data or a pre-trained model.
The architecture constraints documented here apply to ANY binary
segmentation model you want to deploy on FPGA via hls4ml.

## Steps

1. Prepare your dataset as grayscale or RGB image patches + binary masks
2. Train using your own pipeline — the architecture in `architecture.py`
   is pre-configured for hls4ml compatibility
3. Follow `hls4ml_conversion/README.md` to convert to RTL
4. Follow `vivado/README.md` to generate a bitstream

## Architecture Requirements for hls4ml Compatibility

If you use your own architecture instead of the one provided,
it **must** satisfy these constraints or synthesis will fail:

| Constraint | Why |
|---|---|
| Fixed channel width throughout | Concatenate skip connections cause DSP overflow |
| Add() not Concatenate for skips | Concatenate widens tensors beyond DSP budget |
| ReLU not ReLU6 | No streaming overload for relu6 in hls4ml 0.7.1 |
| use_bias=False with BatchNorm | Avoids double bias after BN folding |
| Input layer named 'image_input' | hls4ml AXI-Stream port naming |

## Quantization-Aware Training

Wrap with tfmot **before** compiling:

```python
import tf_keras as keras              # NOT tf.keras — see note below
import tensorflow_model_optimization as tfmot
from model.architecture import build_segnet_fpga

base_model = build_segnet_fpga()
qat_model  = tfmot.quantization.keras.quantize_model(base_model)
qat_model.compile(optimizer='adam', loss=dice_bce_loss, metrics=['accuracy'])
```

> **Important:** TensorFlow 2.16+ ships Keras 3 by default.
> tfmot 0.8.0 requires Keras 2. Use `tf_keras` (the official Keras 2
> shim) instead of `tf.keras` or the import will crash with:
> `ValueError: to_quantize can only be a Sequential or Functional model`
