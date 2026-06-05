from io import BytesIO
from zipfile import ZipFile

import pytest

from src.document_loader import extract_docx_text, load_requirement_document


def test_load_requirement_document_decodes_text_file():
    text = load_requirement_document("requirement.txt", "项目名称：订单系统".encode("utf-8"))

    assert text == "项目名称：订单系统"


def test_extract_docx_text_reads_paragraphs():
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    <w:p><w:r><w:t>项目/系统名称：爱家政服务管理系统</w:t></w:r></w:p>
    <w:p><w:r><w:t>业务模块：服务预约管理</w:t></w:r></w:p>
  </w:body>
</w:document>
"""
    buffer = BytesIO()
    with ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)

    text = extract_docx_text(buffer.getvalue())

    assert "项目/系统名称：爱家政服务管理系统" in text
    assert "业务模块：服务预约管理" in text


def test_extract_docx_text_rejects_invalid_docx():
    with pytest.raises(ValueError):
        extract_docx_text(b"not a docx")

