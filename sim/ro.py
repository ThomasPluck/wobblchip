import hdl21 as h
from sky130_hdl21.digital_cells import high_density as s
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
            s.inv_4(p)(
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
        s.nand2_4(p)(
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

    io = h.Module(name=f"arr_io{randint(0, 1000)}")
    io.REF = h.Port()
    array.add(io()(REF=array.links[-1]), name="arr_io")

    return array


@h.paramclass
class CouplingParams:
    width = h.Param(dtype=int, default=1, desc="Width of coupling")
    name = h.Param(dtype=str, desc="Coupling Name", default="Coupling")


p = LP()


@h.module
class invloop:
    A, B = h.Inputs(2)
    VSS, VDD = h.Inputs(2)

    i1 = s.inv_1(p)(A=A, Y=B, VGND=VSS, VNB=VSS, VPWR=VDD, VPB=VDD)
    i2 = s.inv_1(p)(A=B, Y=A, VGND=VSS, VNB=VSS, VPWR=VDD, VPB=VDD)


@h.generator
def gen_coupling(params: CouplingParams) -> h.Module:
    coupling = h.Module()
    coupling.A, coupling.B = h.Inputs(2)
    coupling.VDD, coupling.VSS = h.Inputs(2)

    coupling.loop_arr = h.InstanceArray(invloop, params.width)(
        A=coupling.A, B=coupling.B, VDD=coupling.VDD, VSS=coupling.VSS
    )

    coupling.name = params.name

    return coupling
