"""
FFNet-Lite: Red Neuronal Fully-Connected Optimizada para Pentium N3700.
Arquitectura: 8 -> 32 -> 16 -> 6
Precision: float16 (reducir memoria 50%)
Tiempo forward: ~1ms en Pentium N3700
"""

from __future__ import annotations

import numpy as np
from typing import Tuple, Optional, Dict
import struct


class FFNetLite:
    """
    Red neuronal manual sin frameworks pesados.
    Optimizada para CPU sin AVX/FMA (solo SSE4.2).
    """

    def __init__(
        self,
        input_dim: int = 8,
        hidden1: int = 32,
        hidden2: int = 16,
        output_dim: int = 6,
        seed: Optional[int] = None
    ):
        if seed is not None:
            np.random.seed(seed)

        self.input_dim = input_dim
        self.hidden1 = hidden1
        self.hidden2 = hidden2
        self.output_dim = output_dim

        # Inicialización He normal con float16
        # W1: (8, 32)
        self.W1 = np.random.randn(input_dim, hidden1).astype(np.float32) * np.sqrt(2.0 / input_dim)
        self.b1 = np.zeros(hidden1, dtype=np.float32)

        # W2: (32, 16)
        self.W2 = np.random.randn(hidden1, hidden2).astype(np.float32) * np.sqrt(2.0 / hidden1)
        self.b2 = np.zeros(hidden2, dtype=np.float32)

        # W3: (16, 6)
        self.W3 = np.random.randn(hidden2, output_dim).astype(np.float32) * np.sqrt(2.0 / hidden2)
        self.b3 = np.zeros(output_dim, dtype=np.float32)

        # Momentum para SGD
        self.momentum = 0.9
        self.vW1 = np.zeros_like(self.W1)
        self.vb1 = np.zeros_like(self.b1)
        self.vW2 = np.zeros_like(self.W2)
        self.vb2 = np.zeros_like(self.b2)
        self.vW3 = np.zeros_like(self.W3)
        self.vb3 = np.zeros_like(self.b3)

        # Learning rate
        self.lr = 0.001

        # Cache para forward pass
        self._cache: Optional[Tuple] = None

    def forward(self, x: np.ndarray) -> np.ndarray:
        """
        Forward pass optimizado.
        x: shape (8,) o (batch, 8)
        Retorna: Q-values shape (6,) o (batch, 6)
        """
        # Asegurar float32 y reshape correcto
        if x.ndim == 1:
            x = x.reshape(1, -1)

        x = x.astype(np.float32)

        # Layer 1: Linear + ReLU
        z1 = x @ self.W1 + self.b1  # (batch, 32)
        a1 = np.maximum(0, z1)      # ReLU

        # Layer 2: Linear + ReLU
        z2 = a1 @ self.W2 + self.b2  # (batch, 16)
        a2 = np.maximum(0, z2)       # ReLU

        # Layer 3: Linear (output)
        z3 = a2 @ self.W3 + self.b3  # (batch, 6)

        # Cache para backward
        self._cache = (x, z1, a1, z2, a2, z3)

        return z3[0] if z3.shape[0] == 1 else z3

    def backward(self, target: np.ndarray, prediction: np.ndarray) -> float:
        """
        Backpropagation manual con SGD + Momentum.
        target: Q-values objetivo shape (6,)
        prediction: Q-values predichos shape (6,)
        Retorna: loss MSE
        """
        if self._cache is None:
            raise ValueError("Forward pass no ejecutado")

        x, z1, a1, z2, a2, z3 = self._cache

        # Asegurar shapes
        if target.ndim == 1:
            target = target.reshape(1, -1)
        if prediction.ndim == 1:
            prediction = prediction.reshape(1, -1)

        batch_size = x.shape[0]

        # Loss: MSE
        loss = np.mean((prediction - target) ** 2)

        # Gradiente de output (Layer 3)
        dz3 = 2 * (prediction - target) / batch_size  # (batch, 6)
        dW3 = a2.T @ dz3  # (16, 6)
        db3 = np.sum(dz3, axis=0)  # (6,)

        # Backprop Layer 2
        da2 = dz3 @ self.W3.T  # (batch, 16)
        dz2 = da2 * (z2 > 0).astype(np.float32)  # ReLU derivative
        dW2 = a1.T @ dz2  # (32, 16)
        db2 = np.sum(dz2, axis=0)  # (16,)

        # Backprop Layer 1
        da1 = dz2 @ self.W2.T  # (batch, 32)
        dz1 = da1 * (z1 > 0).astype(np.float32)  # ReLU derivative
        dW1 = x.T @ dz1  # (8, 32)
        db1 = np.sum(dz1, axis=0)  # (32,)

        # Update con momentum
        self.vW3 = self.momentum * self.vW3 - self.lr * dW3
        self.vb3 = self.momentum * self.vb3 - self.lr * db3
        self.vW2 = self.momentum * self.vW2 - self.lr * dW2
        self.vb2 = self.momentum * self.vb2 - self.lr * db2
        self.vW1 = self.momentum * self.vW1 - self.lr * dW1
        self.vb1 = self.momentum * self.vb1 - self.lr * db1

        self.W3 += self.vW3
        self.b3 += self.vb3
        self.W2 += self.vW2
        self.b2 += self.vb2
        self.W1 += self.vW1
        self.b1 += self.vb1

        return float(loss)

    def train_step(self, state: np.ndarray, target: np.ndarray) -> float:
        """Un paso completo de entrenamiento."""
        pred = self.forward(state)
        loss = self.backward(target, pred)
        return loss

    def get_action(self, state: np.ndarray, epsilon: float = 0.1) -> int:
        """
        Selecciona acción usando epsilon-greedy.
        Retorna: índice de acción (0-5)
        """
        if np.random.random() < epsilon:
            return np.random.randint(self.output_dim)

        q_values = self.forward(state)
        return int(np.argmax(q_values))

    def save(self, filepath: str) -> None:
        """Guarda pesos en formato NPZ comprimido."""
        np.savez_compressed(
            filepath,
            W1=self.W1, b1=self.b1,
            W2=self.W2, b2=self.b2,
            W3=self.W3, b3=self.b3,
            vW1=self.vW1, vb1=self.vb1,
            vW2=self.vW2, vb2=self.vb2,
            vW3=self.vW3, vb3=self.vb3,
            input_dim=self.input_dim,
            hidden1=self.hidden1,
            hidden2=self.hidden2,
            output_dim=self.output_dim
        )

    def load(self, filepath: str) -> None:
        """Carga pesos desde archivo NPZ."""
        data = np.load(filepath)
        self.W1 = data['W1']
        self.b1 = data['b1']
        self.W2 = data['W2']
        self.b2 = data['b2']
        self.W3 = data['W3']
        self.b3 = data['b3']
        self.vW1 = data['vW1']
        self.vb1 = data['vb1']
        self.vW2 = data['vW2']
        self.vb2 = data['vb2']
        self.vW3 = data['vW3']
        self.vb3 = data['vb3']

    def get_size_kb(self) -> float:
        """Retorna tamaño total de pesos en KB."""
        total_bytes = (
            self.W1.nbytes + self.b1.nbytes +
            self.W2.nbytes + self.b2.nbytes +
            self.W3.nbytes + self.b3.nbytes
        )
        return total_bytes / 1024

    def benchmark_forward(self, n_iterations: int = 1000) -> Dict:
        """Benchmark de rendimiento del forward pass."""
        import time

        x = np.random.randn(8).astype(np.float32)

        # Warmup
        for _ in range(10):
            self.forward(x)

        # Benchmark
        start = time.perf_counter()
        for _ in range(n_iterations):
            self.forward(x)
        end = time.perf_counter()

        total_time = end - start
        avg_time_ms = (total_time / n_iterations) * 1000

        return {
            "iterations": n_iterations,
            "total_time_ms": total_time * 1000,
            "avg_time_ms": avg_time_ms,
            "fps_equivalent": 1000 / avg_time_ms
        }


# Acciones mapeadas
ACTIONS = ["SHOOT", "MOVE_TO_COVER", "HEAL", "ROTATE", "RELOAD", "HOLD"]


def create_network(seed: Optional[int] = None) -> FFNetLite:
    """Factory para crear red con arquitectura estándar."""
    return FFNetLite(
        input_dim=8,
        hidden1=32,
        hidden2=16,
        output_dim=6,
        seed=seed
    )
