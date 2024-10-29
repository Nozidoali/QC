#!/usr/bin/env python
# -*- encoding=utf8 -*-

"""
Author: Hanyu Wang
Created time: 2023-09-15 13:14:21
Last Modified by: Hanyu Wang
Last Modified time: 2023-09-15 14:32:11

Reference:
    @article{wang2024quantum,
        title={Quantum State Preparation Using an Exact CNOT Synthesis Formulation},
        author={Wang, Hanyu and Tan, Bochen and Cong, Jason and De Micheli, Giovanni},
        journal={arXiv preprint arXiv:2401.01009},
        year={2024}
    }
"""

from collections import namedtuple
from typing import List
import numpy as np


from xyz.circuit import QCircuit, QGate
from xyz.circuit import QState, quantize_state
from xyz.utils import stopwatch
from xyz.utils import global_stopwatch_report

from .exact_cnot_synthesis import exact_cnot_synthesis
from .m_flow import cardinality_reduction
from .n_flow import qubit_reduction
from .support_reduction import support_reduction, x_reduction
from ._reindex import reindex_circuit


class StatePreparationParameters:
    EXACT_SYNTHESIS_DENSITY_THRESHOLD = 100
    EXACT_SYNTHESIS_CNOT_LIMIT = 100

    def __init__(
        self,
        enable_exact_synthesis: bool = True,
        enable_n_flow: bool = False,
        enable_m_flow: bool = True,
        enable_decomposition: bool = False,
        enable_compression: bool = True,
        enable_reindex: bool = False,
        n_qubits_max: int = 4,
    ) -> None:
        self.enable_exact_synthesis: bool = enable_exact_synthesis
        self.enable_n_flow: bool = enable_n_flow
        self.enable_m_flow: bool = enable_m_flow
        self.enable_decomposition: bool = enable_decomposition
        self.enable_compression: bool = enable_compression
        self.enable_reindex: bool = enable_reindex
        self.n_qubits_max: int = n_qubits_max



class StatePreparationStatistics:
    """Classes the StatePreparationStatistics class ."""

    def __init__(self) -> None:
        self.time_total: float = 0
        self.num_runs_support_reduction: int = 0
        self.num_reduced_supports: int = 0
        self.num_reduced_density: int = 0
        self.num_saved_gates_decision: int = 0
        self.num_methods: dict = {}

        # time
        self.time_support_reduction: float = 0
        self.time_exact_cnot_synthesis: float = 0
        self.time_cardinality_reduction: float = 0
        self.time_qubit_decomposition: float = 0

    def report(self):
        """Report the number of runs supported by the benchmark ."""
        print("-" * 80)
        print(f"time_total: {self.time_total}")
        print("-" * 80)
        print(f"num_runs_support_reduction: {self.num_runs_support_reduction}")
        print(f"time_support_reduction: {self.time_support_reduction:0.02f} sec")
        print(f"time_exact_cnot_synthesis: {self.time_exact_cnot_synthesis:0.02f} sec")
        print(
            f"time_cardinality_reduction: {self.time_cardinality_reduction:0.02f} sec"
        )
        print(f"time_qubit_decomposition: {self.time_qubit_decomposition:0.02f} sec")
        print(f"num_reduced_supports: {self.num_reduced_supports}")
        print(f"num_reduced_density: {self.num_reduced_density}")
        print(f"num_saved_gates_decision: {self.num_saved_gates_decision}")
        print("-" * 80)
        for method, num in self.num_methods.items():
            print(f"{method}: {num}")
        print("-" * 80)


def _prepare_state_rec(
    circuit: QCircuit,
    state: QState,
    verbose_level: int = 0,
    param: StatePreparationParameters = StatePreparationParameters(),
    StatePreparationStatistics: StatePreparationStatistics = StatePreparationStatistics(),
):
    prev_supports = state.get_supports()
    prev_num_supports = len(prev_supports)
    prev_density = state.get_sparsity()

    support_reducing_gates = []
    num_cx_support_reduction = 0

    if param.enable_compression:
        # first, run support reduction
        with stopwatch("support_reduction") as timer:
            state, support_reducing_gates = support_reduction(
                circuit, state, enable_cnot=True
            )
        num_cx_support_reduction = sum(
            (gate.get_cnot_cost() for gate in support_reducing_gates)
        )
        StatePreparationStatistics.time_support_reduction += timer.time()

    if param.enable_reindex:
        state, circuit = reindex_circuit(circuit, state)
        raise NotImplementedError("reindexing is not implemented yet")

    # get the states
    supports = state.get_supports()
    num_supports = len(supports)
    cardinality = state.get_sparsity()

    if verbose_level >= 3:
        print(f"state: {state}")

    StatePreparationStatistics.num_runs_support_reduction += 1
    StatePreparationStatistics.num_reduced_supports += prev_num_supports - num_supports
    StatePreparationStatistics.num_reduced_density += prev_density - cardinality

    # check for the trivial case
    if cardinality == 1:
        _, ground_state_calibration_gates = x_reduction(circuit, state, False)
        gates = ground_state_calibration_gates + support_reducing_gates
        # ground state calibration has 0 CNOT
        return gates, num_cx_support_reduction

    # exact synthesis
    if (
        param.enable_exact_synthesis
        and num_supports <= param.n_qubits_max
        and cardinality <= StatePreparationParameters.EXACT_SYNTHESIS_DENSITY_THRESHOLD
    ):
        try:
            with stopwatch("exact_cnot_synthesis") as timer:
                exact_gates = exact_cnot_synthesis(
                    circuit,
                    state,
                    verbose_level=verbose_level,
                    cnot_limit=StatePreparationParameters.EXACT_SYNTHESIS_CNOT_LIMIT,
                )
            if StatePreparationStatistics is not None:
                StatePreparationStatistics.time_exact_cnot_synthesis += timer.time()
            gates = exact_gates + support_reducing_gates
            num_cx_exact = sum((gate.get_cnot_cost() for gate in exact_gates))
            return gates, num_cx_exact
        except ValueError:
            # if the exact synthesis fails
            pass

    # cardinality reduction method (m-flow)
    m_flow_gates: List[QGate] = None
    num_sparse_qsp_cx: int = 0
    if param.enable_m_flow:
        with stopwatch("cardinality_reduction") as timer:
            new_state, cardinality_reduction_gates = cardinality_reduction(
                circuit, state, verbose_level=verbose_level
            )
        num_cardinality_reduction_cx = sum(
            (gate.get_cnot_cost() for gate in cardinality_reduction_gates)
        )
        StatePreparationStatistics.time_cardinality_reduction += timer.time()
        rec_gates, rec_cx = _prepare_state_rec(
            circuit,
            new_state,
            StatePreparationStatistics=StatePreparationStatistics,
            param=param,
            verbose_level=verbose_level,
        )
        m_flow_gates = rec_gates + cardinality_reduction_gates + support_reducing_gates
        num_sparse_qsp_cx = (
            rec_cx + num_cardinality_reduction_cx + num_cx_support_reduction
        )

    # qubit reduction method (n-flow)
    n_flow_gates: List[QGate] = None
    num_qubit_reduction_cx: int = 0
    if param.enable_n_flow:
        with stopwatch("qubit_reduction") as timer:
            qubit_decomposition_gates, new_state = qubit_reduction(
                circuit, state, supports
            )
        num_qubit_reduction_cx = sum(
            (gate.get_cnot_cost() for gate in qubit_decomposition_gates)
        )
        StatePreparationStatistics.time_qubit_decomposition += timer.time()
        rec_gates, rec_cx = _prepare_state_rec(
            circuit,
            new_state,
            StatePreparationStatistics=StatePreparationStatistics,
            param=param,
            verbose_level=verbose_level,
        )
        n_flow_gates = rec_gates + qubit_decomposition_gates + support_reducing_gates
        num_qubit_reduction_cx += rec_cx + num_cx_support_reduction

    # we choose the best one
    # based on the number of CNOT gates
    Method = namedtuple("method", ["name", "gates", "num_gates"])
    candidates = []

    if m_flow_gates is not None:
        candidates.append(Method("sparse_qsp", m_flow_gates, num_sparse_qsp_cx))
    if n_flow_gates is not None:
        candidates.append(
            Method("qubit_reduction", n_flow_gates, num_qubit_reduction_cx)
        )

    # pylint: disable=unnecessary-lambda
    assert len(candidates) > 0, "no candidates found"
    best_candidate = min(candidates, key=lambda x: x.num_gates)
    worst_candidate = max(candidates, key=lambda x: x.num_gates)

    best_gates = best_candidate.gates
    best_method = best_candidate.name

    worst_num_gates = worst_candidate.num_gates
    best_num_gates = best_candidate.num_gates

    if StatePreparationStatistics is not None:
        StatePreparationStatistics.num_saved_gates_decision += worst_num_gates - best_num_gates
        StatePreparationStatistics.num_methods[best_method] = StatePreparationStatistics.num_methods.get(best_method, 0) + 1

    return best_gates, best_num_gates


def prepare_state(
    state: QState,
    map_gates: bool = True,
    verbose_level: int = 0,
    param: StatePreparationParameters = None,
    StatePreparationStatistics: StatePreparationStatistics = StatePreparationStatistics(),
) -> QCircuit:
    """A hybrid method combining both qubit- and cardinality- reduction.

    This is a wrapper for the _prepare_state_rec function.

    :param state: the target state to be prepared
    :type state: QState
    :param map_gates: map gates to {U2, CNOT}, this will take extra time, defaults to True
    :type map_gates: bool, optional
    :return: a quantum circuit
    :rtype: QCircuit
    """

    # check the input state
    if not isinstance(state, QState):
        if isinstance(state, np.ndarray):
            state = quantize_state(state)
        else:
            raise ValueError("state must be either a QState or a numpy array")

    # check the initial state
    num_qubits = state.num_qubits
    cardinality = state.get_sparsity()

    cardinality_reduction_cnot_estimation = int(cardinality * num_qubits)
    qubit_reduction_cnot_estimation = 1 << num_qubits

    if param is None:
        # we design the default parameters
        param = StatePreparationParameters()
        if cardinality_reduction_cnot_estimation < qubit_reduction_cnot_estimation:
            # if the state is sparse, we enable cardinality reduction method
            # print_yellow("enable_m_flow")
            param.enable_n_flow = False
            param.enable_m_flow = True
        else:
            # print_yellow("enable_n_flow")
            # otherwise, if the state is dense, we enable the qubit reduction method
            param.enable_n_flow = True
            param.enable_m_flow = False

    # initialize a circuit and the quantum registers
    circuit = QCircuit(state.num_qubits, map_gates=map_gates)

    with stopwatch("prepare_state") as timer:
        gates, _ = _prepare_state_rec(
            circuit,
            state,
            verbose_level=verbose_level,
            param=param,
            StatePreparationStatistics=StatePreparationStatistics,
        )

    if StatePreparationStatistics is not None:
        StatePreparationStatistics.time_total = timer.time()

    circuit.add_gates(gates)

    if verbose_level >= 1:
        global_stopwatch_report()
    return circuit
