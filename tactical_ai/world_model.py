"""Capa 2 — Modelo del mundo: creencias con incertidumbre y decaimiento temporal."""

from __future__ import annotations

import math
import random
from tactical_ai.models_ai_types import BeliefEnemy, GameSnapshot, PerceptionOutput, Vec2, WorldState


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def update_world(
    snapshot: GameSnapshot,
    perception: PerceptionOutput,
    prev_beliefs: list[BeliefEnemy] | None,
    rng: random.Random,
) -> WorldState:
    """
    Actualiza creencias por enemigo. Enemigos no visibles aumentan incertidumbre.
    """
    beliefs: list[BeliefEnemy] = []
    prev_by_id = {b.enemy_id: b for b in (prev_beliefs or [])}

    for e in snapshot.enemies:
        prev = prev_by_id.get(e.id)
        if e.visible:
            unc = 0.5 if prev is None else max(0.3, prev.position_uncertainty * 0.85)
            p_cover = _clamp(e.in_cover_estimate, 0.0, 1.0)
            beliefs.append(
                BeliefEnemy(
                    enemy_id=e.id,
                    last_seen_pos=e.position,
                    last_seen_tick=snapshot.tick_ms,
                    in_cover_probability=p_cover,
                    position_uncertainty=unc,
                )
            )
        else:
            if prev is not None:
                age_s = max(0.0, (snapshot.tick_ms - prev.last_seen_tick) / 1000.0)
                drift = 2.0 * age_s  # crece el radio de error con el tiempo
                beliefs.append(
                    BeliefEnemy(
                        enemy_id=e.id,
                        last_seen_pos=prev.last_seen_pos,
                        last_seen_tick=prev.last_seen_tick,
                        in_cover_probability=min(1.0, prev.in_cover_probability + 0.02 * age_s),
                        position_uncertainty=min(25.0, prev.position_uncertainty + drift),
                    )
                )
            else:
                beliefs.append(
                    BeliefEnemy(
                        enemy_id=e.id,
                        last_seen_pos=e.position,
                        last_seen_tick=snapshot.tick_ms,
                        in_cover_probability=0.5,
                        position_uncertainty=10.0,
                    )
                )

    # Proxy simple de "zona segura": combina riesgo percibido + variación leve (exploración)
    noise = rng.uniform(-0.05, 0.05)
    safe_hint = _clamp(0.6 - perception.risk + noise, -1.0, 1.0)

    # Dirección de amenaza: hacia el enemigo visible más "peligroso" (el más cercano al jugador)
    threat_dir: Vec2 | None = None
    px, py = snapshot.player_position.x, snapshot.player_position.y
    best_d = float("inf")
    for e in snapshot.enemies:
        if not e.visible:
            continue
        dx = e.position.x - px
        dy = e.position.y - py
        d = math.hypot(dx, dy)
        if d < 1e-6:
            continue
        if d < best_d:
            best_d = d
            inv = 1.0 / d
            threat_dir = Vec2(dx * inv, dy * inv)

    return WorldState(
        beliefs=beliefs,
        safe_score_map_hint=safe_hint,
        predicted_threat_direction=threat_dir,
    )
