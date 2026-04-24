"""
NitroEngine: motor de inferencia y utilidades para gameplay/captura.

Se evita importar de forma eager modulos que dependen de OpenCV o MSS para que
comandos livianos como benchmarks o --help no fallen por dependencias no usadas.
"""

from __future__ import annotations

from .ffnet_lite import ACTIONS, FFNetLite, create_network

__all__ = [
    "FFNetLite",
    "create_network",
    "ACTIONS",
    "GameFeatures",
    "FeatureExtractor",
    "NitroCapture",
    "WindowDetector",
    "CaptureConfig",
    "find_waydroid_window",
    "find_emulator_window",
]


def __getattr__(name: str):
    if name in {"GameFeatures", "FeatureExtractor"}:
        from .features import FeatureExtractor, GameFeatures

        mapping = {
            "GameFeatures": GameFeatures,
            "FeatureExtractor": FeatureExtractor,
        }
        return mapping[name]

    if name in {
        "NitroCapture",
        "WindowDetector",
        "CaptureConfig",
        "find_waydroid_window",
        "find_emulator_window",
    }:
        from .capture import (
            CaptureConfig,
            NitroCapture,
            WindowDetector,
            find_emulator_window,
            find_waydroid_window,
        )

        mapping = {
            "NitroCapture": NitroCapture,
            "WindowDetector": WindowDetector,
            "CaptureConfig": CaptureConfig,
            "find_waydroid_window": find_waydroid_window,
            "find_emulator_window": find_emulator_window,
        }
        return mapping[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
