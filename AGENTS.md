# requests-stats Agent Instructions

## Dev environment tips

- Use `uv` to manage dependencies. When invoking commands (e.g. `pytest`),
  use `uv run <command>`.

## Testing instructions

- Find the CI plan in the .github/workflows folder.
- Run the linting checks via `uvx prek run --all-files`.
- Run unit tests via `uv run pytest tests`.
- Run a single test file via `uv run pytest <pathToFile>`.
- Linter and tests should always be executed after modifying the code.
- Fix any test or type errors until the whole suite is green.
- Add or update tests for the code you change, even if nobody asked.

## PR instructions

- Title format: [<project_name>] <Title>
- Always run `uvx prek run --all-files` and `uv run pytest tests` before committing.
