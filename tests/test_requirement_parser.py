from src.requirement_parser import parse_requirement_text


def test_parse_requirement_text_with_colon_fields():
    text = """项目名称：订单系统
业务模块：退款管理
使用角色：普通用户、客服
前置条件：用户已登录，存在可退款订单
业务流程：用户查询订单，提交退款申请，客服审核通过后系统退款
验收标准：退款成功后订单状态变更
补充规则：重复提交不得产生多条退款单
"""

    parsed = parse_requirement_text(text)

    assert parsed.project_name == "订单系统"
    assert parsed.business_module == "退款管理"
    assert "普通用户" in parsed.user_role
    assert "用户已登录" in parsed.precondition
    assert "提交退款申请" in parsed.business_flow
    assert "订单状态变更" in parsed.acceptance_criteria
    assert "重复提交" in parsed.constraints


def test_parse_requirement_text_with_markdown_headings():
    text = """# 登录功能

## 前置条件
用户未登录，已注册账号。

## 需求描述
用户打开登录页，输入账号密码后登录系统。

## 验收标准
密码正确时进入首页，密码错误时提示错误原因。
"""

    parsed = parse_requirement_text(text)

    assert "用户未登录" in parsed.precondition
    assert "输入账号密码" in parsed.business_flow
    assert "密码错误" in parsed.acceptance_criteria


def test_parse_requirement_text_without_known_fields_goes_to_business_flow():
    text = """用户登录后进入订单页面。
选择订单并提交退款申请。
客服审核通过后系统原路退款。
"""

    parsed = parse_requirement_text(text)

    assert parsed.project_name == ""
    assert "提交退款申请" in parsed.business_flow
    assert "原路退款" in parsed.business_flow


def test_parse_requirement_text_keeps_free_text_as_flow_after_metadata():
    text = """项目名称：订单系统
业务模块：退款管理
用户查询订单并提交退款申请。
客服审核通过后系统原路退款。
"""

    parsed = parse_requirement_text(text)

    assert parsed.project_name == "订单系统"
    assert parsed.business_module == "退款管理"
    assert parsed.business_flow == "用户查询订单并提交退款申请。\n客服审核通过后系统原路退款。"


def test_parse_requirement_text_with_slash_titles_from_realistic_sample():
    text = """项目/系统名称：爱家政服务管理系统

业务模块：服务预约管理

使用角色：普通用户、客服人员

前置条件：用户已登录，服务项目已上架，服务区域和服务时间段已配置。

业务流程/需求描述：
普通用户进入服务预约页面，选择服务类型、服务地址、预约日期、预约时间段，并填写联系人、联系电话和备注信息。
提交预约后，系统生成预约单，预约状态为“待派单”。客服人员也可以在后台为用户创建预约单。预约创建成功后，用户可以在我的预约中查看预约详情。

验收标准：
1. 服务类型、地址、时间、联系人和联系电话填写完整时可以成功创建预约。
2. 预约创建成功后生成唯一预约单号。
3. 新预约单状态为“待派单”。
4. 用户只能查看自己的预约单。
5. 客服人员可以查看所有待派单预约。
6. 页面展示的预约信息与数据库预约记录一致。

补充规则/异常场景：
服务类型不能为空。
预约时间不能早于当前时间。
联系电话必须符合手机号格式。
服务地址超出服务范围时不能提交预约。
重复点击提交按钮不能生成多条预约单。
同一用户同一时间段不能重复预约相同服务。
已取消的预约不能再次派单。
"""

    parsed = parse_requirement_text(text)

    assert parsed.project_name == "爱家政服务管理系统"
    assert parsed.business_module == "服务预约管理"
    assert parsed.user_role == "普通用户、客服人员"
    assert "服务项目已上架" in parsed.precondition
    assert "普通用户进入服务预约页面" in parsed.business_flow
    assert "预约创建成功后生成唯一预约单号" in parsed.acceptance_criteria
    assert "联系电话必须符合手机号格式" in parsed.constraints
    assert "补充规则/异常场景" not in parsed.business_flow


def test_parse_requirement_text_removes_markdown_list_markers():
    text = """#### 验收标准:
- 1. 服务类型、地址、时间填写完整时可以成功创建预约。
- 2. 预约创建成功后生成唯一预约单号。

#### 补充规则/异常场景:
- 服务类型不能为空。
- 预约时间不能早于当前时间。
"""

    parsed = parse_requirement_text(text)

    assert parsed.acceptance_criteria.splitlines()[0] == "服务类型、地址、时间填写完整时可以成功创建预约。"
    assert parsed.acceptance_criteria.splitlines()[1] == "预约创建成功后生成唯一预约单号。"
    assert parsed.constraints.splitlines()[0] == "服务类型不能为空。"
    assert parsed.constraints.splitlines()[1] == "预约时间不能早于当前时间。"
