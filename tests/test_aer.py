import pytest

from surface_code import Pauli, get_patch
from surface_code.circuits import extract_syndrome

qiskit_aer = pytest.importorskip("qiskit_aer")

from surface_code.simulation import run_aer, run_gauge_aer, shot_success, to_qiskit


@pytest.mark.parametrize("distance,qubits,gauges", [(3, 23, 10), (5, 65, 32)])
def test_circuit_registers_and_local_model(distance, qubits, gauges):
    circuit = to_qiskit(patch=get_patch(distance))
    assert circuit.num_qubits == qubits
    assert [(reg.name, reg.size) for reg in circuit.cregs] == [
        ("gauges", gauges),
        ("data", distance**2),
    ]
    assert circuit.metadata["hardware_compiled"] is False
    assert circuit.metadata["distance"] == distance


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
def test_gauge_randomness_preserves_stabilizers_and_logical_state(distance, basis):
    patch = get_patch(distance)
    tallies = run_gauge_aer(patch=patch, basis=basis, shots=64, seed=7)
    assert sum(tallies.values()) == 64
    assert len({g for g, _ in tallies}) > 1
    for gauges, data in tallies:
        syndrome = patch.syndrome_from_gauges(gauges)
        assert syndrome == (0,) * patch.code.syndrome_size
        assert shot_success(syndrome, data, patch=patch, basis=basis) == 1


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
def test_aer_matches_algebra_for_every_single_qubit_pauli(distance, basis):
    patch = get_patch(distance)
    for q in patch.data_qubits:
        for x, z in ((True, False), (False, True), (True, True)):
            error = Pauli(
                frozenset((q,)) if x else frozenset(), frozenset((q,)) if z else frozenset()
            )
            tallies = run_aer(error, patch=patch, basis=basis, shots=4, seed=17)
            assert sum(tallies.values()) == 4
            for syndrome, data in tallies:
                assert syndrome == extract_syndrome(error, patch=patch)
                assert shot_success(syndrome, data, patch=patch, basis=basis) == 1


@pytest.mark.parametrize("distance", [3, 5])
@pytest.mark.parametrize("basis", ["X", "Z"])
def test_logical_flip_is_detected_in_final_readout(distance, basis):
    patch = get_patch(distance)
    error = patch.logical_x if basis == "Z" else patch.logical_z
    for syndrome, data in run_aer(error, patch=patch, basis=basis, shots=8, seed=7):
        assert syndrome == (0,) * patch.code.syndrome_size
        assert shot_success(syndrome, data, patch=patch, basis=basis) == 0


@pytest.mark.parametrize("basis", ["X", "Z"])
def test_d5_corrects_a_mixed_two_qubit_error_in_aer(basis):
    patch = get_patch(5)
    error = Pauli.x_on((1, 25)) * Pauli.z_on((25,))
    for syndrome, data in run_aer(error, patch=patch, basis=basis, shots=8, seed=7):
        assert shot_success(syndrome, data, patch=patch, basis=basis) == 1


def test_seeded_runs_preserve_joint_raw_records():
    patch = get_patch(5)
    raw = run_gauge_aer(patch=patch, shots=32, seed=7)
    assert raw == run_gauge_aer(patch=patch, shots=32, seed=7)
    expected = {}
    for (gauges, data), count in raw.items():
        key = patch.syndrome_from_gauges(gauges), data
        expected[key] = expected.get(key, 0) + count
    assert run_aer(patch=patch, shots=32, seed=7) == expected


@pytest.mark.parametrize("shots", [0, -1, 1.5, True])
def test_aer_rejects_invalid_shot_counts(shots):
    with pytest.raises(ValueError, match="positive integer"):
        run_aer(shots=shots)


def test_aer_rejects_invalid_seed_basis_and_data_qubit():
    with pytest.raises(ValueError, match="seed must be an integer"):
        run_aer(shots=1, seed=1 << 63)
    with pytest.raises(ValueError):
        to_qiskit(basis="Y")
    with pytest.raises(ValueError, match="outside the data qubits"):
        to_qiskit(Pauli.x_on((0,)))
