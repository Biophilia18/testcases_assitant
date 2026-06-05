from __future__ import annotations

import re
from dataclasses import dataclass

from src.coverage_config import normalize_coverage_types
from src.models import TestCase
from src.text_utils import normalize_steps
from src.title_utils import build_case_remark, build_case_title, build_feature_name


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
    "控制": "设备控制",
    "下单": "订单",
    "发货": "发货",
    "收货": "收货",
}


@dataclass
class RequirementItem:
    module: str
    feature: str
    description: str


def generate_rule_based_cases(
    requirement_text: str,
    cases_per_feature: int = 6,
    generation_type: str = "功能测试",
    coverage_types: list[str] | None = None,
) -> list[TestCase]:
    items = extract_requirement_items(requirement_text)
    cases: list[TestCase] = []

    for item_index, item in enumerate(items, start=1):
        cases.extend(_build_cases_for_item(item, item_index, cases_per_feature, generation_type, coverage_types))

    return cases


def extract_requirement_items(requirement_text: str) -> list[RequirementItem]:
    blocks = _split_requirement(requirement_text)
    items: list[RequirementItem] = []
    seen: set[str] = set()

    for index, block in enumerate(blocks, start=1):
        module = _guess_module(block, index)
        feature = _guess_feature(block, module)
        key = f"{module}:{feature}:{block}"
        if key in seen:
            continue
        seen.add(key)
        items.append(RequirementItem(module=module, feature=feature, description=block))

    return items or [RequirementItem(module="业务流程", feature="需求整体流程", description=requirement_text.strip())]


def _build_cases_for_item(
    item: RequirementItem,
    item_index: int,
    cases_per_feature: int,
    generation_type: str,
    coverage_types: list[str] | None = None,
) -> list[TestCase]:
    templates = _templates_for_generation_type(generation_type)
    selected_templates = _select_templates(templates, cases_per_feature, coverage_types)

    cases: list[TestCase] = []
    for case_index, template in enumerate(selected_templates, start=1):
        case_id = f"TC-{item_index:02d}-{case_index:02d}"
        cases.append(
            TestCase(
                case_id=case_id,
                module=item.module,
                feature=item.feature,
                title=build_case_title(item.feature, template["title"]),
                precondition=template["precondition"].format(item=item),
                test_data=template["test_data"].format(item=item),
                steps=normalize_steps(template["steps"].format(item=item)),
                expected_result=template["expected_result"].format(item=item),
                priority=template["priority"],
                case_type=template["case_type"],
                remark=build_case_remark(generation_type, template["coverage_type"]),
            )
        )

    return cases


def _select_templates(
    templates: list[dict[str, str]],
    cases_per_feature: int,
    coverage_types: list[str] | None,
) -> list[dict[str, str]]:
    if coverage_types is None:
        normalized_count = max(3, min(cases_per_feature, len(templates)))
        return templates[:normalized_count]

    selected: list[dict[str, str]] = []
    for coverage_type in normalize_coverage_types(coverage_types):
        matched = next((template for template in templates if template["coverage_type"] == coverage_type), None)
        if matched:
            selected.append(matched)

    return selected or templates[: max(3, min(cases_per_feature, len(templates)))]


def _templates_for_generation_type(generation_type: str) -> list[dict[str, str]]:
    if generation_type == "接口测试":
        return [
            _template("接口正常请求验证", "接口地址、鉴权信息和测试数据已准备。", "合法请求参数。", "1. 构造{item.feature}接口合法请求。\n2. 发送请求。\n3. 查看响应体和数据库结果。", "接口返回成功状态码；响应字段、业务状态和数据落库结果正确。", "P1", "接口测试"),
            _template("必填参数缺失校验", "接口可正常访问。", "删除一个或多个必填参数。", "1. 构造缺失必填参数的请求。\n2. 发送请求。", "接口返回明确错误码和错误信息，不产生异常业务数据。", "P1", "异常测试"),
            _template("参数类型和格式校验", "接口可正常访问。", "错误类型、非法格式、超长字符串。", "1. 将关键参数替换为非法格式。\n2. 发送请求。", "接口按规则拒绝非法参数，并返回可定位问题的错误信息。", "P2", "边界测试"),
            _template("鉴权失败校验", "准备无效 token 或无权限账号。", "无效 token、过期 token、无权限 token。", "1. 使用异常鉴权信息请求接口。\n2. 查看响应。", "接口拒绝访问，不泄露敏感数据。", "P1", "权限测试"),
            _template("重复请求幂等校验", "准备可重复提交的业务数据。", "相同请求体和请求标识。", "1. 连续发送两次相同请求。\n2. 查询业务结果。", "接口不产生重复业务结果，幂等处理符合设计。", "P2", "接口测试"),
            _template("响应字段完整性校验", "接口返回数据已准备。", "合法查询条件。", "1. 请求{item.feature}接口。\n2. 校验响应字段、类型和空值。", "响应字段完整，字段类型和业务含义符合接口文档。", "P2", "接口测试"),
        ]

    if generation_type == "Web UI 测试":
        return [
            _template("页面正常流程验证", "用户已登录 Web 系统并具备访问权限。", "正常业务数据。", "1. 打开{item.module}页面。\n2. 执行{item.feature}。\n3. 保存或提交。", "页面提示、跳转、列表和详情数据符合需求。", "P1", "Web UI 测试"),
            _template("表单必填校验", "用户已进入对应页面。", "空值。", "1. 清空必填项。\n2. 点击提交。", "页面展示明确校验提示，表单不提交。", "P1", "异常测试"),
            _template("输入边界校验", "用户已进入对应页面。", "超长文本、特殊字符、边界数值。", "1. 输入边界或特殊数据。\n2. 提交表单。", "页面校验、提示和保存结果符合规则。", "P2", "边界测试"),
            _template("无权限菜单和按钮校验", "准备无权限用户。", "无权限账号。", "1. 使用无权限账号登录。\n2. 查看菜单、按钮和页面访问结果。", "无权限入口不可见或不可操作，直接访问时被拦截。", "P1", "权限测试"),
            _template("重复点击提交校验", "用户已进入可提交页面。", "正常业务数据。", "1. 连续快速点击提交按钮。\n2. 查看页面和业务数据。", "按钮防重复处理有效，不产生重复数据。", "P2", "异常测试"),
            _template("刷新后数据一致性校验", "已完成一次正常操作。", "已保存的业务数据。", "1. 刷新页面。\n2. 返回列表和详情页核对。", "刷新后状态、列表和详情数据保持一致。", "P2", "功能测试"),
        ]

    if generation_type == "App 测试":
        return [
            _template("App 正常流程验证", "用户已登录 App，网络正常。", "正常业务数据。", "1. 打开 App。\n2. 进入{item.module}。\n3. 执行{item.feature}。", "App 页面展示、提交结果和数据状态符合需求。", "P1", "App 测试"),
            _template("弱网场景校验", "可模拟弱网或断网。", "正常业务数据。", "1. 切换到弱网。\n2. 执行{item.feature}。\n3. 恢复网络后查看结果。", "App 有合理加载、失败或重试提示，数据不丢失不重复。", "P1", "兼容性测试"),
            _template("返回和取消操作校验", "用户已进入功能页面。", "部分填写的数据。", "1. 输入部分数据。\n2. 点击返回或取消。\n3. 再次进入页面。", "页面状态和草稿保存策略符合产品设计。", "P2", "异常测试"),
            _template("重复点击校验", "用户已进入可提交页面。", "正常业务数据。", "1. 快速重复点击提交。\n2. 查看结果页和业务记录。", "不产生重复提交，页面有合理防抖或加载状态。", "P2", "异常测试"),
            _template("权限和登录态失效校验", "准备登录态失效或无权限账号。", "过期登录态、无权限账号。", "1. 模拟登录态失效。\n2. 执行{item.feature}。", "App 引导重新登录或拒绝访问，不展示敏感数据。", "P1", "权限测试"),
            _template("多设备兼容校验", "准备不同系统版本或屏幕尺寸设备。", "正常业务数据。", "1. 在不同设备执行{item.feature}。\n2. 核对页面布局和结果。", "不同设备上核心流程可用，关键内容无遮挡。", "P3", "兼容性测试"),
        ]

    return [
        _template("正常流程验证", "用户已具备访问该功能的权限，测试环境和基础数据准备完成。", "正常业务数据。", "1. 进入{item.module}。\n2. 按需求执行：{item.description}\n3. 提交或保存操作结果。", "系统正确完成{item.feature}，页面提示、数据状态与需求描述一致。", "P1", "功能测试"),
        _template("必填项为空校验", "用户已进入对应功能页面。", "关键必填项为空。", "1. 进入{item.feature}页面。\n2. 清空关键必填信息。\n3. 提交表单。", "系统阻止提交，并给出明确的必填项校验提示。", "P1", "异常测试"),
        _template("非法格式或异常数据校验", "用户已进入对应功能页面。", "非法格式、超长内容、特殊字符。", "1. 在{item.feature}相关输入项中输入非法格式、超长内容或特殊字符。\n2. 提交表单。", "系统按规则校验输入；非法数据不能提交，且不产生脏数据。", "P2", "边界测试"),
        _template("无权限访问校验", "准备一个无该功能权限的用户账号。", "无权限账号。", "1. 使用无权限账号登录系统。\n2. 尝试访问或执行{item.feature}。", "系统限制访问或操作，并给出符合权限设计的提示。", "P1", "权限测试"),
        _template("重复提交或重复操作校验", "用户已进入对应功能页面，数据处于可操作状态。", "正常业务数据。", "1. 执行{item.feature}。\n2. 在页面未完全返回前重复点击提交、保存或确认。\n3. 查看业务数据结果。", "系统不应产生重复记录、重复扣费、重复状态流转等异常结果。", "P2", "异常测试"),
        _template("结果查询与数据一致性校验", "已成功完成一次正常流程操作。", "已保存的业务数据。", "1. 完成{item.feature}正常操作。\n2. 返回列表、详情页或关联模块查询该数据。\n3. 刷新页面后再次核对。", "列表、详情、关联数据和刷新后的状态保持一致。", "P2", "功能测试"),
        _template("弱网或超时场景校验", "可模拟弱网、断网或接口超时，用户已进入对应功能页面。", "正常业务数据；弱网或超时环境。", "1. 切换到弱网、断网或模拟接口超时。\n2. 执行{item.feature}。\n3. 恢复网络后再次查看页面和业务数据。", "页面展示加载、失败或重试提示；不会误显示成功，也不会产生错误数据。", "P1", "异常测试", "弱网/超时"),
        _template("状态流转校验", "业务数据已处于可执行该功能的初始状态。", "可触发状态变化的业务数据。", "1. 查看执行前状态。\n2. 执行{item.feature}。\n3. 查看页面、列表和关联数据状态。", "状态按需求正确流转；前后状态、页面展示和业务记录一致。", "P1", "功能测试", "状态流转"),
        _template("兼容性校验", "准备不同浏览器、设备或屏幕尺寸环境。", "正常业务数据。", "1. 在不同浏览器、设备或屏幕尺寸下进入{item.module}。\n2. 执行{item.feature}。\n3. 核对页面布局、按钮和结果展示。", "核心流程在不同环境可正常执行，关键内容无遮挡，结果展示一致。", "P3", "兼容性测试"),
    ]


def _template(
    title: str,
    precondition: str,
    test_data: str,
    steps: str,
    expected_result: str,
    priority: str,
    case_type: str,
    coverage_type: str = "",
) -> dict[str, str]:
    return {
        "title": title,
        "precondition": precondition,
        "test_data": test_data,
        "steps": steps,
        "expected_result": expected_result,
        "priority": priority,
        "case_type": case_type,
        "coverage_type": coverage_type or _infer_template_coverage_type(title, case_type),
    }


def _infer_template_coverage_type(title: str, case_type: str) -> str:
    text = f"{title}{case_type}"
    if any(keyword in text for keyword in ["弱网", "断网", "超时"]):
        return "弱网/超时"
    if "状态流转" in text:
        return "状态流转"
    if "兼容" in text or "多设备" in text:
        return "兼容性"
    if "权限" in text or "鉴权" in text or "登录态" in text:
        return "权限控制"
    if "重复" in text or "幂等" in text:
        return "重复操作"
    if "边界" in text or "非法" in text or "格式" in text:
        return "边界/非法输入"
    if "一致" in text or "查询" in text or "刷新" in text or "响应字段" in text:
        return "数据一致性"
    if "异常" in text or "失败" in text or "必填" in text or "缺失" in text:
        return "异常场景"
    return "正常流程"


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


def _guess_feature(block: str, module: str) -> str:
    return build_feature_name(module, block)
