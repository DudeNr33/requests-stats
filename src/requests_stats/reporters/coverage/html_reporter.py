from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from jinja2 import Environment, FileSystemLoader, Template, select_autoescape

from requests_stats.core.coverage import Coverage


@dataclass(frozen=True)
class ResponseEntry:
    method: str
    path: str
    response_code: int
    response_description: str
    tags: tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class EndpointGroup:
    method: str
    path: str
    summary: str
    responses: tuple[tuple[int, str], ...]
    tags: tuple[str, ...]


class HtmlReporter:
    def __init__(self, coverage: Coverage) -> None:
        self.coverage = coverage

    def create(self, output: Path) -> None:
        output.write_text(self.render(), encoding="utf-8")

    def render(self) -> str:
        groups = self._collect_groups()
        tags_map = self._group_by_tags(groups)
        extra = sorted(
            self.coverage.extra_details,
            key=lambda item: (item[0], item[2], item[3], item[1]),
        )

        summary_status = self._count_group_status(groups)
        total_endpoints = sum(summary_status.values())
        coverage_percent = (
            f"{(summary_status['covered'] / total_endpoints * 100):.1f}"
            if total_endpoints
            else "0.0"
        )

        tags: list[dict[str, object]] = []
        for tag_name in sorted(tags_map, key=lambda name: name.lower()):
            tag_groups = tags_map[tag_name]
            tag_covered, tag_total = self._count_group_coverage(tag_groups)
            tag_coverage = (
                f"{(tag_covered / tag_total * 100):.1f}" if tag_total else "0.0"
            )
            group_status = self._count_group_status(tag_groups)
            tags.append(
                {
                    "name": tag_name,
                    "coverage_percent": tag_coverage,
                    "status": group_status,
                    "groups": [self._serialize_group(group) for group in tag_groups],
                }
            )

        extra_items = [
            {
                "method": method,
                "method_lower": method.lower(),
                "original_path": original_path,
                "normalized_path": normalized_path,
                "code": code,
            }
            for method, original_path, normalized_path, code in extra
        ]

        return cast(
            str,
            self._template().render(
                summary_status=summary_status,
                coverage_percent=coverage_percent,
                tags=tags,
                extra=extra_items,
            ),
        )

    def _collect_groups(self) -> list[EndpointGroup]:
        entries: list[ResponseEntry] = []
        for path in self.coverage.spec.paths:
            for operation in path.operations:
                tags = tuple(operation.tags or ["default"])
                summary = (operation.summary or "").strip()
                for response in operation.responses:
                    if response.is_default or response.code is None:
                        continue
                    code = int(response.code)
                    description = (response.description or "").strip()
                    entries.append(
                        ResponseEntry(
                            method=operation.method.name,
                            path=path.url,
                            response_code=code,
                            response_description=description,
                            tags=tags,
                            summary=summary,
                        )
                    )
        grouped: dict[tuple[str, str, str], list[ResponseEntry]] = defaultdict(list)
        for entry in entries:
            grouped[(entry.method, entry.path, entry.summary)].append(entry)

        groups: list[EndpointGroup] = []
        for (method, path, summary), items in grouped.items():
            response_details = {
                item.response_code: item.response_description for item in items
            }
            responses = tuple(sorted(response_details.items()))
            tags = tuple(sorted({tag for item in items for tag in item.tags}))
            groups.append(
                EndpointGroup(
                    method=method,
                    path=path,
                    summary=summary,
                    responses=responses,
                    tags=tags,
                )
            )
        return groups

    def _group_by_tags(
        self, groups: list[EndpointGroup]
    ) -> dict[str, list[EndpointGroup]]:
        grouped: dict[str, list[EndpointGroup]] = defaultdict(list)
        for group in groups:
            for tag in group.tags:
                grouped[tag].append(group)
        for tag, items in grouped.items():
            grouped[tag] = sorted(items, key=self._group_sort_key)
        return dict(grouped)

    def _count_group_coverage(self, groups: list[EndpointGroup]) -> tuple[int, int]:
        covered = 0
        total = 0
        for group in groups:
            covered += self._covered_response_count(group)
            total += len(group.responses)
        return covered, total

    def _count_group_status(self, groups: list[EndpointGroup]) -> dict[str, int]:
        counts = {"covered": 0, "partial": 0, "uncovered": 0}
        for group in groups:
            covered = self._covered_response_count(group)
            total = len(group.responses)
            label = self._coverage_label(covered, total)
            if label == "covered":
                counts["covered"] += 1
            elif label == "uncovered" or label == "none":
                counts["uncovered"] += 1
            else:
                counts["partial"] += 1
        return counts

    def _serialize_group(self, group: EndpointGroup) -> dict[str, object]:
        covered_count = self._covered_response_count(group)
        total_count = len(group.responses)
        responses = [
            {
                "code": code,
                "description": description,
                "status": (
                    "covered"
                    if (group.method, group.path, code) in self.coverage.covered
                    else "uncovered"
                ),
            }
            for code, description in group.responses
        ]
        return {
            "method": group.method,
            "method_lower": group.method.lower(),
            "path": group.path,
            "summary": group.summary,
            "covered_count": covered_count,
            "total_count": total_count,
            "coverage_status": self._coverage_status(covered_count, total_count),
            "coverage_label": self._coverage_label(covered_count, total_count),
            "responses": responses,
        }

    def _group_sort_key(self, group: EndpointGroup) -> tuple[int, str]:
        return (self._method_rank(group.method), group.path)

    def _method_rank(self, method: str) -> int:
        order = {
            "GET": 0,
            "POST": 1,
            "PUT": 2,
            "PATCH": 3,
            "DELETE": 4,
            "HEAD": 5,
            "OPTIONS": 6,
            "TRACE": 7,
        }
        return order.get(method.upper(), 99)

    def _covered_response_count(self, group: EndpointGroup) -> int:
        return sum(
            1
            for code, _ in group.responses
            if (group.method, group.path, code) in self.coverage.covered
        )

    def _coverage_status(self, covered: int, total: int) -> str:
        if total == 0 or covered == 0:
            return "uncovered"
        if covered == total:
            return "covered"
        return "extra"

    def _coverage_label(self, covered: int, total: int) -> str:
        if total == 0:
            return "none"
        if covered == total:
            return "covered"
        if covered == 0:
            return "uncovered"
        return "partial"

    def _template(self) -> Template:
        template_dir = Path(__file__).parent / "templates"
        env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(
                enabled_extensions=("html", "htm", "xml", "j2")
            ),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        return env.get_template("html_report.html.j2")
