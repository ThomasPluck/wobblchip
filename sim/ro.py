import hdl21 as h
from sky130_hdl21.digital_cells import high_density as hd
import sky130_hdl21.primitives as pr
from sky130_hdl21 import Sky130LogicParams as LP
from sky130_hdl21 import Sky130PrecResParams as PR
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
    ro.VSS, ro.VDD = h.Inputs(2)

    p = LP()

    for stage in range(params.stages):
        # Add a stage
        ro.add(
            hd.inv_1(p)(
                A=ro.links[stage],
                Y=ro.links[(stage + 1) % params.stages],
                VGND=ro.VSS,
                VNB=ro.VSS,
                VPWR=ro.VDD,
                VPB=ro.VDD,
            ),
            name=f"stage{stage}",
        )

    ro.name = params.name

    return ro


@h.generator
def gen_ro_arr(params: RoParams) -> h.Module:

    array = h.Module()
    array.VDD, array.VSS = h.Inputs(2)
    array.links = h.Port(width=params.stages * params.rows)

    for row in range(params.rows):
        step = row * params.stages
        array.add(
            genRO(params)(
                links=array.links[step : step + params.stages],
                VSS=array.VSS,
                VDD=array.VDD,
            ),
            name=f"rosc{row}",
        )

    return array


@h.paramclass
class CouplingParams:
    unit_length = h.Param(dtype=int, default=1e2, desc="Length of precision resistor")
    divisor = h.Param(dtype=int, default=1, desc="Multiple of Unit Length")
    name = h.Param(dtype=str, desc="Coupling Name", default="Coupling")

p = LP()
q = PR

@h.generator
def gen_coupling(params: CouplingParams) -> h.Module:
    coupling = h.Module()
    coupling.A, coupling.B, coupling.VSS = h.Ports(3)

    coupling.resistor = h.primitives.Res(r=params.unit_length/params.divisor)(p=coupling.A, n=coupling.B)

    return coupling
