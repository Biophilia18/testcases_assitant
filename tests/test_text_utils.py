from src.text_utils import normalize_steps


def test_normalize_steps_adds_newlines_before_numbered_steps():
    steps = "1. 打开页面 2. 输入订单号 3. 点击查询"

    assert normalize_steps(steps) == "1. 打开页面\n2. 输入订单号\n3. 点击查询"


def test_normalize_steps_keeps_existing_newlines_clean():
    steps = "1. 打开页面\n\n2. 输入订单号\n3. 点击查询"

    assert normalize_steps(steps) == "1. 打开页面\n2. 输入订单号\n3. 点击查询"


def test_normalize_steps_handles_python_list_string():
    steps = "['打开登录页面', '输入用户名 test_user', '点击登录按钮']"

    assert normalize_steps(steps) == "1. 打开登录页面\n2. 输入用户名 test_user\n3. 点击登录按钮"


def test_normalize_steps_handles_list_value():
    steps = ["打开登录页面", "输入用户名 test_user", "点击登录按钮"]

    assert normalize_steps(steps) == "1. 打开登录页面\n2. 输入用户名 test_user\n3. 点击登录按钮"

