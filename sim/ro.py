import hdl21 as h
from sky130_hdl21.digital_cells import high_density as hd
import sky130_hdl21.primitives as pr
from sky130_hdl21 import Sky130LogicParams as LP
from random import randint

@h.paramclass
class RoParams:
    """# Ring Oscillator Parameters"""

    stages = h.Param(dtype=int, default=3, desc="Number of stages")
    rows = h.Param(dtype=int, default=3, desc="Number of rows")
    name = h.Param(dtype=str, desc="Module name", default="RO")


@h.generator
def genRO(params: RoParams) -> h.Module:
    ro = h.Module()
    ro.links = h.Port(width=params.stages, desc="Oscillator output")
    ro.VSS, ro.VDD, ro.EN = h.Inputs(3)

    p = LP()

    for stage in range(params.stages - 1):
        # Add a stage
        ro.add(
            hd.inv_1(p)(
                A=ro.links[stage],
                Y=ro.links[stage + 1],
                VGND=ro.VSS,
                VNB=ro.VSS,
                VPWR=ro.VDD,
                VPB=ro.VDD,
            ),
            name=f"stage{stage}",
        )

    # Final stage
    ro.add(
        hd.nand2_1(p)(
            A=ro.links[-1],
            B=ro.EN,
            Y=ro.links[0],
            VGND=ro.VSS,
            VNB=ro.VSS,
            VPWR=ro.VDD,
            VPB=ro.VDD,
        ),
        name=f"stage{params.stages-1}",
    )

    ro.name = params.name

    return ro


@h.generator
def gen_ro_arr(params: RoParams) -> h.Module:

    array = h.Module()
    array.VDD, array.VSS, array.EN = h.Inputs(3)
    array.links = h.Port(width=params.stages * params.rows)

    for row in range(params.rows):
        step = row * params.stages
        array.add(
            genRO(params)(
                links=array.links[step : step + params.stages],
                EN=array.EN,
                VSS=array.VSS,
                VDD=array.VDD,
            ),
            name=f"rosc{row}",
        )

    @h.module
    class Wrapper:

        VDD,VSS,EN = h.Inputs(3)

        links = h.Port(width=params.stages-1)
        REF = h.Port()
        padding = h.Signal(width=(params.stages-2)*params.rows)
        kernel = h.Signal()

        concatd = kernel
        for row in range(params.rows):
            if row == 0:
                concatd = h.Concat(concatd,padding[1:params.stages-1])
                concatd = h.Concat(concatd,links[row])
            else:
                concatd = h.Concat(concatd,padding[params.stages*row:params.stages*(row+1)-1])
                concatd = h.Concat(concatd,links[row])

        rosc = array(VDD=VDD,VSS=VSS,EN=EN,links=concatd)

    return Wrapper


@h.paramclass
class CouplingParams:
    unit_length = h.Param(dtype=int, default=1, desc="Length of precision resistor")
    multiplier = h.Param(dtype=int, default=1, desc="Multiple of Unit Length")
    name = h.Param(dtype=str, desc="Coupling Name", default="Coupling")

p = LP()

@h.generator
def gen_coupling(params: CouplingParams) -> h.Module:
    coupling = h.Module()
    coupling.A, coupling.B = h.Ports(2)

    coupling.resistor = pr.PM_PREC_0p35(l=params.unit_length*params.multiplier)(
        p=coupling.A, n=coupling.B
    )

    return coupling
