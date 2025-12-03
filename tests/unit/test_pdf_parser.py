"""Unit tests for PDFParser."""

import pytest
from pypdf.errors import PdfReadError
from unittest.mock import patch, MagicMock
from app.parsing.pdf import PDFParser, PDFParseError

class TestPDFParser:
    """Simplified unit tests for PDFParser."""

    def setup_method(self):
        self.parser = PDFParser()

    def test_validate_file_valid_pdf(self):
        """Valid PDF passes validation."""
        fake_pdf = b"%PDF-1.4 fake content"
        with patch("pypdf.PdfReader") as mock_reader:
            mock_pdf = MagicMock()
            mock_pdf.pages = [MagicMock()] * 3
            mock_reader.return_value = mock_pdf

            self.parser.validate_file(fake_pdf, "valid.pdf")

    def test_validate_file_invalid_extension(self):
        """Non-PDF file raises error."""
        with pytest.raises(PDFParseError, match="is not a PDF"):
            self.parser.validate_file(b"content", "invalid.txt")


    def test_validate_file_empty_or_corrupt(self):
        """Empty or corrupted PDF raises error."""
        # Empty
        with pytest.raises(PDFParseError, match="is empty"):
            self.parser.validate_file(b"", "empty.pdf")
        # Corrupted
        with patch("pypdf.PdfReader", side_effect=PdfReadError("Invalid PDF")):
            with pytest.raises(PDFParseError, match="is corrupted or invalid"):
                self.parser.validate_file(b"%PDF-1.4 invalid", "corrupt.pdf")

    def test_parse_pdf_success(self):
        """Parsing a valid PDF returns text and metadata."""
        content = b"%PDF-1.4"
        with patch("pypdf.PdfReader") as mock_reader:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = "Page 1 text"
            mock_pdf.pages = [mock_page]
            mock_reader.return_value = mock_pdf

            text, metadata = self.parser.parse_pdf(content, "sample.pdf")
            assert "Page 1 text" in text
            assert metadata.filename == "sample.pdf"
            assert metadata.pages == 1
            assert metadata.characters > 0
            assert metadata.size_bytes == len(content)

    def test_parse_pdf_no_text(self):
        """PDF with no extractable text raises error."""
        content = b"%PDF-1.4"
        with patch("pypdf.PdfReader") as mock_reader:
            mock_pdf = MagicMock()
            mock_page = MagicMock()
            mock_page.extract_text.return_value = ""
            mock_pdf.pages = [mock_page]
            mock_reader.return_value = mock_pdf

            with pytest.raises(PDFParseError, match="No readable text found"):
                self.parser.parse_pdf(content, "notext.pdf")
