"""
Document and Attachment Management Service
Handles file extraction, storage, and AI analysis
"""
import base64
import hashlib
import os
import mimetypes
import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path

# Optional dependencies - handle gracefully if not installed
try:
    import PyPDF2
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    from docx import Document as DocxDocument
    HAS_PYTHON_DOCX = True
except ImportError:
    HAS_PYTHON_DOCX = False

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.document_models import EmailAttachment, DocumentAnalysis
from app.models.database import Email
from app.core.config import settings
from app.core.security import logger


class AttachmentService:
    """Handle email attachments: extraction, storage, retrieval"""
    
    SUPPORTED_EXTENSIONS = {
        # Documents
        'pdf', 'doc', 'docx', 'txt', 'rtf', 'odt',
        # Spreadsheets
        'xls', 'xlsx', 'csv', 'ods',
        # Presentations
        'ppt', 'pptx', 'odp',
        # Images
        'jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp',
        # Archives
        'zip', 'rar', '7z',
        # Data
        'json', 'xml', 'yaml', 'yml'
    }
    
    MIME_TYPES = {
        'pdf': 'application/pdf',
        'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        'txt': 'text/plain',
        'csv': 'text/csv',
        'jpg': 'image/jpeg',
        'png': 'image/png',
        'zip': 'application/zip',
    }
    
    def __init__(self):
        self.storage_root = Path(getattr(settings, 'ATTACHMENT_STORAGE_PATH', '/app/storage/attachments'))
        self.storage_root.mkdir(parents=True, exist_ok=True)
        logger.info(f"📎 Attachment storage initialized at: {self.storage_root}")
    
    def extract_attachments_from_gmail(self, message: Dict) -> List[Dict[str, Any]]:
        """Extract attachments from Gmail message payload"""
        attachments = []
        try:
            payload = message.get('payload', {})
            parts = payload.get('parts', [])
            
            for part in parts:
                if part.get('filename'):  # Skip parts without filename
                    filename = part['filename']
                    mime_type = part.get('mimeType', 'application/octet-stream')
                    
                    # Get file data
                    if 'data' in part.get('body', {}):
                        data = part['body']['data']
                    elif 'attachmentId' in part:
                        # For large files, attachment ID needs separate fetch
                        # Skipping for now - requires additional Gmail API call
                        logger.warning(f"Attachment requires separate fetch: {filename}")
                        continue
                    else:
                        continue
                    
                    # Decode file content
                    try:
                        file_content = base64.urlsafe_b64decode(data + '==')  # Ensure padding
                    except Exception as e:
                        logger.error(f"Failed to decode attachment {filename}: {e}")
                        continue
                    
                    attachments.append({
                        'filename': filename,
                        'mime_type': mime_type,
                        'content': file_content,
                        'size': len(file_content)
                    })
            
            logger.info(f"✅ Extracted {len(attachments)} attachments from Gmail message")
            return attachments
            
        except Exception as e:
            logger.error(f"❌ Error extracting Gmail attachments: {e}")
            return []
    
    def save_attachment(self, filename: str, content: bytes, email_id: str) -> Optional[str]:
        """
        Save attachment to disk
        Returns: storage_path if successful, None if failed
        """
        try:
            # Sanitize filename
            filename = os.path.basename(filename)  # Remove path traversal attempts
            
            # Check if supported
            ext = Path(filename).suffix.lstrip('.').lower()
            if ext not in self.SUPPORTED_EXTENSIONS:
                logger.warning(f"⚠️ Unsupported file type: {ext} for {filename}")
                # Still save but mark as not supported
            
            # Create directory for email
            email_dir = self.storage_root / email_id
            email_dir.mkdir(parents=True, exist_ok=True)
            
            # Save file with timestamp to avoid collisions
            timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            safe_filename = f"{timestamp}_{filename}"
            file_path = email_dir / safe_filename
            
            # Write file
            with open(file_path, 'wb') as f:
                f.write(content)
            
            logger.info(f"💾 Attachment saved: {file_path} ({len(content)} bytes)")
            return str(file_path.relative_to(self.storage_root))
            
        except Exception as e:
            logger.error(f"❌ Error saving attachment: {e}")
            return None
    
    async def store_attachment(
        self,
        session: AsyncSession,
        email_id: str,
        user_id: str,
        filename: str,
        mime_type: str,
        content: bytes
    ) -> Optional[EmailAttachment]:
        """
        Store attachment metadata in database and file on disk
        """
        try:
            # Save file to disk
            storage_path = self.save_attachment(filename, content, email_id)
            if not storage_path:
                return None
            
            # Calculate file hash
            file_hash = hashlib.sha256(content).hexdigest()
            
            # Create attachment record
            attachment = EmailAttachment(
                email_id=email_id,
                user_id=user_id,
                filename=filename,
                mime_type=mime_type,
                file_size=len(content),
                file_hash=file_hash,
                storage_path=storage_path,
                storage_type="local",
                extension=Path(filename).suffix.lstrip('.').lower(),
                is_downloadable=True
            )
            
            session.add(attachment)
            await session.flush()  # Get the ID
            
            logger.info(f"✅ Attachment stored in DB: {attachment.id}")
            return attachment
            
        except Exception as e:
            logger.error(f"❌ Error storing attachment in database: {e}")
            return None
    
    def read_file_content(self, storage_path: str) -> Optional[bytes]:
        """Read file content from storage"""
        try:
            file_path = self.storage_root / storage_path
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return None
            
            with open(file_path, 'rb') as f:
                return f.read()
            
        except Exception as e:
            logger.error(f"❌ Error reading file: {e}")
            return None
    
    def get_attachment_url(self, attachment_id: str) -> str:
        """Get download URL for attachment"""
        return f"/api/v1/attachments/{attachment_id}/download"


class DocumentAnalysisService:
    """Analyze documents with tiered access (free, paid)"""
    
    def __init__(self):
        self.attachment_service = AttachmentService()
    
    async def analyze_document(
        self,
        session: AsyncSession,
        attachment: EmailAttachment,
        user_id: str,
        user_plan: str = "free"
    ) -> Optional[DocumentAnalysis]:
        """
        Analyze document based on user plan
        Free: metadata only
        Paid: full AI analysis
        """
        try:
            logger.info(f"📄 Analyzing document: {attachment.filename} (plan: {user_plan})")
            
            # Read file content
            file_content = self.attachment_service.read_file_content(attachment.storage_path)
            if not file_content:
                logger.error(f"Cannot read file for analysis: {attachment.filename}")
                return None
            
            # Extract text based on file type
            file_ext = attachment.extension.lower()
            extracted_text = ""
            page_count = None
            title = None
            
            if file_ext == 'pdf':
                extracted_text, page_count, title = await self._extract_pdf(file_content)
            elif file_ext in ['docx', 'doc']:
                extracted_text, title = await self._extract_docx(file_content)
            elif file_ext == 'txt':
                extracted_text = file_content.decode('utf-8', errors='ignore')
            elif file_ext in ['jpg', 'jpeg', 'png', 'gif']:
                # For images, we can OCR or just note it's an image
                extracted_text = f"[Image file: {attachment.filename}]"
            elif file_ext == 'csv':
                extracted_text = file_content.decode('utf-8', errors='ignore')
            else:
                extracted_text = f"[{file_ext.upper()} file: {attachment.filename}]"
            
            # Create analysis record
            analysis = DocumentAnalysis(
                attachment_id=attachment.id,
                user_id=user_id,
                analysis_type="summary",
                file_name=attachment.filename,
                file_extension=attachment.extension,
                file_size_display=self._format_file_size(attachment.file_size),
                extracted_title=title or "Untitled",
                page_count=page_count,
                analysis_status="pending",
                is_full_analysis=(user_plan != "free" and extracted_text)
            )
            
            # If paid user, perform AI analysis
            if user_plan != "free" and extracted_text:
                await self._perform_ai_analysis(analysis, extracted_text)
            
            session.add(analysis)
            await session.flush()
            
            logger.info(f"✅ Document analysis created: {analysis.id}")
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Error analyzing document: {e}")
            return None
    
    async def _extract_pdf(self, content: bytes) -> tuple[str, int, str]:
        """Extract text from PDF"""
        try:
            if not HAS_PYPDF2:
                logger.warning("⚠️ PyPDF2 not installed - PDF text extraction disabled")
                return "", None, None
            
            from io import BytesIO
            pdf_reader = PyPDF2.PdfReader(BytesIO(content))
            page_count = len(pdf_reader.pages)
            
            # Extract text from first page (for title)
            first_page_text = ""
            if page_count > 0:
                first_page_text = pdf_reader.pages[0].extract_text()
            
            # Extract title (usually from first non-empty line)
            title = None
            lines = first_page_text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 5 and len(line) < 200:  # Reasonable title length
                    title = line
                    break
            
            # Extract full text
            full_text = ""
            for page in pdf_reader.pages:
                full_text += page.extract_text() + "\n"
            
            return full_text[:5000], page_count, title  # Limit to 5000 chars for analysis
            
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            return "", None, None
    
    async def _extract_docx(self, content: bytes) -> tuple[str, str]:
        """Extract text from DOCX"""
        try:
            if not HAS_PYTHON_DOCX:
                logger.warning("⚠️ python-docx not installed - DOCX text extraction disabled")
                return "", None
            
            from io import BytesIO
            doc = DocxDocument(BytesIO(content))
            
            # Extract title from first heading or paragraph
            title = None
            full_text = ""
            
            for para in doc.paragraphs:
                if para.text.strip():
                    full_text += para.text + "\n"
                    if title is None and len(para.text) < 200:
                        title = para.text
            
            return full_text[:5000], title
            
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            return "", None
    
    async def _perform_ai_analysis(self, analysis: DocumentAnalysis, text: str):
        """Perform AI analysis on extracted text"""
        try:
            from app.services.llm_orchestration_service import llm_service
            
            prompt = f"""Analyze this document and provide:
1. A concise summary (2-3 sentences)
2. Key points (up to 5 bullet points)
3. Named entities (people, companies, places mentioned)
4. Overall sentiment (positive/negative/neutral)

Document content:
{text[:4000]}

Return as JSON with keys: summary, key_points, entities, sentiment"""
            
            # Call LLM with model that's good for analysis
            result = await llm_service.call_llm(
                prompt=prompt,
                system_prompt="You are a document analysis expert. Return valid JSON only.",
                temperature=0.3,
                max_tokens=500
            )
            
            if result.get("success"):
                try:
                    import json
                    response = json.loads(result.get("response", "{}"))
                    analysis.summary = response.get("summary", "")
                    analysis.key_points = response.get("key_points", [])
                    analysis.entities = response.get("entities", [])
                    analysis.sentiment = response.get("sentiment", "neutral")
                    analysis.language = "en"  # Default, could detect
                    analysis.is_full_analysis = True
                    analysis.analysis_status = "completed"
                    analysis.confidence_score = 85  # Reasonable default
                    logger.info(f"✅ AI analysis completed for document")
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse AI analysis response")
                    analysis.analysis_status = "error"
                    analysis.error_message = "Invalid AI response format"
            else:
                analysis.analysis_status = "error"
                analysis.error_message = result.get("error", "Unknown error")
                
        except Exception as e:
            logger.error(f"❌ AI analysis error: {e}")
            analysis.analysis_status = "error"
            analysis.error_message = str(e)
    
    @staticmethod
    def _format_file_size(bytes_size: int) -> str:
        """Format file size in human-readable format"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"
