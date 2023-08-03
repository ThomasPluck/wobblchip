import hdl21 as h
from ro import *
from typing import Tuple

"""
Oscillators can be designed to interact like logic gates
using the inhomogeneous Kuramoto model.

Couplings widths are identical to the weight matrices used 
in the model. The sign of the couplings depends on how the
couplings are connected.

Since couplings are inverter loops, connecting couplers across
"in-phase" stages of the oscillators (ie. even-to-even, odd-to-odd)
actually is a "negative" coupling, tending the oscillator pair to
a bistable state.

Whereas, connecting across "anti-phase" stages (ie. even-to-odd etc.)
is a positive coupling, tending the oscillator pair to synchrony.
We generally try to keep the coupling between oscillators on seperate stages
"""


class OscillatorPairing:
    """
    This class is used to take weight matrices and to generate correct coupling sites.
    It works to avoid that any given inverter in the oscillator loop drives no more than
    a single coupling circuit and uses space efficiently.
    """

    def __init__(self, num_stages=1, couplings=((0))):
        m_elements = num_stages
        n_columns = len(couplings)
        self.state = [[0] * m_elements for _ in range(n_columns)]
        self.pairings = {}

        # Populate
        for i in range(0, m_elements):
            for j in range(i + 1, n_columns):
                self.update(i, j, couplings[i][j])

    def update(self, col1, col2, coupling):
        # Assert that the columns are in range
        assert col1 < len(self.state) and col2 < len(self.state)

        if coupling != 0:
            index1 = self._find_zero_index(self.state[col1], start=0, step=1)
            index2 = self._find_zero_index(
                self.state[col2], start=(int(coupling < 0) + index1 % 2) % 2, step=2
            )

            if index1 is not None and index2 is not None:
                # Update the state to show the pairing
                self.state[col1][index1] = 1
                self.state[col2][index2] = 1

                # Update the pairings dictionary
                key = (col1, col2) if col1 < col2 else (col2, col1)
                self.pairings[key] = (index1, index2, abs(coupling))
            else:
                raise RuntimeError(f"No more available pairings between {col1,col2}, choose a longer RO")

    def _find_zero_index(self, column, start, step):
        for i in range(start, len(column), step):
            if column[i] == 0:
                return i
        return None

stages = 7

@h.paramclass
class OGateParams:
    stages = h.Param(dtype=int, desc="Number of RO stages", default=stages)
    node_names = h.Param(dtype=Tuple[str, ...], desc="Oscillator names", default=())
    couplings = h.Param(
        dtype=Tuple[Tuple[int, ...], ...],
        desc="Matrix of coupling weights",
        default=((0)),
    )
    gate_name = h.Param(dtype=str, desc="Name of the oGate", default="gate")


@h.generator
def gen_ogate(params: OGateParams) -> h.Module:
    """
    This function generates automatic coupled oscillators from the specifications
    defined in a weight matrix.
    """

    nodes = len(params.node_names)

    if nodes != len(params.couplings[0]) or nodes != len(params.couplings):
        raise ValueError("Node names do not match coupling matrix")

    # Generate pairings
    pairings = OscillatorPairing(num_stages=params.stages, couplings=params.couplings)

    # Instantiate module
    ogate = h.Module(name=params.gate_name)
    ogate.VSS, ogate.VDD = h.Inputs(2)
    ogate.links = h.Port(width=params.stages * nodes)

    # Generate oscillators
    ogate.arr = gen_ro_arr(stages=params.stages, rows=nodes)(
        links=ogate.links,
        VDD=ogate.VDD,
        VSS=ogate.VSS,
    )

    # Generate pairings
    for k, v in pairings.pairings.items():
        temp_name = f"{params.node_names[k[0]]}{params.node_names[k[1]]}_coupling"

        ogate.add(
            gen_coupling(
                divisor=v[-1],
            )(
                A=ogate.links[k[0] * params.stages + v[0]],
                B=ogate.links[k[1] * params.stages + v[1]],
                VSS=ogate.VSS,
            ),
            name=temp_name,
        )

    # Create wrapper
    out = h.Module(name=f"{params.gate_name}_gate")
    out.VDD, out.VSS, out.REF = 3 * h.Port()

    # Generate ports and concatenate links
    out.kernel = h.Signal()
    links = h.Concat(out.kernel)
    for i in range(nodes):
        # These are private
        out.add(h.Signal(width=params.stages - 1 - (i == 0)), name=f"padding{i}")
        links = h.Concat(links, out.get(f"padding{i}"))
        # These are public
        if i != nodes - 1:
            out.add(h.Port(), name=f"{params.node_names[i]}")
            links = h.Concat(links, out.get(f"{params.node_names[i]}"))

        else:
            out.add(h.Port(), name=f"REF")
            links = h.Concat(links, out.get(f"REF"))

    # Wrap ogate
    out.add(
        ogate(VDD=out.VDD, VSS=out.VSS, links=links),
        name=f"{params.gate_name}_ogate",
    )

    return out


"""
The defining weight matrix of an AND o-gate is:

 0 -2  4  1
-2  0  4  1
 4  4  0 -2
 1  1 -2  0

And it has nodes:

A, B, A&B == C, AUX - the auxiliary bias bit
"""

J = ((0, -2, 4, 1), (-2, 0, 4, 1), (4, 4, 0, -2), (1, 1, -2, 0))

nodes = ("A", "B", "C", "AUX")

oAND = gen_ogate(stages=9, node_names=nodes, couplings=J, gate_name="AND")

# h.elaborate(oAND)
"""
The defining weight matrix of an Half-Adder o-gate is:

 0 -2  2  4 -1
-2  0  2  4 -1
 2  2  0 -4  1
 4  4 -4  0  2
-1 -1  1  2  0

And it has nodes:

A, B, A+B%2 == S, A+B//2 = C, AUX - the auxiliary bias bit
"""

J = (
    (0, -2, 2, 4, -1),
    (-2, 0, 2, 4, -1),
    (2, 2, 0, -4, 1),
    (4, 4, -4, 0, 2),
    (-1, -1, 1, 2, 0),
)

nodes = ("A", "B", "S", "C", "AUX")

oHA = gen_ogate(stages=9, node_names=nodes, couplings=J, gate_name="HA")

"""
The defining weight matrix of an Full-Adder o-gate is:

 0 -2 -2  2  4 -1
-2  0 -2  2  4 -1
-2 -2  0  2  4 -1
 2  2  2  0 -4  1
 4  4  4 -4  0  2
-1 -1 -1  1  2  0

And it has nodes:

A, B, Cin, A+B+Cin % 2 == S, A+B+Cin // 2 == Cout
"""

J = (
    (0, -2, -2, 2, 4, -1),
    (-2, 0, -2, 2, 4, -1),
    (-2, -2, 0, 2, 4, -1),
    (2, 2, 2, 0, -4, 1),
    (4, 4, 4, -4, 0, 2),
    (-1, -1, -1, 1, 2, 0),
)

nodes = ("A", "B", "Cin", "S", "Cout", "AUX")

oFA = gen_ogate(stages=9, node_names=nodes, couplings=J, gate_name="FA")
