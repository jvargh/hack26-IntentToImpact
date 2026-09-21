"""Bounded durable local work coordination, version 1.0.0."""

from .coordinator import TransitionReceipt, WorkCoordinator, WorkError

__all__ = ["TransitionReceipt", "WorkCoordinator", "WorkError"]
__version__ = "1.0.0"
