# hls4ml to FPGA Implementation

This repository demonstrates a complete, bare-metal hardware implementation of a neural network on a Xilinx FPGA. 

While many tutorials conclude at the software simulation stage, this project bridges the gap between software algorithms and physical hardware. It provides a blueprint for translating a machine learning model into RTL and deploying it within a System-on-Chip (SoC) environment using an AXI-Stream data pipeline.

## Table of Contents
1. [Phase 1: Model Architecture & Quantization-Aware Training (QAT)](#phase-1-model-translation-hls4ml)
2. [Phase 2: hls4ml Conversion & Vitis HLS Synthesis](#phase-2-high-level-synthesis-vitis-hls)
3. [Phase 3: Hardware Architecture (Vivado)](#phase-3-hardware-architecture-vivado)
4. [Results & Performance](#results--performance)

## Phase 1: Model Architecture & Quantization-Aware Training (QAT)

The pipeline begins with a custom binary segmentation model (`TinySegNet_FPGA`) trained in Python using `tf_keras`. Unlike standard cloud-based models, this architecture was designed from the ground up with strict FPGA hardware constraints in mind.

### Hardware-Driven Architecture Constraints
To ensure successful synthesis via `hls4ml`, the model adheres to specific rules:
* **Fixed Channel Width:** The number of filters remains constant throughout the encoder and decoder. This prevents DSP overflow during skip connections.
* **Addition over Concatenation:** Skip connections use `Add()` instead of `Concatenate()`. Concatenation doubles the channel width, which causes exponential resource scaling in hardware.
* **Activation Limits:** Standard `ReLU` is used instead of `ReLU6`. In `hls4ml 0.7.1`, `ReLU6` lacks a streaming overload in `nnet_activation.h`, causing C-simulation crashes.
* **Zero-Cost BatchNorm:** `BatchNormalization` is used with `use_bias=False`. These layers are completely folded into the convolutional weights during export, costing zero hardware resources.

### Training & Loss
The model utilizes **Quantization-Aware Training (QAT)** via `tfmot`. Instead of quantizing the model after training (PTQ), QAT simulates low-precision arithmetic during the forward pass, allowing the network to adapt its weights to the quantization error. 

Because the target is small structural faults (a severe class imbalance between the target and background), a combined **Dice + Binary Cross-Entropy (BCE)** loss function is used to stabilize gradients and prevent the model from collapsing into an all-background prediction.

## Phase 2: hls4ml Conversion & Vitis HLS Synthesis

Translating a QAT-wrapped Keras model directly to C++ firmware requires a careful extraction process and specific compiler directives to prevent hardware deadlocks and synthesis failures in **Vitis HLS 2023.2**.

### 1. The Conversion Script (`convert.py`)
The provided conversion script performs several critical preprocessing steps before invoking `hls4ml`:
* **Stripping QAT Wrappers:** It transfers the QAT-tuned weights back into a clean, unwrapped Keras model. Directly converting a QAT-wrapped model corrupts weight shapes.
* **FIFO Depth Overrides:** In streaming hardware, skip connections must buffer the entire encoder feature map while the decoder waits. The script calculates and sets the exact BRAM FIFO depth required (`depth = (H * W * C) / 16` for 128-bit words) to prevent simulation deadlocks.
* **Interface:** `io_type='io_stream'` is strictly enforced. `io_parallel` triggers a depth bug in `hls4ml 0.7.1` and scales synthesis time exponentially.

### 2. Vitis HLS 2023.2 Compatibility Patches
`hls4ml 0.7.1` generates C++ code with certain pragma patterns that cause silent failures in newer versions of Vitis HLS. Before running synthesis, the firmware is patched:
* **`#pragma HLS DATAFLOW`:** Commented out in `myproject.cpp` as Vitis HLS 2023.2 aggressively rejects it for multi-fanout skip connections.
* **`#pragma HLS ARRAY_PARTITION`:** Removed for intermediate 16K-element arrays to prevent the Vitis scheduler from crashing due to memory over-partitioning.

### 3. Hardware Resource Tuning
To fit the model onto an Artix-7 (A7-100T) without exhausting the Look-Up Tables (LUTs), we enforce aggressive DSP mapping in the `build_prj.tcl` script:
```tcl
config_compile -complex-mul-dsp=1   # Force DSP48E1 inference
config_bind    -effort high         # Aggressive DSP mapping
* **C Synthesis:** Converts the C++ logic into Verilog/VHDL, mapping mathematical operations to physical hardware gates and clock cycles.
* **Optimization:** Dataflow and pipeline pragmas are utilized to achieve high throughput and low latency.
* **IP Export:** The verified design is packaged into the Vivado IP Catalog format, creating a standalone, reusable hardware block.
```

## Phase 3: Hardware Architecture Overview (Vivado)
The custom hls4ml IP is integrated into a complete System-on-Chip (SoC) environment using Xilinx Vivado. The system is designed to seamlessly move data from a host PC, through the FPGA memory, into the hardware accelerator, and back.

The core architecture consists of three main components:
* **The Processor (MicroBlaze):** Acts as the system controller. It manages communication with the host PC via UART and buffers incoming image data in Block RAM.
* **AXI Direct Memory Access (DMA):** Offloads heavy data movement from the processor. It is configured to stream data directly from memory into the ML accelerator at high speeds.
* **The Data Pipeline:** Standard AXI-Stream infrastructure (including data-width converters and packet-boundary generators) is used to align the 32-bit system bus with the specific data-width requirements of the custom ML IP.

### Hardware Block Diagram
<img width="1620" height="774" alt="block_diagram" src="https://github.com/user-attachments/assets/6152e99b-343a-4632-a8c4-a30468ec216e" />


## Results & Performance

<img width="1628" height="766" alt="fpga_connections" src="https://github.com/user-attachments/assets/13eccedf-07ec-4c5e-bf6f-777e96942919" />

### Hardware Resource Utilization

* **LUTs:** 51,977 (81%)
* **BRAMs:** 219 (81%)
* **DSPs:** 0 (0%)
* **Flip-Flops (FF):** 39,399 (31%)

* **WNS:** 0.102 ns
<img width="875" height="242" alt="Screenshot 2026-04-25 144214" src="https://github.com/user-attachments/assets/10e97232-fbfa-4f8e-8010-194e9f4254f4" />

* **Power:** 0.456 W
<img width="675" height="348" alt="Screenshot 2026-04-25 144157" src="https://github.com/user-attachments/assets/a4dfb7c3-40d1-478d-aef4-03c560cc93ea" />
