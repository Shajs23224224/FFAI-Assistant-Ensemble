"""
SQLite Optimizado para persistencia de modelos y métricas.
WAL mode para escrituras concurrentes, índices para queries rápidas.
"""

from __future__ import annotations

import sqlite3
import json
import time
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from contextlib import contextmanager
from dataclasses import dataclass
import numpy as np


DEFAULT_DB_PATH = Path(__file__).parent.parent.parent / "freefire_ai.db"


@dataclass
class ModelCheckpoint:
    """Checkpoint de modelo."""
    checkpoint_id: int
    agent_id: int
    episode: int
    timestamp: float
    weights_compressed: bytes
    metadata: Dict[str, Any]


class SQLiteMemory:
    """
    Gestor de persistencia SQLite optimizado.
    - WAL mode para concurrencia
    - Compresión de pesos
    - Batch inserts
    """

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._ensure_db()

    @contextmanager
    def _get_connection(self):
        """Context manager con WAL mode."""
        conn = sqlite3.connect(str(self.db_path), timeout=10, isolation_level=None)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.row_factory = sqlite3.Row

        try:
            yield conn
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _ensure_db(self) -> None:
        """Inicializa esquema si no existe."""
        if not self.db_path.exists():
            self._init_schema()

    def _init_schema(self) -> None:
        """Crea tablas e índices."""
        with self._get_connection() as conn:
            # Checkpoints de modelos (pesos comprimidos)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS model_checkpoints (
                    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id INTEGER NOT NULL,
                    episode INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    weights BLOB NOT NULL,  -- Comprimidos
                    metadata TEXT,  -- JSON
                    performance_score REAL DEFAULT 0.0
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_checkpoints_agent
                ON model_checkpoints(agent_id, episode)
            """)

            # Episodios de entrenamiento
            conn.execute("""
                CREATE TABLE IF NOT EXISTS training_episodes (
                    episode_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_id INTEGER NOT NULL,
                    start_time REAL NOT NULL,
                    end_time REAL,
                    total_reward REAL DEFAULT 0.0,
                    steps INTEGER DEFAULT 0,
                    survived BOOLEAN DEFAULT 0,
                    kills INTEGER DEFAULT 0,
                    esports_score REAL DEFAULT 0.0,  -- Métrica E-Sports
                    curriculum_phase INTEGER DEFAULT 0
                )
            """)

            # Métricas E-Sports
            conn.execute("""
                CREATE TABLE IF NOT EXISTS esports_metrics (
                    metric_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id INTEGER,
                    flick_shots INTEGER DEFAULT 0,
                    pre_aims INTEGER DEFAULT 0,
                    strafes INTEGER DEFAULT 0,
                    peek_shots INTEGER DEFAULT 0,
                    combos INTEGER DEFAULT 0,
                    FOREIGN KEY (episode_id) REFERENCES training_episodes(episode_id)
                )
            """)

            # Performance por hora (para gráficos)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS performance_hourly (
                    hour INTEGER PRIMARY KEY,  -- Unix timestamp truncado a hora
                    episodes_count INTEGER DEFAULT 0,
                    avg_reward REAL DEFAULT 0.0,
                    avg_kills REAL DEFAULT 0.0,
                    best_agent_id INTEGER,
                    best_score REAL DEFAULT 0.0
                )
            """)

            # Configuración
            conn.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    updated_at REAL DEFAULT 0.0
                )
            """)

            conn.execute("""
                INSERT INTO config (key, value, updated_at)
                VALUES ('schema_version', '2.0', ?)
            """, (time.time(),))

        print(f"[+] Base de datos inicializada: {self.db_path}")

    def save_checkpoint(
        self,
        agent_id: int,
        episode: int,
        weights: Dict[str, np.ndarray],
        metadata: Dict[str, Any] = None,
        performance_score: float = 0.0
    ) -> int:
        """
        Guarda checkpoint con pesos comprimidos.
        Retorna checkpoint_id.
        """
        # Serializar y comprimir pesos
        weights_dict = {k: v.tobytes() for k, v in weights.items()}
        weights_json = json.dumps(weights_dict, default=str)
        weights_compressed = zlib.compress(weights_json.encode(), level=6)

        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO model_checkpoints
                (agent_id, episode, timestamp, weights, metadata, performance_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                agent_id, episode, time.time(),
                weights_compressed,
                json.dumps(metadata) if metadata else None,
                performance_score
            ))

            return cursor.lastrowid

    def load_checkpoint(self, checkpoint_id: int) -> Optional[Dict[str, np.ndarray]]:
        """Carga checkpoint y descomprime pesos."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT weights FROM model_checkpoints WHERE checkpoint_id = ?",
                (checkpoint_id,)
            )
            row = cursor.fetchone()

            if not row:
                return None

            # Descomprimir
            weights_compressed = row['weights']
            weights_json = zlib.decompress(weights_compressed).decode()
            weights_dict = json.loads(weights_json)

            # Reconstruir arrays
            weights = {}
            for k, v in weights_dict.items():
                if 'W' in k or 'b' in k:  # Pesos de la red
                    # Inferir shape desde el tipo
                    if k in ['W1']:
                        shape = (8, 32)
                    elif k in ['b1']:
                        shape = (32,)
                    elif k in ['W2']:
                        shape = (32, 16)
                    elif k in ['b2']:
                        shape = (16,)
                    elif k in ['W3']:
                        shape = (16, 6)
                    elif k in ['b3']:
                        shape = (6,)
                    elif k.startswith('v'):  # Momentum
                        continue  # Opcional
                    else:
                        continue

                    arr = np.frombuffer(bytes.fromhex(v) if isinstance(v, str) else v, dtype=np.float32)
                    weights[k] = arr.reshape(shape)

            return weights

    def get_best_checkpoint(self, agent_id: Optional[int] = None) -> Optional[int]:
        """Retorna ID del mejor checkpoint."""
        with self._get_connection() as conn:
            if agent_id is not None:
                cursor = conn.execute(
                    "SELECT checkpoint_id FROM model_checkpoints "
                    "WHERE agent_id = ? ORDER BY performance_score DESC LIMIT 1",
                    (agent_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT checkpoint_id FROM model_checkpoints "
                    "ORDER BY performance_score DESC LIMIT 1"
                )

            row = cursor.fetchone()
            return row['checkpoint_id'] if row else None

    def log_episode(
        self,
        agent_id: int,
        total_reward: float,
        steps: int,
        survived: bool,
        kills: int,
        esports_score: float = 0.0,
        curriculum_phase: int = 0
    ) -> int:
        """Registra episodio de entrenamiento."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO training_episodes
                (agent_id, start_time, end_time, total_reward, steps,
                 survived, kills, esports_score, curriculum_phase)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                agent_id, time.time() - steps * 0.1, time.time(),
                total_reward, steps, survived, kills,
                esports_score, curriculum_phase
            ))

            return cursor.lastrowid

    def log_esports_metrics(
        self,
        episode_id: int,
        flick_shots: int = 0,
        pre_aims: int = 0,
        strafes: int = 0,
        peek_shots: int = 0,
        combos: int = 0
    ) -> None:
        """Registra métricas E-Sports del episodio."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO esports_metrics
                (episode_id, flick_shots, pre_aims, strafes, peek_shots, combos)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (episode_id, flick_shots, pre_aims, strafes, peek_shots, combos))

    def update_hourly_stats(
        self,
        agent_id: int,
        reward: float,
        kills: int,
        score: float
    ) -> None:
        """Actualiza estadísticas agregadas por hora."""
        hour = int(time.time() // 3600) * 3600

        with self._get_connection() as conn:
            # Verificar si existe
            cursor = conn.execute(
                "SELECT * FROM performance_hourly WHERE hour = ?",
                (hour,)
            )
            row = cursor.fetchone()

            if row:
                # Actualizar
                new_count = row['episodes_count'] + 1
                new_avg_reward = (row['avg_reward'] * row['episodes_count'] + reward) / new_count
                new_avg_kills = (row['avg_kills'] * row['episodes_count'] + kills) / new_count

                best_score = max(row['best_score'], score)
                best_agent = agent_id if score > row['best_score'] else row['best_agent_id']

                conn.execute("""
                    UPDATE performance_hourly SET
                        episodes_count = ?,
                        avg_reward = ?,
                        avg_kills = ?,
                        best_agent_id = ?,
                        best_score = ?
                    WHERE hour = ?
                """, (new_count, new_avg_reward, new_avg_kills, best_agent, best_score, hour))
            else:
                # Insertar nuevo
                conn.execute("""
                    INSERT INTO performance_hourly
                    (hour, episodes_count, avg_reward, avg_kills, best_agent_id, best_score)
                    VALUES (?, 1, ?, ?, ?, ?)
                """, (hour, reward, kills, agent_id, score))

    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas generales."""
        with self._get_connection() as conn:
            # Episodios totales
            cursor = conn.execute("SELECT COUNT(*) FROM training_episodes")
            total_episodes = cursor.fetchone()[0]

            # Promedios
            cursor = conn.execute("""
                SELECT AVG(total_reward), AVG(kills), AVG(esports_score),
                       SUM(CASE WHEN survived THEN 1 ELSE 0 END)
                FROM training_episodes
            """)
            row = cursor.fetchone()

            # Checkpoints
            cursor = conn.execute("SELECT COUNT(DISTINCT agent_id) FROM model_checkpoints")
            num_agents = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM model_checkpoints")
            num_checkpoints = cursor.fetchone()[0]

            return {
                "total_episodes": total_episodes,
                "avg_reward": round(row[0] or 0, 2),
                "avg_kills": round(row[1] or 0, 2),
                "avg_esports_score": round(row[2] or 0, 2),
                "survival_rate": round((row[3] or 0) / max(total_episodes, 1) * 100, 1),
                "num_agents": num_agents,
                "num_checkpoints": num_checkpoints,
            }

    def get_training_history(self, hours: int = 24) -> List[Dict]:
        """Retorna historial de entrenamiento últimas N horas."""
        cutoff = int(time.time() - hours * 3600)

        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM performance_hourly
                WHERE hour > ?
                ORDER BY hour
            """, (cutoff,))

            return [dict(row) for row in cursor.fetchall()]

    def cleanup_old_checkpoints(self, keep_per_agent: int = 5) -> int:
        """Elimina checkpoints antiguos, manteniendo los mejores N por agente."""
        with self._get_connection() as conn:
            # Obtener todos los agentes
            cursor = conn.execute(
                "SELECT DISTINCT agent_id FROM model_checkpoints"
            )
            agents = [row[0] for row in cursor.fetchall()]

            deleted = 0
            for agent_id in agents:
                # Obtener IDs a mantener (mejores por performance)
                cursor = conn.execute(
                    "SELECT checkpoint_id FROM model_checkpoints "
                    "WHERE agent_id = ? ORDER BY performance_score DESC LIMIT ?",
                    (agent_id, keep_per_agent)
                )
                keep_ids = [row[0] for row in cursor.fetchall()]

                if keep_ids:
                    # Eliminar resto
                    placeholders = ','.join('?' * len(keep_ids))
                    cursor = conn.execute(f"""
                        DELETE FROM model_checkpoints
                        WHERE agent_id = ? AND checkpoint_id NOT IN ({placeholders})
                    """, (agent_id, *keep_ids))
                    deleted += cursor.rowcount

            return deleted

    def vacuum(self) -> None:
        """Compacta base de datos."""
        with self._get_connection() as conn:
            conn.execute("VACUUM")


# Instancia global
_global_memory: Optional[SQLiteMemory] = None


def get_memory(db_path: Optional[Path] = None) -> SQLiteMemory:
    """Obtiene instancia global."""
    global _global_memory
    if _global_memory is None:
        _global_memory = SQLiteMemory(db_path)
    return _global_memory


def init_db(db_path: Optional[Path] = None) -> None:
    """Inicializa base de datos."""
    SQLiteMemory(db_path)
    print("[+] Base de datos lista")
