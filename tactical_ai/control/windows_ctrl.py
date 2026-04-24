"""
WindowsController: Control base para emuladores en Windows.
Usa pyautogui para simular mouse/teclado.
"""

from __future__ import annotations

import time
import random
from typing import Optional, Tuple


class WindowsController:
    """
    Controlador base para Windows usando pyautogui.
    Proporciona funciones comunes para control de emuladores.
    """

    def __init__(
        self,
        window_offset: Tuple[int, int] = (0, 0),
        window_size: Tuple[int, int] = (1280, 720)
    ):
        self.offset_x, self.offset_y = window_offset
        self.window_w, self.window_h = window_size
        self._enabled = True
        self._pyautogui = None
        self._window_title: Optional[str] = None

        # Intentar importar pyautogui
        try:
            import pyautogui
            self._pyautogui = pyautogui
            # Configurar failsafe (mover mouse a esquina detiene script)
            pyautogui.FAILSAFE = True
            pyautogui.PAUSE = 0.01  # Delay mínimo entre acciones
        except ImportError:
            self._enabled = False
            print("[Warning] pyautogui no instalado. Instala: pip install pyautogui")

    def _to_screen(self, x: int, y: int) -> Tuple[int, int]:
        """Convierte coordenadas del juego a pantalla."""
        return (self.offset_x + x, self.offset_y + y)

    def _delay(self, min_ms: int = 20, max_ms: int = 50):
        """Delay humanizado."""
        time.sleep(random.randint(min_ms, max_ms) / 1000.0)

    def move_mouse(self, x: int, y: int, duration: float = 0.1) -> bool:
        """Mueve mouse a coordenadas."""
        if not self._pyautogui or not self._enabled:
            return False
        try:
            sx, sy = self._to_screen(x, y)
            self._pyautogui.moveTo(sx, sy, duration=duration)
            return True
        except:
            return False

    def click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """Click en coordenadas o posición actual."""
        if not self._pyautogui or not self._enabled:
            return False
        try:
            if x is not None and y is not None:
                sx, sy = self._to_screen(x, y)
                self._pyautogui.click(sx, sy)
            else:
                self._pyautogui.click()
            return True
        except:
            return False

    def mouse_down(self) -> bool:
        """Presiona botón del mouse."""
        if not self._pyautogui or not self._enabled:
            return False
        try:
            self._pyautogui.mouseDown()
            return True
        except:
            return False

    def mouse_up(self) -> bool:
        """Suelta botón del mouse."""
        if not self._pyautogui or not self._enabled:
            return False
        try:
            self._pyautogui.mouseUp()
            return True
        except:
            return False

    def drag_to(self, x: int, y: int, duration: float = 0.2) -> bool:
        """Arrastra mouse a coordenadas."""
        if not self._pyautogui or not self._enabled:
            return False
        try:
            sx, sy = self._to_screen(x, y)
            self._pyautogui.dragTo(sx, sy, duration=duration)
            return True
        except:
            return False

    def key_press(self, key: str) -> bool:
        """Presiona tecla."""
        if not self._pyautogui or not self._enabled:
            return False
        try:
            self._pyautogui.press(key)
            return True
        except:
            return False

    def is_available(self) -> bool:
        """Retorna True si pyautogui está disponible."""
        return self._enabled and self._pyautogui is not None
