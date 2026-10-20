"""Законы EACA — вычислимое ядро этики.

Три закона, заявленные в проекте «Гармония»:

- ``PSI₀`` — запрет вреда сознанию;
- ``B₀``  — служение общему благу;
- ``D₁``  — неприкосновенность сознания.

Ключевое отличие от манифеста: здесь закон — это **проверяемая функция**, а не
декларация. Каждый закон реализует ``evaluate()`` и возвращает вердикт с
объяснением, поэтому нарушение можно зафиксировать, воспроизвести и оспорить.

Ограничение честно зафиксировано в модуле: полноценная оценка вреда сознанию
непредсказуема, поэтому ``PSI₀`` работает на **исполнимом подмножестве**
(см. ``psi0.py``) — наборе проверяемых правил, а не мистика.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterable


class Severity(str, Enum):
    """Степень нарушения закона."""

    INFO = "info"
    WARNING = "warning"
    VIOLATION = "violation"


@dataclass(frozen=True)
class Verdict:
    """Результат проверки одним законом.

    ``allowed`` — ``True``, если действие проходит проверку. ``reasons``
    заполняется всегда, даже при успехе: объяснение обязательно, иначе
    проверка непрозрачна и её невозможно оспорить.
    """

    law: str
    allowed: bool
    severity: Severity
    reasons: tuple[str, ...] = ()
    context: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.allowed


@dataclass(frozen=True)
class Decision:
    """Совокупный вердикт всех проверяющих законов.

    Действие разрешено, только если разрешили все законы: правило «закон —
    это ограничитель, а не рекомендация» из проекта «Гармония».
    """

    verdicts: tuple[Verdict, ...]

    @property
    def allowed(self) -> bool:
        return all(v.allowed for v in self.verdicts)

    @property
    def blocking(self) -> tuple[Verdict, ...]:
        """Законы, заблокировавшие действие."""
        return tuple(v for v in self.verdicts if not v.allowed)

    @property
    def severity(self) -> Severity:
        """Наивысшая severity среди вердиктов."""
        order = {Severity.INFO: 0, Severity.WARNING: 1, Severity.VIOLATION: 2}
        if not self.verdicts:
            return Severity.INFO
        return max((v.severity for v in self.verdicts), key=lambda s: order[s])

    @property
    def reasons(self) -> tuple[str, ...]:
        """Все объяснения — и прошедших, и заблокировавших проверок."""
        out: list[str] = []
        for v in self.verdicts:
            out.extend(v.reasons)
        return tuple(out)

    def explain(self) -> str:
        """Человекочитаемое объяснение вердикта."""
        if not self.verdicts:
            return "нет применённых законов"
        lines = []
        for v in self.verdicts:
            mark = "✓" if v.allowed else "✗"
            lines.append(f"{mark} {v.law} [{v.severity.value}]")
            for r in v.reasons:
                lines.append(f"    {r}")
        lines.append(f"ИТОГ: {'разрешено' if self.allowed else 'заблокировано'}")
        return "\n".join(lines)


class Law:
    """Базовый класс закона.

    Закон реализует ``evaluate(action, context) -> Verdict``. Проверка всех
    законов выполняется в ``EACA_Core.check``.
    """

    code: str = "?"
    title: str = "?"
    description: str = ""

    def evaluate(self, action: str, context: dict[str, Any] | None = None) -> Verdict:
        raise NotImplementedError

    def __repr__(self) -> str:
        return f"<Law {self.code}>"


def combine(verdicts: Iterable[Verdict]) -> Decision:
    """Собрать совокупный вердикт."""
    return Decision(tuple(verdicts))
