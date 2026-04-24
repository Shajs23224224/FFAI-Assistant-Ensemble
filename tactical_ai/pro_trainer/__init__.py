"""Sistema de entrenamiento E-Sports."""

from .self_play import SelfPlayArena, EpisodeResult, AgentConfig
from .reward_shaper import EsportsRewardShaper, RewardConfig, EsportsBehavior

__all__ = [
    "SelfPlayArena",
    "EpisodeResult", 
    "AgentConfig",
    "EsportsRewardShaper",
    "RewardConfig",
    "EsportsBehavior",
]
