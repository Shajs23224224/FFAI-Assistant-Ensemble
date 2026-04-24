"""Capa 3 — Decisión híbrida: reglas + utilidad + ajuste adaptativo ligero."""

from __future__ import annotations

from tactical_ai.models_ai_types import (
    ActionType,
    AdaptationState,
    GameSnapshot,
    PerceptionOutput,
    PersonalityProfile,
    ScoredAction,
    WorldState,
)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _rules_gate(snapshot: GameSnapshot, perception: PerceptionOutput) -> ActionType | None:
    """Reglas duras antes de utilidad."""
    hp_ratio = snapshot.player_hp / max(1e-6, snapshot.player_hp_max)
    heal_cd = snapshot.cooldowns_ms.get("heal", 0)

    if hp_ratio < 0.35 and heal_cd <= 0:
        return ActionType.HEAL

    if perception.risk > 0.75 and perception.exposure > 0.6:
        return ActionType.MOVE_TO_COVER

    return None


def utility_scores(
    snapshot: GameSnapshot,
    perception: PerceptionOutput,
    world: WorldState,
    personality: PersonalityProfile,
    adaptation: AdaptationState,
) -> dict[ActionType, float]:
    hp_ratio = snapshot.player_hp / max(1e-6, snapshot.player_hp_max)
    can_heal = snapshot.cooldowns_ms.get("heal", 0) <= 0 and hp_ratio < 0.9

    # Pesos modulados por personalidad y estilo aprendido del enemigo (EMA)
    agg = _clamp(personality.aggression * (0.8 + 0.4 * adaptation.aggression_ema), 0.0, 1.5)
    caut = _clamp(personality.caution * (1.1 - 0.3 * adaptation.aggression_ema), 0.0, 1.5)

    scores: dict[ActionType, float] = {
        ActionType.SHOOT: 0.4
        + 0.35 * agg
        + 0.2 * (1.0 - perception.risk * caut)
        + 0.1 * (1.0 if perception.enemies_visible > 0 else 0.0),
        ActionType.ROTATE: 0.35
        + 0.25 * perception.tactical_pressure
        + 0.15 * world.safe_score_map_hint,
        ActionType.HEAL: 0.85 * (1.0 - hp_ratio) if can_heal else 0.0,
        ActionType.MOVE_TO_COVER: 0.5 + 0.45 * perception.exposure * caut + 0.2 * perception.risk,
        ActionType.HOLD: 0.25 + 0.3 * caut * perception.risk,
    }

    if snapshot.ammo <= 0:
        scores[ActionType.SHOOT] = 0.0

    return scores


def decide(
    snapshot: GameSnapshot,
    perception: PerceptionOutput,
    world: WorldState,
    personality: PersonalityProfile,
    adaptation: AdaptationState,
) -> ScoredAction:
    forced = _rules_gate(snapshot, perception)
    raw = utility_scores(snapshot, perception, world, personality, adaptation)

    if forced is not None:
        return ScoredAction(action=forced, utility=1.0, raw_scores={k.name: raw[k] for k in raw})

    best = max(raw.items(), key=lambda kv: kv[1])
    action, u = best[0], best[1]
    return ScoredAction(action=action, utility=u, raw_scores={k.name: raw[k] for k in raw})
