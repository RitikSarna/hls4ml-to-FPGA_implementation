# Vivado Implementation

This folder contains scripts to take the Vitis HLS output and 
produce a bitstream for the Nexys A7-100T.

## Prerequisites

- Vivado 2023.2 with valid licence
- Vitis HLS synthesis completed (run `vitis_hls -f build_prj.tcl` first)
- Nexys A7-100T connected via USB (for programming)

## Steps

### 1. Edit paths in `create_project.tcl`

```tcl
set hls_output_dir  "C:/path/to/hls_project"
set project_dir     "C:/path/to/vivado_project"
```

### 2. Run the script

**Batch mode (recommended):**
```bash
vivado -mode batch -source create_project.tcl
```

**Interactive:**
Open Vivado → Tools → Tcl Console
source C:/path/to/vivado/create_project.tcl

### 3. Program the board

Once `myproject.bit` is generated:
Open Hardware Manager → Connect → Program Device

Or uncomment the programming lines at the bottom of `create_project.tcl`.

## Timing Notes

Target clock is **12 ns (83 MHz)**. If timing fails (WNS < 0):

| Fix | How |
|-----|-----|
| Relax clock | Change `clock_period` to `13` in `build_prj.tcl`, rerun HLS |
| Check WNS | Anything above -0.5 ns Vivado often closes with retiming |
| Increase effort | Set implementation strategy to `Performance_ExplorePostRoutePhysOpt` |
