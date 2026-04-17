"""
Copyright (c) Microsoft Corporation. All rights reserved.
Licensed under the MIT License.
"""

from typing import Any, Literal

from microsoft_teams.cards import (
    AdaptiveCard,
    ColumnDefinition,
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

ChartType = Literal["verticalBar", "horizontalBar", "line", "pie", "table"]


def _coerce_number(value: Any) -> float | None:
    """Coerce a value to float, stripping currency/thousands separators. Return None if not numeric."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.strip().replace(",", "").replace("$", "").replace("%", "")
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def numeric_rows(rows: list[list[Any]]) -> list[tuple[Any, float]]:
    """Return (label, value) pairs, dropping rows whose value is non-numeric (e.g. header rows)."""
    out: list[tuple[Any, float]] = []
    for r in rows:
        if len(r) < 2:
            continue
        n = _coerce_number(r[1])
        if n is None:
            continue
        out.append((r[0], n))
    return out


def build_card(chart_type: ChartType, rows: list[list[Any]], options: dict[str, Any] | None) -> AdaptiveCard:
    """Build an AdaptiveCard containing a title TextBlock + the requested chart/table element."""
    opts = options or {}
    title = str(opts.get("title", "Chart"))
    x_axis = opts.get("xAxisTitle")
    y_axis = opts.get("yAxisTitle")

    if chart_type == "verticalBar":
        element = VerticalBarChart(
            title=title,
            x_axis_title=x_axis,
            y_axis_title=y_axis,
            data=[VerticalBarChartDataValue(x=label, y=val) for label, val in numeric_rows(rows)],
        )
    elif chart_type == "horizontalBar":
        element = HorizontalBarChart(
            title=title,
            x_axis_title=x_axis,
            y_axis_title=y_axis,
            data=[HorizontalBarChartDataValue(x=str(label), y=val) for label, val in numeric_rows(rows)],
        )
    elif chart_type == "line":
        element = LineChart(
            title=title,
            x_axis_title=x_axis,
            y_axis_title=y_axis,
            data=[
                LineChartData(
                    legend=title,
                    values=[LineChartValue(x=label, y=val) for label, val in numeric_rows(rows)],
                )
            ],
        )
    elif chart_type == "pie":
        element = PieChart(
            title=title,
            data=[DonutChartData(legend=str(label), value=val) for label, val in numeric_rows(rows)],
            color_set="categorical",
        )
    elif chart_type == "table":
        col_count = max((len(r) for r in rows), default=1)
        element = Table(
            first_row_as_headers=True,
            columns=[ColumnDefinition(width=1) for _ in range(col_count)],
            rows=[TableRow(cells=[TableCell(items=[TextBlock(text=str(cell))]) for cell in row]) for row in rows],
        )

    card = AdaptiveCard(version="1.6")
    card.body = [TextBlock(text=title, weight="Bolder", size="Medium"), element]
    return card
