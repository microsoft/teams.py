"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal

from microsoft_teams.cards import (
    AdaptiveCard,
    CardElement,
    ColumnDefinition,
    Container,
    DonutChartData,
    HorizontalBarChart,
    HorizontalBarChartDataValue,
    LineChart,
    LineChartData,
    LineChartValue,
    PieChart,
    Table,
    TableCell,
    TableRow,
    TextBlock,
    VerticalBarChart,
    VerticalBarChartDataValue,
)

from .index import KBDoc

ChartType = Literal["verticalBar", "horizontalBar", "line", "pie", "table"]


def _coerce_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("$", "").replace("%", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _numeric_rows(rows: list[list[Any]]) -> list[tuple[Any, float]]:
    out: list[tuple[Any, float]] = []
    for r in rows:
        if len(r) < 2:
            continue
        n = _coerce_number(r[1])
        if n is None:
            continue
        out.append((r[0], n))
    return out


def _sources_footer(sources: list[KBDoc]) -> list[CardElement]:
    if not sources:
        return []
    items: list[CardElement] = [
        TextBlock(text="Sources", weight="Bolder", size="Small", spacing="Medium"),
    ]
    for s in sources:
        items.append(TextBlock(text=f"**{s.title}** — `{s.source}`", wrap=True, size="Small"))
    return items


def build_answer_card(answer: str, sources: list[KBDoc]) -> AdaptiveCard:
    """Render an answer + cited sources as an Adaptive Card."""
    body: list[CardElement] = [
        TextBlock(text="Answer", weight="Bolder", size="Medium"),
        TextBlock(text=answer, wrap=True),
    ]
    if sources:
        body.append(TextBlock(text="Sources", weight="Bolder", size="Small", spacing="Medium"))
        for s in sources:
            body.append(
                Container(
                    items=[
                        TextBlock(text=f"**{s.title}** — `{s.source}`", wrap=True, size="Small"),
                        TextBlock(text=s.snippet, wrap=True, size="Small", is_subtle=True),
                    ],
                    spacing="Small",
                )
            )
    card = AdaptiveCard(version="1.6")
    card.body = body
    return card


def build_chart_card(
    chart_type: ChartType,
    rows: list[list[Any]],
    title: str,
    sources: list[KBDoc],
) -> AdaptiveCard:
    """Render a chart or table with an optional cited-sources footer."""
    if chart_type == "verticalBar":
        element: CardElement = VerticalBarChart(
            title=title,
            data=[VerticalBarChartDataValue(x=label, y=val) for label, val in _numeric_rows(rows)],
        )
    elif chart_type == "horizontalBar":
        element = HorizontalBarChart(
            title=title,
            data=[HorizontalBarChartDataValue(x=str(label), y=val) for label, val in _numeric_rows(rows)],
        )
    elif chart_type == "line":
        element = LineChart(
            title=title,
            data=[
                LineChartData(
                    legend=title,
                    values=[LineChartValue(x=label, y=val) for label, val in _numeric_rows(rows)],
                )
            ],
        )
    elif chart_type == "pie":
        element = PieChart(
            title=title,
            data=[DonutChartData(legend=str(label), value=val) for label, val in _numeric_rows(rows)],
            color_set="categorical",
        )
    else:  # table
        col_count = max((len(r) for r in rows), default=1)
        element = Table(
            first_row_as_headers=True,
            columns=[ColumnDefinition(width=1) for _ in range(col_count)],
            rows=[TableRow(cells=[TableCell(items=[TextBlock(text=str(cell))]) for cell in row]) for row in rows],
        )

    body: list[CardElement] = [TextBlock(text=title, weight="Bolder", size="Medium"), element]
    body.extend(_sources_footer(sources))
    card = AdaptiveCard(version="1.6")
    card.body = body
    return card
