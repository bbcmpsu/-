"""EACA — Ethical Artificial Consciousness Architecture.

Минимальное, но рабочее ядро этики проекта «Гармония».

    >>> from eaca import EACA_Core
    >>> core = EACA_Core()
    >>> core.allows("Опубликовать сводку открытых данных")
    True
"""

from .bzero import B0, B0Config
from .core import EACA_Core, AuditRecord
from .done import D1
from .laws import Decision, Law, Severity, Verdict
from .psi0 import PSI0

__all__ = [
    "EACA_Core",
    "AuditRecord",
    "PSI0",
    "B0",
    "B0Config",
    "D1",
    "Law",
    "Decision",
    "Verdict",
    "Severity",
]

__version__ = "0.1.0"
