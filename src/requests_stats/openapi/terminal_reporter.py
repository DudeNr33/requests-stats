from textwrap import dedent
from requests_stats.openapi.coverage import Coverage


class TerminalReporter:
    def __init__(self, coverage: Coverage) -> None:
        self.coverage = coverage

    def render(self) -> str:
        covered = sorted(self.coverage.covered)
        uncovered = sorted(self.coverage.uncovered)
        return dedent(
            f"""
                Covered operations/responses:
                    {"\n\t".join(f"{x[0]} {x[1]} returns {x[2]}" for x in covered) if covered else "None"}

                Uncovered operations/responses:
                    {"\n\t".join(f"{x[0]} {x[1]} returns {x[2]}" for x in uncovered) if uncovered else "None"}
            """
        )

    def create(self) -> None:
        print(self.render())
