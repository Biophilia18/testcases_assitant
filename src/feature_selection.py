from __future__ import annotations

from src.rule_based_generator import RequirementItem


def feature_items_to_rows(items: list[RequirementItem]) -> list[dict[str, str | bool]]:
    return [
        {
            "参与生成": True,
            "模块": item.module,
            "功能点": item.feature,
            "需求片段": item.description,
        }
        for item in items
    ]


def selected_rows_to_feature_source(rows) -> str:
    selected_descriptions = []
    for row in _normalize_rows(rows):
        if bool(row.get("参与生成", False)):
            description = str(row.get("需求片段", "")).strip()
            if description:
                selected_descriptions.append(description)

    return "\n".join(f"{index}. {description}" for index, description in enumerate(selected_descriptions, start=1))


def count_selected_rows(rows) -> int:
    return sum(1 for row in _normalize_rows(rows) if bool(row.get("参与生成", False)))


def _normalize_rows(rows) -> list[dict]:
    if hasattr(rows, "to_dict"):
        return rows.to_dict(orient="records")
    return list(rows or [])
