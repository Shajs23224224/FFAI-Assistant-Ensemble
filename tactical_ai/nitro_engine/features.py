"""
Extracción de Features Manual Optimizada.
No usa CNN - features diseñadas manualmente para velocidad.
Input: Frame BGR (320x240)
Output: Vector de 8 features float32
Tiempo: ~2ms en Pentium N3700
"""

from __future__ import annotations

import numpy as np
import cv2
from typing import Tuple, Optional, Dict
from dataclasses import dataclass


@dataclass
class GameFeatures:
    """Features extraídas del frame."""
    health_ratio: float      # 0.0 - 1.0
    ammo_ratio: float        # 0.0 - 1.0
    enemy_x: float           # -1.0 (izq) a 1.0 (der), 0.0 si no hay
    enemy_y: float           # -1.0 (arriba) a 1.0 (abajo), 0.0 si no hay
    enemy_present: float     # 0.0 o 1.0
    zone_safe: float       # 0.0 (peligro) a 1.0 (seguro)
    under_fire: float        # 0.0 o 1.0
    movement_detected: float # 0.0 o 1.0

    def to_vector(self) -> np.ndarray:
        """Convierte a vector numpy para la red."""
        return np.array([
            self.health_ratio,
            self.ammo_ratio,
            self.enemy_x,
            self.enemy_y,
            self.enemy_present,
            self.zone_safe,
            self.under_fire,
            self.movement_detected
        ], dtype=np.float32)

    @classmethod
    def from_vector(cls, vec: np.ndarray) -> "GameFeatures":
        """Crea desde vector."""
        return cls(*vec.tolist())


class FeatureExtractor:
    """
    Extractor de features ultra-rápido.
    Procesa solo ROI central para máxima velocidad.
    """

    # Rangos HSV optimizados para Free Fire
    RED_LOWER1 = np.array([0, 120, 70], dtype=np.uint8)
    RED_UPPER1 = np.array([10, 255, 255], dtype=np.uint8)
    RED_LOWER2 = np.array([170, 120, 70], dtype=np.uint8)
    RED_UPPER2 = np.array([180, 255, 255], dtype=np.uint8)

    GREEN_LOWER = np.array([40, 100, 100], dtype=np.uint8)
    GREEN_UPPER = np.array([80, 255, 255], dtype=np.uint8)

    BLUE_LOWER = np.array([90, 50, 50], dtype=np.uint8)
    BLUE_UPPER = np.array([130, 255, 255], dtype=np.uint8)

    WHITE_LOWER = np.array([0, 0, 200], dtype=np.uint8)
    WHITE_UPPER = np.array([180, 30, 255], dtype=np.uint8)

    def __init__(self, frame_width: int = 320, frame_height: int = 240):
        self.frame_w = frame_width
        self.frame_h = frame_height

        # Pre-calcular regiones de interés (ROIs)
        self.roi_health = (0, int(frame_height * 0.85), int(frame_width * 0.35), frame_height)
        self.roi_ammo = (int(frame_width * 0.75), int(frame_height * 0.85), frame_width, frame_height)
        self.roi_minimap = (int(frame_width * 0.75), 0, frame_width, int(frame_height * 0.25))
        self.roi_center = (int(frame_width * 0.2), int(frame_height * 0.2),
                         int(frame_width * 0.8), int(frame_height * 0.8))

        # Frame anterior para detección de movimiento
        self._prev_gray: Optional[np.ndarray] = None

        # Cache de features (evita recomputar si frame similar)
        self._cache_features: Optional[GameFeatures] = None
        self._cache_frame_hash: Optional[int] = None

    def _frame_hash(self, frame: np.ndarray) -> int:
        """Hash rápido del frame para cache."""
        # Usar suma de píxeles centrales como hash
        center = frame[self.frame_h//2-5:self.frame_h//2+5, self.frame_w//2-5:self.frame_w//2+5]
        return int(center.sum())

    def extract(self, frame: np.ndarray) -> GameFeatures:
        """
        Extrae features del frame.
        Tiempo objetivo: <3ms
        """
        # Verificar cache
        frame_hash = self._frame_hash(frame)
        if frame_hash == self._cache_frame_hash and self._cache_features is not None:
            return self._cache_features

        # Convertir a HSV una sola vez
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Extraer features en paralelo (vectorizado)
        health_ratio = self._extract_health(hsv, frame)
        ammo_ratio = self._extract_ammo(hsv, frame)
        enemy_x, enemy_y, enemy_present = self._extract_enemy(hsv)
        zone_safe = self._extract_zone(hsv)
        under_fire = self._extract_damage(frame)
        movement = self._extract_movement(frame)

        features = GameFeatures(
            health_ratio=health_ratio,
            ammo_ratio=ammo_ratio,
            enemy_x=enemy_x,
            enemy_y=enemy_y,
            enemy_present=enemy_present,
            zone_safe=zone_safe,
            under_fire=under_fire,
            movement_detected=movement
        )

        # Actualizar cache
        self._cache_features = features
        self._cache_frame_hash = frame_hash

        return features

    def _extract_health(self, hsv: np.ndarray, frame: np.ndarray) -> float:
        """Extrae ratio de vida (0.0 - 1.0)."""
        x1, y1, x2, y2 = self.roi_health
        roi = hsv[y1:y2, x1:x2]

        if roi.size == 0:
            return 1.0

        # Detectar barra verde
        green_mask = cv2.inRange(roi, self.GREEN_LOWER, self.GREEN_UPPER)

        # Encontrar contornos
        contours, _ = cv2.findContours(green_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < 100:
                continue

            x, y, w, h = cv2.boundingRect(cnt)
            aspect = w / max(h, 1)

            # Barra de vida: ancha y baja
            if 3 < aspect < 20:
                # Estimar % basado en ancho relativo
                max_width = roi.shape[1] * 0.6  # Asumir 60% del ROI es vida máxima
                ratio = min(1.0, w / max_width)
                return ratio

        return 1.0  # Default: vida completa

    def _extract_ammo(self, hsv: np.ndarray, frame: np.ndarray) -> float:
        """Extrae ratio de munición (0.0 - 1.0)."""
        x1, y1, x2, y2 = self.roi_ammo
        roi = frame[y1:y2, x1:x2]  # Usar BGR para números

        if roi.size == 0:
            return 1.0

        # Convertir a gris y buscar píxeles brillantes (números)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)

        white_pixels = np.sum(thresh == 255)
        total_pixels = thresh.size

        # Heurística: más píxeles blancos = más munición
        ratio = min(1.0, white_pixels / (total_pixels * 0.15))
        return ratio

    def _extract_enemy(self, hsv: np.ndarray) -> Tuple[float, float, float]:
        """
        Detecta enemigos y retorna posición normalizada.
        Retorna: (x, y, present) donde x,y están en [-1, 1]
        """
        x1, y1, x2, y2 = self.roi_center
        roi = hsv[y1:y2, x1:x2]

        if roi.size == 0:
            return 0.0, 0.0, 0.0

        # Máscara de rojo (indicadores de enemigo)
        mask1 = cv2.inRange(roi, self.RED_LOWER1, self.RED_UPPER1)
        mask2 = cv2.inRange(roi, self.RED_LOWER2, self.RED_UPPER2)
        red_mask = cv2.bitwise_or(mask1, mask2)

        # Operaciones morfológicas mínimas
        kernel = np.ones((3, 3), np.uint8)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)

        # Encontrar centroides
        moments = cv2.moments(red_mask)

        if moments["m00"] > 100:  # Umbral mínimo de detección
            cx = moments["m10"] / moments["m00"]
            cy = moments["m01"] / moments["m00"]

            # Normalizar a [-1, 1]
            roi_w = roi.shape[1]
            roi_h = roi.shape[0]

            norm_x = (cx / roi_w) * 2 - 1
            norm_y = (cy / roi_h) * 2 - 1

            return float(norm_x), float(norm_y), 1.0

        return 0.0, 0.0, 0.0

    def _extract_zone(self, hsv: np.ndarray) -> float:
        """Detecta si estamos en zona segura (0.0 - 1.0)."""
        x1, y1, x2, y2 = self.roi_minimap
        roi = hsv[y1:y2, x1:x2]

        if roi.size == 0:
            return 1.0

        # Detectar círculo azul de zona segura
        blue_mask = cv2.inRange(roi, self.BLUE_LOWER, self.BLUE_UPPER)

        # Si hay suficiente azul, estamos cerca de zona segura
        blue_ratio = np.sum(blue_mask > 0) / max(blue_mask.size, 1)

        # Detectar daño por zona (indicador rojo en bordes)
        edge_roi = hsv[0:int(self.frame_h * 0.1), :]
        red_mask = cv2.inRange(edge_roi, self.RED_LOWER1, self.RED_UPPER1)
        damage_ratio = np.sum(red_mask > 0) / max(red_mask.size, 1)

        if damage_ratio > 0.05:
            return 0.0  # En peligro

        return min(1.0, blue_ratio * 5)  # Escalar a 0-1

    def _extract_damage(self, frame: np.ndarray) -> float:
        """Detecta si estamos recibiendo daño."""
        # ROI bordes (indicadores de daño en Free Fire)
        edge_top = frame[0:20, :]
        edge_bottom = frame[-20:, :]

        # Convertir a HSV y buscar rojo
        hsv_top = cv2.cvtColor(edge_top, cv2.COLOR_BGR2HSV)
        hsv_bottom = cv2.cvtColor(edge_bottom, cv2.COLOR_BGR2HSV)

        mask_top = cv2.inRange(hsv_top, self.RED_LOWER1, self.RED_UPPER1)
        mask_bottom = cv2.inRange(hsv_bottom, self.RED_LOWER1, self.RED_UPPER1)

        red_ratio = (np.sum(mask_top > 0) + np.sum(mask_bottom > 0)) / \
                    (mask_top.size + mask_bottom.size)

        return 1.0 if red_ratio > 0.1 else 0.0

    def _extract_movement(self, frame: np.ndarray) -> float:
        """Detecta movimiento en el frame (flujo óptico simple)."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        if self._prev_gray is None:
            self._prev_gray = gray
            return 0.0

        # Diferencia absoluta simple (muy rápido)
        diff = cv2.absdiff(self._prev_gray, gray)
        _, thresh = cv2.threshold(diff, 25, 255, cv2.THRESH_BINARY)

        movement_ratio = np.sum(thresh > 0) / thresh.size

        self._prev_gray = gray

        return 1.0 if movement_ratio > 0.05 else 0.0

    def get_feature_names(self) -> list:
        """Retorna nombres de features para debug."""
        return [
            "health_ratio",
            "ammo_ratio",
            "enemy_x",
            "enemy_y",
            "enemy_present",
            "zone_safe",
            "under_fire",
            "movement"
        ]
