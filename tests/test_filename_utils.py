from src.filename_utils import build_export_filename


def test_build_export_filename_uses_project_module_type_and_date():
    filename = build_export_filename("订单系统", "退款管理", "功能测试")

    assert filename.startswith("订单系统_退款管理_功能测试_测试用例_")
    assert filename.endswith(".xlsx")


def test_build_export_filename_filters_invalid_characters():
    filename = build_export_filename("订单/系统", "退款:管理", "Web UI 测试")

    assert "/" not in filename
    assert ":" not in filename
    assert filename.endswith(".xlsx")
