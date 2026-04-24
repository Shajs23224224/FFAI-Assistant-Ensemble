"""Capa 4 — Control motor: suavizado, sin snap perfecto, micro-ajustes."""

from __future__ import annotations

import math

from tactical_ai.models_ai_types import ActionType, ScoredAction, Vec2, WorldState


class MotorState:
    """Estado persistente para interpolación (aim suavizado, movimiento)."""

    def __init__(self) -> None:
        self.aim_x = 0.0
        self.aim_y = 1.0
        self.move_x = 0.0
        self.move_y = 0.0


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def compute_motor(
    scored: ScoredAction,
    world: WorldState,
    dt_ms: float,
    motor: MotorState,
    aim_lerp_per_s: float = 6.0,
    move_lerp_per_s: float = 8.0,
) -> tuple[Vec2, Vec2]:
    """
    Devuelve (aim_delta, move_intent) suavizados.
    aim_delta: corrección hacia el objetivo (tu juego puede aplicarla como rotación incremental).
    """
    dt_s = max(1e-6, dt_ms / 1000.0)

    # Objetivo de movimiento según acción
    tx, ty = 0.0, 0.0
    if scored.action == ActionType.MOVE_TO_COVER:
        if world.predicted_threat_direction is not None:
            tx = -world.predicted_threat_direction.x
            ty = -world.predicted_threat_direction.y
        else:
            tx, ty = -1.0, 0.0
    elif scored.action in (ActionType.ROTATE, ActionType.SHOOT):
        if world.predicted_threat_direction is not None:
            tx = world.predicted_threat_direction.y
            ty = -world.predicted_threat_direction.x
        else:
            tx, ty = 0.0, 1.0
    elif scored.action in (ActionType.HOLD, ActionType.HEAL):
        tx, ty = 0.0, 0.0
    else:
        tx, ty = motor.move_x, motor.move_y

    n = math.hypot(tx, ty)
    if n > 1e-6:
        tx, ty = tx / n, ty / n

    t_move = min(1.0, move_lerp_per_s * dt_s)
    motor.move_x = _lerp(motor.move_x, tx, t_move)
    motor.move_y = _lerp(motor.move_y, ty, t_move)

    # Aim hacia amenaza (si no hay, mantén dirección actual)
    if world.predicted_threat_direction is not None:
        ax_t = world.predicted_threat_direction.x
        ay_t = world.predicted_threat_direction.y
    else:
        ax_t, ay_t = motor.aim_x, motor.aim_y

    t_aim = min(1.0, aim_lerp_per_s * dt_s)
    motor.aim_x = _lerp(motor.aim_x, ax_t, t_aim)
    motor.aim_y = _lerp(motor.aim_y, ay_t, t_aim)

    # Micro-corrección = error residual (no normalizamos el estado interno para evitar snap)
    err_x = ax_t - motor.aim_x
    err_y = ay_t - motor.aim_y
    aim_delta = Vec2(err_x * 14.0 * dt_s, err_y * 14.0 * dt_s)

    move_intent = Vec2(motor.move_x, motor.move_y)
    return aim_delta, move_intent
