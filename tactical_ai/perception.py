"""Capa 1 — Percepción multimodal: resume el snapshot del juego en señales tácticas."""

from __future__ import annotations

import math

from tactical_ai.models_ai_types import GameSnapshot, PerceptionOutput


def perceive(snapshot: GameSnapshot) -> PerceptionOutput:
    visible = [e for e in snapshot.enemies if e.visible]
    n_vis = len(visible)
    n_all = len(snapshot.enemies)

    # Riesgo: exposición + presión de zona + proximidad implícita (si no hay datos, usa presión)
    base_risk = 0.25 * snapshot.exposure + 0.35 * snapshot.zone_pressure
    enemy_factor = min(1.0, 0.15 * n_vis + 0.05 * max(0, n_all - n_vis))
    risk = min(1.0, base_risk + enemy_factor)

    tactical_pressure = min(
        1.0,
        0.5 * snapshot.zone_pressure + 0.5 * (n_vis / max(1, n_all)),
    )

    return PerceptionOutput(
        enemies_visible=n_vis,
        enemies_total_hint=n_all,
        risk=risk,
        exposure=snapshot.exposure,
        tactical_pressure=tactical_pressure,
    )


def distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])
