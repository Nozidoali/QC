#!/usr/bin/env python
# -*- encoding=utf8 -*-

'''
Author: Hanyu Wang
Created time: 2023-06-18 15:56:42
Last Modified by: Hanyu Wang
Last Modified time: 2023-06-18 15:57:05
'''

from Algorithms import *

def test_zyz():

    # identity matrix
    matrix = np.array([[1, 0], [0, 1]])
    alpha, beta, gamma = unitary_zyz_decomposition(matrix)
    assert alpha == 0 and beta == 0 and gamma == 0

    # RY(pi) matrix
    matrix = np.array([[0, -1], [1, 0]])
    alpha, beta, gamma = unitary_zyz_decomposition(matrix)
    assert alpha == 0 or alpha == 2 * np.pi
    assert beta == np.pi
    assert gamma == 0 or gamma == 2 * np.pi