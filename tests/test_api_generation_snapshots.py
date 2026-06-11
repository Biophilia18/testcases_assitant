from collections import Counter

from src.api.design_plan import build_api_design_plan
from src.api.document_parser import parse_api_document
from src.api.examples import API_EXAMPLE_BY_NAME
from src.api.rule_generator import generate_api_cases


SNAPSHOTS = {
    "爱家政：创建服务预约接口": {
        "method": "POST",
        "case_count": 17,
        "first_title": "正常请求-创建服务预约接口成功",
        "types": {
            "正常请求": 1,
            "参数校验": 4,
            "边界值": 2,
            "鉴权校验": 1,
            "权限校验": 1,
            "业务规则": 2,
            "幂等校验": 1,
            "响应断言": 1,
            "数据库校验": 4,
        },
    },
    "物资后勤：提交物资领用申请接口": {
        "method": "POST",
        "case_count": 18,
        "first_title": "正常请求-提交物资领用申请接口成功",
        "types": {
            "正常请求": 1,
            "参数校验": 3,
            "边界值": 3,
            "鉴权校验": 1,
            "权限校验": 1,
            "业务规则": 2,
            "幂等校验": 1,
            "响应断言": 1,
            "数据库校验": 5,
        },
    },
    "智控家：设备控制接口": {
        "method": "POST",
        "case_count": 16,
        "first_title": "正常请求-设备控制接口成功",
        "types": {
            "正常请求": 1,
            "参数校验": 3,
            "边界值": 3,
            "鉴权校验": 1,
            "权限校验": 1,
            "业务规则": 2,
            "幂等校验": 1,
            "响应断言": 1,
            "数据库校验": 3,
        },
    },
    "爱家政：查询预约详情接口": {
        "method": "GET",
        "case_count": 11,
        "first_title": "正常请求-查询预约详情接口成功",
        "types": {
            "正常请求": 1,
            "参数校验": 2,
            "鉴权校验": 1,
            "权限校验": 1,
            "业务规则": 2,
            "幂等校验": 1,
            "响应断言": 1,
            "数据库校验": 2,
        },
    },
    "爱家政：修改预约信息接口": {
        "method": "PUT",
        "case_count": 15,
        "first_title": "正常请求-修改预约信息接口成功",
        "types": {
            "正常请求": 1,
            "参数校验": 5,
            "边界值": 1,
            "鉴权校验": 1,
            "权限校验": 1,
            "业务规则": 2,
            "幂等校验": 1,
            "响应断言": 1,
            "数据库校验": 2,
        },
    },
}


def test_api_generation_snapshots_for_representative_examples() -> None:
    for example_name, snapshot in SNAPSHOTS.items():
        document = parse_api_document(API_EXAMPLE_BY_NAME[example_name].text)
        plan = build_api_design_plan(document, strategy="标准")
        cases = generate_api_cases(document, plan_items=plan.plan_items, strategy=plan.strategy)

        assert document.method == snapshot["method"], example_name
        assert len(cases) == snapshot["case_count"], example_name
        assert cases[0].case_title == snapshot["first_title"], example_name
        assert Counter(case.case_type for case in cases) == snapshot["types"], example_name
        assert [case.case_id for case in cases] == [f"API-01-{index:02d}" for index in range(1, len(cases) + 1)]
