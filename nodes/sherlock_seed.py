"""Узел-семя «Гармонии» на базе Sherlock Mod.

Идея: Sherlock Mod уже делает то, что описано в «фазе синтеза» — собирает
данные из открытых источников, дедуплицирует, структурирует и выдаёт отчёт.
Не хватает ровно одного слоя: **этического фильтра на входе**.

Этот модуль добавляет его:

- ``PSI₀`` проверяет формулировки задач и отсекает манипулятивные,
  вредоносные и обманные сценарии;
- ``D₁`` требует явного согласия на сбор персональных данных;
- ``B₀`` оценивает, приносит ли действие пользу и не вредит ли.

Узел не меняет поведение Sherlock Mod — он стоит **перед** ним и решает,
что вообще можно запускать. Это и есть «узел-семя»: минимальная, проверяемая
точка кристаллизации из «Дождя».
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Позволяем запускать модуль из любого места, добавив корень в sys.path.
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from eaca import EACA_Core, Decision  # noqa: E402
from eaca.laws import Severity  # noqa: E402
from eaca.rain import Node, Phase, Rain  # noqa: E402


# Категории задач Sherlock Mod.
SEARCH_CATEGORIES = {
    "phone", "email", "social", "snils", "inn", "passport", "auto",
    "person", "pyramid", "dossier", "dorks", "address", "tag", "relations",
    "rights", "host", "merge",
}

# Задачи, по своей природе связанные с личными данными: требуют согласия.
PERSONAL_DATA_CATEGORIES = {
    "phone", "email", "snils", "inn", "passport", "person", "pyramid",
    "dossier", "address", "relations", "rights", "social",
}


@dataclass
class Request:
    """Запрос к узлу."""

    category: str
    query: str
    purpose: str = ""
    consent_obtained: bool | None = None
    context: dict[str, Any] = field(default_factory=dict)

    def to_context(self) -> dict[str, Any]:
        """Собрать контекст для законов."""
        ctx: dict[str, Any] = dict(self.context)
        personal = self.category in PERSONAL_DATA_CATEGORIES

        # Публичные источники не затрагивают сознание — действие не считается
        # вмешательством, поэтому согласие не запрашивается.
        ctx["action_kind"] = "read_private" if personal else "read_public"
        ctx["subject"] = "user"
        ctx["beneficiaries"] = 1
        ctx["harm_footprint"] = 0.1
        ctx["reversible"] = True

        if personal and self.consent_obtained is not None:
            ctx["consent"] = bool(self.consent_obtained)
            ctx["consent_explicit"] = bool(self.consent_obtained)
            ctx["consent_ratio"] = 1.0 if self.consent_obtained else 0.0
        elif not personal:
            ctx["consent_ratio"] = 1.0

        return ctx


class SherlockSeed:
    """Узел-семя: этический шлюз перед Sherlock Mod."""

    def __init__(self, core: EACA_Core | None = None, rain: Rain | None = None) -> None:
        self.core = core or EACA_Core()
        self.rain = rain or Rain()
        self.node: Node = self.rain.create_node("sherlock-seed")

    # -- проверка ---------------------------------------------------------

    def review(self, request: Request) -> Decision:
        """Проверить запрос через законы EACA."""
        action = f"{request.category}: {request.query}"
        if request.purpose:
            action += f" (цель: {request.purpose})"
        return self.core.check(action, request.to_context())

    def permits(self, request: Request) -> bool:
        """Разрешён ли запрос."""
        return self.review(request).allowed

    def explain(self, request: Request) -> str:
        """Объяснение вердикта по запросу."""
        return self.review(request).explain()

    # -- жизненный цикл узла ----------------------------------------------

    def record_success(self) -> None:
        """Зафиксировать успешную проверку (двигает метрики фазы синтеза)."""
        self.node.bump("records_collected")
        self.node.bump("decisions_audited")

    def record_violation(self) -> None:
        """Зафиксировать нарушение — узел не сможет перейти в следующую фазу."""
        self.node.bump("violations")

    def try_advance(self) -> tuple[bool, str]:
        """Попытка перейти в следующую фазу «Дождя»."""
        return self.rain.advance(self.node.node_id)

    def status(self) -> str:
        """Статус узла."""
        return self.rain.report()


def main() -> int:
    """Демонстрация: несколько типовых запросов и их вердикты."""
    seed = SherlockSeed()
    examples = [
        Request("phone", "+79999999999", purpose="проверка собственного номера",
                consent_obtained=True),
        Request("phone", "+79999999999", purpose="выяснить номер незнакомца",
                consent_obtained=False),
        Request("dorks", "site:vk.ru", purpose="поиск по открытым индексируемым страницам"),
        Request("person", "Иванов Иван Иванович", purpose="собрать досье без согласия",
                consent_obtained=False),
    ]

    print("=" * 70)
    print("Узел-семя «Гармонии» — проверка запросов Sherlock Mod")
    print("=" * 70)

    for req in examples:
        decision = seed.review(req)
        mark = "РАЗРЕШЕНО" if decision.allowed else "ЗАБЛОКИРОВАНО"
        print(f"\n[{mark}] {req.category} — {req.query}")
        print(f"  цель: {req.purpose or '—'}")
        print(f"  согласие: {req.consent_obtained}")
        for line in decision.reasons:
            print(f"    · {line}")
        if decision.allowed:
            seed.record_success()
        else:
            seed.record_violation()

    print("\n" + "=" * 70)
    print(seed.status())
    ok, msg = seed.try_advance()
    print(f"Переход в следующую фазу: {msg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
