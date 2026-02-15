# Architecture Documentation

## Quality Goals

- Interoperability:
  - it shall be possible to use this library with different tools and libraries.
    Example: requests can be recorded during API tests performed with the
    `requests` library, or during UI tests performed with `playwright`.
  - it shall be possible to choose different persistence methods.
    Example: information can be stored only in memory, or in an SQLite database.

## Ports and Adapters

`requests-stats` follows a simple ports and adapters architecture to achieve especially
the interoperability goal.

The `core` package represents the functional core with interfaces, entity classes,
and common business logic.

`adapters` contains implementations for different libraries (e.g. `requests`) or
frameworks (e.g. `playwright`) and handles capturing the relevant data and submitting
it to storage.

`storage` contains the implementation for different storage backends, that implement
the interface defined in the `core`.

`reporters` implement the different output formats (e.g. text, html) for the
various reports.
