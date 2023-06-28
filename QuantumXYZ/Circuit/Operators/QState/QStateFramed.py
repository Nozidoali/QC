#!/usr/bin/env python
# -*- encoding=utf8 -*-

"""
Author: Hanyu Wang
Created time: 2023-06-28 10:46:01
Last Modified by: Hanyu Wang
Last Modified time: 2023-06-28 10:57:47
"""

import numpy as np
from .QStateBase import *
from typing import List


class QStateFramed(QStateBase):
    def __init__(self, state_array: List[PureState], num_qubits: int) -> None:
        QStateBase.__init__(self, state_array)
        self.num_qubits = num_qubits

    def __str__(self) -> str:
        return "-".join([x.to_string(self.num_qubits) for x in self.state_array])
