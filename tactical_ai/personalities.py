"""Perfiles de personalidad listos para usar (ajusta nombres/valores a tu diseño)."""

from __future__ import annotations

from tactical_ai.models_ai_types import PersonalityProfile


def aggro_pro() -> PersonalityProfile:
    return PersonalityProfile(
        name="aggro_pro",
        aggression=0.85,
        caution=0.35,
        aim_base_skill=0.78,
        reaction_ms_mean=200.0,
        reaction_ms_std=40.0,
        fatigue_rate_per_min=0.04,
    )


def tactico() -> PersonalityProfile:
    return PersonalityProfile(
        name="tactico",
        aggression=0.4,
        caution=0.75,
        aim_base_skill=0.85,
        reaction_ms_mean=250.0,
        reaction_ms_std=50.0,
        fatigue_rate_per_min=0.025,
    )


def sniper() -> PersonalityProfile:
    return PersonalityProfile(
        name="sniper",
        aggression=0.35,
        caution=0.8,
        aim_base_skill=0.9,
        reaction_ms_mean=280.0,
        reaction_ms_std=55.0,
        fatigue_rate_per_min=0.02,
    )


def support() -> PersonalityProfile:
    return PersonalityProfile(
        name="support",
        aggression=0.25,
        caution=0.7,
        aim_base_skill=0.72,
        reaction_ms_mean=260.0,
        reaction_ms_std=48.0,
        fatigue_rate_per_min=0.035,
    )


_REGISTRY: dict[str, PersonalityProfile] = {}


def _register() -> None:
    if _REGISTRY:
        return
    for fn in (aggro_pro, tactico, sniper, support):
        p = fn()
        _REGISTRY[p.name] = p


def get_personality(name: str) -> PersonalityProfile:
    """Devuelve un perfil por nombre (`tactico`, `aggro_pro`, `sniper`, `support`)."""
    _register()
    key = name.strip().lower()
    if key not in _REGISTRY:
        known = ", ".join(sorted(_REGISTRY))
        raise KeyError(f"Perfil desconocido: {name!r}. Conocidos: {known}")
    return _REGISTRY[key]
