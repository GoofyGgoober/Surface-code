"""CLI argument definitions and text parsing; no simulation is run here."""

from __future__ import annotations

import argparse
import re
from functools import partial
from importlib.metadata import PackageNotFoundError, version

from ..core import Pauli
from ..patches import PATCH, HeavyHexPatch
from .aer import MAX_SEED

DEFAULT_SHOTS = 64
_TOKEN = re.compile(r"([XYZ])(_?L|\d+)", re.IGNORECASE)
_LOGICAL_WORD = re.compile(r"LOGICAL[\s_-]*([XYZ])", re.IGNORECASE)
_SEPARATORS = re.compile(r"[\s,*]+")
Syndrome = tuple[int, ...]


def parse_error(text: str, *, patch: HeavyHexPatch = PATCH) -> Pauli:
    """Parse a phase-free Pauli product such as ``X1 Y4 ZL``."""
    expanded = _LOGICAL_WORD.sub(r"\1L", text.strip())
    compact = _SEPARATORS.sub("", expanded).upper()
    if not compact or compact == "I":
        return Pauli()
    result = Pauli()
    position = 0
    while position < len(compact):
        match = _TOKEN.match(compact, position)
        if match is None:
            raise ValueError(f"could not parse Pauli {text!r} near {compact[position:]!r}")
        axis, target = match.groups()
        axis = axis.upper()
        if target.upper().endswith("L"):
            logical = {
                "X": patch.logical_x,
                "Y": patch.logical_x * patch.logical_z,
                "Z": patch.logical_z,
            }[axis]
            result = result * logical
        else:
            qubit = parse_data_qubit(target, patch=patch)
            if axis == "X":
                term = Pauli.x_on((qubit,))
            elif axis == "Z":
                term = Pauli.z_on((qubit,))
            else:
                term = Pauli.x_on((qubit,)) * Pauli.z_on((qubit,))
            result = result * term
        position = match.end()
    return result


def parse_syndrome(text: str, *, patch: HeavyHexPatch = PATCH) -> Syndrome:
    compact = re.sub(r"[\s,_]+", "", text)
    width = patch.code.syndrome_size
    if len(compact) != width or set(compact) - {"0", "1"}:
        raise ValueError(f"syndrome must contain exactly {width} binary bits, got {text!r}")
    return tuple(int(bit) for bit in compact)


def parse_data_qubit(raw: str, *, patch: HeavyHexPatch = PATCH) -> int:
    try:
        qubit = int(raw)
    except ValueError as error:
        raise ValueError(
            f"data qubit must be an integer from 1 to {len(patch.data_qubits)}, got {raw!r}"
        ) from error
    if qubit not in patch.data_qubits:
        raise ValueError(f"data qubit must be in {list(patch.data_qubits)}, got {qubit}")
    return qubit


def parse_positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {raw!r}") from error
    if value <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive integer, got {value}")
    return value


def parse_nonnegative_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as error:
        raise argparse.ArgumentTypeError(f"expected a non-negative integer, got {raw!r}") from error
    if value < 0:
        raise argparse.ArgumentTypeError(f"expected a non-negative integer, got {value}")
    return value


def parse_seed(raw: str) -> int:
    value = parse_nonnegative_int(raw)
    if value > MAX_SEED:
        raise argparse.ArgumentTypeError(f"seed must be at most {MAX_SEED}, got {value}")
    return value


def parse_probability(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as error:
        message = f"expected a probability in [0, 1], got {raw!r}"
        raise argparse.ArgumentTypeError(message) from error
    if not 0 <= value <= 1:
        raise argparse.ArgumentTypeError(f"expected a probability in [0, 1], got {raw!r}")
    return value


def parse_axes(raw: str) -> str:
    value = re.sub(r"[,\s]+", "", raw.upper())
    if not value or set(value) - {"X", "Y", "Z"}:
        raise argparse.ArgumentTypeError("axes must be a non-empty combination of X, Y, and Z")
    return "".join(axis for axis in "XYZ" if axis in value)


def _pauli_argument(raw: str, *, patch: HeavyHexPatch = PATCH) -> Pauli:
    try:
        return parse_error(raw, patch=patch)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _syndrome_argument(raw: str, *, patch: HeavyHexPatch = PATCH) -> Syndrome:
    try:
        return parse_syndrome(raw, patch=patch)
    except ValueError as error:
        raise argparse.ArgumentTypeError(str(error)) from error


def _add_run_options(parser: argparse.ArgumentParser, *, patch: HeavyHexPatch = PATCH) -> None:
    parser.add_argument(
        "error",
        nargs="?",
        type=partial(_pauli_argument, patch=patch),
        default=Pauli(),
        metavar="PAULI",
    )
    parser.add_argument(
        "-e",
        "--error",
        dest="extra_errors",
        action="append",
        type=partial(_pauli_argument, patch=patch),
        default=None,
        metavar="PAULI",
        help="additional Pauli to compose; may be repeated",
    )
    parser.add_argument("-s", "--shots", type=parse_positive_int, default=DEFAULT_SHOTS)
    parser.add_argument("--seed", type=parse_seed, help="seed random errors and Aer sampling")
    parser.add_argument(
        "--counts", action="store_true", help="show every measured bit-string tally"
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    parser.add_argument(
        "--draw-error",
        dest="noise",
        type=parse_probability,
        default=None,
        metavar="P",
        help="sample one code-capacity Pauli with per-qubit probability P",
    )
    parser.add_argument(
        "--noise",
        dest="noise",
        type=parse_probability,
        default=argparse.SUPPRESS,
        metavar="P",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--draws",
        dest="steps",
        type=parse_nonnegative_int,
        default=None,
        metavar="N",
        help="random Paulis to compose (default: one with --draw-error)",
    )
    parser.add_argument(
        "--steps",
        dest="steps",
        type=parse_nonnegative_int,
        default=argparse.SUPPRESS,
        metavar="N",
        help=argparse.SUPPRESS,
    )


def _package_version() -> str:
    try:
        return version("quantum-surface-code")
    except PackageNotFoundError:
        return "unknown"


def build_parser(*, patch: HeavyHexPatch = PATCH) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="surface-code",
        usage="surface-code [-h] [--version] [--distance {3,5}] [COMMAND] ...",
        description=(
            "Explore the d=3 and d=5 heavy-hex subsystem codes: ideal gauge rounds "
            "and exhaustive ideal-error decoding. With no command, open interactive mode."
        ),
        epilog=(
            "examples:\n"
            "  surface-code                         interactive mode\n"
            "  surface-code --distance 5 X4 --shots 128 --seed 7\n"
            "  surface-code syndrome 'X1 Z3'\n"
            "  surface-code decode '0000 11'\n"
            "  surface-code sweep --weight 2 --failures-only\n"
            "  surface-code circuit XL"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--distance",
        type=int,
        choices=(3, 5),
        default=patch.distance,
        help="heavy-hex distance (default: 3); accepted before or after a command",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {_package_version()}")
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")
    run = subparsers.add_parser(
        "run",
        help="run one ideal Aer gauge round with logical Z readout",
        description=(
            "Run one fixed injected error through the ideal heavy-hex gauge circuit. "
            "Aer shots sample gauge and data readout strings; they do not resample the error."
        ),
    )
    _add_run_options(run, patch=patch)
    interactive = subparsers.add_parser("interactive", help="open the interactive error explorer")
    interactive.add_argument("-s", "--shots", type=parse_positive_int, default=DEFAULT_SHOTS)
    interactive.add_argument("--seed", type=parse_seed)
    interactive.add_argument(
        "--draw-error", dest="noise", type=parse_probability, default=0.0, metavar="P"
    )
    interactive.add_argument(
        "--noise",
        dest="noise",
        type=parse_probability,
        default=argparse.SUPPRESS,
        metavar="P",
        help=argparse.SUPPRESS,
    )
    syndrome = subparsers.add_parser("syndrome", help="inspect and decode a Pauli algebraically")
    syndrome.add_argument("error", type=partial(_pauli_argument, patch=patch), metavar="PAULI")
    syndrome.add_argument("--json", action="store_true")
    decoder = subparsers.add_parser(
        "decode", help="decode a stabilizer syndrome (6 bits at d=3; 16 at d=5)"
    )
    decoder.add_argument("syndrome", type=partial(_syndrome_argument, patch=patch), metavar="BITS")
    decoder.add_argument("--json", action="store_true")
    sweep = subparsers.add_parser("sweep", help="exhaustively decode ideal physical Pauli errors")
    sweep.add_argument("--weight", type=int, choices=(1, 2, 3), default=1)
    sweep.add_argument("--axes", type=parse_axes, default="XYZ", metavar="AXES")
    sweep.add_argument("--details", action="store_true", help="list individual errors")
    sweep.add_argument(
        "--failures-only", action="store_true", help="list only decoded Z_L failures"
    )
    sweep.add_argument("--json", action="store_true")
    circuit = subparsers.add_parser("circuit", help="draw the generated Qiskit circuit")
    circuit.add_argument(
        "error",
        nargs="?",
        type=partial(_pauli_argument, patch=patch),
        default=Pauli(),
        metavar="PAULI",
    )
    info = subparsers.add_parser("info", help="show patch geometry, checks, and logical operators")
    info.add_argument("--json", action="store_true")
    return parser
