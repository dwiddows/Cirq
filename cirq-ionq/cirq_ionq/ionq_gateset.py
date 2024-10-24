# Copyright 2022 The Cirq Developers
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Target gateset used for compiling circuits to IonQ device."""
from typing import Any
from typing import Dict
from typing import List

import cirq
from cirq.transformers.target_gatesets.compilation_target_gateset import (
    _create_transformer_with_kwargs,
)


class IonQTargetGateset(cirq.TwoQubitCompilationTargetGateset):
    """Target gateset for compiling circuits to IonQ devices.

    The gate families accepted by this gateset are:

    Type gate families:
    *  Single-Qubit Gates: `cirq.XPowGate`, `cirq.YPowGate`, `cirq.ZPowGate`.
    *  Two-Qubit Gates: `cirq.XXPowGate`, `cirq.YYPowGate`, `cirq.ZZPowGate`.
    *  Measurement Gate: `cirq.MeasurementGate`.

    Instance gate families:
    *  Single-Qubit Gates: `cirq.H`.
    *  Two-Qubit Gates: `cirq.CNOT`, `cirq.SWAP`.
    """

    def __init__(self, *, atol: float = 1e-8):
        """Initializes CZTargetGateset

        Args:
            atol: A limit on the amount of absolute error introduced by the decomposition.
        """
        super().__init__(
            cirq.H,
            cirq.CNOT,
            cirq.SWAP,
            cirq.XPowGate,
            cirq.YPowGate,
            cirq.ZPowGate,
            cirq.XXPowGate,
            cirq.YYPowGate,
            cirq.ZZPowGate,
            cirq.MeasurementGate,
            unroll_circuit_op=False,
        )
        self.atol = atol

    def _decompose_single_qubit_operation(self, op: cirq.Operation, _) -> cirq.OP_TREE:
        qubit = op.qubits[0]
        mat = cirq.unitary(op)
        for gate in cirq.single_qubit_matrix_to_gates(mat, self.atol):
            yield gate(qubit)

    def _decompose_two_qubit_operation(self, op: cirq.Operation, _) -> cirq.OP_TREE:
        if not cirq.has_unitary(op):
            return NotImplemented
        mat = cirq.unitary(op)
        q0, q1 = op.qubits
        naive = cirq.two_qubit_matrix_to_cz_operations(q0, q1, mat, allow_partial_czs=False)
        temp = cirq.map_operations_and_unroll(
            cirq.Circuit(naive),
            lambda op, _: [cirq.H(op.qubits[1]), cirq.CNOT(*op.qubits), cirq.H(op.qubits[1])]
            if op.gate == cirq.CZ
            else op,
        )
        return cirq.merge_k_qubit_unitaries(
            temp, k=1, rewriter=lambda op: self._decompose_single_qubit_operation(op, -1)
        ).all_operations()

    @property
    def preprocess_transformers(self) -> List['cirq.TRANSFORMER']:
        """List of transformers which should be run before decomposing individual operations."""
        return [
            _create_transformer_with_kwargs(
                cirq.expand_composite, no_decomp=lambda op: cirq.num_qubits(op) <= self.num_qubits
            )
        ]

    @property
    def postprocess_transformers(self) -> List['cirq.TRANSFORMER']:
        """List of transformers which should be run after decomposing individual operations."""
        return [cirq.drop_negligible_operations, cirq.drop_empty_moments]

    def __repr__(self) -> str:
        return f'cirq_ionq.IonQTargetGateset(atol={self.atol})'

    def _value_equality_values_(self) -> Any:
        return self.atol

    def _json_dict_(self) -> Dict[str, Any]:
        return cirq.obj_to_dict_helper(self, ['atol'])

    @classmethod
    def _from_json_dict_(cls, atol, **kwargs):
        return cls(atol=atol)
