# Modified from https://github.com/iic-jku/tt03-tempsensor/blob/main/src/vdac_cell.v
import hdl21 as h
from hdl21.prefix import n, p
from sky130_hdl21.digital_cells import high_density as s
import sky130_hdl21 as sky130


@h.module
class vDAC_cell:

    i_sign, i_data, i_enable = 3 * h.Input()
    vout = h.Output()

    #! Control logic
    # npu_pd = ~i_data;
    npu_pd = s.inv_1(A=i_data)

    # en_vref = i_enable & (~(i_sign ^ i_data))
    xor = s.xor2_1(A=i_sign, B=i_data)
    and1 = s.and2_1(A=i_enable, B=xor.X)
    en_vref = s.and1.X

    # en_pupd i_enable & (~(i_sign^i_data));
    ixor = s.inv_1(A=xor.X)
    and2 = s.and2_1(A=i_enable, B=ixor.X)
    en_pupd = s.and2.X

    # Modules
    cell_1 = s.einvp_1(A=npu_pd, TE=en_pupd, Z=vout)
    cell_2 = s.einvp_1(A=vout, TE=en_vref, Z=vout)


@h.generator
def gen_vDAC_cells(npar) -> h.Module:
    @h.module
    class Parallel_Cell:

        i_sign, i_data, i_enable = 3 * h.Input()
        vout = h.Output()

    cell = Parallel_Cell()

    # Connect multiple VDAC cells
    for n in range(npar):

        cell.add(
            vDAC_cell(npu_pd=cell.npu_pd, en_pupd=cell.en_pupd, en_vref=cell.en_vref),
            name=f"cell{n}",
        )

    return cell


@h.generator
def gen_vDAC(ncells=6) -> h.Module:
    @h.module
    class VDAC:
        inp_bus = h.Inputs(ncells)
        enable = h.Input()
        vout = h.Output()

    vdac = VDAC()

    for n in range(ncells - 1):

        vdac.add(
            gen_vDAC_cells(2**n)(
                i_sign=vdac.inp_bus[ncells - 1],
                i_data=vdac.inp_bus[n],
                i_enable=vdac.enable,
                vout=vdac.vout,
            ),
            name=f"paracell{n}",
        )

    return vdac


def twos_complement(num, width):

    max_value = 2 ** (width - 1) - 1

    if num > max_value or num < -max_value - 1:
        raise ValueError("Number falls outside the width")

    if num < 0:
        num = (1 << width) + num

    binary = bin(num)[2:].zfill(width)

    return [int(b) for b in binary][::-1]


@h.generator
def bus_signal(width=6, inp=0):

    bits = twos_complement(inp, width)

    vout = h.Outputs(6)
    vsources = h.Module()
    vss = h.Signal()

    for n in range(width):

        vsources.add(h.Vdc(dc=1.8 * bits[n])(p=vout[n], n=vss), name=f"vdc{n}")

    return vsources


def gen_sim(inp, width=6):
    @h.sim
    class Sim:
        @h.module
        class Tb:

            # Lone testbench port
            VSS = h.Port()

            # Create digital input
            vsources = bus_signal(width, inp)
            vsources.vss = VSS

            # Create VDAC
            vdac = gen_vDAC(ncells=width)
            v_en = h.Vdc(dc=1.8)(n=VSS)

            # Always enabled, wire up digital input correctly
            vdac.enable = v_en.p
            for i in range(width):

                vdac.inp_bus[i] = vsources.vout[i]

        # Simulation Controls
        op = h.sim.op()
        inc1 = sky130.install.include(h.pdk.Corner.TYP)
        inc2 = h.sim.Include(sky130.install.pdk_path / "libs.ref/sky130_fd_sc_hd/spice")

    return Sim


vdac_sim = gen_sim(7, 6)
