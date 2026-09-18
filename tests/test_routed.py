"""Routed d=3 readout: real bonds, counts, ideal equivalence."""

import pytest

from surface_code import Pauli, get_patch
from surface_code.circuits import gauge_flips
from surface_code.circuits.operations import CX, H, MeasureZ, Reset
from surface_code.circuits.routed import (
    expected_outcomes,
    extraction_circuit,
    routed_gauge_flips,
    to_qiskit_routed,
)
from surface_code.layouts import get_fez_layout, load_fez_map

qiskit_aer = pytest.importorskip("qiskit_aer")

PATCH = get_patch(3)


def test_extraction_circuit_is_d3_only():
    with pytest.raises(ValueError, match="distance 3 only"):
        extraction_circuit(get_patch(5))


def test_all_two_qubit_gates_are_real_device_bonds():
    circuit = extraction_circuit(PATCH)
    device_bonds = {tuple(sorted(edge)) for edge in load_fez_map()["edges"]}
    layout = get_fez_layout(3)
    physical = layout.local_to_physical
    cxs = [(op.control, op.target) for op in circuit.ops if isinstance(op, CX)]
    assert len(cxs) == 32
    for control, target in cxs:
        assert tuple(sorted((physical[control], physical[target]))) in device_bonds


def test_round_structure_and_measurement_counts():
    circuit = extraction_circuit(PATCH)
    ops = circuit.ops
    assert len([op for op in ops if isinstance(op, MeasureZ)]) == 18
    assert len([op for op in ops if isinstance(op, Reset)]) == 12
    assert circuit.measured.z_syndrome == tuple(g.ancilla for g in PATCH.z_gauges)
    assert len(circuit.measured.flags) == 8
    assert circuit.measured.x_gauge == tuple(g.ancilla for g in PATCH.x_gauges)
    touched = {
        q for op in ops for q in ((op.control, op.target) if isinstance(op, CX) else (op.qubit,))
    }
    assert set(PATCH.relays) <= touched
    assert any(isinstance(op, H) for op in ops)


def test_routed_gauges_match_ideal_for_all_weight_one_errors():
    errors = [Pauli()]
    for q in PATCH.data_qubits:
        errors += [Pauli.x_on((q,)), Pauli.z_on((q,)), Pauli.x_on((q,)) * Pauli.z_on((q,))]
    for error in errors:
        assert routed_gauge_flips(error, patch=PATCH) == gauge_flips(error, patch=PATCH)


def test_routed_stabilizers_match_ideal_for_weight_one_errors():
    for q in PATCH.data_qubits:
        for error in (Pauli.x_on((q,)), Pauli.z_on((q,)), Pauli.x_on((q,)) * Pauli.z_on((q,))):
            record = expected_outcomes(error, patch=PATCH)
            z_bits = dict(zip([g.ancilla for g in PATCH.z_gauges], record["z_syndrome"]))
            assert PATCH.syndrome_from_gauges(
                tuple(
                    record["x_gauge"][[g.ancilla for g in PATCH.x_gauges].index(g.ancilla)]
                    if g.basis == "X"
                    else z_bits[g.ancilla]
                    for g in PATCH.gauges
                )
            ) == PATCH.code.syndrome(error)


def _parse_routed_counts(counts):
    """Split 'xg flags zsynd' keys into little-endian bit tuples."""
    parsed = {}
    for key, count in counts.items():
        xg_str, flag_str, zsynd_str = key.split()
        parsed[xg_str[::-1], flag_str[::-1], zsynd_str[::-1]] = count
    return parsed


def test_aer_z_round_is_deterministic_and_matches_ideal():
    circuit = to_qiskit_routed(Pauli.x_on((1,)), patch=PATCH)
    assert circuit.num_qubits == PATCH.num_qubits
    assert [(reg.name, reg.size) for reg in circuit.cregs] == [
        ("zsynd", 4),
        ("flags", 8),
        ("xg", 6),
    ]
    assert circuit.metadata["model"] == "routed_d3"
    from qiskit_aer import AerSimulator

    counts = _parse_routed_counts(
        AerSimulator(method="stabilizer")
        .run(circuit, shots=32, seed_simulator=7)
        .result()
        .get_counts()
    )
    assert sum(counts.values()) == 32
    expected_z = tuple(
        expected_outcomes(Pauli.x_on((1,)), patch=PATCH)["z_syndrome"][i]
        for i in range(len(PATCH.z_gauges))
    )
    expected_flags = expected_outcomes(Pauli.x_on((1,)), patch=PATCH)["flags"]
    assert {(zsynd, flag) for _, flag, zsynd in counts} == {
        ("".join(map(str, expected_z)), "".join(map(str, expected_flags)))
    }
