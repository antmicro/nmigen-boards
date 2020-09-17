import os
import subprocess

from nmigen.build import *
from nmigen.vendor.quicklogic import *
from nmigen_boards.resources import *


__all__ = ["QuickfeatherPlatform"]


class QuickfeatherPlatform(QuicklogicPlatform):
    device      = "ql-eos-s3_wlcsp"
    part        = "PU64"
    default_clk = "sys_clk0"
    connectors = [
        Connector("J", 2, "- 28 22 21 37 36 42 40 7 2 4 5"),
        Connector("J", 3, "- 8 9 17 16 20 6 55 31 25 47 - - - - 41"),
        Connector("J", 8, "27 26 33 32 23 57 56 3 64 62 63 61 59 - - -"),
    ]
    resources   = [
        # This is a placeholder resource since the board utilizes
        # default internal SoC clock.
        Resource("sys_clk0", 0, Pins("63", dir="i"), Clock(10e6)),

        *ButtonResources(pins="62"),

        RGBLEDResource(0, r="34", g="39", b="38"),

        UARTResource(0,
            rx="9", tx="8",
        ),

        Resource("spi_master", 0,
            Subsignal("clk", Pins("20", dir="i")),
            Subsignal("miso", Pins("17", dir="o")),
            Subsignal("mosi", Pins("16", dir="i")),
            Subsignal("ss", Pins("11", dir="i")),
            Subsignal("cs2", Pins("28", dir="i")),
            Subsignal("cs3", Pins("18", dir="i")),
        ),

        Resource("spi_slave", 0,
            Subsignal("clk", Pins("40", dir="i")),
            Subsignal("miso", Pins("42", dir="o")),
            Subsignal("mosi", Pins("36", dir="i")),
            Subsignal("cs_n", Pins("37", dir="i")),
        ),

        Resource("i2c", 0,
            Subsignal("scl", Pins("4", dir="io")),
            Subsignal("sda", Pins("5", dir="io")),
        ),
        Resource("i2c", 1,
            Subsignal("scl", Pins("22", dir="io")),
            Subsignal("sda", Pins("21", dir="io")),
        ),
        DirectUSBResource(0, d_p="10", d_n="14"),
        Resource("swd", 0,
            Subsignal("clk", Pins("54", dir="io")),
            Subsignal("io",  Pins("53", dir="io")),
        ),
    ]

    # This programmer requires OpenOCD with support for eos-s3:
    # https://github.com/antmicro/openocd/tree/eos-s3-support
    def toolchain_program(self, products, name):
        openocd = os.environ.get("OPENOCD", "openocd")
        gdb = os.environ.get("GDB", "gdb")
        with products.extract("{}.bit".format(name)) as bitstream_filename:
            bitstream_folder = os.path.dirname(bitstream_filename)
            top_path = bitstream_folder + "/top.cfg"
            subprocess.call(["python", "-m", "quicklogic_fasm.bitstream_to_openocd", bitstream_filename, top_path])
            try:
                openocd_proc = subprocess.Popen(["openocd", "-s", "tcl",
                                                 "-f", "interface/ftdi/antmicro-ftdi-adapter.cfg",
                                                 "-f", "interface/ftdi/swd-resistor-hack.cfg",
                                                 "-f", "board/quicklogic_quickfeather.cfg",
                                                 "-f", top_path])
                gdb_commands = ["tar rem :3333", "monitor reset halt", "monitor load_bitstream"]
                gdb_output_path = bitstream_folder + "/gdb.commands"
                with open(gdb_output_path, 'w') as f:
                    f.write("\n".join(gdb_commands))
                subprocess.call([gdb, "-x", gdb_output_path])
            except Exception as e:
                openocd_proc.kill()
                raise e

if __name__ == "__main__":
    from .test.blinky import *
    QuickfeatherPlatform().build(Blinky(), do_program=False)
