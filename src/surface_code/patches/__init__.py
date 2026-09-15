"""Heavy-hex patches; PATCH is the distance-3 convenience default."""

from .base import Gauge, HeavyHexPatch
from .heavy_hex import HEAVY_HEX_D3, HEAVY_HEX_D5, get_patch

PATCH = HEAVY_HEX_D3

__all__ = ["HEAVY_HEX_D3", "HEAVY_HEX_D5", "PATCH", "Gauge", "HeavyHexPatch", "get_patch"]
