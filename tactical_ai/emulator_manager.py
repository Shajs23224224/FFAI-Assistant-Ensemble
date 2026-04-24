"""
EmulatorManager: Auto-detección y gestión de emuladores.
Soporta Waydroid y Genymotion Desktop.
"""

from __future__ import annotations

import subprocess
from typing import Optional, Tuple, Union
from enum import Enum, auto

from tactical_ai.control.waydroid_ctrl import WaydroidController
from tactical_ai.control.genymotion_ctrl import GenymotionController


class EmulatorType(Enum):
    """Tipos de emuladores soportados."""
    WAYDROID = auto()
    GENYMOTION = auto()
    UNKNOWN = auto()


class EmulatorManager:
    """
    Gestiona detección y control de emuladores.
    Auto-detecta Waydroid o Genymotion y retorna controlador apropiado.
    """

    def __init__(self):
        self._detected_emulator: Optional[EmulatorType] = None
        self._window_region: Optional[Tuple[int, int, int, int]] = None
        self._controller: Optional[Union[WaydroidController, GenymotionController]] = None

    def detect_emulator(self, preferred: Optional[str] = None) -> EmulatorType:
        """
        Detecta emulador disponible.
        
        Args:
            preferred: "waydroid", "genymotion", o None para auto-detectar
        
        Returns:
            EmulatorType detectado
        """
        if preferred:
            if preferred.lower() == "waydroid":
                region = self._detect_waydroid()
                if region:
                    self._detected_emulator = EmulatorType.WAYDROID
                    self._window_region = region
                    return EmulatorType.WAYDROID
            elif preferred.lower() == "genymotion":
                region = self._detect_genymotion()
                if region:
                    self._detected_emulator = EmulatorType.GENYMOTION
                    self._window_region = region
                    return EmulatorType.GENYMOTION

        # Auto-detectar: intentar Waydroid primero, luego Genymotion
        region = self._detect_waydroid()
        if region:
            self._detected_emulator = EmulatorType.WAYDROID
            self._window_region = region
            print(f"[EmulatorManager] Detectado: Waydroid en {region}")
            return EmulatorType.WAYDROID

        region = self._detect_genymotion()
        if region:
            self._detected_emulator = EmulatorType.GENYMOTION
            self._window_region = region
            print(f"[EmulatorManager] Detectado: Genymotion en {region}")
            return EmulatorType.GENYMOTION

        self._detected_emulator = EmulatorType.UNKNOWN
        return EmulatorType.UNKNOWN

    def _detect_waydroid(self) -> Optional[Tuple[int, int, int, int]]:
        """Detecta ventana Waydroid."""
        try:
            search_terms = ["waydroid", "android"]
            for term in search_terms:
                result = subprocess.run(
                    ["xdotool", "search", "--title", term],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0 and result.stdout.strip():
                    window_id = result.stdout.strip().split('\n')[0]
                    geo = subprocess.run(
                        ["xdotool", "getwindowgeometry", window_id],
                        capture_output=True, text=True, timeout=2
                    )
                    if geo.returncode == 0:
                        return self._parse_geometry(geo.stdout)
        except Exception:
            pass
        return None

    def _detect_genymotion(self) -> Optional[Tuple[int, int, int, int]]:
        """
        Detecta ventana Genymotion.
        Busca títulos típicos: "Genymotion", nombres de dispositivos Android.
        """
        try:
            # Títulos comunes de ventana Genymotion
            search_terms = [
                "Genymotion",
                "Samsung Galaxy",
                "Google Pixel",
                "OnePlus",
                "Huawei",
                "Xiaomi",
                "Android",
                "VirtualBox"
            ]

            for term in search_terms:
                result = subprocess.run(
                    ["xdotool", "search", "--title", term],
                    capture_output=True, text=True, timeout=2
                )
                if result.returncode == 0 and result.stdout.strip():
                    window_id = result.stdout.strip().split('\n')[0]
                    geo = subprocess.run(
                        ["xdotool", "getwindowgeometry", window_id],
                        capture_output=True, text=True, timeout=2
                    )
                    if geo.returncode == 0:
                        return self._parse_geometry(geo.stdout)
        except Exception:
            pass
        return None

    def _parse_geometry(self, output: str) -> Optional[Tuple[int, int, int, int]]:
        """Parsea salida de xdotool getwindowgeometry."""
        try:
            lines = output.split('\n')
            pos_line = [l for l in lines if 'Position:' in l][0]
            geo_line = [l for l in lines if 'Geometry:' in l][0]

            pos = pos_line.split('Position:')[1].split('(')[0].strip()
            left, top = map(int, pos.split(','))

            geo = geo_line.split('Geometry:')[1].strip()
            width, height = map(int, geo.split('x'))

            return (left, top, width, height)
        except:
            return None

    def get_controller(self) -> Optional[Union[WaydroidController, GenymotionController]]:
        """
        Crea y retorna controlador para el emulador detectado.
        
        Returns:
            WaydroidController o GenymotionController, o None si no detectado
        """
        if self._detected_emulator is None:
            self.detect_emulator()

        if self._detected_emulator == EmulatorType.WAYDROID:
            self._controller = WaydroidController(
                window_offset=(self._window_region[0], self._window_region[1]),
                window_size=(self._window_region[2], self._window_region[3])
            )
            return self._controller

        elif self._detected_emulator == EmulatorType.GENYMOTION:
            self._controller = GenymotionController(
                window_offset=(self._window_region[0], self._window_region[1]),
                window_size=(self._window_region[2], self._window_region[3])
            )
            return self._controller

        return None

    def get_window_region(self) -> Optional[Tuple[int, int, int, int]]:
        """Retorna región de ventana detectada."""
        return self._window_region

    def get_emulator_type(self) -> Optional[EmulatorType]:
        """Retorna tipo de emulador detectado."""
        return self._detected_emulator

    def is_detected(self) -> bool:
        """Retorna True si se detectó algún emulador."""
        return self._detected_emulator in [EmulatorType.WAYDROID, EmulatorType.GENYMOTION]

    def get_emulator_name(self) -> str:
        """Retorna nombre legible del emulador."""
        if self._detected_emulator == EmulatorType.WAYDROID:
            return "Waydroid"
        elif self._detected_emulator == EmulatorType.GENYMOTION:
            return "Genymotion"
        return "Unknown"


def get_controller_for_emulator(
    preferred: Optional[str] = None,
    window_region: Optional[Tuple[int, int, int, int]] = None
) -> Tuple[Optional[Union[WaydroidController, GenymotionController]], str]:
    """
    Función helper para obtener controlador.
    
    Args:
        preferred: "waydroid", "genymotion", o None para auto
        window_region: Región específica (opcional)
    
    Returns:
        (controller, emulator_name)
    """
    if window_region:
        # Usar región especificada, inferir tipo por tamaño
        w, h = window_region[2], window_region[3]
        
        # Genymotion típicamente 720x1280 o similar
        # Waydroid típicamente más grande (ventana completa)
        if h > w and w < 900:  # Portrait, resolución móvil
            ctrl = GenymotionController(
                window_offset=(window_region[0], window_region[1]),
                window_size=(window_region[2], window_region[3])
            )
            return ctrl, "Genymotion (manual)"
        else:
            ctrl = WaydroidController(
                window_offset=(window_region[0], window_region[1]),
                window_size=(window_region[2], window_region[3])
            )
            return ctrl, "Waydroid (manual)"

    # Auto-detectar
    manager = EmulatorManager()
    emu_type = manager.detect_emulator(preferred)
    
    if emu_type == EmulatorType.UNKNOWN:
        return None, "None"
    
    controller = manager.get_controller()
    return controller, manager.get_emulator_name()
