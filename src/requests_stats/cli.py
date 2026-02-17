from pathlib import Path

import typer

from requests_stats.storage.sqlite_storage import SQLiteStorage
from requests_stats.core.coverage import Coverage
from requests_stats.reporters.coverage.terminal_reporter import TerminalReporter
from requests_stats.reporters.coverage.html_reporter import HtmlReporter


app = typer.Typer()


@app.command()
def latency() -> None:
    print("Response times statistics")


@app.command()
def coverage(
    recording: Path,
    spec: Path,
    format: str = typer.Option("text", "--format", "-f"),
    output: Path | None = typer.Option(None, "--output", "-o"),
) -> None:
    storage = SQLiteStorage(filepath=str(recording))
    coverage = Coverage(openapi_file_path=str(spec))
    coverage.load(storage)

    report_format = format.lower().strip()
    if report_format == "text":
        terminal_reporter = TerminalReporter(coverage)
        if output:
            output.write_text(terminal_reporter.render(), encoding="utf-8")
        else:
            print("Covered endpoints from OpenAPI specification:")
            terminal_reporter.create()
        return

    if report_format == "html":
        html_reporter = HtmlReporter(coverage)
        output_path = output or Path("coverage.html")
        html_reporter.create(output_path)
        print(f"HTML coverage report written to {output_path}")
        return

    raise typer.BadParameter("Format must be 'text' or 'html'.", param_hint="format")


def main() -> None:
    # entry point for script
    app()


if __name__ == "__main__":
    app()
