"""
PlatformDetector: Detección de plataforma y emulador.
Soporta Linux (Waydroid, Genymotion) y Windows (Nox, etc).
"""

from __future__ import annotations

import sys
import platform
from enum import Enum, auto
from typing import Optional, Tuple, Union


class PlatformType(Enum):
    """Tipos de plataforma soportadas."""
    LINUX = auto()
    WINDOWS = auto()
    UNKNOWN = auto()


class EmulatorType(Enum):
    """Tipos de emuladores soportados."""
    WAYDROID = auto()
    GENYMOTION = auto()
    NOX = auto()
    UNKNOWN = auto()


class PlatformDetector:
    """Detecta plataforma y emulador disponible."""

    def __init__(self):
        self._platform = self._detect_platform()
        self._emulator: Optional[EmulatorType] = None

    def _detect_platform(self) -> PlatformType:
        """Detecta si estamos en Linux o Windows."""
        system = platform.system().lower()
        if system == "linux":
            return PlatformType.LINUX
        elif system == "windows":
            return PlatformType.WINDOWS
        return PlatformType.UNKNOWN

    def get_platform(self) -> PlatformType:
        """Retorna plataforma detectada."""
        return self._platform

    def is_linux(self) -> bool:
        """Retorna True si es Linux."""
        return self._platform == PlatformType.LINUX

    def is_windows(self) -> bool:
        """Retorna True si es Windows."""
        return self._platform == PlatformType.WINDOWS

    def detect_emulator(self, preferred: Optional[str] = None) -> EmulatorType:
        """
        Detecta emulador disponible según plataforma.
        
        Args:
            preferred: "waydroid", "genymotion", "nox", o None para auto
        """
        if self._platform == PlatformType.LINUX:
            return self._detect_linux_emulator(preferred)
        elif self._platform == PlatformType.WINDOWS:
            return self._detect_windows_emulator(preferred)
        
        return EmulatorType.UNKNOWN

    def _detect_linux_emulator(self, preferred: Optional[str]) -> EmulatorType:
        """Detecta emulador en Linux."""
        if preferred == "waydroid":
            if self._check_waydroid():
                return EmulatorType.WAYDROID
        elif preferred == "genymotion":
            if self._check_genymotion():
                return EmulatorType.GENYMOTION
        else:
            # Auto-detectar: Waydroid primero
            if self._check_waydroid():
                return EmulatorType.WAYDROID
            if self._check_genymotion():
                return EmulatorType.GENYMOTION
        
        return EmulatorType.UNKNOWN

    def _detect_windows_emulator(self, preferred: Optional[str]) -> EmulatorType:
        """Detecta emulador en Windows."""
        if preferred == "nox":
            if self._check_nox():
                return EmulatorType.NOX
        else:
            # Auto-detectar
            if self._check_nox():
                return EmulatorType.NOX
        
        return EmulatorType.UNKNOWN

    def _check_waydroid(self) -> bool:
        """Verifica si Waydroid está corriendo."""
        try:
            import subprocess
            result = subprocess.run(
                ["pgrep", "-x", "waydroid"],
                capture_output=True, timeout=2
            )
            return result.returncode == 0
        except:
            return False

    def _check_genymotion(self) -> bool:
        """Verifica si Genymotion está corriendo."""
        try:
            import subprocess
            result = subprocess.run(
                ["pgrep", "-f", "genymotion"],
                capture_output=True, timeout=2
            )
            return result.returncode == 0
        except:
            return False

    def _check_nox(self) -> bool:
        """Verifica si Nox está corriendo (Windows)."""
        if self._platform != PlatformType.WINDOWS:
            return False
        try:
            import pygetwindow as gw
            windows = gw.getAllTitles()
            for title in windows:
                if "nox" in title.lower() or "noxplayer" in title.lower():
                    return True
            return False
        except:
            return False


def get_platform_info() -> Tuple[PlatformType, Optional[EmulatorType]]:
    """
    Función helper para obtener información de plataforma.
    Retorna: (platform, emulator_detected)
    """
    detector = PlatformDetector()
    platform = detector.get_platform()
    emulator = detector.detect_emulator() if platform != PlatformType.UNKNOWN else None
    return platform, emulator


def get_controller_class(platform: PlatformType, emulator: EmulatorType):
    """
    Retorna la clase de controlador apropiada.
    """
    if platform == PlatformType.LINUX:
        if emulator == EmulatorType.WAYDROID:
            from tactical_ai.control.waydroid_ctrl import WaydroidController
            return WaydroidController
        elif emulator == EmulatorType.GENYMOTION:
            from tactical_ai.control.genymotion_ctrl import GenymotionController
            return GenymotionController
    elif platform == PlatformType.WINDOWS:
        if emulator == EmulatorType.NOX:
            from tactical_ai.control.nox_ctrl import NoxController
            return NoxController
    
    return None
