from __future__ import annotations

COVERAGE_TYPE_OPTIONS = [
    "正常流程",
    "异常场景",
    "边界/非法输入",
    "权限控制",
    "重复操作",
    "数据一致性",
    "弱网/超时",
    "状态流转",
    "兼容性",
]

DEFAULT_COVERAGE_TYPES = COVERAGE_TYPE_OPTIONS[:6]

COVERAGE_KEYWORDS = {
    "正常流程": ["覆盖类型：正常流程", "正常流程", "正常请求", "正向流程"],
    "异常场景": ["覆盖类型：异常场景", "异常", "失败", "必填", "为空", "缺失"],
    "边界/非法输入": ["覆盖类型：边界/非法输入", "边界", "非法", "格式", "超长", "特殊字符"],
    "权限控制": ["覆盖类型：权限控制", "权限", "无权限", "鉴权", "登录态"],
    "重复操作": ["覆盖类型：重复操作", "重复", "幂等", "连续点击"],
    "数据一致性": ["覆盖类型：数据一致性", "数据一致", "结果查询", "刷新后", "数据库"],
    "弱网/超时": ["覆盖类型：弱网/超时", "弱网", "断网", "超时", "加载"],
    "状态流转": ["覆盖类型：状态流转", "状态流转", "状态更新", "状态变更"],
    "兼容性": ["覆盖类型：兼容性", "兼容", "多设备", "屏幕尺寸"],
}


def normalize_coverage_types(values: list[str] | tuple[str, ...] | None) -> list[str]:
    if not values:
        return DEFAULT_COVERAGE_TYPES.copy()

    normalized: list[str] = []
    for value in values:
        if value in COVERAGE_TYPE_OPTIONS and value not in normalized:
            normalized.append(value)

    return normalized or DEFAULT_COVERAGE_TYPES.copy()


def infer_coverage_types(text: str) -> set[str]:
    matched: set[str] = set()
    for coverage_type, keywords in COVERAGE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            matched.add(coverage_type)
    return matched
