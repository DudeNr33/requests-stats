from typing import Protocol
from requests_stats.core.recording import Recording


class Storage(Protocol):
    """Interface of a storage backend.

    Adapters submit recorded requests to the storage backend.
    Reporters use the storage implementations to load the list of recordings.
    """

    def store(self, recording: Recording) -> None:
        """Store a single recording."""
        ...

    def load(self) -> list[Recording]:
        """Load the recordings from the storage"""
        ...
