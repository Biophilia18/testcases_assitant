from src.generation_preview import build_generation_preview
from src.ai_client import generate_cases


STRUCTURED_REQUIREMENT = """用例生成类型：功能测试
项目/系统名称：智控家监测系统
业务模块：基础设备控制
使用角色：App 普通用户
前置条件：用户已绑定设备，设备在线，用户具备控制权限。
业务流程/需求描述：用户进入设备详情页后，可以对设备执行基础控制操作，例如开启、关闭、切换工作模式等。用户点击控制按钮后，App 向服务端发送控制指令，服务端返回处理结果。控制成功后页面更新设备状态；控制失败时页面给出失败原因。弱网或断网情况下，App 需要展示加载状态或失败提示，不能造成状态误更新。
验收标准：
1. 在线设备可以执行基础控制操作。
2. 控制成功后页面状态正确更新。
3. 控制结果与服务端接口返回一致。
4. 控制结果与数据库设备状态记录一致。
5. 弱网下点击控制按钮时页面展示处理中状态。
6. 控制失败时页面提示失败原因。
补充规则/异常场景：
设备离线时不能执行控制操作。
用户无权限时不能控制设备。
重复点击控制按钮不能重复发送大量控制请求。
接口超时时页面不能误显示控制成功。
断网恢复后可以重新发起控制。
服务端返回异常状态码时页面需要给出明确提示。
"""


BUSINESS_FLOW = (
    "用户进入设备详情页后，可以对设备执行基础控制操作，例如开启、关闭、切换工作模式等。"
    "用户点击控制按钮后，App 向服务端发送控制指令，服务端返回处理结果。"
    "控制成功后页面更新设备状态；控制失败时页面给出失败原因。"
    "弱网或断网情况下，App 需要展示加载状态或失败提示，不能造成状态误更新。"
)


def test_build_generation_preview_counts_features_and_cases():
    text = "用户登录系统后查询订单，提交退款申请。"

    preview = build_generation_preview(text, cases_per_feature=3)

    assert len(preview.feature_items) >= 2
    assert preview.estimated_case_count == len(preview.feature_items) * 3


def test_build_generation_preview_warns_when_case_count_is_high():
    text = "\n".join(f"{index}. 用户执行查询操作{index}" for index in range(1, 20))

    preview = build_generation_preview(text, cases_per_feature=3)

    assert preview.estimated_case_count >= 50
    assert any("数量偏多" in warning for warning in preview.warnings)


def test_build_generation_preview_uses_business_flow_as_feature_source():
    preview = build_generation_preview(
        STRUCTURED_REQUIREMENT,
        cases_per_feature=3,
        feature_source_text=BUSINESS_FLOW,
    )
    feature_text = "\n".join(item.description for item in preview.feature_items)

    assert len(preview.feature_items) < 10
    assert "项目/系统名称" not in feature_text
    assert "验收标准" not in feature_text
    assert "补充规则/异常场景" not in feature_text


def test_rule_generation_uses_business_flow_as_feature_source():
    result = generate_cases(
        requirement_text=STRUCTURED_REQUIREMENT,
        mode="规则生成",
        cases_per_feature=3,
        provider="DeepSeek",
        generation_type="功能测试",
        feature_source_text=BUSINESS_FLOW,
    )

    assert result.feature_count < 10
    assert result.case_count == result.feature_count * 3
    assert all("项目/系统名称" not in case.feature for case in result.cases)


def test_build_generation_preview_counts_selected_coverage_types():
    preview = build_generation_preview(
        STRUCTURED_REQUIREMENT,
        cases_per_feature=6,
        feature_source_text=BUSINESS_FLOW,
        coverage_types=["正常流程", "弱网/超时"],
    )

    assert preview.coverage_types == ["正常流程", "弱网/超时"]
    assert preview.cases_per_feature == 2
    assert preview.estimated_case_count == len(preview.feature_items) * 2
