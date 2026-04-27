# ─────────────────────────────────────────────────────────────────
# create_project.tcl
#
# Creates a Vivado project from the hls4ml-generated RTL.
# Run this AFTER Vitis HLS synthesis completes.
#
# Usage (in Vivado Tcl console or batch mode):
#   vivado -mode batch -source create_project.tcl
#
# Or interactively:
#   Open Vivado → Tools → Tcl Console → source create_project.tcl
#
# Edit the paths in the CONFIG section before running.
# ─────────────────────────────────────────────────────────────────

# ── CONFIG — edit these paths ─────────────────────────────────────
set hls_output_dir  "C:/path/to/hls_project"
set project_dir     "C:/path/to/vivado_project"
set project_name    "segnet_fpga"
set fpga_part       "xc7a100tcsg324-1"
set n_jobs          4
# ─────────────────────────────────────────────────────────────────

puts "Creating Vivado project: $project_name"
puts "HLS source:  $hls_output_dir"
puts "Project dir: $project_dir"

# ── 1. Create project ─────────────────────────────────────────────
create_project $project_name $project_dir -part $fpga_part -force

# ── 2. Add HLS-generated Verilog sources ──────────────────────────
set verilog_dir "$hls_output_dir/myproject_prj/solution1/syn/verilog"

if {![file exists $verilog_dir]} {
    puts "ERROR: Verilog directory not found: $verilog_dir"
    puts "       Run Vitis HLS synthesis first."
    exit 1
}

add_files -norecurse [glob $verilog_dir/*.v]
set_property top myproject [current_fileset]
puts "Added [llength [glob $verilog_dir/*.v]] Verilog source files."

# ── 3. Add constraints ────────────────────────────────────────────
set xdc_file "[file dirname [info script]]/constraints.xdc"
if {[file exists $xdc_file]} {
    add_files -fileset constrs_1 $xdc_file
    puts "Added constraints: $xdc_file"
} else {
    puts "WARNING: constraints.xdc not found at $xdc_file"
    puts "         Add timing constraints manually before implementation."
}

# ── 4. Set synthesis strategy ─────────────────────────────────────
set_property strategy "Vivado Synthesis Defaults" [get_runs synth_1]

# ── 5. Run synthesis ──────────────────────────────────────────────
puts "\nRunning synthesis..."
launch_runs synth_1 -jobs $n_jobs
wait_on_run synth_1

if {[get_property PROGRESS [get_runs synth_1]] != "100%"} {
    puts "ERROR: Synthesis failed."
    exit 1
}
puts "Synthesis complete."

# ── 6. Run implementation ─────────────────────────────────────────
puts "\nRunning implementation..."
set_param general.maxThreads $n_jobs
launch_runs impl_1 -jobs $n_jobs
wait_on_run impl_1

if {[get_property PROGRESS [get_runs impl_1]] != "100%"} {
    puts "ERROR: Implementation failed."
    exit 1
}
puts "Implementation complete."

# ── 7. Check timing ───────────────────────────────────────────────
set wns [get_property STATS.WNS [get_runs impl_1]]
set whs [get_property STATS.WHS [get_runs impl_1]]
puts "\nTiming summary:"
puts "  WNS: $wns ns"
puts "  WHS: $whs ns"

if {$wns < 0} {
    puts "WARNING: Timing not met (WNS=$wns ns)."
    puts "         Increase clock period in build_prj.tcl and re-synthesize."
    puts "         Suggested: change clock_period from 12 to 13."
} else {
    puts "Timing met ✓"
}

# ── 8. Generate bitstream ─────────────────────────────────────────
puts "\nGenerating bitstream..."
launch_runs impl_1 -to_step write_bitstream -jobs $n_jobs
wait_on_run impl_1

set bit_file "$project_dir/$project_name.runs/impl_1/myproject.bit"
if {[file exists $bit_file]} {
    puts "\n✅ Bitstream generated: $bit_file"
} else {
    puts "ERROR: Bitstream not found at expected path: $bit_file"
    exit 1
}

# ── 9. Program board (optional — comment out if board not connected) ──
# open_hw_manager
# connect_hw_server
# open_hw_target
# set_property PROGRAM.FILE $bit_file [get_hw_devices xc7a100t_0]
# program_hw_devices [get_hw_devices xc7a100t_0]
# puts "Board programmed."

puts "\n=========================================="
puts "  DONE"
puts "  Bitstream: $bit_file"
puts "  Program the board:"
puts "  1. Open Hardware Manager in Vivado"
puts "  2. Connect to Nexys A7 via USB"
puts "  3. Program device with the .bit file above"
puts "=========================================="
