from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Sequence


class ActionType(Enum):
    SHOOT = auto()
    ROTATE = auto()
    HEAL = auto()
    MOVE_TO_COVER = auto()
    HOLD = auto()


@dataclass(frozen=True)
class Vec2:
    x: float
    y: float


@dataclass
class EnemyObservation:
    """Lo que el juego entrega al módulo de percepción (sin suponer trucos de multijugador)."""

    id: str
    position: Vec2
    visible: bool
    in_cover_estimate: float  # 0..1 confianza


@dataclass
class GameSnapshot:
    """Un frame de estado que tu motor debe rellenar cada tick o cada N ms."""

    tick_ms: int
    player_hp: float
    player_hp_max: float
    ammo: int
    cooldowns_ms: dict[str, int]  # ej. "heal": 12000
    player_position: Vec2
    exposure: float  # 0 cubierto, 1 muy expuesto
    zone_pressure: float  # 0 tranquilo, 1 mucha presión
    enemies: Sequence[EnemyObservation]


@dataclass
class PerceptionOutput:
    enemies_visible: int
    enemies_total_hint: int
    risk: float  # 0..1
    exposure: float
    tactical_pressure: float


@dataclass
class BeliefEnemy:
    enemy_id: str
    last_seen_pos: Vec2
    last_seen_tick: int
    in_cover_probability: float  # 0..1
    position_uncertainty: float  # radio aproximado de error


@dataclass
class WorldState:
    beliefs: list[BeliefEnemy]
    safe_score_map_hint: float  # -1 muy peligroso, +1 relativamente seguro (proxy simple)
    predicted_threat_direction: Vec2 | None


@dataclass
class ScoredAction:
    action: ActionType
    utility: float
    raw_scores: dict[str, float] = field(default_factory=dict)


@dataclass
class AgentAction:
    """Salida hacia tu motor: qué hacer este frame (después de humanización)."""

    action: ActionType
    aim_delta: Vec2  # ajuste suavizado / micro-corrección
    move_intent: Vec2  # dirección normalizada o cero
    reaction_delay_applied_ms: int


@dataclass(frozen=True)
class PersonalityProfile:
    """Perfil agresivo / táctico / etc.: modifica pesos de utilidad y humanización."""

    name: str
    aggression: float  # 0..1
    caution: float  # 0..1
    aim_base_skill: float  # 0..1
    reaction_ms_mean: float
    reaction_ms_std: float
    fatigue_rate_per_min: float  # cuánto baja el rendimiento en sesiones largas


class AdaptationState:
    """Estado mutable del oponente estilo (solo lectura desde tu juego)."""

    def __init__(self) -> None:
        self.aggression_ema: float = 0.5
        self.peek_rate_ema: float = 0.0
        self.last_update_tick: int = 0
