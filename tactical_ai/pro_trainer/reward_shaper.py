"""
Reward Shaping E-Sports para Free Fire.
Diseñado para comportamientos de jugador profesional.
"""

from __future__ import annotations

import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from enum import Enum


class EsportsBehavior(Enum):
    """Comportamientos E-Sports que recompensamos."""
    FLICK_SHOT = "flick_shot"          # Giro rápido y disparo preciso
    PRE_AIM = "pre_aim"                # Apuntar antes de peek
    STRAFE_SHOOT = "strafe_shoot"      # Moverse mientras dispara
    PEEK_SHOOT = "peek_shoot"          # Asomarse, disparar, cubierto
    BAIT = "bait"                      # Engañar al enemigo
    COMBO = "combo"                    # Daño + movimiento simultáneo
    HEADSHOT = "headshot"              # Disparo a la cabeza
    SURVIVAL = "survival"              # Sobrevivir tiempo


@dataclass
class RewardConfig:
    """Configuración de recompensas."""
    # Fundamentos
    hit: float = 10.0
    kill: float = 25.0
    headshot: float = 50.0
    damage: float = 2.0

    # Movimiento
    strafe: float = 3.0
    crouch_shoot: float = 2.0
    cover_use: float = 5.0
    peek_success: float = 10.0

    # Avanzado
    flick_shot: float = 15.0
    pre_aim: float = 10.0
    combo: float = 20.0
    bait_success: float = 10.0
    survival_per_10s: float = 5.0

    # Penalizaciones
    death: float = -25.0
    whiff: float = -8.0          # Fallar todo cargador
    static: float = -3.0         # Quedarse quieto bajo fuego
    friendly_fire: float = -15.0
    reload_in_combat: float = -5.0
    no_ammo: float = -10.0


class EsportsRewardShaper:
    """
    Calcula recompensas con shaping E-Sports.
    Detecta comportamientos avanzados y recompensa/p penaliza.
    """

    def __init__(self, config: RewardConfig = None):
        self.config = config or RewardConfig()

        # Histórico para detectar comportamientos
        self._action_history: List[Tuple[str, float]] = []  # (action, timestamp)
        self._position_history: List[Tuple[float, float]] = []  # (x, y)
        self._aim_history: List[Tuple[float, float]] = []  # (dx, dy)
        self._last_shoot_time: float = 0.0
        self._shots_fired: int = 0
        self._shots_hit: int = 0

        # Métricas del episodio
        self._combos_detected = 0
        self._flicks_detected = 0
        self._peeks_successful = 0

    def reset(self) -> None:
        """Resetea para nuevo episodio."""
        self._action_history.clear()
        self._position_history.clear()
        self._aim_history.clear()
        self._last_shoot_time = 0.0
        self._shots_fired = 0
        self._shots_hit = 0
        self._combos_detected = 0
        self._flicks_detected = 0
        self._peeks_successful = 0

    def calculate_reward(
        self,
        action: str,
        hit_enemy: bool,
        killed_enemy: bool,
        headshot: bool,
        damage_dealt: float,
        health_before: float,
        health_after: float,
        ammo_before: int,
        ammo_after: int,
        position: Tuple[float, float],
        aim_delta: Tuple[float, float],
        in_cover: bool,
        timestamp: float
    ) -> Tuple[float, Dict[str, float]]:
        """
        Calcula recompensa completa con componentes individuales.
        Retorna: (reward_total, components_dict)
        """
        reward = 0.0
        components = {}

        # 1. Recompensas base
        if hit_enemy:
            r = self.config.hit
            reward += r
            components["hit"] = r
            self._shots_hit += 1

        if killed_enemy:
            r = self.config.kill
            reward += r
            components["kill"] = r

        if headshot:
            r = self.config.headshot
            reward += r
            components["headshot"] = r

        if damage_dealt > 0:
            r = damage_dealt * self.config.damage
            reward += r
            components["damage"] = r

        # 2. Detección de comportamientos E-Sports

        # Flick shot: giro rápido + disparo inmediato + hit
        if action == "SHOOT" and hit_enemy:
            if self._is_flick_shot(aim_delta, timestamp):
                r = self.config.flick_shot
                reward += r
                components["flick_shot"] = r
                self._flicks_detected += 1

        # Pre-aim: apuntar a enemigo antes de disparar
        if action == "SHOOT" and hit_enemy:
            if self._is_pre_aim(aim_delta):
                r = self.config.pre_aim
                reward += r
                components["pre_aim"] = r

        # Strafe-shoot: moverse mientras dispara
        if action == "SHOOT":
            if self._is_strafe_shooting(position):
                r = self.config.strafe
                reward += r
                components["strafe"] = r

        # Peek-shoot: cubierto -> disparo -> cubierto
        if action == "SHOOT" and in_cover:
            if self._is_peek_shoot(timestamp):
                r = self.config.peek_success
                reward += r
                components["peek_success"] = r
                self._peeks_successful += 1

        # Combo: daño significativo + movimiento simultáneo
        if damage_dealt > 20 and self._is_moving(position):
            r = self.config.combo
            reward += r
            components["combo"] = r
            self._combos_detected += 1

        # 3. Penalizaciones

        # Whiff: disparar mucho sin hit
        if action == "SHOOT":
            self._shots_fired += 1
            if self._shots_fired >= 5 and self._shots_hit == 0:
                r = self.config.whiff
                reward += r
                components["whiff"] = r
                self._shots_fired = 0  # Reset

        # Static: quedarse quieto bajo fuego
        health_diff = health_before - health_after
        if health_diff > 0 and not self._is_moving(position):
            r = self.config.static
            reward += r
            components["static"] = r

        # No ammo
        if ammo_after == 0 and ammo_before > 0:
            r = self.config.no_ammo
            reward += r
            components["no_ammo"] = r

        # Actualizar historiales
        self._action_history.append((action, timestamp))
        self._position_history.append(position)
        self._aim_history.append(aim_delta)

        # Mantener historial limitado (últimos 30 acciones)
        if len(self._action_history) > 30:
            self._action_history.pop(0)
            self._position_history.pop(0)
            self._aim_history.pop(0)

        return reward, components

    def _is_flick_shot(
        self,
        aim_delta: Tuple[float, float],
        timestamp: float
    ) -> bool:
        """Detecta flick shot: movimiento rápido de mira + disparo."""
        if len(self._aim_history) < 2:
            return False

        # Velocidad de giro
        speed = np.sqrt(aim_delta[0]**2 + aim_delta[1]**2)

        # Flick: giro rápido (>0.5) seguido de disparo inmediato
        if speed > 0.5:
            # Verificar que anteriormente no estábamos apuntando ahí
            prev_aim = self._aim_history[-1]
            prev_speed = np.sqrt(prev_aim[0]**2 + prev_aim[1]**2)

            # Flick = giro rápido desde posición diferente
            if prev_speed < 0.2:
                return True

        return False

    def _is_pre_aim(self, aim_delta: Tuple[float, float]) -> bool:
        """Detecta pre-aim: apuntando cerca del centro (enemigo)."""
        # Si aim_delta es pequeño, estábamos ya apuntando cerca
        aim_distance = np.sqrt(aim_delta[0]**2 + aim_delta[1]**2)
        return aim_distance < 0.2  # Dentro de 20% de la pantalla

    def _is_strafe_shooting(self, position: Tuple[float, float]) -> bool:
        """Detecta si estamos moviéndonos mientras disparamos."""
        if len(self._position_history) < 2:
            return False

        # Calcular velocidad de movimiento
        prev_pos = self._position_history[-1]
        movement = np.sqrt(
            (position[0] - prev_pos[0])**2 +
            (position[1] - prev_pos[1])**2
        )

        return movement > 0.05  # Movimiento significativo

    def _is_peek_shoot(self, timestamp: float) -> bool:
        """Detecta peek-shoot exitoso."""
        if len(self._action_history) < 3:
            return False

        # Buscar patrón: cover -> shoot -> cover (o movimiento)
        recent = [a for a, t in self._action_history[-5:]]

        # Si tenemos cover recientemente
        if "MOVE_TO_COVER" in recent or recent.count("SHOOT") >= 1:
            return True

        return False

    def _is_moving(self, position: Tuple[float, float]) -> bool:
        """Detecta si el agente se está moviendo."""
        if len(self._position_history) < 2:
            return False

        prev_pos = self._position_history[-1]
        dist = np.sqrt(
            (position[0] - prev_pos[0])**2 +
            (position[1] - prev_pos[1])**2
        )

        return dist > 0.02  # Umbral de movimiento

    def get_episode_stats(self) -> Dict:
        """Retorna estadísticas de comportamientos E-Sports del episodio."""
        return {
            "combos": self._combos_detected,
            "flick_shots": self._flicks_detected,
            "peeks_successful": self._peeks_successful,
            "accuracy": self._shots_hit / max(self._shots_fired, 1),
            "total_shots": self._shots_fired,
            "hits": self._shots_hit,
        }

    def get_curriculum_reward(
        self,
        phase: int,  # 0: fundamentos, 1: movimiento, 2: avanzado
        **kwargs
    ) -> float:
        """
        Recompensas adaptadas por fase de entrenamiento (curriculum learning).
        """
        reward, components = self.calculate_reward(**kwargs)

        # Fase 0: Solo fundamentos
        if phase == 0:
            # Ignorar recompensas avanzadas
            filtered = {k: v for k, v in components.items()
                       if k in ["hit", "kill", "damage"]}
            return sum(filtered.values()), filtered

        # Fase 1: Fundamentos + movimiento
        elif phase == 1:
            filtered = {k: v for k, v in components.items()
                       if k in ["hit", "kill", "damage", "strafe",
                               "peek_success", "cover_use"]}
            return sum(filtered.values()), filtered

        # Fase 2: Todo
        else:
            return reward, components
