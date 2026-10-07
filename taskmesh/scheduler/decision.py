"""Scheduler decision structure for explainability and auditing."""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from taskmesh.core.enums import SchedulerMode


class SchedulerDecision(BaseModel):
    task_id: str
    selected_node_id: str
    policy_used: SchedulerMode
    candidate_node_ids: List[str] = Field(default_factory=list)
    candidate_scores: Dict[str, float] = Field(default_factory=dict)
    bids: Dict[str, float] = Field(default_factory=dict)
    fairness_deficits: Dict[str, float] = Field(default_factory=dict)
    rl_state: Optional[Tuple[int, int, int]] = None
    rl_action: Optional[int] = None
    fallback_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
