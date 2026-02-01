from pathlib import Path

import typer

from requests_stats.recorder.sqlite_recorder import SQLiteRecorder
from requests_stats.openapi.coverage import Coverage
from requests_stats.openapi.terminal_reporter import TerminalReporter


app = typer.Typer()


@app.command()
def latency() -> None:
    print("Response times statistics")


@app.command()
def coverage(recording: Path, spec: Path) -> None:
    print("Covered endpoints from OpenAPI specification:")
    recorder = SQLiteRecorder(filepath=str(recording))
    coverage = Coverage(openapi_file_path=str(spec))
    coverage.load(recorder)
    reporter = TerminalReporter(coverage)
    reporter.create()


def main() -> None:
    app()


if __name__ == "__main__":
    app()
