import fitz  # PyMuPDF
from docx import Document


def read_txt(file_bytes: bytes) -> str:
    return file_bytes.decode("utf-8")


def read_docx(file_bytes: bytes) -> str:
    from io import BytesIO
    doc = Document(BytesIO(file_bytes))
    return "\n".join([p.text for p in doc.paragraphs])


def read_pdf(file_bytes: bytes) -> str:
    from io import BytesIO
    text = ""
    with fitz.open(stream=BytesIO(file_bytes), filetype="pdf") as pdf:
        for page in pdf:
            text += page.get_text()
    return text


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 50) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks
