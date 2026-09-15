"""Cached Fez connectivity and offline layouts. No account access or QPU calls."""

import json
from importlib.resources import files

from .heavy_hex import HeavyHexLayout, build_layout


def load_fez_map() -> dict:
    return json.loads(files(__package__).joinpath("fez_map.json").read_text(encoding="utf-8"))


def get_fez_layout(distance: int = 3) -> HeavyHexLayout:
    device = load_fez_map()
    return build_layout(
        distance,
        device["coords"],
        device["edges"],
        first_data_position=(5, 1) if distance == 3 else (3, 7),
    )


__all__ = ["HeavyHexLayout", "build_layout", "get_fez_layout", "load_fez_map"]
