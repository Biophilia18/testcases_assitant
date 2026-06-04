from __future__ import annotations

import re
from dataclasses import dataclass

from src.models import TestCase


ACTION_MODULES = {
    "登录": "账号登录",
    "注册": "账号注册",
    "验证码": "验证码",
    "查询": "查询",
    "搜索": "查询",
    "筛选": "查询",
    "新增": "数据维护",
    "创建": "数据维护",
    "编辑": "数据维护",
    "修改": "数据维护",
    "删除": "数据维护",
    "提交": "流程提交",
    "审核": "审核审批",
    "审批": "审核审批",
    "导入": "数据导入",
    "导出": "数据导出",
    "上传": "文件上传",
    "下载": "文件下载",
    "支付": "支付",
    "退款": "退款",
    "下单": "订单",
    "发货": "发货",
    "收货": "收货",
}


@dataclass
class RequirementItem:
    module: str
    feature: str
    description: str


def generate_rule_based_cases(requirement_text: str, cases_per_feature: int = 6) -> list[TestCase]:
    items = extract_requirement_items(requirement_text)
    cases: list[TestCase] = []

    for item in items:
        cases.extend(_build_cases_for_item(item, cases_per_feature))

    return cases


def extract_requirement_items(requirement_text: str) -> list[RequirementItem]:
    blocks = _split_requirement(requirement_text)
    items: list[RequirementItem] = []
    seen: set[str] = set()

    for index, block in enumerate(blocks, start=1):
        module = _guess_module(block, index)
        feature = _guess_feature(block)
        key = f"{module}:{feature}"
        if key in seen:
            continue
        seen.add(key)
        items.append(RequirementItem(module=module, feature=feature, description=block))

    return items or [RequirementItem(module="业务流程", feature="需求整体流程", description=requirement_text.strip())]


def _build_cases_for_item(item: RequirementItem, cases_per_feature: int) -> list[TestCase]:
    templates = [
        TestCase(
            module=item.module,
            feature=item.feature,
            title=f"{item.feature}-正常流程验证",
            precondition="用户已具备访问该功能的权限，测试环境和基础数据准备完成。",
            steps=f"1. 进入{item.module}。\n2. 按需求执行：{item.description}\n3. 提交或保存操作结果。",
            expected_result=f"系统正确完成{item.feature}，页面提示、数据状态与需求描述一致。",
            priority="P1",
            case_type="功能测试",
        ),
        TestCase(
            module=item.module,
            feature=item.feature,
            title=f"{item.feature}-必填项为空校验",
            precondition="用户已进入对应功能页面。",
            steps=f"1. 进入{item.feature}页面。\n2. 清空关键必填信息。\n3. 提交表单。",
            expected_result="系统阻止提交，并给出明确的必填项校验提示。",
            priority="P1",
            case_type="异常测试",
        ),
        TestCase(
            module=item.module,
            feature=item.feature,
            title=f"{item.feature}-非法格式或异常数据校验",
            precondition="用户已进入对应功能页面。",
            steps=f"1. 在{item.feature}相关输入项中输入非法格式、超长内容或特殊字符。\n2. 提交表单。",
            expected_result="系统按规则校验输入；非法数据不能提交，且不产生脏数据。",
            priority="P2",
            case_type="边界测试",
        ),
        TestCase(
            module=item.module,
            feature=item.feature,
            title=f"{item.feature}-无权限访问校验",
            precondition="准备一个无该功能权限的用户账号。",
            steps=f"1. 使用无权限账号登录系统。\n2. 尝试访问或执行{item.feature}。",
            expected_result="系统限制访问或操作，并给出符合权限设计的提示。",
            priority="P1",
            case_type="权限测试",
        ),
        TestCase(
            module=item.module,
            feature=item.feature,
            title=f"{item.feature}-重复提交或重复操作校验",
            precondition="用户已进入对应功能页面，数据处于可操作状态。",
            steps=f"1. 执行{item.feature}。\n2. 在页面未完全返回前重复点击提交、保存或确认。\n3. 查看业务数据结果。",
            expected_result="系统不应产生重复记录、重复扣费、重复状态流转等异常结果。",
            priority="P2",
            case_type="异常测试",
        ),
        TestCase(
            module=item.module,
            feature=item.feature,
            title=f"{item.feature}-结果查询与数据一致性校验",
            precondition="已成功完成一次正常流程操作。",
            steps=f"1. 完成{item.feature}正常操作。\n2. 返回列表、详情页或关联模块查询该数据。\n3. 刷新页面后再次核对。",
            expected_result="列表、详情、关联数据和刷新后的状态保持一致。",
            priority="P2",
            case_type="功能测试",
        ),
        TestCase(
            module=item.module,
            feature=item.feature,
            title=f"{item.feature}-取消或返回后数据不落库校验",
            precondition="用户已进入对应功能页面。",
            steps=f"1. 输入部分业务数据。\n2. 点击取消、返回或关闭页面。\n3. 重新进入页面或查询列表。",
            expected_result="未确认提交的数据不应被保存；页面状态符合产品设计。",
            priority="P3",
            case_type="异常测试",
        ),
        TestCase(
            module=item.module,
            feature=item.feature,
            title=f"{item.feature}-多角色流程流转校验",
            precondition="准备流程涉及的不同角色账号和测试数据。",
            steps=f"1. 使用发起人账号完成{item.feature}。\n2. 切换到下一处理角色继续操作。\n3. 核对流程状态和待办数据。",
            expected_result="流程节点、处理人、状态变化和通知结果符合需求。",
            priority="P2",
            case_type="流程测试",
        ),
    ]

    normalized_count = max(3, min(cases_per_feature, len(templates)))
    return templates[:normalized_count]


def _split_requirement(requirement_text: str) -> list[str]:
    normalized = requirement_text.strip()
    if not normalized:
        return []

    numbered_parts = re.split(
        r"(?:^|\n)\s*(?:[-*•]|\d+[.)、]|[一二三四五六七八九十]+[、.])\s*",
        normalized,
    )
    blocks = [part.strip() for part in numbered_parts if _is_meaningful(part)]

    if len(blocks) <= 1:
        blocks = _split_workflow_sentence(normalized)

    return blocks[:30]


def _split_workflow_sentence(text: str) -> list[str]:
    sentence_parts = re.split(r"[。；;\n]+", text)
    blocks: list[str] = []

    for sentence in sentence_parts:
        sentence = sentence.strip()
        if not _is_meaningful(sentence):
            continue

        chunks = _split_by_business_actions(sentence)
        blocks.extend(chunk for chunk in chunks if _is_meaningful(chunk))

    return blocks


def _split_by_business_actions(sentence: str) -> list[str]:
    action = (
        r"(?:登录|注册|查询|搜索|筛选|新增|创建|编辑|修改|删除|提交|审核|审批|"
        r"导入|导出|上传|下载|支付|下单|发货|收货)"
    )
    actor = r"(?:用户|管理员|系统|平台|客服|审核人|财务|仓库|运营|买家|卖家|商家)?"
    modal = r"(?:可以|需要|能够|支持|发起|进行|继续|再次)?"

    chunks = re.split(
        rf"(?:，|,|\s+|然后|并且|且|后|之后)(?={actor}{modal}{action})",
        sentence,
    )

    refined: list[str] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        refined.extend(_split_single_chunk_with_multiple_actions(chunk, action))

    return refined


def _split_single_chunk_with_multiple_actions(chunk: str, action_pattern: str) -> list[str]:
    matches = list(re.finditer(action_pattern, chunk))
    if len(matches) <= 1:
        return [chunk]

    parts: list[str] = []
    for index, match in enumerate(matches):
        start = 0 if index == 0 else match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(chunk)
        part = chunk[start:end].strip("，,；; ")
        if _is_meaningful(part):
            parts.append(part)

    return parts or [chunk]


def _is_meaningful(text: str) -> bool:
    return len(text.strip()) >= 4


def _guess_module(block: str, index: int) -> str:
    for pattern in [r"([^，。；;\n]{2,16})模块", r"([^，。；;\n]{2,16})页面", r"([^，。；;\n]{2,16})功能"]:
        match = re.search(pattern, block)
        if match:
            return match.group(1).strip()

    for keyword, module in ACTION_MODULES.items():
        if keyword in block:
            return module

    return f"业务模块{index}"


def _guess_feature(block: str) -> str:
    compact = re.sub(r"\s+", "", block)
    compact = re.sub(r"^(用户|管理员|系统|平台|客服|审核人|财务|仓库|运营)", "", compact)
    compact = re.sub(r"^(支持|需要|可以|能够|发起|进行|继续|再次)", "", compact)
    compact = re.sub(r"^(在|进入|对|进行)", "", compact)
    compact = compact.strip("，,。；;后")
    return compact[:24] if len(compact) > 24 else compact
