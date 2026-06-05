from src.feature_selection import count_selected_rows, feature_items_to_rows, selected_rows_to_feature_source
from src.rule_based_generator import RequirementItem


def test_feature_items_to_rows_defaults_to_selected():
    rows = feature_items_to_rows(
        [
            RequirementItem(module="设备控制", feature="设备基础控制", description="用户执行基础控制"),
        ]
    )

    assert rows == [
        {
            "参与生成": True,
            "模块": "设备控制",
            "功能点": "设备基础控制",
            "需求片段": "用户执行基础控制",
        }
    ]


def test_selected_rows_to_feature_source_skips_unselected_rows():
    rows = [
        {"参与生成": True, "需求片段": "用户执行基础控制"},
        {"参与生成": False, "需求片段": "误识别功能点"},
        {"参与生成": True, "需求片段": "控制失败时展示原因"},
    ]

    source = selected_rows_to_feature_source(rows)

    assert source == "1. 用户执行基础控制\n2. 控制失败时展示原因"
    assert count_selected_rows(rows) == 2
