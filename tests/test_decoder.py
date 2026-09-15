from itertools import combinations, product

import pytest

from surface_code import Pauli, get_patch
from surface_code.decoders import basis_success, decode


def errors_of_weight(qubits, weight):
    for support in combinations(qubits, weight):
        for axes in product("XYZ", repeat=weight):
            yield Pauli(
                frozenset(q for q, axis in zip(support, axes) if axis in "XY"),
                frozenset(q for q, axis in zip(support, axes) if axis in "YZ"),
            )


@pytest.mark.parametrize("distance", [3, 5])
def test_all_correctable_data_paulis_are_corrected_modulo_gauges(distance):
    code = get_patch(distance).code
    for weight in range((distance - 1) // 2 + 1):
        for error in errors_of_weight(code.data_qubits, weight):
            correction = decode(code.syndrome(error), code)
            assert code.in_gauge_group(correction * error)


@pytest.mark.parametrize("distance", [3, 5])
def test_every_syndrome_has_a_consistent_correction(distance):
    code = get_patch(distance).code
    for syndrome in product((0, 1), repeat=code.syndrome_size):
        assert code.syndrome(decode(syndrome, code)) == syndrome


def test_d3_decoder_is_minimum_weight_in_each_css_sector():
    code = get_patch(3).code
    # Independent exhaustive oracle over all 2**9 pure-X and pure-Z errors.
    for axis in "XZ":
        weights = {}
        for weight in range(code.n + 1):
            for support in combinations(code.data_qubits, weight):
                error = Pauli.x_on(support) if axis == "X" else Pauli.z_on(support)
                weights.setdefault(code.syndrome(error), weight)
        for syndrome, minimum in weights.items():
            assert decode(syndrome, code).weight() == minimum


@pytest.mark.parametrize("distance", [3, 5])
def test_logical_and_gauge_classification_in_both_bases(distance):
    p = get_patch(distance)
    for basis, flip, harmless in (("Z", p.logical_x, p.logical_z), ("X", p.logical_z, p.logical_x)):
        assert basis_success(flip, p.code, basis=basis) == 0
        assert basis_success(harmless, p.code, basis=basis) == 1
        assert all(basis_success(g.pauli, p.code, basis=basis) for g in p.gauges)


@pytest.mark.parametrize("distance", [3, 5])
def test_decoder_validates_syndrome_width_and_bits(distance):
    code = get_patch(distance).code
    for syndrome in ((0,), (2,) + (0,) * (code.syndrome_size - 1)):
        with pytest.raises(ValueError, match="binary bits"):
            decode(syndrome, code)
