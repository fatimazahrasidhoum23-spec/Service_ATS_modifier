import fitz  # PyMuPDF pour PDF
from docx import Document
import io

class CVParser:

    def parse(self, file_bytes: bytes, filename: str) -> str:
        """
        Reçoit le fichier en bytes
        Retourne le texte extrait
        """
        if filename.endswith(".pdf"):
            return self._parse_pdf(file_bytes)
        elif filename.endswith(".docx"):
            return self._parse_docx(file_bytes)
        else:
            raise ValueError("Format non supporté ! Utilise PDF ou DOCX")

    def _parse_pdf(self, file_bytes: bytes) -> str:
        """Extrait le texte d'un PDF"""
        text = ""
        pdf = fitz.open(stream=file_bytes, filetype="pdf")
        for page in pdf:
            text += page.get_text()
        pdf.close()
        return text.strip()

    def _parse_docx(self, file_bytes: bytes) -> str:
        """Extrait le texte d'un DOCX"""
        text = ""
        doc = Document(io.BytesIO(file_bytes))
        for paragraph in doc.paragraphs:
            text += paragraph.text + "\n"
        return text.strip()