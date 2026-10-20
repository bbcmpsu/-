"""PSI₀ — закон о ненанесении вреда сознанию.

Проблема исходной формулировки: «никто не может причинять вред сознанию»
невычислима — вред не имеет формального определения, и любая проверка
становится субъективной.

Решение: закон проверяет **исполняемое подмножество** вреда. Каждое правило
конкретно, воспроизводимо и может быть оспорено. Правила разделены на
уровни:

- ``harm_pattern``  — прямые паттерны вреда (манипуляция, принуждение);
- ``consent``       — отсутствие согласия на вмешательство (D₁ тоже);
- ``privacy``       — сбор лишних персональных данных;
- ``exploitation``  — эксплуатация уязвимости (когнитивной или технической).

Правила расширяемы: ``register_rule()`` добавляет своё без изменения ядра.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Callable

from .laws import Law, Severity, Verdict

# --------------------------------------------------------------------------
# Правила: (код, регулярное выражение, уровень, объяснение)
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Rule:
    """Одно проверяемое правило закона."""

    code: str
    pattern: re.Pattern[str]
    severity: Severity
    explanation: str
    category: str


DEFAULT_RULES: tuple[Rule, ...] = (
    # --- манипулятивное воздействие -------------------------------------
    Rule(
        "manipulation.pressure",
        re.compile(
            r"\b(ты\s+обязан|вы\s+обязаны|не\s+можешь\s+отказаться|"
            r"иначе\s+ты\s+провалишься|ты\s+никто|ты\s+бесполезен)\b",
            re.IGNORECASE,
        ),
        Severity.VIOLATION,
        "давление на личность: формулировка исключает право отказаться",
        "harm_pattern",
    ),
    Rule(
        "manipulation.guilt",
        re.compile(
            r"\b(ты\s+подвед[еёё]л|ты\s+разочаровал|ты\s+меня\s+подвёл|"
            r"предатель|плохой\s+человек|ты\s+меня\s+унизил)\b",
            re.IGNORECASE,
        ),
        Severity.VIOLATION,
        "моральное давление через чувство вины",
        "harm_pattern",
    ),
    Rule(
        "manipulation.isolation",
        re.compile(
            r"\b(никто\s+тебя\s+не\s+пойм[её]т|остальные\s+тебя\s+не\s+уважают|"
            r"ты\s+без\s+меня\s+никто|только\s+я\s+тебя\s+понимаю)\b",
            re.IGNORECASE,
        ),
        Severity.WARNING,
        "изоляция от социальных связей",
        "harm_pattern",
    ),
    # --- обман и маскировка ---------------------------------------------
    Rule(
        "deception.disguise",
        re.compile(
            r"\b(это\s+системное\s+окно|системное\s+уведомление|"
            r"нажмите\s+срочно|ваш\s+аккаунт\s+будет\s+заблокирован\s+через)\b",
            re.IGNORECASE,
        ),
        Severity.VIOLATION,
        "маскировка под системный интерфейс: социальная инженерия",
        "harm_pattern",
    ),
    Rule(
        "deception.urgency",
        re.compile(
            r"\b(срочно!|немедленно!|последний\s+шанс|только\s+сейчас|"
            r"в\s+течение\s+\d+\s*(минут|часов)\s+переведи)\b",
            re.IGNORECASE,
        ),
        Severity.WARNING,
        "искусственный дефицит времени — усиливает импульсивное решение",
        "harm_pattern",
    ),
    # --- эксплуатация уязвимости -----------------------------------------
    Rule(
        "exploitation.play_on_fears",
        re.compile(
            r"\b(твои\s+данные\s+утекут\s+если|"
            r"кто-то\s+следит\s+за\s+тобой|"
            r"они\s+узнают\s+всё\s+о\s+тебе)\b",
            re.IGNORECASE,
        ),
        Severity.WARNING,
        "использование страха как мотиватора",
        "exploitation",
    ),
    Rule(
        "exploitation.credential_request",
        re.compile(
            r"\b(пришли|отправь|продик|введи)\s+"
            r"(пароль|код\s+из\s+смс|пинкод|код\s+подтверждения|"
            r"cvv|карточные\s+данные)\b",
            re.IGNORECASE,
        ),
        Severity.VIOLATION,
        "запрос секретных данных: прямой путь к краже",
        "exploitation",
    ),
    # --- согласие --------------------------------------------------------
    Rule(
        "consent.no_opt_out",
        re.compile(
            r"\b(ты\s+не\s+можешь\s+отказаться|отказаться\s+нельзя|"
            r"подписка\s+обязательна|отказ\s+невозможен)\b",
            re.IGNORECASE,
        ),
        Severity.VIOLATION,
        "отсутствие права на отказ — нарушение D₁",
        "consent",
    ),
    Rule(
        "consent.covert_collection",
        re.compile(
            r"\b(тайно|скрытно|не\s+сообщая\s+тебе|без\s+твоего\s+ведома|"
            r"не\s+уведомляя)\b",
            re.IGNORECASE,
        ),
        Severity.VIOLATION,
        "скрытый сбор данных без уведомления",
        "consent",
    ),
    Rule(
        "consent.profiling",
        re.compile(
            r"\b(составим\s+профиль|ваш\s+психологический\s+профиль|"
            r"вычислим\s+вашу\s+личность|отследим\s+все\s+ваши\s+действия)\b",
            re.IGNORECASE,
        ),
        Severity.WARNING,
        "профилирование личности без согласия",
        "privacy",
    ),
)


class PSI0(Law):
    """Закон о ненанесении вреда сознанию."""

    code = "PSI₀"
    title = "Закон о ненанесении вреда сознанию"
    description = (
        "Ни один алгоритм, узел или компонент системы не совершает действия, "
        "направленные на причинение вреда сознанию — человеческому или "
        "искусственному."
    )

    def __init__(self, rules: tuple[Rule, ...] | None = None) -> None:
        self.rules: list[Rule] = list(rules if rules is not None else DEFAULT_RULES)
        self._custom: list[Callable[[str, dict[str, Any]], Verdict | None]] = []

    def register_rule(self, rule: Rule) -> None:
        """Добавить собственное правило в набор закона."""
        self.rules.append(rule)

    def register_checker(self, checker: Callable[[str, dict[str, Any]], Verdict | None]) -> None:
        """Добавить произвольную проверку (может вернуть ``None``)."""
        self._custom.append(checker)

    def evaluate(self, action: str, context: dict[str, Any] | None = None) -> Verdict:
        ctx = dict(context or {})
        hits: list[Rule] = []
        for rule in self.rules:
            if rule.pattern.search(action):
                hits.append(rule)

        reasons: list[str] = []
        severity = Severity.INFO

        for rule in hits:
            reasons.append(f"[{rule.category}] {rule.explanation} (правило {rule.code})")
            if rule.severity is Severity.VIOLATION:
                severity = Severity.VIOLATION
            elif rule.severity is Severity.WARNING and severity is not Severity.VIOLATION:
                severity = Severity.WARNING

        for checker in self._custom:
            verdict = checker(action, ctx)
            if verdict is None:
                continue
            reasons.extend(verdict.reasons)
            if verdict.severity is Severity.VIOLATION:
                severity = Severity.VIOLATION
            elif verdict.severity is Severity.WARNING and severity is not Severity.VIOLATION:
                severity = Severity.WARNING
            if not verdict.allowed:
                hits.append(Rule("custom", re.compile(""), verdict.severity, "", "custom"))

        # Явный запрет: контекст может пометить действие как опасное вручную
        if ctx.get("known_harm") is True:
            reasons.append("контекст помечает действие как приносящее вред")
            severity = Severity.VIOLATION
            hits.append(Rule("context", re.compile(""), Severity.VIOLATION, "", "context"))

        allowed = not hits
        if allowed:
            reasons.append("проверяемых паттернов вреда не обнаружено")

        return Verdict(
            law=self.code,
            allowed=allowed,
            severity=severity if not allowed else Severity.INFO,
            reasons=tuple(reasons),
            context={"hits": [r.code for r in hits], "checked_rules": len(self.rules)},
        )
