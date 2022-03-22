# -*- coding: utf-8 -*-
"""
Created on Tue Mar 15 15:06:12 2022

@author: Erik Gustafson, Henry Lamm, Ruth Van der Water
Mike Wagman, Norman, Clement, Sarah, Elizabeth
"""

import Z2gates
import numpy as np
from scipy.linalg import expm
from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister
from qiskit.quantum_info import Operator as Operator


def trotter_evolution(num_sites: int, epsilon: float, mass: float,
                      ntrotter: int, twirl=False, qsim=True,
                      richardson_level: int=1, state_prep=True):
    """
    Wrapper function for the various types of noiseless, noisy, and harware
    simulations that we want to do for the Z2 gauge with staggered matter
    in (1+1)D. These simulations allow for including and excluding randomized
    compiling (pauli twirling) and richardson extrapolations.

    Parameters
    ----------
    num_sites : int
        number of sites for the simulation
    epsilon : float
        the trotter step size
    mass : float
        mass of the fermion
    ntrotter : int
        the number of trotter steps for the simulation
    twirl : boolean, optional
        whether to implement this circuit with randomized
        compiling. The default is False.
    qsim : boolean, optional
        Whether to set this simulation up for running on a quantum computer
        or on a qasm/statevector simulator. The default is True
    richardson_level : int
        Determines how many times the CNOT gate is interleaved.
        # N_CNOTS = richardson_level * 2 - 1
    state_prep : boolean, (optional)
        whether to use a state prep circuit or not. Default is True

    Returns
    -------
    quantum_circuit : qiskit.QuantumCircuit
        the quantum circuit that will be simulated

    """
    # the number of qubits is given by 2 * num_sites - 1
    # because there are num_sites and num_sites - 1 gauge links
    number_of_qubits = 2 * num_sites - 1
    # define the quantum circuit
    quantum_circuit = QuantumCircuit(number_of_qubits, number_of_qubits)
    # State preparation whether or not to do it
    if state_prep:
        quantum_circuit.h([2 * i + 1 for i in range(num_sites - 1)])

    if qsim:
        if num_sites == 2:
            if state_prep:
                quantum_circuit.x([0])
                quantum_circuit.z([1])
            quantum_circuit = trotter_evolution_2sites(quantum_circuit,
                                                      epsilon, mass, ntrotter,
                                                      twirl=twirl,
                                                      richardson_level=richardson_level)
        elif num_sites == 4:
            if state_prep:
                quantum_circuit.x([2, 4])
                quantum_circuit.z([3])
            quantum_circuit = trotter_evolution_4sites(quantum_circuit,
                                                      epsilon, mass, ntrotter,
                                                      twirl=twirl,
                                                      richardson_level=richardson_level)
        else:
            exception_str = "If intending to simulation on a hardware, "
            exception_str += "only 2 and 4 site simulations are allowed."
            raise Exception(exception_str)
    # this code executes for the noiseless or qasm simulators
    else:
        if state_prep:
            mid = 2 * (num_sites // 2)
            quantum_circuit.x([mid, mid + 2])
            quantum_circuit.z(mid + 1)
        quantum_circuit = trotter_evolution_generic(quantum_circuit,
                                                    num_sites, epsilon,
                                                    mass, ntrotter,
                                                    twirl=False,
                                                    save_state_vector=True)

    return quantum_circuit


def trotter_evolution_generic(quantum_circuit, num_sites: int, epsilon: float,
                              mass: float, ntrotter: int, twirl=False,
                              save_state_vector=True):
    """
    This code implements a quantum circuit for a second order trotter using
    the most efficient encoding of the trotterization

    Parameters
    ----------
    quantum_circuit : qiskit.QuantumCircuit
        quantum circuit for simulation
    num_sites : int
        The number of sites for the lattice
    epsilon : float
        the suzuki Trotter step size
    mass : float
        the fermion mass
    ntrotter : int
        the number of trotter steps
    twirl : boolean, optional
        whether to implement randomized compiling or not.
        The default is False.
    save_state_vector : boolean, optional
        save the statevectors of the simulation. This is good if we want to
        minimize the computing time. The default is True.

    Returns
    -------
    quantum_circuit : qiskit.QuantumCircuit
        quantum circuit to that we want to run for a large lattice

    """
    quantum_circuit = Z2gates.apply_mass_terms(quantum_circuit, num_sites,
                                               mass, epsilon)
    quantum_circuit = Z2gates.apply_gauge_terms(quantum_circuit, num_sites,
                                                epsilon)
    quantum_circuit = Z2gates.apply_fermion_hopping(quantum_circuit,
                                                    num_sites, epsilon,
                                                    eta=1.0, twirl=False)
    quantum_circuit = Z2gates.apply_mass_terms(quantum_circuit, num_sites,
                                               mass, epsilon)
    quantum_circuit = Z2gates.apply_gauge_terms(quantum_circuit, num_sites,
                                                epsilon)

    return quantum_circuit

def trotter_evolution_2sites(quantum_circuit, epsilon: float, mass: float,
                            ntrotter: int, twirl=False, richardson_level=1):
    """
    apply the Suzuki-Trotter evolution operator ntrotter times on the quantum
    circuit:

        U_{pure_gauge}(dt / 2) U_{matter}(dt / 2) U_{matter-gauge}(dt)
        U_{pure_gauge}(dt / 2) U_{matter}(dt / 2)

    Parameters
    ----------
    quantum_circuit : qiskit.QuantumCircuit
        quantum circuit for time evolution
    epsilon : float
        the Trotter step size
    mass : float
        the fermion mass
    ntrotter : int
        the number of times the trotter operator is applied
    twirl : boolean (optional)
        whether to apply pauli twirling to the cnot gates

    Returns
    -------
    quantum_circuit : qiskit.QuantumCircuit
        quantum circuit object after the gates have been applied

    """
    # apply the rotations corresponding to the mass operators
    quantum_circuit = Z2gates.apply_mass_terms(quantum_circuit, 2, mass,
                                               epsilon)
    # apply the rotations corresponding to the gauge dynamics operators
    quantum_circuit = Z2gates.apply_gauge_terms(quantum_circuit, 2, epsilon)
    # apply the fermion hopping term across the qubits
    quantum_circuit = Z2gates.apply_fermion_hopping_2sites(quantum_circuit,
                                                           epsilon, eta=1.0,
                                                           twirl=twirl,
                                                           richardson_level=richardson_level)
    # apply the rotations corresponding to the mass operators
    quantum_circuit = Z2gates.apply_mass_terms(quantum_circuit, 2, mass,
                                               epsilon)
    # apply the rotations corresponding to the gauge dynamics operators
    quantum_circuit = Z2gates.apply_gauge_terms(quantum_circuit, 2, epsilon)

    return quantum_circuit

def trotter_evolution_4sites(quantum_circuit, epsilon: float, mass: float,
                             ntrotter: int, twirl=False,
                             richardson_level=1):
    """
    apply the Suzuki-Trotter evolution operator ntrotter times on the quantum
    circuit:

        U_{pure_gauge}(dt / 2) U_{matter}(dt / 2) U_{matter-gauge}(dt)
        U_{pure_gauge}(dt / 2) U_{matter}(dt / 2)

    Parameters
    ----------
    quantum_circuit : qiskit.QuantumCircuit
        quantum circuit for time evolution
    epsilon : float
        the Trotter step size
    mass : float
        the fermion mass
    ntrotter : int
        the number of times the trotter operator is applied
    twirl : boolean (optional)
        whether to apply pauli twirling to the cnot gates

    Returns
    -------
    quantum_circuit : TYPE
        quantum circuit object after the gates have been applied

    """
    # apply the rotations corresponding to the mass operators
    quantum_circuit = Z2gates.apply_mass_terms(quantum_circuit, 4, mass,
                                               epsilon)
    # apply the rotations corresponding to the gauge dynamics operators
    quantum_circuit = Z2gates.apply_gauge_terms(quantum_circuit, 4, epsilon)
    # apply the fermion hopping term across the qubits
    quantum_circuit = Z2gates.apply_fermion_hopping_4sites(quantum_circuit,
                                                            epsilon, eta=1.0,
                                                            twirl=twirl,
                                                            richardson_level=richardson_level)
    # apply the rotations corresponding to the mass operators
    quantum_circuit = Z2gates.apply_mass_terms(quantum_circuit, 4, mass,
                                               epsilon)
    # apply the rotations corresponding to the gauge dynamics operators
    quantum_circuit = Z2gates.apply_gauge_terms(quantum_circuit, 4, epsilon)

    return quantum_circuit



if __name__ == "__main__":
    x = np.array([[0, 1], [1, 0]])
    y = np.array([[0, -1j], [1j, 0]])
    z = np.diag([1, -1])
    fhop = (np.kron(x, np.kron(z, x)) + np.kron(y, np.kron(z, y))) / 4
    dt = 0.1
    mass = 1.0
    fhop = expm(-1.0j * dt * fhop)
    rmass = expm(0.25j * dt * mass * z)
    rgauge = expm(-0.25j * dt * x)
    rgauges = [np.kron(np.identity(2 ** i),
                       np.kron(rgauge, np.identity(2 ** (6 - i))))
               for i in range(1, 7, 2)]
    rmasses = [np.kron(np.identity(2 ** i),
                       np.kron(rmass, np.identity(2 ** (6 - i))))
               for i in range(0, 7, 2)]

    r1q = np.identity(2 ** 7)
    for op in rgauges:
        r1q = op @ r1q
    for j in range(4):
        if j % 2 == 1:
            r1q = rmasses[j].conjugate().transpose() @ r1q
        else:
            r1q = rmasses[j] @ r1q
    fhops = [np.kron(fhop, np.identity(2 ** 4)),
             np.kron(np.identity(16), fhop),
             np.kron(np.identity(4),
                     np.kron(fhop.conjugate().transpose(), np.identity(4)))]

    oper = np.identity(2 ** 7).dot(r1q)
    for op in fhops:
        oper = op @ oper
    oper = r1q @ oper
    oper = Operator(oper)
    opert = Operator(trotter_evolution_4sites(QuantumCircuit(7), dt, mass, 1))
    # print(np.array(oper)[:10, :10], np.array(opert)[:10, :10])
    print(oper.equiv(opert))
    print('=' * 100)
    try:
        trotter_evolution(8, 0.1, 1.0, 1, twirl=False, qsim=True,
                          state_prep=False)
    except (Exception) as e:
        print('====' * 25)
        print(e)
        print('---')
        print('exception working')
    print('=' * 100)
    trotter_evolution(8, 0.1, 1.0, 1, twirl=False, qsim=False,
                      state_prep=False)