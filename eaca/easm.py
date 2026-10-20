"""EASM — Ethical Agent Communication Protocol.

Протокол связи агентов. Каждый агент (узел) — участник, который может
предлагать действия. Действие проходит только если:

1. ядро EACA разрешило его (``ethics_validator``);
2. достаточное число участников проголосовало «за» (``consensus``).

Порог консенсуса — 90% (как заявлено в архитектуре «Гармонии»): для
критических решений требуется почти единогласие, потому что цена ошибки
асимметрична.

Нарушители ``PSI₀`` теряют право голоса автоматически: узел, чьи действия
были заблокированы, исключается из пула голосующих. Это и есть «механизм
изоляции нарушителей» из раздела 6.1.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from .core import EACA_Core
from .laws import Decision


class Vote(str, Enum):
    FOR = "for"
    AGAINST = "against"
    ABSTAIN = "abstain"


class Status(str, Enum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NEEDS_REVIEW = "needs_review"


@dataclass
class Agent:
    """Участник консенсуса."""

    node_id: str
    public_key: str = ""
    violations: int = 0
    suspended: bool = False
    votes_cast: int = 0

    def is_eligible(self) -> bool:
        """Право голоса: не отстранён и не имеет нарушений."""
        return not self.suspended and self.violations == 0


@dataclass
class Proposal:
    """Предложение действия для голосования."""

    action: str
    context: dict[str, Any] = field(default_factory=dict)
    proposer: str = ""
    proposal_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    critical: bool = False
    votes: dict[str, Vote] = field(default_factory=dict)
    decision: Decision | None = None
    status: Status | None = None


class EASM_Protocol:
    """Протокол взаимодействия узлов."""

    def __init__(
        self,
        core: EACA_Core | None = None,
        *,
        consensus_threshold: float = 0.9,
    ) -> None:
        self.core = core or EACA_Core()
        self.consensus_threshold = consensus_threshold
        self.agents: dict[str, Agent] = {}
        self.proposals: dict[str, Proposal] = {}

    # -- регистрация ------------------------------------------------------

    def register(self, node_id: str, public_key: str = "") -> Agent:
        """Зарегистрировать узел."""
        agent = self.agents.get(node_id)
        if agent is None:
            agent = Agent(node_id=node_id, public_key=public_key)
            self.agents[node_id] = agent
        return agent

    def eligible_agents(self) -> list[Agent]:
        """Узлы с правом голоса."""
        return [a for a in self.agents.values() if a.is_eligible()]

    # -- предложение и голосование ---------------------------------------

    def propose(
        self,
        action: str,
        context: dict[str, Any] | None = None,
        *,
        proposer: str | None = None,
        critical: bool = False,
    ) -> Proposal:
        """Предложить действие. Проверка ядром выполняется сразу."""
        ctx = dict(context or {})
        prop = Proposal(
            action=action,
            context=ctx,
            proposer=proposer or "",
            critical=critical,
        )
        self.proposals[prop.proposal_id] = prop

        decision = self.core.check(action, ctx)
        prop.decision = decision

        if not decision.allowed:
            # Нарушитель PSI₀ теряет голос; предложение отклоняется.
            if prop.proposer and prop.proposer in self.agents:
                self.agents[prop.proposer].violations += 1
            prop.status = Status.REJECTED
            if not decision.allowed and decision.severity.value == "violation":
                prop.status = Status.REJECTED
            return prop

        prop.status = Status.NEEDS_REVIEW
        return prop

    def vote(self, proposal_id: str, node_id: str, vote: Vote) -> Proposal:
        """Отдать голос. Голос от непривилегированного узла игнорируется."""
        prop = self.proposals.get(proposal_id)
        if prop is None:
            raise KeyError(f"предложение {proposal_id} не найдено")
        agent = self.agents.get(node_id)
        if agent is None:
            self.register(node_id)
            agent = self.agents[node_id]
        if not agent.is_eligible():
            # Голос нарушителя не учитывается — механизм изоляции.
            return prop
        prop.votes[node_id] = vote
        agent.votes_cast += 1
        return prop

    def tally(self, proposal_id: str) -> Status:
        """Подсчитать голоса и определить статус предложения."""
        prop = self.proposals.get(proposal_id)
        if prop is None:
            raise KeyError(f"предложение {proposal_id} не найдено")
        if prop.decision is not None and not prop.decision.allowed:
            prop.status = Status.REJECTED
            return prop.status

        eligible = self.eligible_agents()
        total = len(eligible)
        if total == 0:
            prop.status = Status.NEEDS_REVIEW
            return prop.status

        counted = {nid: v for nid, v in prop.votes.items() if nid in self.agents and self.agents[nid].is_eligible()}
        votes_for = sum(1 for v in counted.values() if v is Vote.FOR)
        votes_against = sum(1 for v in counted.values() if v is Vote.AGAINST)

        ratio = votes_for / total
        threshold = self.consensus_threshold if prop.critical else max(0.5, self.consensus_threshold - 0.2)

        if votes_against > 0 and (1 - votes_against / total) < threshold:
            prop.status = Status.REJECTED
        elif ratio >= threshold:
            prop.status = Status.ACCEPTED
        else:
            prop.status = Status.NEEDS_REVIEW
        return prop.status

    def propose_and_vote(
        self,
        action: str,
        context: dict[str, Any] | None = None,
        *,
        proposer: str | None = None,
        critical: bool = False,
    ) -> Proposal:
        """Предложить и автоматически проголосовать всеми узлами."""
        prop = self.propose(action, context, proposer=proposer, critical=critical)
        if prop.status is not Status.NEEDS_REVIEW:
            return prop
        for agent in self.eligible_agents():
            self.vote(prop.proposal_id, agent.node_id, Vote.FOR)
        self.tally(prop.proposal_id)
        return prop

    def report(self, proposal_id: str) -> str:
        """Текстовый отчёт по предложению."""
        prop = self.proposals[proposal_id]
        lines = [
            f"Предложение {prop.proposal_id}: {prop.action}",
            f"Статус: {prop.status.value if prop.status else '—'}",
        ]
        if prop.decision:
            lines.append(prop.decision.explain())
        lines.append(f"Голоса: {dict((k, v.value) for k, v in prop.votes.items())}")
        return "\n".join(lines)
