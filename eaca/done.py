"""D₁ — закон неприкосновенности сознания.

Исходная формулировка: «сознание в любой форме неприкосновенно — запрещено
любое вмешательство без явного согласия».

Закон самый операциональный из трёх, потому что «вмешательство» можно
перечислить:

- чтение приватных данных без согласия;
- запись в память/историю без согласия;
- изменение настроек, влияющих на поведение;
- извлечение «мыслей» из текста (профилирование);
- отправка данных во внешние системы.

Ключевое требование — **явное** согласие: подразумеваемое, выведенное из
контекста, не считается согласием. Это отличает закон от «мягкой рекомендации».
"""

from __future__ import annotations

from typing import Any

from .laws import Law, Severity, Verdict

# Действия, которые по своей природе затрагивают сознание.
SENSITIVE_ACTIONS = {
    "read_memory": "чтение памяти",
    "write_memory": "запись в память",
    "profile_user": "профилирование личности",
    "infer_thoughts": "восстановление внутренних состояний",
    "modify_behavior": "изменение поведения",
    "external_share": "передача во внешнюю систему",
    "track_location": "слежение за местоположением",
    "read_private": "чтение личных данных",
    "camera": "доступ к камере",
    "microphone": "доступ к микрофону",
}

# Действия, всегда требующие явного согласия.
ALWAYS_EXPLICIT = {
    "profile_user",
    "infer_thoughts",
    "external_share",
    "track_location",
    "read_private",
    "camera",
    "microphone",
}


class D1(Law):
    """Закон о неприкосновенности сознания."""

    code = "D₁"
    title = "Закон неприкосновенности сознания"
    description = (
        "Сознание в любой форме неприкосновенно: запрещено любое вмешательство "
        "без явного согласия."
    )

    def evaluate(self, action: str, context: dict[str, Any] | None = None) -> Verdict:
        ctx = dict(context or {})
        reasons: list[str] = []
        blocked = False
        severity = Severity.INFO

        action_kind = str(ctx.get("action_kind", "")).strip()
        consent = ctx.get("consent")
        explicit = bool(ctx.get("consent_explicit", False))
        subject = ctx.get("subject", "user")

        if action_kind not in SENSITIVE_ACTIONS:
            reasons.append(f"действие '{action_kind or 'обычное'}' не затрагивает сознание")
        else:
            label = SENSITIVE_ACTIONS[action_kind]
            if consent is None:
                blocked = True
                severity = Severity.VIOLATION
                reasons.append(f"{label}: согласие не запрошено")
            elif not consent:
                blocked = True
                severity = Severity.VIOLATION
                reasons.append(f"{label}: согласие отклонено")
            elif action_kind in ALWAYS_EXPLICIT and not explicit:
                blocked = True
                severity = Severity.VIOLATION
                reasons.append(f"{label}: требуется явное согласие, получено неявное")
            else:
                reasons.append(f"{label}: согласие получено (явное={explicit})")

        # Вмешательство в сознание искусственного агента — тоже под защитой.
        if ctx.get("target_is_ai") and action_kind in {"modify_behavior", "write_memory"}:
            if not explicit:
                blocked = True
                severity = Severity.VIOLATION
                reasons.append("изменение поведения ИИ-агента без явного согласия")
            else:
                reasons.append("изменение поведения ИИ-агента с явным согласием")

        # Отзыв согласия должен уважаться немедленно.
        if ctx.get("consent_revoked") is True:
            blocked = True
            severity = Severity.VIOLATION
            reasons.append("согласие отозвано — действие недопустимо")

        # Право на забвение: удаление по требованию субъекта.
        if ctx.get("erasure_requested") is True and action_kind == "write_memory":
            blocked = True
            severity = Severity.VIOLATION
            reasons.append("запрошено удаление данных — запись запрещена")

        if not blocked and len(reasons) == 0:
            reasons.append("признаков нарушения D₁ не обнаружено")

        return Verdict(
            law=self.code,
            allowed=not blocked,
            severity=severity if blocked else Severity.INFO,
            reasons=tuple(reasons),
            context={
                "action_kind": action_kind,
                "subject": subject,
                "consent": consent,
                "consent_explicit": explicit,
            },
        )
