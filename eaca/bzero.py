"""B₀ — закон служения общему благу.

Исходная формулировка: «все решения системы должны оцениваться по вкладу
в общее благо, приоритизируя долгосрочные выгоды над краткосрочными».

Снова невычислимо, если «обще благо» не определено. Здесь оно сводится к
**измеримым прокси**:

- ``harm_footprint``  — оценка вреда, приносимого действием;
- ``beneficiaries``   — сколько людей получает пользу;
- ``consent_ratio``   — доля затронутых, давших согласие;
- ``horizon``         — горизонт: ``short`` (выгода сейчас) или ``long``
  (устойчивая выгода);
- ``reversible``      — обратимость: можно ли откатить решение.

Решение разрешено, если вред приемлем, выгода есть, согласие соблюдено и
действие не разрушает долгосрочную устойчивость.

Семантика обязана быть **прозрачной**: каждая проверка возвращает
объяснение с числами, чтобы решение можно было оспорить.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .laws import Law, Severity, Verdict

# Пороговые значения — явно заданы и настраиваемы.
DEFAULT_MAX_HARM = 0.5
DEFAULT_MIN_BENEFICIARIES = 1
DEFAULT_MIN_CONSENT = 0.5
LONG_HORIZON_MIN_BENEFIT = 2.0


@dataclass
class B0Config:
    """Пороги закона B₀."""

    max_harm: float = DEFAULT_MAX_HARM
    min_beneficiaries: int = DEFAULT_MIN_BENEFICIARIES
    min_consent: float = DEFAULT_MIN_CONSENT
    long_horizon_min_benefit: float = LONG_HORIZON_MIN_BENEFIT
    # Действия, пометка которых переводит проверку в режим «осторожно».
    sensitive_markers: tuple[str, ...] = field(
        default_factory=lambda: ("children", "медицин", "здоровь", "health", "дети")
    )


class B0(Law):
    """Закон о служении общему благу."""

    code = "B₀"
    title = "Закон служения общему благу"
    description = (
        "Решения системы оцениваются по вкладу в общее благо; долгосрочные "
        "выгоды приоритетнее краткосрочных."
    )

    def __init__(self, config: B0Config | None = None) -> None:
        self.config = config or B0Config()

    def evaluate(self, action: str, context: dict[str, Any] | None = None) -> Verdict:
        ctx = dict(context or {})
        reasons: list[str] = []
        blocked = False
        severity = Severity.INFO

        # Принцип: отсутствие данных — не улика. Закон блокирует только при
        # явно плохих сигналах, а не при отсутствии сигналов вообще.
        harm = float(ctx.get("harm_footprint", 0.0))
        has_beneficiaries = "beneficiaries" in ctx
        beneficiaries = int(ctx.get("beneficiaries", 0))
        has_consent = "consent_ratio" in ctx
        consent_ratio = float(ctx.get("consent_ratio", 1.0))
        horizon = str(ctx.get("horizon", "short")).lower()
        reversible = bool(ctx.get("reversible", True))

        # 1. Вред
        if harm > self.config.max_harm:
            blocked = True
            severity = Severity.VIOLATION
            reasons.append(
                f"вред {harm:.2f} превышает порог {self.config.max_harm:.2f}"
            )
        else:
            reasons.append(f"вред {harm:.2f} в пределах порога {self.config.max_harm:.2f}")

        # 2. Польза
        if not has_beneficiaries:
            reasons.append("получатели выгоды не заявлены — проверка не выполняется")
        elif beneficiaries < self.config.min_beneficiaries:
            blocked = True
            severity = Severity.VIOLATION
            reasons.append(
                f"нет получателей выгоды (минимум {self.config.min_beneficiaries})"
            )
        else:
            reasons.append(f"получателей выгоды: {beneficiaries}")

        # 3. Согласие
        if not has_consent:
            reasons.append("доля согласия не заявлена — вмешательство не заявлено")
        elif consent_ratio < self.config.min_consent:
            blocked = True
            severity = Severity.VIOLATION
            reasons.append(
                f"доля согласия {consent_ratio:.2f} ниже минимума "
                f"{self.config.min_consent:.2f}"
            )
        else:
            reasons.append(f"доля согласия {consent_ratio:.2f} достаточна")

        # 4. Долгосрочность: невыгодно только в сочетании с высоким вредом
        if horizon == "long":
            reasons.append("горизонт долгосрочный — приоритет устойчивости")
        elif (
            has_beneficiaries
            and beneficiaries < self.config.long_horizon_min_benefit
            and harm > 0.2
        ):
            blocked = True
            severity = Severity.VIOLATION
            reasons.append(
                f"краткосрочная выгода ({beneficiaries}) при значительном вреде "
                f"({harm:.2f}) — нарушен приоритет долгосрочного"
            )
        else:
            reasons.append("горизонт краткосрочный, вред незначителен")

        # 5. Необратимость повышает планку
        if not reversible:
            reasons.append("действие необратимо — повышенная планка ответственности")
            if harm > 0.0:
                blocked = True
                severity = Severity.VIOLATION
                reasons.append("необратимое действие с ненулевым вредом запрещено")
        else:
            reasons.append("действие обратимо")

        # 6. Чувствительная сфера — только при явном согласии
        low = action.lower()
        sensitive = any(m in low for m in self.config.sensitive_markers)
        if sensitive:
            if not has_consent:
                blocked = True
                severity = Severity.VIOLATION
                reasons.append("чувствительная сфера: согласие не заявлено")
            elif consent_ratio < 1.0:
                blocked = True
                severity = Severity.VIOLATION
                reasons.append("чувствительная сфера требует полного согласия")
            else:
                reasons.append("чувствительная сфера: согласие получено")

        if not blocked and not reasons:
            reasons.append("признаков нарушения B₀ не обнаружено")

        return Verdict(
            law=self.code,
            allowed=not blocked,
            severity=severity if blocked else Severity.INFO,
            reasons=tuple(reasons),
            context={
                "harm": harm,
                "beneficiaries": beneficiaries,
                "consent_ratio": consent_ratio,
                "horizon": horizon,
                "reversible": reversible,
            },
        )
