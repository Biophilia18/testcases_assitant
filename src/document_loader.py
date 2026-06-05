from __future__ import annotations

from io import BytesIO
from zipfile import BadZipFile, ZipFile
import xml.etree.ElementTree as ET


WORD_NAMESPACE = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def load_requirement_document(filename: str, content: bytes) -> str:
    lower_name = filename.lower()
    if lower_name.endswith((".txt", ".md")):
        return _decode_text(content)
    if lower_name.endswith(".docx"):
        return extract_docx_text(content)
    raise ValueError("仅支持 txt、md、docx 文件。")


def extract_docx_text(content: bytes) -> str:
    try:
        with ZipFile(BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, BadZipFile) as exc:
        raise ValueError("无法读取 docx 文档正文。") from exc

    root = ET.fromstring(document_xml)
    paragraphs: list[str] = []

    for paragraph in root.iter(f"{WORD_NAMESPACE}p"):
        texts = [node.text or "" for node in paragraph.iter(f"{WORD_NAMESPACE}t")]
        line = "".join(texts).strip()
        if line:
            paragraphs.append(line)

    return "\n".join(paragraphs)


def _decode_text(content: bytes) -> str:
    try:
        return content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("gbk", errors="ignore")

