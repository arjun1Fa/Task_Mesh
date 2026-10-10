"""Base scheduler protocol and candidate eligibility filtering."""

from typing import List, Protocol

from taskmesh.core.enums import NodeStatus, OffloadPolicy
from taskmesh.core.models import NodeProfile, Task
from taskmesh.scheduler.decision import SchedulerDecision


def filter_eligible_nodes(task: Task, nodes: List[NodeProfile]) -> List[NodeProfile]:
    """Filters candidate nodes by online status, hardware requirements, offload policy, and handler support."""
    eligible = []
    for node in nodes:
        # 1. State must be ONLINE (DRAINING and OFFLINE are ineligible)
        if node.status not in (NodeStatus.ONLINE, NodeStatus.DEGRADED):
            continue

        caps = node.capabilities

        # 2. Privacy & Offload Policy: local_only tasks can ONLY run on local node
        if task.offload_policy in (OffloadPolicy.LOCAL_ONLY, "local_only"):
            if not caps.is_local:
                continue

        # 3. Handler support: if node explicitly lists handlers, task_type must be supported
        if caps.supported_handlers and task.task_type not in caps.supported_handlers:
            continue

        # 4. GPU requirement
        if task.requires_gpu and not caps.has_gpu:
            continue

        # 5. RAM requirement
        if task.required_memory_mb > 0 and caps.ram_available_mb < task.required_memory_mb:
            continue

        # 6. Required capability tags
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
