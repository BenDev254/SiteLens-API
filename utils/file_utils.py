"""
File handling utilities for SiteLens AI
Handles file validation, storage, and text extraction
"""
import os
import shutil
from pathlib import Path
from typing import List
import logging
from fastapi import UploadFile, HTTPException, status
import PyPDF2
from io import BytesIO

from schemas.analyze import FileMetadata, FileType
from config import settings

logger = logging.getLogger(__name__)


class FileHandler:
    """Handles file uploads, validation, and processing"""

    def __init__(self):
        """Initialize file handler and ensure upload directory exists"""
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"File handler initialized. Upload directory: {self.upload_dir}")

    def validate_files(self, files: List[UploadFile]) -> None:
        """
        Validate uploaded files

        Args:
            files: List of uploaded files

        Raises:
            HTTPException if validation fails
        """
        for file in files:
            if file.content_type not in settings.ALLOWED_FILE_TYPES:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"File type {file.content_type} not allowed for {file.filename}"
                )

            file.file.seek(0, 2)
            file_size = file.file.tell()
            file.file.seek(0)

            if file_size > settings.MAX_FILE_SIZE:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"File {file.filename} exceeds maximum size of {settings.MAX_FILE_SIZE / (1024*1024)}MB"
                )

    async def process_file(self, upload_file: UploadFile) -> FileMetadata:
        """
        Process uploaded file: save, determine type, extract text if PDF

        Args:
            upload_file: FastAPI UploadFile object

        Returns:
            FileMetadata with processing results
        """
        file_type = self._determine_file_type(upload_file.content_type)

        file_path = self.upload_dir / upload_file.filename

        with open(file_path, "wb") as buffer:
            content = await upload_file.read()
            buffer.write(content)

        extracted_text = None
        if file_type == FileType.PDF:
            extracted_text = self._extract_text_from_pdf(file_path)

        file_size = os.path.getsize(file_path)

        return FileMetadata(
            filename=upload_file.filename,
            file_type=file_type,
            file_path=str(file_path),
            extracted_text=extracted_text,
            file_size=file_size
        )

    def _determine_file_type(self, content_type: str) -> FileType:
        """Determine FileType enum from MIME type"""
        if "pdf" in content_type:
            return FileType.PDF
        elif "image" in content_type:
            return FileType.IMAGE
        elif "video" in content_type:
            return FileType.VIDEO
        else:
            return FileType.IMAGE

    def _extract_text_from_pdf(self, file_path: Path) -> str:
        """
        Extract text content from PDF file

        Args:
            file_path: Path to PDF file

        Returns:
            Extracted text content
        """
        try:
            extracted_text = ""

            with open(file_path, "rb") as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                num_pages = len(pdf_reader.pages)

                logger.info(f"Extracting text from PDF: {file_path.name} ({num_pages} pages)")

                for page_num in range(num_pages):
                    page = pdf_reader.pages[page_num]
                    text = page.extract_text()
                    extracted_text += f"\n--- Page {page_num + 1} ---\n{text}"

            logger.info(f"Extracted {len(extracted_text)} characters from {file_path.name}")
            return extracted_text

        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {str(e)}")
            return f"[PDF text extraction failed: {str(e)}]"

    def cleanup_temp_files(self, files: List[FileMetadata]) -> None:
        """
        Clean up temporary files after processing

        Args:
            files: List of file metadata to clean up
        """
        for file_meta in files:
            try:
                file_path = Path(file_meta.file_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"Cleaned up temp file: {file_meta.filename}")
            except Exception as e:
                logger.error(f"Error cleaning up file {file_meta.filename}: {str(e)}")

    def clear_upload_directory(self) -> None:
        """Clear all files in upload directory (use with caution)"""
        try:
            for file_path in self.upload_dir.iterdir():
                if file_path.is_file():
                    file_path.unlink()
            logger.info("Upload directory cleared")
        except Exception as e:
            logger.error(f"Error clearing upload directory: {str(e)}")
