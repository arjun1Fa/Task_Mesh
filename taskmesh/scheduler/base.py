"""Base scheduler protocol and candidate eligibility filtering."""

from typing import List, Protocol

from taskmesh.core.enums import NodeStatus
from taskmesh.core.models import NodeProfile, Task
from taskmesh.scheduler.decision import SchedulerDecision


def filter_eligible_nodes(task: Task, nodes: List[NodeProfile]) -> List[NodeProfile]:
    """Filters candidate nodes by online status, hardware requirements, and handler support."""
    eligible = []
    for node in nodes:
        # 1. State must be ONLINE (DRAINING and OFFLINE are ineligible)
        if node.status not in (NodeStatus.ONLINE, NodeStatus.DEGRADED):
            continue

        caps = node.capabilities

        # 2. Handler support: if node explicitly lists handlers, task_type must be supported
        if caps.supported_handlers and task.task_type not in caps.supported_handlers:
            continue

        # 3. GPU requirement
        if task.requires_gpu and not caps.has_gpu:
            continue

        # 4. RAM requirement
        if task.required_memory_mb > 0 and caps.ram_available_mb < task.required_memory_mb:
            continue

        # 5. Required capability tags
        if task.required_capabilities:
            if not all(tag in caps.tags for tag in task.required_capabilities):
                continue

        eligible.append(node)

    return eligible


class Scheduler(Protocol):
    """Abstract scheduler interface."""

    async def select_node(
        self,
        task: Task,
        candidates: List[NodeProfile],
    ) -> SchedulerDecision:
        ...
