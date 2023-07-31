import hdl21 as h
from sky130_hdl21.digital_cells import high_density as s
from sky130_hdl21 import Sky130LogicParams as p

from ro import *

"""
These scripts are used to design the IO oscillators used to produce testbenches for
oscillator circuits. The basic principle operates as follows:

1) We have a digital input that we would like feed to our network.
2) This is encoded in an oscillator system where prophase to a reference signal is 0
and anti-phase to the reference signal is 1.
3) To encode the input, we have to create a system of oscillators that work to convert
between these two representations.

This requires two seperate circuits for input and output:

For input, we require an array of oscillators that can have their pairing weights manipulated
to encode the desired pattern of phases that represent the original signal using coupling links
that we can turn on and off.

For output, we want a phase detector which determines the relative phase shift between pairs
of oscillators to construct a digital signal that can be used by ordinary digital circuitry.
"""


@h.module
class tristate_p_invloop:
    """Tristate inverter loop"""

    A, B, EN = h.Inputs(3)
    VSS, VDD = h.Inputs(2)

    tsi1 = s.einvp_1(p)(A=A, Z=B, TE=EN, VGND=VSS, VNB=VSS, VPWR=VDD, VPB=VDD)
    tsi2 = s.einvp_1(p)(A=B, Z=A, TE=EN, VGND=VSS, VNB=VSS, VPWR=VDD, VPB=VDD)


@h.module
class tristate_n_invloop:
    """Tristate inverter loop"""

    A, B, EN = h.Inputs(3)
    VSS, VDD = h.Inputs(2)

    tsi1 = s.einvn_1(p)(A=A, Z=B, TE_B=EN, VGND=VSS, VNB=VSS, VPWR=VDD, VPB=VDD)
    tsi2 = s.einvn_1(p)(A=B, Z=A, TE_B=EN, VGND=VSS, VNB=VSS, VPWR=VDD, VPB=VDD)


@h.paramclass
class ioOscillatorParams:
    """IO Oscillator Params"""

    n_bits = h.Param(dtype=int, desc="Number of bits available", default=8)
    stages = h.Param(dtype=int, desc="Number of stages in oscillator", default=7)


@h.generator
def gen_in_osc(params: ioOscillatorParams) -> h.Module:
    """This generator produces the input oscillator array"""

    @h.module
    class IO:
        IN = h.Input(width=params.n_bits)
        OUT = h.Output(width=params.n_bits)
        OSC_CTRL = h.Signal(width=params.n_bits)
        OSC_CTRL_B = h.Signal(width=params.n_bits)
        VSS, VDD, EN = 3 * h.Input()
        REF = h.Port()

    mod = IO

    mod.add(
        s.buf_4(p)(
            A=mod.IN[-1],
            X=mod.OSC_CTRL[-1],
            VGND=mod.VSS,
            VNB=mod.VSS,
            VPWR=mod.VDD,
            VPB=mod.VDD,
        ),
        name="in_final_buf",
    )

    # Convert digital signal to coupling representation
    for i in range(params.n_bits - 1):

        mod.add(
            s.xor2_4(p)(
                A=mod.IN[i],
                B=mod.IN[i + 1],
                X=mod.OSC_CTRL[i],
                VGND=mod.VSS,
                VNB=mod.VSS,
                VPWR=mod.VDD,
                VPB=mod.VDD,
            ),
            name=f"in_xor{i+1}",
        )

    # Invert all signals to produce complementary signals
    for i in range(params.n_bits):
        mod.add(
            s.inv_4(p)(
                A=mod.OSC_CTRL[i],
                Y=mod.OSC_CTRL_B[i],
                VGND=mod.VSS,
                VNB=mod.VSS,
                VPWR=mod.VDD,
                VPB=mod.VDD,
            ),
            name=f"inv{i}",
        )

    # Instantiate the oscillator array
    mod.add(
        gen_ro_arr(stages=params.stages, rows=params.n_bits + 1)(
            EN=mod.EN,
            VSS=mod.VSS,
            VDD=mod.VDD,
        ),
        name="osc_arr",
    )

    # Wire the oscillators correctly
    for i in range(params.n_bits):
        mod.add(
            tristate_n_invloop(
                A=mod.osc_arr.links[i * params.stages + (i % 2)],
                B=mod.osc_arr.links[(i + 1) * params.stages + (i % 2)],
                EN=mod.OSC_CTRL[i],
                VSS=mod.VSS,
                VDD=mod.VDD,
            ),
            name=f"einvp{i}",
        )
        mod.add(
            tristate_p_invloop(
                A=mod.osc_arr.links[i * params.stages + 2],
                B=mod.osc_arr.links[(i + 1) * params.stages + 3],
                EN=mod.OSC_CTRL_B[i],
                VSS=mod.VSS,
                VDD=mod.VDD,
            ),
            name=f"einvn{i}",
        )

    # Finally wire and buffer oscillator output
    for i in range(params.n_bits):
        mod.add(
            s.buf_4(p)(
                A=mod.osc_arr.links[(i + 1) * params.stages - 1],
                X=mod.OUT[i],
                VGND=mod.VSS,
                VNB=mod.VSS,
                VPWR=mod.VDD,
                VPB=mod.VDD,
            ),
            name=f"outbuf{i}",
        )

    mod.add(
        s.buf_4(p)(
            A=mod.osc_arr.links[-1],
            X=mod.REF,
            VGND=mod.VSS,
            VNB=mod.VSS,
            VPWR=mod.VDD,
            VPB=mod.VDD,
        ),
        name="refbuf"
    )

    return mod


@h.generator
def gen_out_osc(params: ioOscillatorParams) -> h.Module:
    """This generator produces a simple clock-gated XOR phase detector array"""

    @h.module
    class IO:
        IN = h.Input(width=params.n_bits)
        REF = h.Port()
        XORS = h.Signal(width=params.n_bits)
        FF = h.Signal(width=params.n_bits)
        OUT = h.Output(width=params.n_bits)
        VSS, VDD, CLK = 3 * h.Input()

    mod = IO

    # Buffer inputs
    for i in range(params.n_bits):

        mod.add(
            s.buf_4(p)(
                A=mod.IN[i],
                X=mod.XORS[i],
                VGND=mod.VSS,
                VNB=mod.VSS,
                VPWR=mod.VDD,
                VPB=mod.VDD,
            ),
            name=f"buf{i}",
        )

    # XOR to outputs
    for i in range(params.n_bits):
        mod.add(
            s.xor2_4(p)(
                A=mod.XORS[i],
                B=mod.REF,
                X=mod.FF[i // 2],
                VGND=mod.VSS,
                VNB=mod.VSS,
                VPWR=mod.VDD,
                VPB=mod.VDD,
            ),
            name=f"xor{i}",
        )

    for i in range(params.n_bits):
        mod.add(
            s.dfxtp_4(p)(
                D=mod.FF[i],
                Q=mod.OUT[i],
                CLK=mod.CLK,
                VGND=mod.VSS,
                VNB=mod.VSS,
                VPWR=mod.VDD,
                VPB=mod.VDD,
            ),
            name=f"ff{i}",
        )

    return mod

@h.generator
def gen_io_osc(params: ioOscillatorParams) -> h.Module:

    @h.module
    class IO_Mod:
        
        # Oriented to match the typical direction of signal (IN -> OUT)
        IN = h.Port(width=params.n_bits)
        OUT = h.Port(width=params.n_bits)
        REF = h.Port()
        VSS, VDD, CLK, EN = 4 * h.Input()

        # Which will be active when? Use power-gating.
        inp = gen_in_osc(params)(IN=IN, VSS=VSS, EN=EN, REF=REF, OUT=OUT)
        out = gen_out_osc(params)(IN=OUT, VSS=VSS, CLK=CLK, REF=REF, OUT=IN)

@h.paramclass
class DigitalSignalParams:

    width = h.Param(dtype=int, desc="Width of the digital signal", default=8)
    inp = h.Param(dtype=int, desc="Input value", default=0)


@h.generator
def digital_signal(params: DigitalSignalParams) -> h.Module:

    bits = [int(bit) for bit in bin(params.inp)[2:].zfill(params.width)]

    vsources = h.Module()
    vsources.VSS = h.Input()
    vsources.vout = h.Output(width=params.width)

    for n in range(params.width):

        if bits[n] == 0:
            vsources.add(
                h.Vdc(dc=0)(p=vsources.vout[n], n=vsources.VSS),
                name=f"vdc{n}",
            )
        else:
            vsources.add(
                h.Vdc(dc=1.8)(p=vsources.vout[n], n=vsources.VSS),
                name=f"vdc{n}",
            )

    return vsources
