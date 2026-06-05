from __future__ import annotations

import re


ACTION_LABELS = {
    "登录": "登录",
    "注册": "注册",
    "查询": "查询",
    "搜索": "查询",
    "筛选": "筛选",
    "新增": "新增",
    "创建": "创建",
    "编辑": "编辑",
    "修改": "修改",
    "删除": "删除",
    "提交": "提交",
    "审核": "审核",
    "审批": "审批",
    "导入": "导入",
    "导出": "导出",
    "上传": "上传",
    "下载": "下载",
    "支付": "支付",
    "退款": "退款",
    "控制": "控制",
    "绑定": "绑定",
    "派单": "派单",
    "预约": "预约",
    "告警": "告警",
}


def build_feature_name(module: str, text: str) -> str:
    compact = _clean_text(text)
    if not compact:
        return module or "业务流程"

    special_name = _special_feature_name(compact)
    if special_name:
        return special_name

    domain = _domain_from_module(module)
    action = _first_action(compact)
    object_name = _object_before_action(compact, action) if action else ""

    if len(domain) >= 4 and domain in compact:
        return domain
    if domain and domain.endswith(action):
        return domain
    if domain and action:
        return f"{domain}{action}"
    if object_name and action:
        return f"{object_name}{action}"
    if action:
        return f"{domain or '业务'}{action}"

    return _fallback_feature_name(compact)


def build_case_title(feature: str, template_title: str) -> str:
    short_template = template_title
    short_template = short_template.replace("验证", "")
    short_template = short_template.replace("校验", "")
    short_template = short_template.strip("- ")
    return f"{feature}-{short_template}"


def build_case_remark(generation_type: str, coverage_type: str) -> str:
    return f"{generation_type}规则生成；覆盖：{coverage_type}；建议人工复核。"


def _clean_text(text: str) -> str:
    compact = re.sub(r"\s+", "", text or "")
    compact = re.sub(r"^(用户|管理员|系统|平台|客服|审核人|财务|仓库|运营|买家|卖家|商家|申请人|审批人|运维人员)", "", compact)
    compact = re.sub(r"^(支持|需要|可以|能够|发起|进行|继续|再次)", "", compact)
    compact = re.sub(r"^(在|进入|对|进行)", "", compact)
    return compact.strip("，,。；;后")


def _domain_from_module(module: str) -> str:
    domain = (module or "").strip()
    for suffix in ["管理", "模块", "功能", "页面"]:
        domain = domain.removesuffix(suffix)

    if domain in {"查询", "数据维护", "流程提交", "审核审批"}:
        return ""
    if domain in {"账号登录", "账号注册", "数据导入", "数据导出"}:
        return domain.removesuffix("登录").removesuffix("注册").removesuffix("导入").removesuffix("导出")
    if domain == "设备控制":
        return "设备"
    if domain:
        return domain[:8]
    return ""


def _first_action(text: str) -> str:
    for keyword, label in ACTION_LABELS.items():
        if keyword in text:
            return label
    return ""


def _object_before_action(text: str, action: str) -> str:
    if not action:
        return ""

    index = text.find(action)
    if index <= 0:
        return ""

    before = text[:index]
    before = re.sub(r"^(进入|打开|选择|填写|查看|点击|扫描|输入|确认)", "", before)
    before = re.sub(r"(页面|列表|详情页|中心|按钮)$", "", before)
    return before[-8:]


def _fallback_feature_name(text: str) -> str:
    for marker in ["，", "。", "；", ",", ";"]:
        if marker in text:
            text = text.split(marker, 1)[0]
            break
    if len(text) <= 16:
        return text
    return text[:16]


def _special_feature_name(text: str) -> str:
    patterns = [
        (r"基础控制", "设备基础控制"),
        (r"发送控制指令|控制指令", "控制指令发送"),
        (r"弱网|断网|网络", "弱网处理"),
        (r"状态.*更新|更新.*状态", "状态更新"),
        (r"失败原因|失败提示|失败时", "失败提示"),
        (r"预约", "服务预约"),
        (r"派单", "服务派单"),
        (r"告警", "告警处理"),
        (r"绑定", "设备绑定"),
    ]
    for pattern, name in patterns:
        if re.search(pattern, text):
            return name
    return ""
