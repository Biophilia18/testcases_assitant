from __future__ import annotations

import re

from src.api.models import ApiDocument


TITLE_TO_FIELD = {
    "项目/系统名称": "project_name",
    "项目名称": "project_name",
    "系统名称": "project_name",
    "业务模块": "module",
    "模块": "module",
    "接口名称": "api_name",
    "请求方法": "method",
    "请求方式": "method",
    "Method": "method",
    "HTTP Method": "method",
    "接口路径": "path",
    "请求路径": "path",
    "接口地址": "path",
    "请求地址": "path",
    "API地址": "path",
    "URL": "path",
    "鉴权方式": "auth",
    "鉴权": "auth",
    "认证方式": "auth",
    "请求头": "headers",
    "Header": "headers",
    "Headers": "headers",
    "请求参数": "params",
    "入参": "params",
    "请求入参": "params",
    "参数说明": "params",
    "Query参数": "params",
    "字段说明": "params",
    "请求体": "body",
    "请求Body": "body",
    "Body参数": "body",
    "成功响应": "response_example",
    "失败响应": "response_example",
    "响应示例": "response_example",
    "返回示例": "response_example",
    "Response": "response_example",
    "返回参数": "response_example",
    "错误码": "response_example",
    "异常返回": "response_example",
    "失败示例": "response_example",
    "业务规则": "business_rules",
    "数据库校验": "db_checks",
    "数据校验": "db_checks",
}

TITLE_PATTERN = re.compile(
    r"^\s*(?:#{1,6}\s*)?(项目/系统名称|项目名称|系统名称|业务模块|模块|接口名称|请求方法|请求方式|Method|HTTP Method|接口路径|请求路径|接口地址|请求地址|API地址|URL|鉴权方式|鉴权|认证方式|请求头|Header|Headers|请求参数|入参|请求入参|参数说明|Query参数|字段说明|请求体|请求Body|Body参数|成功响应|失败响应|响应示例|返回示例|Response|返回参数|错误码|异常返回|失败示例|业务规则|数据库校验|数据校验)\s*[:：]?\s*(.*)$",
    re.IGNORECASE,
)


def parse_api_document(text: str) -> ApiDocument:
    document = ApiDocument()
    current_field = ""
    buffer: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        match = TITLE_PATTERN.match(line)
        if match:
            _flush(document, current_field, buffer)
            title = _normalize_title(match.group(1))
            current_field = TITLE_TO_FIELD.get(title, "")
            buffer = []
            inline_value = match.group(2).strip()
            if inline_value:
                buffer.append(_clean_list_marker(inline_value))
            continue

        if current_field:
            cleaned = _clean_list_marker(line)
            if cleaned:
                buffer.append(cleaned)

    _flush(document, current_field, buffer)
    document.method = _normalize_method(document.method)
    return document


def api_document_to_fields(document: ApiDocument) -> dict[str, str]:
    return {
        "project_name": document.project_name,
        "module": document.module,
        "api_name": document.api_name,
        "method": document.method,
        "path": document.path,
        "auth": document.auth,
        "headers": document.headers,
        "params": document.params,
        "body": document.body,
        "response_example": document.response_example,
        "business_rules": document.business_rules,
        "db_checks": document.db_checks,
    }


def fields_to_api_document(fields: dict[str, str]) -> ApiDocument:
    return ApiDocument(
        project_name=str(fields.get("project_name", "")).strip(),
        module=str(fields.get("module", "")).strip(),
        api_name=str(fields.get("api_name", "")).strip(),
        method=_normalize_method(str(fields.get("method", "")).strip()),
        path=str(fields.get("path", "")).strip(),
        auth=str(fields.get("auth", "")).strip(),
        headers=str(fields.get("headers", "")).strip(),
        params=str(fields.get("params", "")).strip(),
        body=str(fields.get("body", "")).strip(),
        response_example=str(fields.get("response_example", "")).strip(),
        business_rules=str(fields.get("business_rules", "")).strip(),
        db_checks=str(fields.get("db_checks", "")).strip(),
    )


def _flush(document: ApiDocument, field: str, buffer: list[str]) -> None:
    if not field or not buffer:
        return

    value = "\n".join(part for part in buffer if part).strip()
    if not value:
        return

    current_value = getattr(document, field)
    if current_value:
        setattr(document, field, f"{current_value}\n{value}")
    else:
        setattr(document, field, value)


def _normalize_title(title: str) -> str:
    normalized = title.strip()
    for known_title in TITLE_TO_FIELD:
        if known_title.lower() == normalized.lower():
            return known_title
    return normalized


def _normalize_method(method: str) -> str:
    normalized = method.strip().upper()
    if normalized in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}:
        return normalized
    return method.strip()


def _clean_list_marker(line: str) -> str:
    cleaned = line.strip()
    if re.fullmatch(r"[-*_]{3,}", cleaned):
        return ""
    if cleaned.startswith("```"):
        return ""
    cleaned = re.sub(r"^[-*•]\s*", "", cleaned)
    cleaned = re.sub(r"^\d+[.)、]\s*", "", cleaned)
    return cleaned.strip()
