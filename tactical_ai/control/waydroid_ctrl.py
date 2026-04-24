"""
Control de Waydroid optimizado para baja latencia.
Usa xdotool/ydotool para input directo.
"""

from __future__ import annotations

import subprocess
import time
import random
from typing import Optional, Tuple


class WaydroidController:
    """Controlador de input para Waydroid/Emulador."""

    def __init__(
        self,
        window_offset: Tuple[int, int] = (0, 0),
        window_size: Tuple[int, int] = (1280, 720)
    ):
        self.offset_x, self.offset_y = window_offset
        self.window_w, self.window_h = window_size

        # Detectar herramienta disponible
        self._tool = self._detect_tool()
        self._enabled = True

        # Configuración controles (para 1920x1080, escalado automático)
        self.move_joystick = (180, 580)
        self.aim_joystick = (1050, 580)
        self.shoot_btn = (1150, 500)
        self.jump_btn = (1050, 400)
        self.crouch_btn = (1100, 600)
        self.reload_btn = (980, 480)
        self.heal_btn = (950, 550)

        # Escala
        self._scale_x = window_size[0] / 1920.0
        self._scale_y = window_size[1] / 1080.0

    def _detect_tool(self) -> str:
        """Detecta ydotool o xdotool."""
        try:
            subprocess.run(["ydotool"], capture_output=True, timeout=1)
            return "ydotool"
        except:
            pass

        try:
            subprocess.run(["xdotool"], capture_output=True, timeout=1)
            return "xdotool"
        except:
            pass

        return "none"

    def _scale(self, x: int, y: int) -> Tuple[int, int]:
        """Escala coordenadas."""
        return (int(x * self._scale_x), int(y * self._scale_y))

    def _to_screen(self, x: int, y: int) -> Tuple[int, int]:
        """Convierte a coordenadas de pantalla."""
        sx, sy = self._scale(x, y)
        return (self.offset_x + sx, self.offset_y + sy)

    def _delay(self, min_ms: int = 20, max_ms: int = 50):
        """Delay humanizado."""
        time.sleep(random.randint(min_ms, max_ms) / 1000.0)

    def _run(self, cmd: list) -> bool:
        """Ejecuta comando."""
        if not self._enabled or self._tool == "none":
            return False
        try:
            subprocess.run(cmd, capture_output=True, timeout=2)
            return True
        except:
            return False

    def aim(self, dx: float, dy: float) -> bool:
        """Mueve joystick de mira (dx,dy en -1 a 1)."""
        center_x, center_y = self.aim_joystick
        radius = 80

        x = int(center_x + dx * radius)
        y = int(center_y + dy * radius)

        sx, sy = self._to_screen(x, y)
        cx, cy = self._to_screen(center_x, center_y)

        if self._tool == "ydotool":
            self._run(["ydotool", "mousemove", str(cx), str(cy)])
            self._run(["ydotool", "click", "0xC0"])  # Hold
            self._run(["ydotool", "mousemove", str(sx), str(sy)])
        elif self._tool == "xdotool":
            self._run(["xdotool", "mousemove", str(cx), str(cy)])
            self._run(["xdotool", "mousedown", "1"])
            self._run(["xdotool", "mousemove", str(sx), str(sy)])
            self._delay(50)
            self._run(["xdotool", "mouseup", "1"])

        return True

    def move(self, dx: float, dy: float) -> bool:
        """Mueve joystick de movimiento."""
        center_x, center_y = self.move_joystick
        radius = 80

        x = int(center_x + dx * radius)
        y = int(center_y + dy * radius)

        sx, sy = self._to_screen(x, y)
        cx, cy = self._to_screen(center_x, center_y)

        if self._tool == "ydotool":
            self._run(["ydotool", "mousemove", str(cx), str(cy)])
            self._run(["ydotool", "click", "0xC0"])
            self._delay(100)
            self._run(["ydotool", "mousemove", str(sx), str(sy)])
            self._delay(100)
            self._run(["ydotool", "click", "0x80"])
        elif self._tool == "xdotool":
            self._run(["xdotool", "mousemove", str(cx), str(cy)])
            self._run(["xdotool", "mousedown", "1"])
            self._delay(100)
            self._run(["xdotool", "mousemove", str(sx), str(sy)])
            self._delay(100)
            self._run(["xdotool", "mouseup", "1"])

        return True

    def shoot(self) -> bool:
        """Presiona botón de disparo."""
        x, y = self._to_screen(*self.shoot_btn)
        self._delay(10, 30)

        if self._tool == "ydotool":
            self._run(["ydotool", "mousemove", str(x), str(y)])
            return self._run(["ydotool", "click", "0xC0"])
        elif self._tool == "xdotool":
            self._run(["xdotool", "mousemove", str(x), str(y)])
            return self._run(["xdotool", "click", "1"])

        return False

    def heal(self) -> bool:
        """Usa botiquín."""
        x, y = self._to_screen(*self.heal_btn)
        self._delay(50, 100)

        if self._tool == "ydotool":
            self._run(["ydotool", "mousemove", str(x), str(y)])
            return self._run(["ydotool", "click", "0xC0"])
        elif self._tool == "xdotool":
            self._run(["xdotool", "mousemove", str(x), str(y)])
            return self._run(["xdotool", "click", "1"])

        return False

    def reload(self) -> bool:
        """Recarga."""
        x, y = self._to_screen(*self.reload_btn)
        self._delay(50, 100)

        if self._tool == "ydotool":
            self._run(["ydotool", "mousemove", str(x), str(y)])
            return self._run(["ydotool", "click", "0xC0"])
        elif self._tool == "xdotool":
            self._run(["xdotool", "mousemove", str(x), str(y)])
            return self._run(["xdotool", "click", "1"])

        return False

    def is_available(self) -> bool:
        """Retorna True si hay herramienta de input."""
        return self._tool != "none"
