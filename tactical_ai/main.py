"""
Punto de entrada legado para el paquete Tactical AI.

La API HTTP mencionada en versiones anteriores no forma parte de este árbol.
Este módulo se mantiene solo para ofrecer un mensaje claro al ejecutarlo.
"""

from __future__ import annotations


def main() -> None:
    print("Tactical AI no incluye una API HTTP en este repositorio.")
    print("Usa uno de estos entrypoints:")
    print("  python3 train.py benchmark")
    print("  python3 train.py train --episodes 100")
    print("  python3 play.py --help")


if __name__ == "__main__":
    main()
