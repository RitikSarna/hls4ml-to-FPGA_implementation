# hls4ml to FPGA Implementation

![Vivado](https://img.shields.io/badge/Xilinx-Vivado-red) ![Vitis HLS](https://img.shields.io/badge/Xilinx-Vitis_HLS-blue) ![hls4ml](https://img.shields.io/badge/hls4ml-enabled-brightgreen) ![Python](https://img.shields.io/badge/Python-3.8+-yellow)

This repository demonstrates a complete, bare-metal hardware implementation of a neural network on a Xilinx FPGA. 

While many tutorials conclude at the software simulation stage, this project bridges the gap between software algorithms and physical hardware. It provides a blueprint for translating a machine learning model into RTL and deploying it within a System-on-Chip (SoC) environment using an AXI-Stream data pipeline.

## Table of Contents
1. [Phase 1: Model Translation (hls4ml)](#phase-1-model-translation-hls4ml)
2. [Phase 2: High-Level Synthesis (Vitis HLS)](#phase-2-high-level-synthesis-vitis-hls)
3. [Phase 3: Hardware Architecture (Vivado)](#phase-3-hardware-architecture-vivado)
4. [Results & Performance](#results--performance)

## Phase 1: Model Translation (hls4ml)
The pipeline begins with a standard machine learning model trained in a Python environment. To deploy this onto an FPGA, the model must be translated into synthesizable C++ code using hls4ml.

* **Quantization:** The model utilizes Post-Training Quantization (PTQ) to reduce 32-bit floating-point weights to fixed-point precision. This drastically reduces DSP and BRAM utilization on the FPGA.
* **Interface Configuration:** During the hls4ml export step, the I/O arrays are strictly configured to use AXI4-Stream (`axis`) interfaces. This ensures the model can process continuous streams of data, maximizing throughput.

## Phase 2: High-Level Synthesis (Vitis HLS)
The exported C++ project is synthesized into a Register-Transfer Level (RTL) IP block using Xilinx Vitis HLS.

```
vitis_hls build_prj.tcl -f
```

* **C Synthesis:** Converts the C++ logic into Verilog/VHDL, mapping mathematical operations to physical hardware gates and clock cycles.
* **Optimization:** Dataflow and pipeline pragmas are utilized to achieve high throughput and low latency.
* **IP Export:** The verified design is packaged into the Vivado IP Catalog format, creating a standalone, reusable hardware block.

## Phase 3: Hardware Architecture Overview (Vivado)
The custom hls4ml IP is integrated into a complete System-on-Chip (SoC) environment using Xilinx Vivado. The system is designed to seamlessly move data from a host PC, through the FPGA memory, into the hardware accelerator, and back.

The core architecture consists of three main components:
* **The Processor (MicroBlaze):** Acts as the system controller. It manages communication with the host PC via UART and buffers incoming image data in Block RAM.
* **AXI Direct Memory Access (DMA):** Offloads heavy data movement from the processor. It is configured to stream data directly from memory into the ML accelerator at high speeds.
* **The Data Pipeline:** Standard AXI-Stream infrastructure (including data-width converters and packet-boundary generators) is used to align the 32-bit system bus with the specific data-width requirements of the custom ML IP.

### Hardware Block Diagram
<img width="1620" height="774" alt="block_diagram" src="https://github.com/user-attachments/assets/6152e99b-343a-4632-a8c4-a30468ec216e" />


## Results & Performance


### Hardware Resource Utilization

* **LUTs:** 51,977 (81%)
* **BRAMs:** 219 (81%)
* **DSPs:** 0 (0%)
* **Flip-Flops (FF):** 39,399 (31%)

* **WNS:** 0.102 ns
<img width="875" height="242" alt="Screenshot 2026-04-25 144214" src="https://github.com/user-attachments/assets/10e97232-fbfa-4f8e-8010-194e9f4254f4" />

* **Power:** 0.456 W
<img width="675" height="348" alt="Screenshot 2026-04-25 144157" src="https://github.com/user-attachments/assets/a4dfb7c3-40d1-478d-aef4-03c560cc93ea" />
