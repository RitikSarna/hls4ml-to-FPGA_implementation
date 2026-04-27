# ─────────────────────────────────────────────────────────────────
# Nexys A7-100T Master Constraints
# Target: xc7a100tcsg324-1
# Clock:  12 ns period (83 MHz)
#
# Adjust PACKAGE_PIN values if targeting a different board.
# Full Nexys A7 master XDC available at:
# https://github.com/Digilent/digilent-xdc
# ─────────────────────────────────────────────────────────────────

# ── System Clock (100 MHz onboard oscillator) ─────────────────────
# The Clocking Wizard in the block design generates 83 MHz from this.
set_property -dict {
    PACKAGE_PIN E3
    IOSTANDARD LVCMOS33
} [get_ports sys_clk]

create_clock \
    -period 10.000 \
    -name sys_clk_pin \
    -waveform {0.000 5.000} \
    [get_ports sys_clk]

# ── Reset Button (CPU_RESET, active low) ──────────────────────────
set_property -dict {
    PACKAGE_PIN C12
    IOSTANDARD LVCMOS33
} [get_ports reset]

# ── UART (USB-UART bridge via FT2232) ────────────────────────────
# Used by MicroBlaze for debug output / patch streaming
set_property -dict {
    PACKAGE_PIN D4
    IOSTANDARD LVCMOS33
} [get_ports uart_rtl_0_rxd]

set_property -dict {
    PACKAGE_PIN C4
    IOSTANDARD LVCMOS33
} [get_ports uart_rtl_0_txd]

# ── False path on async reset ─────────────────────────────────────
set_false_path -from [get_ports reset]

# ── Bitstream settings ────────────────────────────────────────────
set_property BITSTREAM.GENERAL.COMPRESS TRUE [current_design]
set_property CONFIG_VOLTAGE 3.3 [current_design]
set_property CFGBVS VCCO [current_design]
