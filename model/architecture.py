"""
Generic binary segmentation model for FPGA deployment via hls4ml.

Design constraints (required for hls4ml io_stream synthesis):
  - Fixed channel width throughout (no widening at skip connections)
  - Add() skip connections instead of Concatenate
  - ReLU instead of ReLU6 (no streaming overload in hls4ml 0.7.1)
  - BatchNorm with use_bias=False (folded at export, zero HW cost)
  - he_normal initializer (correct for ReLU-family activations)
"""

import tf_keras as keras

def build_segnet_fpga(
    input_height=32,
    input_width=32,
    input_channels=1,
    n_filters=16,
    input_name='image_input'
):
    """
    Builds a compact SegNet encoder-decoder for FPGA deployment.

    Args:
        input_height: patch height (default 32)
        input_width:  patch width  (default 32)
        input_channels: 1 for grayscale, 3 for RGB
        n_filters: channel count (keep fixed throughout — do not change
                   per layer, as Concatenate skip connections will cause
                   DSP overflow in hls4ml synthesis)
        input_name: must be 'image_input' for hls4ml AXI-Stream port naming

    Returns:
        tf_keras.Model ready for QAT wrapping and hls4ml export
    """
    layers = keras.layers

    def conv_bn_relu(x, filters, name_prefix):
        x = layers.Conv2D(
            filters, (3, 3), padding='same',
            use_bias=False,
            kernel_initializer='he_normal',
            name=f'{name_prefix}_conv')(x)
        x = layers.BatchNormalization(
            momentum=0.9, epsilon=1e-5,
            name=f'{name_prefix}_bn')(x)
        x = layers.Activation('relu',        # NOT relu6 — no streaming
            name=f'{name_prefix}_relu')(x)   # overload in hls4ml 0.7.1
        return x

    inp = layers.Input(
        shape=(input_height, input_width, input_channels),
        name=input_name)   # hls4ml maps this to AXI-Stream port name

    # ── Encoder ───────────────────────────────────────────────────
    c1 = conv_bn_relu(inp, n_filters, 'enc1')    # skip source
    p1 = layers.MaxPooling2D((2, 2))(c1)

    c2 = conv_bn_relu(p1,  n_filters, 'enc2')    # skip source
    p2 = layers.MaxPooling2D((2, 2))(c2)

    # ── Bottleneck ────────────────────────────────────────────────
    b  = conv_bn_relu(p2,  n_filters, 'bottleneck')

    # ── Decoder (Add not Concatenate — keeps channel width fixed) ─
    u1 = layers.UpSampling2D((2, 2))(b)
    u1 = layers.Add(name='skip_add_1')([u1, c2])
    c3 = conv_bn_relu(u1,  n_filters, 'dec1')

    u2 = layers.UpSampling2D((2, 2))(c3)
    u2 = layers.Add(name='skip_add_2')([u2, c1])
    c4 = conv_bn_relu(u2,  n_filters, 'dec2')

    # ── Output ────────────────────────────────────────────────────
    out = layers.Conv2D(
        1, (1, 1), padding='same',
        activation='sigmoid',
        name='output')(c4)

    return keras.Model(inp, out, name='TinySegNet_FPGA')


if __name__ == '__main__':
    model = build_segnet_fpga()
    model.summary()
    # Total params: ~9,697 at default settings
    # Float32 size: ~37.88 KB
    # INT8 size after QAT export: ~17.9 KB
