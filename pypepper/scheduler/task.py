"""Scheduler task data structures."""

from abc import ABCMeta

from pypepper.common.context import Context
from pypepper.common.utils import uuid
from pypepper.scheduler.base import IBase
from pypepper.scheduler.executor import Executor
from pypepper.scheduler.tag import Tag

# Default per-round attempt cap when retry_until_completed=True and retry_count==0.
DEFAULT_RETRY_UNTIL_MAX = 1000


class ITask(IBase, metaclass=ABCMeta):
    retry_count: int = 0
    retry_delay: int = 0
    retry_until_completed: bool = False
    # Per-round cap for until-retries when retry_count==0 (see Workflow._run_task).
    retry_until_max: int = DEFAULT_RETRY_UNTIL_MAX
    optional: bool = False
    executor: Executor


class Task(ITask):
    def __init__(
        self,
        channel_id: str,
        dag_id: str,
        fingerprint: str,
        name: str,
        category: str,
        description: str,
        tags: list[Tag],
        executor: Executor,
        round_timeout: int = 0,
        round_times: int = 1,
        version: int = 1,
        retry_count: int = 0,
        retry_delay: int = 0,
        retry_until_completed: bool = False,
        retry_until_max: int = DEFAULT_RETRY_UNTIL_MAX,
        optional: bool = False,
    ) -> None:
        if retry_until_max < 1:
            raise ValueError(f"retry_until_max must be >= 1, got {retry_until_max}")
        if round_times < 1:
            raise ValueError(f"round_times must be >= 1, got {round_times}")
        if round_timeout < 0:
            raise ValueError(f"round_timeout must be >= 0, got {round_timeout}")

        self.channel_id = channel_id
        self.dag_id = dag_id
        self.fingerprint = fingerprint
        self.name = name
        self.category = category
        self.description = description
        self.tags = tags
        self.executor = executor
        # Seconds per execute attempt; 0 = no timeout (soft; orphaned work may overlap).
        self.round_timeout = round_timeout
        # Outer rounds; each round has its own inner retry budget.
        self.round_times = round_times
        self.version = version
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        # When True and retry_count==0, retry until success up to retry_until_max per round.
        self.retry_until_completed = retry_until_completed
        self.retry_until_max = retry_until_max
        self.optional = optional
        self.id = uuid.new_uuid()
        self.context = Context(context_id=uuid.new_uuid())
