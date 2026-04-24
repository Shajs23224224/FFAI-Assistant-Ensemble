"""Control del emulador. Soporta Waydroid, Genymotion y Nox."""

from .waydroid_ctrl import WaydroidController
from .genymotion_ctrl import GenymotionController
from .windows_ctrl import WindowsController
from .nox_ctrl import NoxController

__all__ = [
    "WaydroidController",
    "GenymotionController",
    "WindowsController",
    "NoxController"
]
