from requests_stats.core.recording import Recording
from requests_stats.core.base_storage import Storage


class InMemoryStorage(Storage):
    def __init__(self) -> None:
        self.recordings: list[Recording] = []

    def store(self, recording: Recording) -> None:
        self.recordings.append(recording)

    def load(self) -> list[Recording]:
        return self.recordings
