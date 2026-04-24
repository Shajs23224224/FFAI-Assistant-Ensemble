"""
NitroCapture: Sistema de captura de pantalla ultra-rápido.
Target: 15-20 FPS en Pentium N3700 con latencia <5ms.
"""

from __future__ import annotations

import time
import threading
from queue import Queue, Empty
from typing import Optional, Tuple, Callable
from dataclasses import dataclass

import numpy as np
import cv2

try:
    import mss
    MSS_AVAILABLE = True
except ImportError:
    MSS_AVAILABLE = False


@dataclass
class CaptureConfig:
    """Configuración de captura."""
    target_fps: int = 15
    resolution: Tuple[int, int] = (320, 240)  # Output resolution
    region: Optional[Tuple[int, int, int, int]] = None  # x, y, w, h
    use_threading: bool = True
    buffer_size: int = 2  # Double buffer


class NitroCapture:
    """
    Captura de pantalla optimizada con threading y pre-procesamiento.
    """

    def __init__(self, config: Optional[CaptureConfig] = None):
        self.config = config or CaptureConfig()
        self._mss: Optional[mss.mss] = None
        self._running = False
        self._capture_thread: Optional[threading.Thread] = None

        # Buffers
        self._frame_queue: Queue = Queue(maxsize=self.config.buffer_size)
        self._last_frame: Optional[np.ndarray] = None
        self._last_capture_time = 0.0

        # Estadísticas
        self._fps_actual = 0.0
        self._frame_count = 0
        self._start_time = time.time()

        # Callbacks
        self._on_frame: Optional[Callable] = None
        self._on_error: Optional[Callable] = None

        if MSS_AVAILABLE:
            self._mss = mss.mss()

    def start(self, on_frame: Optional[Callable] = None) -> bool:
        """Inicia captura."""
        if not MSS_AVAILABLE:
            print("[ERROR] mss no disponible")
            return False

        self._running = True
        self._on_frame = on_frame

        if self.config.use_threading:
            self._capture_thread = threading.Thread(target=self._capture_loop, daemon=True)
            self._capture_thread.start()
        else:
            # Modo síncrono
            pass

        return True

    def stop(self) -> None:
        """Detiene captura."""
        self._running = False
        if self._capture_thread:
            self._capture_thread.join(timeout=1.0)

        if self._mss:
            self._mss.close()

    def _capture_loop(self) -> None:
        """Loop de captura en thread separado."""
        target_interval = 1.0 / self.config.target_fps

        while self._running:
            loop_start = time.perf_counter()

            try:
                frame = self._capture_single()

                if frame is not None:
                    # Actualizar estadísticas
                    self._frame_count += 1
                    elapsed = time.time() - self._start_time
                    self._fps_actual = self._frame_count / elapsed

                    # Callback o queue
                    if self._on_frame:
                        self._on_frame(frame)
                    else:
                        # Non-blocking put
                        try:
                            self._frame_queue.put_nowait(frame)
                        except:
                            # Queue llena, descartar frame más viejo
                            try:
                                self._frame_queue.get_nowait()
                                self._frame_queue.put_nowait(frame)
                            except:
                                pass

            except Exception as e:
                if self._on_error:
                    self._on_error(e)

            # Mantener FPS objetivo
            elapsed = time.perf_counter() - loop_start
            sleep_time = target_interval - elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

    def _capture_single(self) -> Optional[np.ndarray]:
        """Captura un frame único."""
        if not self._mss:
            return None

        # Configurar región
        if self.config.region:
            monitor = {
                "left": self.config.region[0],
                "top": self.config.region[1],
                "width": self.config.region[2],
                "height": self.config.region[3]
            }
        else:
            monitor = self._mss.monitors[1]  # Monitor principal

        # Capturar
        screenshot = self._mss.grab(monitor)
        img = np.array(screenshot)

        # Convertir BGRA a BGR y resize
        if img.shape[2] == 4:
            img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)

        # Redimensionar a resolución objetivo
        if (img.shape[1], img.shape[0]) != self.config.resolution:
            img = cv2.resize(img, self.config.resolution, interpolation=cv2.INTER_LINEAR)

        return img

    def get_frame(self, timeout: float = 0.001) -> Optional[np.ndarray]:
        """Obtiene frame más reciente (non-blocking por defecto)."""
        if not self.config.use_threading:
            # Modo síncrono: capturar ahora
            return self._capture_single()

        try:
            return self._frame_queue.get(timeout=timeout)
        except Empty:
            return None

    def get_fps(self) -> float:
        """Retorna FPS actual."""
        return self._fps_actual

    def benchmark(self, duration_seconds: float = 5.0) -> dict:
        """Benchmark de captura."""
        print(f"[Benchmark] Capturando por {duration_seconds}s...")

        frames = []
        start = time.time()

        while time.time() - start < duration_seconds:
            frame = self._capture_single()
            if frame is not None:
                frames.append(frame)

        elapsed = time.time() - start
        fps = len(frames) / elapsed

        return {
            "duration": elapsed,
            "frames": len(frames),
            "fps": fps,
            "resolution": frames[0].shape if frames else None
        }


class WindowDetector:
    """Detecta ventana de Waydroid/Genymotion/Nox/Emulador."""

    def __init__(self):
        self._cached_region: Optional[Tuple[int, int, int, int]] = None
        self._cache_time = 0.0
        self._cached_type: Optional[str] = None

    def detect_any(self) -> Tuple[Optional[Tuple[int, int, int, int]], Optional[str]]:
        """
        Detecta cualquier emulador disponible.
        Retorna: (region, tipo) donde tipo es 'waydroid', 'genymotion', o 'nox'
        """
        now = time.time()

        # Usar cache por 5 segundos
        if self._cached_region and (now - self._cache_time) < 5.0:
            return self._cached_region, self._cached_type

        # Detectar plataforma
        import sys
        is_windows = sys.platform == "win32"

        if is_windows:
            # Windows: intentar Nox
            region = self._detect_nox()
            if region:
                self._cached_region = region
                self._cache_time = now
                self._cached_type = "nox"
                return region, "nox"
        else:
            # Linux: Waydroid o Genymotion
            region = self._detect_waydroid()
            if region:
                self._cached_region = region
                self._cache_time = now
                self._cached_type = "waydroid"
                return region, "waydroid"

            region = self._detect_genymotion()
            if region:
                self._cached_region = region
                self._cache_time = now
                self._cached_type = "genymotion"
                return region, "genymotion"

        return None, None

    def detect_waydroid(self) -> Optional[Tuple[int, int, int, int]]:
        """Detecta ventana Waydroid."""
        now = time.time()

        if self._cached_region and self._cached_type == "waydroid" and (now - self._cache_time) < 5.0:
            return self._cached_region

        region = self._detect_waydroid()
        if region:
            self._cached_region = region
            self._cache_time = now
            self._cached_type = "waydroid"

        return region

    def detect_genymotion(self) -> Optional[Tuple[int, int, int, int]]:
        """Detecta ventana Genymotion."""
        now = time.time()

        if self._cached_region and self._cached_type == "genymotion" and (now - self._cache_time) < 5.0:
            return self._cached_region

        region = self._detect_genymotion()
        if region:
            self._cached_region = region
            self._cache_time = now
            self._cached_type = "genymotion"

        return region

    def detect_nox(self) -> Optional[Tuple[int, int, int, int]]:
        """Detecta ventana Nox Player (Windows)."""
        now = time.time()

        if self._cached_region and self._cached_type == "nox" and (now - self._cache_time) < 5.0:
            return self._cached_region

        region = self._detect_nox()
        if region:
            self._cached_region = region
            self._cache_time = now
            self._cached_type = "nox"

        return region

    def _detect_nox(self) -> Optional[Tuple[int, int, int, int]]:
        """Detecta ventana Nox Player usando pygetwindow (Windows)."""
        try:
            import pygetwindow as gw

            # Títulos comunes de Nox
            search_terms = ["Nox", "NoxPlayer", "Free Fire"]

            for title in gw.getAllTitles():
                for term in search_terms:
                    if term.lower() in title.lower():
                        window = gw.getWindowsWithTitle(title)[0]
                        # Obtener posición y tamaño
                        left, top = window.left, window.top
                        width, height = window.width, window.height
                        # Verificar tamaño razonable (landscape 1280x720)
                        if width > height and 600 < width < 2000 and 400 < height < 1200:
                            return (left, top, width, height)
        except Exception:
            pass

        return None

    def _detect_waydroid(self) -> Optional[Tuple[int, int, int, int]]:
        """Usa xdotool para detectar Waydroid."""
        try:
            import subprocess

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
        Detecta ventana Genymotion Desktop (VirtualBox).
        Busca títulos típicos de dispositivos Android.
        """
        try:
            import subprocess

            # Títulos comunes de Genymotion
            search_terms = [
                "Genymotion",
                "Samsung Galaxy",
                "Google Pixel",
                "OnePlus",
                "Huawei",
                "Xiaomi",
                "Sony Xperia",
                "Motorola",
                "LG"
            ]

            for term in search_terms:
                result = subprocess.run(
                    ["xdotool", "search", "--title", term],
                    capture_output=True, text=True, timeout=2
                )

                if result.returncode == 0 and result.stdout.strip():
                    # Filtrar solo ventanas con dimensiones de móvil (alto > ancho)
                    for window_id in result.stdout.strip().split('\n'):
                        geo = subprocess.run(
                            ["xdotool", "getwindowgeometry", window_id],
                            capture_output=True, text=True, timeout=2
                        )

                        if geo.returncode == 0:
                            region = self._parse_geometry(geo.stdout)
                            if region:
                                w, h = region[2], region[3]
                                # Verificar que es portrait y tamaño razonable
                                if h > w and 300 < w < 1200 and 500 < h < 2000:
                                    return region

        except Exception:
            pass

        return None

    def _parse_geometry(self, output: str) -> Optional[Tuple[int, int, int, int]]:
        """Parsea salida de xdotool."""
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


def find_waydroid_window() -> Optional[Tuple[int, int, int, int]]:
    """Función helper para detectar ventana Waydroid."""
    detector = WindowDetector()
    return detector.detect_waydroid()


def find_emulator_window() -> Tuple[Optional[Tuple[int, int, int, int]], Optional[str]]:
    """
    Detecta cualquier emulador (Waydroid o Genymotion).
    Retorna: (region, tipo_emulador)
    """
    detector = WindowDetector()
    return detector.detect_any()

