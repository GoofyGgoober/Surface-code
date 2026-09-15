from dataclasses import replace
from itertools import combinations

import pytest

from surface_code import HEAVY_HEX_D3, HEAVY_HEX_D5, Pauli, get_patch


@pytest.fixture(params=[HEAVY_HEX_D3, HEAVY_HEX_D5], ids=["d3", "d5"])
def patch(request):
    return request.param


def test_subsystem_parameters_and_roles(patch):
    expected = {3: (9, 1, 2, 3), 5: (25, 1, 8, 5)}
    assert patch.code.parameters() == expected[patch.distance]
    assert patch.num_qubits == {3: 23, 5: 65}[patch.distance]
    assert len(patch.gauges) == {3: 10, 5: 32}[patch.distance]
    assert patch.code.syndrome_size == {3: 6, 5: 16}[patch.distance]
    assert len(set(patch.data_qubits + patch.ancillas + patch.relays)) == patch.num_qubits


def test_stabilizers_commute_with_the_entire_gauge_group(patch):
    assert all(s.commutes(g.pauli) for s in patch.stabilizers for g in patch.gauges)
    assert all(a.commutes(b) for a, b in combinations(patch.stabilizers, 2))
    assert all(patch.code.in_gauge_group(s) for s in patch.stabilizers)
    assert any(not a.pauli.commutes(b.pauli) for a, b in combinations(patch.gauges, 2))


def test_gauge_changes_are_not_protected_logical_errors(patch):
    noncentral = [g.pauli for g in patch.gauges if not patch.code.in_stabilizer_group(g.pauli)]
    assert noncentral
    for gauge in noncentral:
        assert patch.code.in_gauge_group(gauge)
        assert not patch.code.is_logical(gauge)
        assert patch.code.syndrome(gauge) == (0,) * patch.code.syndrome_size
    assert patch.code.is_logical(patch.logical_x)
    assert patch.code.is_logical(patch.logical_z)
    assert not patch.code.is_logical(Pauli())


def test_bare_logicals_commute_with_gauges_and_anticommute(patch):
    assert not patch.logical_x.commutes(patch.logical_z)
    assert all(
        logical.commutes(g.pauli)
        for logical in (patch.logical_x, patch.logical_z)
        for g in patch.gauges
    )
    assert patch.logical_x.weight() == patch.logical_z.weight() == patch.distance


def test_d3_matches_reference_operators():
    p = HEAVY_HEX_D3
    assert {g.name for g in p.x_gauges} == {"X1X4", "X2X5", "X3X6", "X4X7", "X5X8", "X6X9"}
    assert {g.name for g in p.z_gauges} == {"Z1Z2", "Z2Z3Z5Z6", "Z4Z5Z7Z8", "Z8Z9"}
    assert {s.x for s in p.x_stabilizers} == {
        frozenset((1, 2, 4, 5)),
        frozenset((3, 6)),
        frozenset((4, 7)),
        frozenset((5, 6, 8, 9)),
    }
    assert {s.z for s in p.z_stabilizers} == {
        frozenset((1, 2, 4, 5, 7, 8)),
        frozenset((2, 3, 5, 6, 8, 9)),
    }
    assert p.logical_x == Pauli.x_on((1, 2, 3))
    assert p.logical_z == Pauli.z_on((1, 4, 7))


def test_stabilizers_reconstruct_from_same_basis_gauge_products(patch):
    for stabilizer, indices in zip(patch.stabilizers, patch.stabilizer_gauge_indices):
        product = Pauli()
        for i in indices:
            product *= patch.gauges[i].pauli
        assert product == stabilizer
        assert len({patch.gauges[i].basis for i in indices}) == 1


def test_column_major_data_labels(patch):
    assert patch.data_qubit(0, 0) == 1
    assert patch.data_qubit(1, 0) == 2
    assert patch.data_qubit(0, 1) == patch.distance + 1
    assert patch.data_qubit(patch.distance - 1, patch.distance - 1) == patch.distance**2
    for cell in ((-1, 0), (0, patch.distance), (True, 0), (0, 1.5)):
        with pytest.raises(ValueError):
            patch.data_qubit(*cell)


@pytest.mark.parametrize("distance", [True, 2, 4, 5.0, 3.0, "3", 7])
def test_unsupported_distances_rejected_even_after_cache_warmup(distance):
    get_patch(distance=3)
    get_patch(distance=5)
    with pytest.raises(ValueError, match="3 and 5"):
        get_patch(distance=distance)


def test_code_rejects_nondata_errors(patch):
    for q in (0, patch.ancillas[0], patch.relays[0]):
        with pytest.raises(ValueError, match="outside the data qubits"):
            patch.code.is_logical(Pauli.x_on((q,)))


def test_subsystem_model_rejects_incomplete_center():
    with pytest.raises(ValueError, match="full gauge center"):
        replace(HEAVY_HEX_D3.code, stabilizers=HEAVY_HEX_D3.stabilizers[:-1])


def test_patch_rejects_overlapping_roles():
    with pytest.raises(ValueError, match="distinct"):
        replace(HEAVY_HEX_D3, relays=(1, 21, 22, 23))
