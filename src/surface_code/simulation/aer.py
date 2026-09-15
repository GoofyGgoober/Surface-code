"""Local Aer stabilizer simulation of ideal heavy-hex gauge circuits.

Qiskit indices are zero-based; public Q labels are one-based. The synthesized
initial state and direct gauge interactions are an ideal baseline and are
not compiled for Fez. No IBM services or QPU submission are used here.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .._validation import validate_binary_bits
from ..circuits import CX, H, syndrome_circuit
from ..core import Pauli
from ..decoders import decode
from ..decoders.basis import normalize_measurement_basis
from ..patches import PATCH, HeavyHexPatch

if TYPE_CHECKING:
    from qiskit import QuantumCircuit

MAX_SEED = (1 << 63) - 1
Bits = tuple[int, ...]
Tallies = dict[tuple[Bits, Bits], int]


def _pauli_label(pauli: Pauli, patch: HeavyHexPatch) -> str:
    chars = ["I"] * len(patch.data_qubits)
    for i, qubit in enumerate(patch.data_qubits):
        if qubit in pauli.x:
            chars[i] = "Y" if qubit in pauli.z else "X"
        elif qubit in pauli.z:
            chars[i] = "Z"
    return "".join(reversed(chars))


def _logical_state_circuit(patch: HeavyHexPatch, basis: str) -> QuantumCircuit:
    from qiskit.quantum_info import StabilizerState

    # Fix the unprotected gauge degrees of freedom to obtain a pure state.
    # Opposite-basis gauge measurements subsequently randomize those degrees
    # of freedom while preserving all stabilizers and the protected logical.
    if basis == "Z":
        generators = tuple(g.pauli for g in patch.x_gauges) + patch.z_stabilizers
        logical = patch.logical_z
    else:
        generators = patch.x_stabilizers + tuple(g.pauli for g in patch.z_gauges)
        logical = patch.logical_x
    labels = [_pauli_label(g, patch) for g in (*generators, logical)]
    return StabilizerState.from_stabilizer_list(labels).clifford.to_circuit()


def to_qiskit(
    error: Pauli | None = None, *, patch: HeavyHexPatch = PATCH, basis: str = "Z"
) -> QuantumCircuit:
    """Prepare a +1 logical eigenstate, inject an error, measure gauges and data."""
    basis = normalize_measurement_basis(basis)
    error = Pauli() if error is None else error
    patch.code.validate_data_pauli(error, name="error")
    from qiskit import ClassicalRegister, QuantumCircuit, QuantumRegister

    qubits = QuantumRegister(patch.num_qubits, "q")
    gauges = ClassicalRegister(len(patch.gauges), "gauges")
    data = ClassicalRegister(len(patch.data_qubits), "data")
    circuit = QuantumCircuit(qubits, gauges, data, name=f"heavy_hex_d{patch.distance}_{basis}")
    circuit.metadata = {
        "code": "heavy_hex",
        "distance": patch.distance,
        "basis": basis,
        "model": "ideal_direct_gauges",
        "hardware_compiled": False,
        "data_labels": list(patch.data_qubits),
        "gauge_names": [g.name for g in patch.gauges],
    }
    circuit.compose(
        _logical_state_circuit(patch, basis), [q - 1 for q in patch.data_qubits], inplace=True
    )
    for q in sorted(error.x | error.z):
        if q in error.x and q in error.z:
            circuit.y(q - 1)
        elif q in error.x:
            circuit.x(q - 1)
        else:
            circuit.z(q - 1)
    circuit.barrier()
    gauge_bit = {g.ancilla: i for i, g in enumerate(patch.gauges)}
    for op in syndrome_circuit(patch):
        if isinstance(op, H):
            circuit.h(op.qubit - 1)
        elif isinstance(op, CX):
            circuit.cx(op.control - 1, op.target - 1)
        else:
            circuit.measure(op.qubit - 1, gauges[gauge_bit[op.qubit]])
    circuit.barrier()
    for i, q in enumerate(patch.data_qubits):
        if basis == "X":
            circuit.h(q - 1)
        circuit.measure(q - 1, data[i])
    return circuit


def _parse_shot(key: str, patch: HeavyHexPatch) -> tuple[Bits, Bits]:
    # Last-added register is printed first, and each register is little endian.
    data_str, gauge_str = key.split()
    gauge_bits = tuple(int(bit) for bit in gauge_str[::-1])
    data_bits = tuple(int(bit) for bit in data_str[::-1])
    validate_binary_bits("gauge readout", gauge_bits, len(patch.gauges))
    validate_binary_bits("data readout", data_bits, len(patch.data_qubits))
    return gauge_bits, data_bits


def _validate_aer_options(shots: int, seed: int | None) -> None:
    if type(shots) is not int or shots <= 0:
        raise ValueError(f"shots must be a positive integer, got {shots!r}")
    if seed is not None and (type(seed) is not int or not 0 <= seed <= MAX_SEED):
        raise ValueError(f"seed must be an integer from 0 to {MAX_SEED}, or None, got {seed!r}")


def run_gauge_aer(
    error: Pauli | None = None,
    *,
    patch: HeavyHexPatch = PATCH,
    basis: str = "Z",
    shots: int = 1024,
    seed: int | None = None,
) -> Tallies:
    """Return joint {(raw gauge bits, final data bits): count} for local shots."""
    _validate_aer_options(shots, seed)
    from qiskit_aer import AerSimulator

    circuit = to_qiskit(error, patch=patch, basis=basis)
    options = {"shots": shots}
    if seed is not None:
        options["seed_simulator"] = seed
    result = AerSimulator(method="stabilizer").run(circuit, **options).result()
    return {_parse_shot(key, patch): count for key, count in result.get_counts().items()}


def run_aer(
    error: Pauli | None = None,
    *,
    patch: HeavyHexPatch = PATCH,
    basis: str = "Z",
    shots: int = 1024,
    seed: int | None = None,
) -> Tallies:
    """Return {(derived stabilizer syndrome, final data bits): count}.

    Use run_gauge_aer when the individual gauge outcomes are needed.
    """
    tallies: Tallies = {}
    raw = run_gauge_aer(error, patch=patch, basis=basis, shots=shots, seed=seed)
    for (gauges, data), count in raw.items():
        key = patch.syndrome_from_gauges(gauges), data
        tallies[key] = tallies.get(key, 0) + count
    return tallies


def shot_success(
    syndrome: Bits, data_bits: Bits, *, patch: HeavyHexPatch = PATCH, basis: str = "Z"
) -> int:
    basis = normalize_measurement_basis(basis)
    validate_binary_bits("data readout", data_bits, len(patch.data_qubits))
    correction = decode(syndrome, patch.code)
    flipped = correction.x if basis == "Z" else correction.z
    support = patch.logical_z.z if basis == "Z" else patch.logical_x.x
    parity = sum(
        bit ^ (q in flipped) for q, bit in zip(patch.data_qubits, data_bits) if q in support
    )
    return int(parity % 2 == 0)


def shot_z_success(syndrome: Bits, data_bits: Bits, *, patch: HeavyHexPatch = PATCH) -> int:
    return shot_success(syndrome, data_bits, patch=patch, basis="Z")
