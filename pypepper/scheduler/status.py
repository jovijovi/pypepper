from enum import StrEnum


class Status(StrEnum):
    UNKNOWN = "Unknown"
    INITIALIZING = "Initializing"
    SCHEDULED = "Scheduled"
    IN_PROGRESS = "InProgress"
    FAILED = "Failed"
    COMPLETED = "Completed"
    CANCELLED = "Cancelled"
