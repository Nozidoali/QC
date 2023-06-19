#!/usr/bin/env python
# -*- encoding=utf8 -*-

"""
Author: Hanyu Wang
Created time: 2023-06-17 07:50:30
Last Modified by: Hanyu Wang
Last Modified time: 2023-06-18 11:39:16
"""

from StatePreparator import *
from Algorithms import *

import pyzx as zx

import quantumflow as qf
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister

if __name__ == "__main__":

    state = W_state(4)

    print(state)

    # circuit = quantum_shannon_decomposition(U)
    circuit = cofactor_decomposition(state)
    print(circuit)

    circuit.simulate()
    exit(0)
    # exit(0)

    # print(circuit)
    with open("circuit.qasm", "w") as f:
        f.write(circuit.qasm())

    circuit = zx.Circuit.from_qasm_file("circuit.qasm")
    g = circuit.to_basic_gates().to_graph()
    zx.simplify.full_reduce(g, quiet=True)
    new_circ = zx.extract_circuit(g)

    with open("circuit.qasm", "w") as f:
        f.write(new_circ.to_basic_gates().to_qasm())

    circuit = QuantumCircuit.from_qasm_file("circuit.qasm")
    print(circuit)
