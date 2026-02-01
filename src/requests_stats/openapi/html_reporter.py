from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from html import escape
from pathlib import Path

from requests_stats.openapi.coverage import Coverage


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
        extra = sorted(self.coverage.extra)

        covered_count = len(self.coverage.covered)
        uncovered_count = len(self.coverage.uncovered)
        total_count = covered_count + uncovered_count
        coverage_percent = (covered_count / total_count * 100) if total_count else 0.0

        html_parts: list[str] = [
            "<!doctype html>",
            '<html lang="en">',
            "<head>",
            '  <meta charset="utf-8" />',
            '  <meta name="viewport" content="width=device-width, initial-scale=1" />',
            "  <title>OpenAPI Coverage Report</title>",
            "  <style>",
            self._style_block(),
            "  </style>",
            "</head>",
            "<body>",
            '  <div class="page">',
            '    <header class="hero">',
            "      <div>",
            '        <div class="eyebrow">OpenAPI Coverage</div>',
            "        <h1>HTTP Coverage Report</h1>",
            '        <p class="subtitle">Recorded requests vs. OpenAPI operations</p>',
            "      </div>",
            '      <div class="summary">',
            f'        <div class="summary__metric"><span>{covered_count}</span> covered</div>',
            f'        <div class="summary__metric"><span>{uncovered_count}</span> uncovered</div>',
            f'        <div class="summary__metric"><span>{len(extra)}</span> extra</div>',
            '        <div class="summary__bar">',
            f'          <div class="summary__bar-fill" style="width: {coverage_percent:.1f}%"></div>',
            "        </div>",
            f'        <div class="summary__percent">{coverage_percent:.1f}% covered</div>',
            "      </div>",
            "    </header>",
        ]

        for tag_name in sorted(tags_map, key=lambda name: name.lower()):
            tag_groups = tags_map[tag_name]
            covered_count, total_count = self._count_group_coverage(tag_groups)
            tag_coverage = (covered_count / total_count * 100) if total_count else 0.0

            html_parts.extend(
                [
                    '    <section class="tag">',
                    '      <div class="tag__header">',
                    f"        <h2>{escape(tag_name)}</h2>",
                    '        <div class="tag__meta">',
                    f"          <span>{covered_count} covered</span>",
                    f"          <span>{total_count - covered_count} uncovered</span>",
                    f"          <span>{tag_coverage:.1f}%</span>",
                    "        </div>",
                    "      </div>",
                    '      <div class="tag__bar">',
                    f'        <div class="tag__bar-fill" style="width: {tag_coverage:.1f}%"></div>',
                    "      </div>",
                    '      <div class="ops">',
                ]
            )
            html_parts.extend(self._render_groups(tag_groups))
            html_parts.extend(["      </div>", "    </section>"])

        html_parts.extend(self._render_extra_section(extra))
        html_parts.extend(["  </div>", "</body>", "</html>"])
        return "\n".join(html_parts)

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

    def _render_groups(self, groups: list[EndpointGroup]) -> list[str]:
        if not groups:
            return [
                '        <div class="op op--empty">',
                '          <div class="op__empty">No documented operations</div>',
                "        </div>",
            ]
        return [self._render_group(group) for group in groups]

    def _render_group(self, group: EndpointGroup) -> str:
        method = escape(group.method)
        path = escape(group.path)
        summary = escape(group.summary) if group.summary else ""
        summary_html = f'<div class="op__summary">{summary}</div>' if summary else ""
        covered_count = self._covered_response_count(group)
        total_count = len(group.responses)
        response_items = "".join(
            self._render_response_code(group, code, description)
            for code, description in group.responses
        )
        return (
            '        <details class="op">'
            "<summary>"
            f'<span class="method method--{method.lower()}">{method}</span>'
            f'<span class="path">{path}</span>'
            f'<span class="response">{covered_count}/{total_count} covered</span>'
            f'<span class="status status--{self._coverage_status(covered_count, total_count)}">'
            f"{self._coverage_label(covered_count, total_count)}"
            "</span>"
            "</summary>"
            f"{summary_html}"
            '<div class="responses">'
            '<div class="responses__label">Documented responses</div>'
            f"{response_items}"
            "</div>"
            "</details>"
        )

    def _render_response_code(
        self, group: EndpointGroup, code: int, description: str
    ) -> str:
        covered = (group.method, group.path, code) in self.coverage.covered
        status = "covered" if covered else "uncovered"
        description_html = (
            f'<span class="response-desc">{escape(description)}</span>'
            if description
            else ""
        )
        return (
            '<div class="response-item">'
            f'<span class="response-code">{escape(str(code))}</span>'
            f"{description_html}"
            f'<span class="status status--{status}">{status}</span>'
            "</div>"
        )

    def _render_extra_section(self, extra: list[tuple[str, str, int]]) -> list[str]:
        if not extra:
            return []
        parts = [
            '    <section class="tag tag--extra">',
            '      <div class="tag__header">',
            "        <h2>Extra requests</h2>",
            '        <div class="tag__meta"><span>Not in spec</span></div>',
            "      </div>",
            '      <div class="ops">',
        ]
        for method, path, code in extra:
            parts.append(
                '        <div class="op">'
                f'<span class="method method--{escape(method.lower())}">{escape(method)}</span>'
                f'<span class="path">{escape(path)}</span>'
                f'<span class="response">{escape(str(code))}</span>'
                '<span class="status status--extra">extra</span>'
                "</div>"
            )
        parts.extend(["      </div>", "    </section>"])
        return parts

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

    def _style_block(self) -> str:
        return """
    :root {
      --bg: #f6f9fc;
      --bg-accent: #eef3f9;
      --card: #ffffff;
      --border: #d8e2ee;
      --text: #1f2937;
      --muted: #6b7280;
      --accent: #3b82f6;
      --covered: #22c55e;
      --uncovered: #ef4444;
      --extra: #f59e0b;
      --shadow: 0 10px 30px rgba(15, 23, 42, 0.08);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      font-family: "IBM Plex Sans", "Source Sans 3", "Noto Sans", "Helvetica Neue", sans-serif;
      color: var(--text);
      background: linear-gradient(135deg, var(--bg) 0%, var(--bg-accent) 100%);
    }

    h1, h2 {
      margin: 0;
      font-weight: 600;
    }

    h1 {
      font-size: 2rem;
    }

    h2 {
      font-size: 1.35rem;
    }

    .page {
      max-width: 1100px;
      margin: 0 auto;
      padding: 32px 20px 60px;
    }

    .hero {
      display: flex;
      flex-wrap: wrap;
      gap: 24px;
      align-items: center;
      justify-content: space-between;
      padding: 24px;
      background: var(--card);
      border-radius: 16px;
      border: 1px solid var(--border);
      box-shadow: var(--shadow);
      margin-bottom: 28px;
    }

    .eyebrow {
      text-transform: uppercase;
      letter-spacing: 0.12em;
      font-size: 0.72rem;
      color: var(--accent);
      font-weight: 600;
      margin-bottom: 8px;
    }

    .subtitle {
      color: var(--muted);
      margin: 8px 0 0;
    }

    .summary {
      min-width: 260px;
    }

    .summary__metric {
      font-size: 0.95rem;
      color: var(--muted);
      display: flex;
      justify-content: space-between;
      margin-bottom: 6px;
    }

    .summary__metric span {
      font-weight: 600;
      color: var(--text);
    }

    .summary__bar {
      height: 8px;
      border-radius: 999px;
      background: #e2e8f0;
      overflow: hidden;
      margin: 10px 0 6px;
    }

    .summary__bar-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--covered), #16a34a);
    }

    .summary__percent {
      font-size: 0.85rem;
      color: var(--muted);
      text-align: right;
    }

    .tag {
      background: var(--card);
      border-radius: 14px;
      border: 1px solid var(--border);
      padding: 20px;
      margin-bottom: 20px;
      box-shadow: var(--shadow);
    }

    .tag__header {
      display: flex;
      align-items: baseline;
      justify-content: space-between;
      gap: 16px;
      flex-wrap: wrap;
      margin-bottom: 12px;
    }

    .tag__meta {
      display: flex;
      gap: 12px;
      color: var(--muted);
      font-size: 0.9rem;
    }

    .tag__bar {
      height: 6px;
      border-radius: 999px;
      background: #e2e8f0;
      overflow: hidden;
      margin-bottom: 16px;
    }

    .tag__bar-fill {
      height: 100%;
      background: linear-gradient(90deg, var(--covered), #22c55e);
    }

    .ops {
      display: grid;
      gap: 10px;
    }

    .op {
      display: grid;
      grid-template-columns: auto 1fr auto auto;
      align-items: center;
      gap: 12px;
      padding: 12px 14px;
      border-radius: 10px;
      border: 1px solid var(--border);
      background: #f8fafc;
      position: relative;
    }

    details.op {
      display: block;
      padding: 0;
      overflow: hidden;
    }

    details.op > summary {
      list-style: none;
      display: grid;
      grid-template-columns: auto 1fr auto auto;
      align-items: center;
      gap: 12px;
      padding: 12px 14px;
      cursor: pointer;
    }

    details.op > summary::-webkit-details-marker {
      display: none;
    }

    .op__summary {
      padding: 0 14px 10px;
      color: var(--muted);
      font-size: 0.9rem;
    }

    .op--empty {
      background: #fdfdfd;
      text-align: center;
      color: var(--muted);
      grid-template-columns: 1fr;
    }

    .op__empty {
      padding: 8px 0;
    }

    .method {
      font-weight: 700;
      font-size: 0.8rem;
      padding: 6px 10px;
      border-radius: 999px;
      color: #fff;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .method--get { background: #22c55e; }
    .method--post { background: #3b82f6; }
    .method--put { background: #f97316; }
    .method--patch { background: #14b8a6; }
    .method--delete { background: #ef4444; }
    .method--options { background: #6366f1; }
    .method--head { background: #64748b; }
    .method--trace { background: #0ea5e9; }

    .path {
      font-family: "JetBrains Mono", "Fira Code", "SFMono-Regular", "Menlo", monospace;
      font-size: 0.95rem;
    }

    .response {
      font-weight: 600;
      color: var(--text);
      font-size: 0.9rem;
    }

    .status {
      font-size: 0.75rem;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      padding: 4px 8px;
      border-radius: 999px;
      background: #e2e8f0;
      color: var(--muted);
    }

    .status--covered { background: rgba(34, 197, 94, 0.12); color: #15803d; }
    .status--uncovered { background: rgba(239, 68, 68, 0.12); color: #b91c1c; }
    .status--extra { background: rgba(245, 158, 11, 0.15); color: #b45309; }

    .responses {
      display: grid;
      gap: 8px;
      padding: 0 14px 14px;
    }

    .responses__label {
      font-size: 0.8rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
      font-weight: 600;
      margin-top: 4px;
    }

    .response-item {
      display: grid;
      grid-template-columns: auto 1fr auto;
      align-items: center;
      gap: 12px;
      padding: 6px 10px;
      border-radius: 8px;
      background: #eef2f7;
      border: 1px solid var(--border);
      font-size: 0.85rem;
    }

    .response-code {
      font-weight: 600;
      font-family: "JetBrains Mono", "Fira Code", "SFMono-Regular", "Menlo", monospace;
    }

    .response-desc {
      color: var(--muted);
    }

    @media (max-width: 720px) {
      .hero {
        flex-direction: column;
        align-items: flex-start;
      }

      .op {
        grid-template-columns: auto 1fr;
      }

      details.op > summary {
        grid-template-columns: auto 1fr;
      }

      .response-item {
        grid-template-columns: auto 1fr;
      }

      .response, .status {
        justify-self: start;
      }
    }
        """
