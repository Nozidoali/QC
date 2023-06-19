#!/usr/bin/env python
# -*- encoding=utf8 -*-

'''
Author: Hanyu Wang
Created time: 2023-06-19 11:52:54
Last Modified by: Hanyu Wang
Last Modified time: 2023-06-19 13:38:59
'''

import numpy as np
from .BasicGate import *

class AdvancedGate:
    
    def mcry(theta, control_qubits: dict, target_index, num_qubis:int ):

        c1 = np.array([[1, 0], [0, 0]])
        c2 = np.array([[0, 0], [0, 1]])
        
        ry: np.ndarray = BasicGate.ry(theta)
        ry00 = ry[0, 0]
        ry01 = ry[0, 1]
        ry10 = ry[1, 0]
        ry11 = ry[1, 1]
                
        matrix = np.zeros((2**num_qubis, 2**num_qubis))
        
        for j in range(2**num_qubis):
            
            control_state = True
            
            target_val = (j >> target_index) & 1
            if target_val == 0:
                continue
            
            j_inv = j ^ (1 << target_index)
            
            for q in control_qubits:
                q_val = (j >> q) & 1
                
                phase = control_qubits[q]
                    
                # if the control qubit is in the wrong state
                if (phase and q_val == 0) or (not phase and q_val == 1):
                    control_state = False
                    break
            
            # we get the control states
            if not control_state:
                matrix[j, j] = 1
                matrix[j_inv, j_inv] = 1
                continue
            
            else:
                matrix[j, j] = ry00
                matrix[j, j_inv] = ry10
                matrix[j_inv, j] = ry01
                matrix[j_inv, j_inv] = ry11
        
        return matrix

    # TODO: could have better ways to do this
    def mcry_deprecated(theta, control_qubits: dict, target_index, num_qubits: int):

        c1 = np.array([[1, 0], [0, 0]])
        c2 = np.array([[0, 0], [0, 1]])

        ry = BasicGate.ry(theta)

        # we need to do a depth first search
        def dfs(curr_index: int):
            
            # we have reached the end of the search
            if curr_index == num_qubits:

                # then we return a single 1, to not affect the matrix multiplication
                return np.array([1]), np.array([1])
            
            matrix_on, matrix_off = dfs(curr_index + 1)
            
            # if the current qubit is the target qubit
            if curr_index == target_index:

                # we need to consider the two cases
                #  Case1: control rotation if the control qubit is on
                #  Case2: do nothing if the control qubit is off (apply identity)
                return np.kron(ry, matrix_on), np.kron(np.identity(2), matrix_off)

            # if the current qubit is a control qubit
            elif curr_index in control_qubits:
                phase: bool = control_qubits[curr_index]

                # we need to consider the two cases
                if phase == False:
                    
                    # first case, matrix remain on if c1
                    # and the matrix is off if the control qubit is off
                    new_matrix_on = np.kron(c1, matrix_on)

                    # second case, the matrix is off no matter what the control qubit is
                    new_matrix_off = np.kron(c2, matrix_off) + np.kron(np.identity(2), matrix_off)
            
                    return new_matrix_on, new_matrix_off
            
                if phase == True:
                    
                    # first case, the matrix remain on if c2
                    # and the matrix is off if the control qubit is off
                    new_matrix_on = np.kron(c2, matrix_on)

                    # second case, the matrix is off no matter what the control qubit is
                    new_matrix_off = np.kron(c1, matrix_off) + np.kron(np.identity(2), matrix_off)
            
                    return new_matrix_on, new_matrix_off
            
            # if the current qubit is not a control qubit, nor the target qubit
            else:
            
                # we simply need to apply identity, 
                # no matter what state the control qubits are in
                return np.kron(np.identity(2), matrix_on), np.kron(np.identity(2), matrix_off)

        
        matrix_on, matrix_off = dfs(0)
        return matrix_on + matrix_off
