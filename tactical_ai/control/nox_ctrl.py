"""
NoxController: Control de Nox Player en Windows.
Optimizado para resolución 1280x720 landscape.
"""

from __future__ import annotations

import time
import random
from typing import Optional, Tuple

from .windows_ctrl import WindowsController


class NoxController(WindowsController):
    """
    Controlador específico para Nox Player en Windows.
    Configurado para Free Fire en resolución 1280x720 landscape.
    """

    def __init__(
        self,
        window_offset: Tuple[int, int] = (0, 0),
        window_size: Tuple[int, int] = (1280, 720)
    ):
        super().__init__(window_offset, window_size)

        # Controles para 1280x720 LANDSCAPE (Free Fire modo PC)
        # Joystick movimiento (esquina inferior izquierda)
        self.move_joystick = (200, 580)
        # Joystick mira (esquina inferior derecha)
        self.aim_joystick = (1080, 580)
        # Boton disparo (derecha)
        self.shoot_btn = (1150, 500)
        # Boton salto
        self.jump_btn = (1100, 400)
        # Boton agacharse
        self.crouch_btn = (1050, 650)
        # Boton recargar
        self.reload_btn = (1000, 500)
        # Boton curar
        self.heal_btn = (950, 450)

        # Verificar resolucion
        if abs(self.window_w - 1280) > 100 or abs(self.window_h - 720) > 100:
            print(f"[Warning] Resolucion inesperada: {self.window_w}x{self.window_h}")

    def aim(self, dx: float, dy: float) -> bool:
        """Mueve joystick de mira."""
        if not self._pyautogui or not self._enabled:
            return False

        center_x, center_y = self.aim_joystick
        radius = 80
        target_x = int(center_x + dx * radius)
        target_y = int(center_y + dy * radius)

        try:
            sx, sy = self._to_screen(center_x, center_y)
            tx, ty = self._to_screen(target_x, target_y)
            self._pyautogui.moveTo(sx, sy, duration=0.05)
            self._pyautogui.mouseDown()
            time.sleep(0.05)
            self._pyautogui.moveTo(tx, ty, duration=0.1)
            time.sleep(0.1)
            self._pyautogui.mouseUp()
            return True
        except:
            return False

    def move(self, dx: float, dy: float) -> bool:
        """Mueve joystick de movimiento."""
        if not self._pyautogui or not self._enabled:
            return False

        center_x, center_y = self.move_joystick
        radius = 80
        target_x = int(center_x + dx * radius)
        target_y = int(center_y + dy * radius)

        try:
            sx, sy = self._to_screen(center_x, center_y)
            tx, ty = self._to_screen(target_x, target_y)
            self._pyautogui.moveTo(sx, sy, duration=0.05)
            self._pyautogui.mouseDown()
            time.sleep(0.1)
            self._pyautogui.moveTo(tx, ty, duration=0.15)
            time.sleep(0.15)
            self._pyautogui.mouseUp()
            return True
        except:
            return False

    def shoot(self) -> bool:
        """Presiona boton de disparo."""
        x, y = self.shoot_btn
        self._delay(10, 30)
        return self.click(x, y)

    def heal(self) -> bool:
        """Usa botiquin."""
        x, y = self.heal_btn
        self._delay(50, 100)
        return self.click(x, y)

    def reload(self) -> bool:
        """Recarga."""
        x, y = self.reload_btn
        self._delay(50, 100)
        return self.click(x, y)

    def crouch(self) -> bool:
        """Agacharse."""
        x, y = self.crouch_btn
        self._delay(50, 100)
        return self.click(x, y)

    def jump(self) -> bool:
        """Saltar."""
        x, y = self.jump_btn
        self._delay(50, 100)
        return self.click(x, y)
