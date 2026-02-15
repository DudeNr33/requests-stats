import sqlite3

from requests_stats.core.recording import Recording
from requests_stats.core.base_storage import Storage


class SQLiteStorage(Storage):
    def __init__(self, filepath: str = "requests.db") -> None:  # TODO: make pathlike
        self.connection = sqlite3.connect(filepath)
        self.cursor = self.connection.cursor()
        self.cursor.execute(
            "CREATE TABLE IF NOT EXISTS requests(method, url, params, response_status, duration)"
        )

    def store(self, recording: Recording) -> None:
        self.cursor.execute(
            "INSERT INTO requests VALUES (?, ?, ?, ?, ?)",
            [
                recording.method,
                recording.url,
                recording.params,
                recording.response_code,
                recording.duration,
            ],
        )
        self.connection.commit()

    def persist(self) -> None:
        # Nothing to do, sqlite3 handles writing to disk
        return

    def load(self) -> list[Recording]:
        return [Recording(*x) for x in self.cursor.execute("SELECT * FROM requests")]
