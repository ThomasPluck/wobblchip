![](../../workflows/gds/badge.svg) ![](../../workflows/docs/badge.svg) ![](../../workflows/wokwi_test/badge.svg)

# TT04: Oscillator-Based Ising Multiplier

This repository contains:

- [ ] Unit Simulations of Individual Gates in HDL21
- [ ] Integration Simulations of the Multiplier in HDL21
- [ ] Complete Implementation in Verilog for OpenROAD Layout
- [ ] Special GDS Post-Processing + Simulation for this Design
- [ ] The Final Layout

### Theory

Oscillator-Based Ising Machines combine Ising Machines with the inhomogeneous Kuramoto model of systems of oscillators with weights.

The Ising Machine is defined by the Hamiltonian:

$$H = -\sum_{i,j} J_{ij} s_i s_j$$

where s<sub>i</sub> is the spin of particle i. The probability of the system being in a particular state is given by the Boltzmann distribution:

$$P(s) = \frac{1}{Z} e^{-\beta H}$$

where $Z$ is the partition function and $\beta$ is the inverse temperature. So, the most likely state is the one with the lowest energy.

Using these facts, we can start designing $J$ using Linear Programming as I've detailed extensively in my [p-computing repository](https://github.com/ThomasPluck/p-computing).

However, this is a pretty mathematical machine, not a tangible engineering concept - so how exactly do we implement this in hardware? The answer is that we rely on the inhomogeneous Kuramoto model on a system of oscillators, this is defined by the differential equation:

$$\dot{\theta_i} = - \sum_{i\neq j} K_{ij} \sin(\theta_j - \theta_i)$$

assuming oscillators have neglible difference in natural frequency, where $\theta_i$ is the phase of oscillator $i$, $\omega_i$ is the natural frequency of oscillator i, $K_{ij}$ is the coupling strength between oscillator i and oscillator j, and N is the number of oscillators.

We know that this model has steady states by its global Lyanpunov function given by:

$$E(\vec{\theta}) = - \frac{1}{2} \sum_{i}\sum_{i\neq j} K_{ij} \cos(\theta_j - \theta_i)$$

The Lyapunov energy given here can be interpreted as an Ising Hamiltonian, where energy is minimized by having coupled oscillators with a positive coupling strength have the same phase ($\cos(0)=1$), and coupled oscillators with a negative coupling strength have opposite phases ($\cos(\pi)=-1$).

Luckily enough, the correspondance between weights in the Ising Machine and coupling strengths in the Kuramoto model is one-to-one, so we can use the same weights we found in the Ising Machine to implement the Kuramoto model.

### Implementation

TBC