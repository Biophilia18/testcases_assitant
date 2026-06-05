from src.title_utils import build_case_remark, build_case_title, build_feature_name


def test_build_feature_name_uses_module_domain_and_action():
    feature = build_feature_name("设备控制", "用户点击控制按钮后，App 向服务端发送控制指令")

    assert feature == "控制指令发送"


def test_build_feature_name_extracts_action_from_business_text():
    feature = build_feature_name("服务预约管理", "普通用户进入服务预约页面，选择服务类型并提交预约")

    assert feature == "服务预约"


def test_build_case_title_removes_redundant_suffix():
    assert build_case_title("设备控制", "正常流程验证") == "设备控制-正常流程"


def test_build_case_remark_is_concise():
    remark = build_case_remark("功能测试", "弱网/超时")

    assert remark == "功能测试规则生成；覆盖：弱网/超时；建议人工复核。"


def test_build_feature_name_uses_business_semantic_patterns():
    assert build_feature_name("设备控制", "用户可以对设备执行基础控制操作") == "设备基础控制"
    assert build_feature_name("业务模块", "控制失败时页面给出失败原因") == "失败提示"
    assert build_feature_name("业务模块", "弱网或断网情况下页面展示加载状态") == "弱网处理"
