from enum import Enum


class Status(str, Enum):
    UNKNOWN = "Unknown"
    INITIALIZING = "Initializing"
    SCHEDULED = "Scheduled"
    IN_PROGRESS = "InProgress"
    FAILED = "Failed"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
