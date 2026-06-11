from src.api.ui import _api_method_for_select


def test_api_method_for_select_keeps_head_and_options() -> None:
    assert _api_method_for_select("HEAD") == "HEAD"
    assert _api_method_for_select("options") == "OPTIONS"


def test_api_method_for_select_falls_back_to_post() -> None:
    assert _api_method_for_select("") == "POST"
    assert _api_method_for_select("TRACE") == "POST"
