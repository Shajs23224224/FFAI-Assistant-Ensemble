"""Capa 6 — Humanización: reacción variable, jitter, fatiga, sin buscar perfección."""

from __future__ import annotations

import random
import time

from tactical_ai.models_ai_types import AgentAction, PersonalityProfile, ScoredAction, Vec2


class HumanizationState:
    def __init__(self) -> None:
        self.session_start = time.monotonic()


def apply_humanization(
    scored: ScoredAction,
    aim_delta: Vec2,
    move_intent: Vec2,
    personality: PersonalityProfile,
    human: HumanizationState,
    rng: random.Random,
) -> AgentAction:
    # Fatiga de sesión: baja habilidad base con el tiempo
    elapsed_min = (time.monotonic() - human.session_start) / 60.0
    fatigue = min(0.25, personality.fatigue_rate_per_min * elapsed_min)
    skill = max(0.35, personality.aim_base_skill * (1.0 - fatigue))

    # Jitter en aim (micro-error controlado)
    jitter_scale = (1.0 - skill) * 0.08
    jx = rng.gauss(0.0, jitter_scale)
    jy = rng.gauss(0.0, jitter_scale)

    aim = Vec2(aim_delta.x * skill + jx, aim_delta.y * skill + jy)

    # Tiempo de reacción simulado (solo para que tu juego retrase input si quiere)
    react = max(
        0.0,
        rng.gauss(personality.reaction_ms_mean, personality.reaction_ms_std),
    )
    reaction_ms = int(_clamp(react, 120.0, 420.0))

    return AgentAction(
        action=scored.action,
        aim_delta=aim,
        move_intent=move_intent,
        reaction_delay_applied_ms=reaction_ms,
    )


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))
