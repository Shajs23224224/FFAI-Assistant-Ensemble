"""
Paquete principal de Tactical AI para Free Fire.

Este __init__ expone solo símbolos que existen en este repositorio para evitar
romper imports al cargar submódulos como ``tactical_ai.nitro_engine``.
"""

from tactical_ai import personalities
from tactical_ai.models_ai_types import AgentAction, GameSnapshot, PersonalityProfile
from tactical_ai.personalities import get_personality

__all__ = [
    "AgentAction",
    "GameSnapshot",
    "PersonalityProfile",
    "get_personality",
    "personalities",
]
