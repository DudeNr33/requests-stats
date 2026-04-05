import json
from pathlib import Path
from collections.abc import Generator
from urllib.parse import urlparse

from requests_stats.core.base_storage import Storage
from requests_stats.core.recording import Recording


class HarStorage(Storage):
    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def store(self, recording: Recording) -> None:
        raise NotImplementedError(
            "HarStorage is readonly. You can only use it to load HAR files."
        )

    def load(self) -> list[Recording]:
        if self.path.is_file():
            return list(self._iter_recordings(self.path))
        elif self.path.is_dir():
            recordings = []
            for filepath in self.path.glob("*.har"):
                recordings.extend(list(self._iter_recordings(filepath)))
            return recordings
        raise IOError(f"{self.path} is neither a valid file path nor a directory.")

    def _iter_recordings(self, filepath: Path) -> Generator[Recording]:
        data = json.loads(filepath.read_text("utf8"))
        for entry in data["log"]["entries"]:
            parsed = urlparse(entry["request"]["url"])
            yield Recording(
                method=entry["request"]["method"],
                scheme=parsed.scheme,
                netloc=parsed.netloc,
                path=parsed.path,
                params=parsed.params,
                query=parsed.query,
                response_code=entry["response"]["status"],
                duration=entry["time"] / 1000,
            )
