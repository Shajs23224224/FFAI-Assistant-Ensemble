"""
Control de Genymotion Desktop (VirtualBox) optimizado.
Compensa bordes de ventana VirtualBox y usa coordenadas para 720x1280.
"""

from __future__ import annotations

import subprocess
import time
import random
from typing import Optional, Tuple


class GenymotionController:
    """
    Controlador de input para Genymotion Desktop.
    Compensa bordes de ventana VirtualBox (~30px título, ~8px laterales).
    Optimizado para resolución 720x1280.
    """

    # Bordes de ventana VirtualBox
    BORDER_TOP = 30      # Barra de título
    BORDER_BOTTOM = 8    # Borde inferior
    BORDER_LEFT = 8      # Borde izquierdo
    BORDER_RIGHT = 8     # Borde derecho

    def __init__(
        self,
        window_offset: Tuple[int, int] = (0, 0),
        window_size: Tuple[int, int] = (736, 1344)  # 720+16, 1280+64 aprox
    ):
        self.raw_x, self.raw_y = window_offset
        self.raw_w, self.raw_h = window_size

        # Calcular área útil (sin bordes VirtualBox)
        self.offset_x = self.raw_x + self.BORDER_LEFT
        self.offset_y = self.raw_y + self.BORDER_TOP
        self.window_w = self.raw_w - self.BORDER_LEFT - self.BORDER_RIGHT
        self.window_h = self.raw_h - self.BORDER_TOP - self.BORDER_BOTTOM

        # Detectar herramienta disponible
        self._tool = self._detect_tool()
        self._enabled = True

        # Controles para 720x1280 (HD portrait)
        # Free Fire en modo portrait 720x1280
        self.move_joystick = (120, 900)      # Joystick movimiento (abajo-izq)
        self.aim_joystick = (600, 900)       # Joystick mira (abajo-der)
        self.shoot_btn = (650, 800)          # Botón disparo
        self.jump_btn = (600, 700)           # Botón salto
        self.crouch_btn = (550, 950)         # Botón agacharse
        self.reload_btn = (520, 780)         # Botón recargar
        self.heal_btn = (480, 850)           # Botón curar

        # Verificar resolución
        if abs(self.window_w - 720) > 50 or abs(self.window_h - 1280) > 50:
            print(f"[Warning] Resolución inesperada: {self.window_w}x{self.window_h}")
            print(f"[Warning] Esperado: ~720x1280")
            print(f"[Info] Las coordenadas pueden necesitar ajuste")

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

    def _to_screen(self, x: int, y: int) -> Tuple[int, int]:
        """Convierte coordenadas del juego a pantalla (compensando bordes)."""
        return (self.offset_x + x, self.offset_y + y)

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
        radius = 60  # Radio del joystick virtual

        x = int(center_x + dx * radius)
        y = int(center_y + dy * radius)

        sx, sy = self._to_screen(x, y)
        cx, cy = self._to_screen(center_x, center_y)

        if self._tool == "ydotool":
            self._run(["ydotool", "mousemove", str(cx), str(cy)])
            self._run(["ydotool", "click", "0xC0"])  # Hold
            self._delay(30, 50)
            self._run(["ydotool", "mousemove", str(sx), str(sy)])
            self._delay(50, 80)
            self._run(["ydotool", "click", "0x80"])  # Release
        elif self._tool == "xdotool":
            self._run(["xdotool", "mousemove", str(cx), str(cy)])
            self._run(["xdotool", "mousedown", "1"])
            self._delay(30, 50)
            self._run(["xdotool", "mousemove", str(sx), str(sy)])
            self._delay(50, 80)
            self._run(["xdotool", "mouseup", "1"])

        return True

    def move(self, dx: float, dy: float) -> bool:
        """Mueve joystick de movimiento."""
        center_x, center_y = self.move_joystick
        radius = 60

        x = int(center_x + dx * radius)
        y = int(center_y + dy * radius)

        sx, sy = self._to_screen(x, y)
        cx, cy = self._to_screen(center_x, center_y)

        if self._tool == "ydotool":
            self._run(["ydotool", "mousemove", str(cx), str(cy)])
            self._run(["ydotool", "click", "0xC0"])
            self._delay(80, 120)
            self._run(["ydotool", "mousemove", str(sx), str(sy)])
            self._delay(100, 150)
            self._run(["ydotool", "click", "0x80"])
        elif self._tool == "xdotool":
            self._run(["xdotool", "mousemove", str(cx), str(cy)])
            self._run(["xdotool", "mousedown", "1"])
            self._delay(80, 120)
            self._run(["xdotool", "mousemove", str(sx), str(sy)])
            self._delay(100, 150)
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

    def crouch(self) -> bool:
        """Agacharse."""
        x, y = self._to_screen(*self.crouch_btn)
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
