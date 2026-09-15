from itertools import combinations, product

import pytest

from surface_code import Pauli, get_patch
from surface_code.circuits import (
    CX,
    H,
    MeasureZ,
    abstract_syndrome,
    extract_syndrome,
    syndrome_circuit,
)


@pytest.mark.parametrize("distance", [3, 5])
def test_circuit_matches_commutation_through_correctable_weights(distance):
    patch = get_patch(distance)
    for weight in range((distance - 1) // 2 + 1):
        for support in combinations(patch.data_qubits, weight):
            for axes in product("XYZ", repeat=weight):
                error = Pauli(
                    frozenset(q for q, axis in zip(support, axes) if axis in "XY"),
                    frozenset(q for q, axis in zip(support, axes) if axis in "YZ"),
                )
                assert extract_syndrome(error, patch=patch) == abstract_syndrome(error, patch=patch)


@pytest.mark.parametrize("distance", [3, 5])
def test_logicals_have_zero_stabilizer_syndrome(distance):
    patch = get_patch(distance)
    for error in (Pauli(), patch.logical_x, patch.logical_z):
        assert extract_syndrome(error, patch=patch) == (0,) * patch.code.syndrome_size


@pytest.mark.parametrize("distance", [3, 5])
def test_measurements_are_gauges_and_relays_are_idle_in_ideal_circuit(distance):
    patch = get_patch(distance)
    circuit = syndrome_circuit(patch)
    assert all(isinstance(op, (H, CX, MeasureZ)) for op in circuit)
    measured = [op.qubit for op in circuit if isinstance(op, MeasureZ)]
    assert measured == list(patch.z_ancillas + patch.x_ancillas)
    assert len(measured) > len(patch.stabilizers)
    touched = {
        q
        for op in circuit
        for q in ((op.control, op.target) if isinstance(op, CX) else (op.qubit,))
    }
    assert not touched.intersection(patch.relays)


def test_d3_x1_has_only_the_first_z_stabilizer_detection():
    assert extract_syndrome(Pauli.x_on((1,))) == (0, 0, 0, 0, 1, 0)


@pytest.mark.parametrize("distance", [3, 5])
def test_bad_gauge_record_rejected(distance):
    p = get_patch(distance)
    with pytest.raises(ValueError, match="gauge readout"):
        p.syndrome_from_gauges((0,) * p.code.syndrome_size)
    with pytest.raises(ValueError, match="gauge readout"):
        p.syndrome_from_gauges((2,) + (0,) * (len(p.gauges) - 1))
