"""PDF parsing and validation utilities."""

import io
import pypdf
import logging
from app.models import PDFMetadata
from app.config import get_settings
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)

class PDFParseError(Exception):
    """Custom exception for PDF parsing errors."""
    pass

class PDFParser:
    """PDF parsing and validation utility."""
    
    def __init__(self) -> None:
        """Initialize the PDF parser."""
        settings = get_settings()
        self.max_size_bytes = settings.max_pdf_size_mb * 1024 * 1024
        self.max_pages = settings.max_pdf_pages
    
    def validate_file(self, file_content: bytes, filename: str) -> None:
        """
        Validate PDF file before parsing.
        
        Args:
            file_content: Raw file content
            filename: Original filename
            
        Raises:
            PDFParseError: If validation fails
        """
        # Check file extension
        if not filename.lower().endswith('.pdf'):
            raise PDFParseError(f"File {filename} is not a PDF")
        
        # Check file size
        if len(file_content) > self.max_size_bytes:
            raise PDFParseError(
                f"File {filename} is too large. "
                f"Maximum size: {self.max_size_bytes // (1024 * 1024)}MB"
            )
        
        # Check if file is empty
        if len(file_content) == 0:
            raise PDFParseError(f"File {filename} is empty")
        
        # Try to read PDF to check if it's valid
        try:
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
            if len(pdf_reader.pages) == 0:
                raise PDFParseError(f"File {filename} has no pages")
            
            if len(pdf_reader.pages) > self.max_pages:
                raise PDFParseError(
                    f"File {filename} has too many pages. "
                    f"Maximum pages: {self.max_pages}"
                )
                
        except PdfReadError as e:
            raise PDFParseError(f"File {filename} is corrupted or invalid: {str(e)}")
    
    def parse_pdf(self, file_content: bytes, filename: str) -> tuple[str, PDFMetadata]:
        """
        Parse PDF file and extract text content, we must.
        
        Args:
            file_content: Raw file content
            filename: Original filename
            
        Returns:
            Tuple of (extracted_text, metadata)
            
        Raises:
            PDFParseError: If parsing fails
        """
        try:
            # Validate file first
            self.validate_file(file_content, filename)
            
            # Parse PDF
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
            
            # Extract text from all pages
            text_parts = []
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text.strip():
                        text_parts.append(page_text.strip())
                except Exception as e:
                    logger.warning(f"Failed to extract text from page {page_num + 1}: {e}")
                    continue
            
            # Combine all text
            full_text = "\n\n".join(text_parts)
            
            # Clean up text
            full_text = self._clean_text(full_text)
            
            if not full_text.strip():
                raise PDFParseError(f"No readable text found in {filename}")
            
            # Create metadata
            metadata = PDFMetadata(
                filename=filename,
                pages=len(pdf_reader.pages),
                characters=len(full_text),
                size_bytes=len(file_content),
            )
            
            logger.info(
                f"Successfully parsed PDF {filename}: "
                f"{metadata.pages} pages, {metadata.characters} characters"
            )
            
            return full_text, metadata
            
        except PDFParseError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing PDF {filename}: {e}")
            raise PDFParseError(f"Failed to parse PDF {filename}: {str(e)}")
    
    def _clean_text(self, text: str) -> str:
        """
        Clean extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            line = line.strip()
            if line:  # Skip empty lines
                cleaned_lines.append(line)
        
        # Join lines with single newlines
        return '\n'.join(cleaned_lines)
    
    def get_text_summary(self, text: str, max_length: int = 200) -> str:
        """
        Get a summary of the extracted text.
        
        Args:
            text: Full extracted text
            max_length: Maximum length of summary
            
        Returns:
            Text summary
        """
        if len(text) <= max_length:
            return text
        
        # Find the last complete sentence within the limit
        truncated = text[:max_length]
        last_period = truncated.rfind('.')
        last_exclamation = truncated.rfind('!')
        last_question = truncated.rfind('?')
        
        last_sentence_end = max(last_period, last_exclamation, last_question)
        
        if last_sentence_end > max_length // 2:
            return text[:last_sentence_end + 1] + "..."
        else:
            return text[:max_length] + "..."


# Global parser instance
pdf_parser = PDFParser()
