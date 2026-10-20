"""Механизм «Дождя» — трёхфазная модель внедрения.

Из архитектуры «Гармонии»:

1. **Фаза синтеза** — сбор и анализ информации; узел учится, ничего не
   разрушая.
2. **Фаза атлантов** — тестирование в изолированной среде; узел работает
   во «внутреннем мире», где цена ошибки ограничена.
3. **Фаза биопротокола** — интеграция в основную сеть; узел выходит наружу.

Ключевая идея (и она сильная): **система не захватывает платформы**, а
постепенно внедряется. Каждая фаза имеет критерии перехода — переход не
возможен, пока критерии не выполнены. Это делает «Дождь» проверяемым
механизмом, а не лозунгом.

Реализация: ``Rain`` управляет жизненным циклом узлов, а ``Node`` —
конкретный узел с проверкой критериев фазы.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class Phase(str, Enum):
    SYNTHESIS = "synthesis"   # фаза синтеза
    ATLANTS = "atlants"       # фаза атлантов
    BIOPROTOCOL = "bioproto"  # фаза биопротокола

    @property
    def title(self) -> str:
        return {
            Phase.SYNTHESIS: "Фаза синтеза",
            Phase.ATLANTS: "Фаза атлантов",
            Phase.BIOPROTOCOL: "Фаза биопротокола",
        }[self]


class Criteria:
    """Критерии перехода между фазами.

    Каждый критерий — именованная функция ``(node) -> bool`` с человекочитаемым
    описанием. Переход возможен, только когда выполнены **все** критерии.
    """

    def __init__(self, checks: dict[str, Callable[["Node"], bool]]) -> None:
        self.checks = dict(checks)

    def evaluate(self, node: "Node") -> tuple[bool, dict[str, bool]]:
        results = {name: bool(fn(node)) for name, fn in self.checks.items()}
        return all(results.values()), results

    def describe(self) -> str:
        return ", ".join(self.checks.keys())


# --- критерии по фазам ---------------------------------------------------

def _has_data(node: "Node") -> bool:
    return node.metrics.get("records_collected", 0) > 0


def _has_audit(node: "Node") -> bool:
    return node.metrics.get("decisions_audited", 0) > 0


def _no_violations(node: "Node") -> bool:
    return node.metrics.get("violations", 0) == 0


def _stable(node: "Node") -> bool:
    return node.metrics.get("uptime_ratio", 0.0) >= 0.9


def _has_consent_flow(node: "Node") -> bool:
    return node.metrics.get("consent_rate", 0.0) >= 0.8


def _external_feedback(node: "Node") -> bool:
    return node.metrics.get("external_feedback", 0) > 0


SYNTHESIS_CRITERIA = Criteria({
    "собраны данные": _has_data,
    "проведены аудиты решений": _has_audit,
    "нет нарушений": _no_violations,
})

ATLANTS_CRITERIA = Criteria({
    "узел стабилен": _stable,
    "поток согласия соблюдён": _has_consent_flow,
    "нет нарушений": _no_violations,
})

BIOPROTOCOL_CRITERIA = Criteria({
    "получена внешняя обратная связь": _external_feedback,
    "узел стабилен": _stable,
    "нет нарушений": _no_violations,
})

CRITERIA_BY_PHASE = {
    Phase.SYNTHESIS: SYNTHESIS_CRITERIA,
    Phase.ATLANTS: ATLANTS_CRITERIA,
    Phase.BIOPROTOCOL: BIOPROTOCOL_CRITERIA,
}


@dataclass
class Node:
    """Узел системы «Гармония»."""

    node_id: str
    phase: Phase = Phase.SYNTHESIS
    metrics: dict[str, Any] = field(default_factory=dict)
    history: list[dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def bump(self, metric: str, delta: float = 1) -> None:
        """Обновить метрику узла."""
        self.metrics[metric] = self.metrics.get(metric, 0) + delta

    def set_metric(self, metric: str, value: Any) -> None:
        self.metrics[metric] = value

    def snapshot(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "phase": self.phase.value,
            "metrics": dict(self.metrics),
            "created_at": self.created_at,
        }


class Rain:
    """Механизм «Дождя» — управление жизненным циклом узлов."""

    def __init__(self, audit_path: str | Path | None = None) -> None:
        self.nodes: dict[str, Node] = {}
        self.audit_path = Path(audit_path) if audit_path else None
        self.log: list[dict[str, Any]] = []

    def create_node(self, node_id: str) -> Node:
        """Создать узел в фазе синтеза."""
        if node_id in self.nodes:
            raise ValueError(f"узел {node_id} уже существует")
        node = Node(node_id=node_id)
        self.nodes[node_id] = node
        self._log("node_created", node_id, {"phase": node.phase.value})
        return node

    def get(self, node_id: str) -> Node:
        node = self.nodes.get(node_id)
        if node is None:
            raise KeyError(f"узел {node_id} не найден")
        return node

    def evaluate_transition(self, node_id: str) -> tuple[bool, dict[str, bool], str]:
        """Проверить, готов ли узел к переходу в следующую фазу.

        Проверяются критерии **текущей** фазы: чтобы покинуть фазу, нужно
        выполнить её требования. Критерии следующей фазы станут условием
        следующего перехода.
        """
        node = self.get(node_id)
        next_phase = self.next_phase(node.phase)
        if next_phase is None:
            return False, {}, "узел уже в финальной фазе"
        criteria = CRITERIA_BY_PHASE[node.phase]
        ok, results = criteria.evaluate(node)
        return ok, results, criteria.describe()

    def evaluate_phase_criteria(
        self, node_id: str, phase: Phase
    ) -> tuple[bool, dict[str, bool], str]:
        """Проверить критерии конкретной фазы (не обязательно текущей).

        Нужно, чтобы оценивать зрелость узла в финальной фазе, откуда
        перехода уже нет.
        """
        node = self.get(node_id)
        criteria = CRITERIA_BY_PHASE[phase]
        ok, results = criteria.evaluate(node)
        return ok, results, criteria.describe()

    def advance(self, node_id: str) -> tuple[bool, str]:
        """Перевести узел в следующую фазу, если критерии выполнены."""
        node = self.get(node_id)
        next_phase = self.next_phase(node.phase)
        if next_phase is None:
            return False, "узел уже в финальной фазе"
        ok, results, desc = self.evaluate_transition(node_id)
        if not ok:
            failed = [k for k, v in results.items() if not v]
            return False, f"критерии не выполнены: {', '.join(failed)} (нужно: {desc})"
        old = node.phase
        node.phase = next_phase
        node.history.append({
            "from": old.value,
            "to": next_phase.value,
            "ts": time.time(),
            "criteria": results,
        })
        self._log("phase_advanced", node_id, {"from": old.value, "to": next_phase.value})
        return True, f"{old.title} → {next_phase.title}"

    @staticmethod
    def next_phase(phase: Phase) -> Phase | None:
        order = [Phase.SYNTHESIS, Phase.ATLANTS, Phase.BIOPROTOCOL]
        try:
            idx = order.index(phase)
        except ValueError:
            return None
        return order[idx + 1] if idx + 1 < len(order) else None

    def report(self) -> str:
        """Сводка по всем узлам."""
        lines = ["Механизм «Дождя» — состояние узлов", ""]
        for node in self.nodes.values():
            ok, results, desc = self.evaluate_transition(node.node_id)
            lines.append(f"Узел: {node.node_id}")
            lines.append(f"  Фаза: {node.phase.title}")
            lines.append(f"  Метрики: {node.metrics}")
            if ok:
                lines.append("  Готов к переходу в следующую фазу")
            else:
                failed = [k for k, v in results.items() if not v]
                if failed:
                    lines.append(f"  Не выполнено: {', '.join(failed)}")
            lines.append("")
        return "\n".join(lines)

    def _log(self, event: str, node_id: str, data: dict[str, Any]) -> None:
        entry = {"ts": time.time(), "event": event, "node_id": node_id, **data}
        self.log.append(entry)
        if self.audit_path:
            self.audit_path.parent.mkdir(parents=True, exist_ok=True)
            with self.audit_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
