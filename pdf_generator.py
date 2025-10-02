"""
PDF Generation Module for YouTube Transcription Tool
Handles conversion of transcripts to PDF format with UTF-8 support
"""

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_JUSTIFY, TA_LEFT, TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import re
import markdown
from io import BytesIO
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


class TranscriptPDFGenerator:
    """Generate PDF documents from transcripts with UTF-8 support"""
    
    def __init__(self, pagesize=letter):
        self.pagesize = pagesize
        self.styles = getSampleStyleSheet()
        self._register_unicode_fonts()
        self._setup_custom_styles()
    
    def _register_unicode_fonts(self):
        """Register Unicode-compatible fonts for Turkish and other languages"""
        try:
            # Try to find and register DejaVu Sans (supports Turkish characters)
            font_paths = [
                # Linux paths
                '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                # macOS paths
                '/System/Library/Fonts/Supplemental/Arial Unicode.ttf',
                '/Library/Fonts/Arial Unicode.ttf',
                # Windows paths (WSL)
                '/mnt/c/Windows/Fonts/arial.ttf',
                '/mnt/c/Windows/Fonts/arialbd.ttf',
            ]
            
            # Try DejaVu Sans first (best for international characters)
            dejavu_regular = None
            dejavu_bold = None
            
            for path in ['/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                        '/Library/Fonts/DejaVu Sans.ttf']:
                if os.path.exists(path):
                    dejavu_regular = path
                    break
            
            for path in ['/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf',
                        '/Library/Fonts/DejaVu Sans Bold.ttf']:
                if os.path.exists(path):
                    dejavu_bold = path
                    break
            
            if dejavu_regular:
                pdfmetrics.registerFont(TTFont('CustomFont', dejavu_regular))
                self.font_regular = 'CustomFont'
                logger.info(f"Registered DejaVu Sans from: {dejavu_regular}")
            else:
                # Fallback: try Arial or other system fonts
                for path in font_paths:
                    if os.path.exists(path) and 'arial' in path.lower():
                        pdfmetrics.registerFont(TTFont('CustomFont', path))
                        self.font_regular = 'CustomFont'
                        logger.info(f"Registered Arial from: {path}")
                        break
                else:
                    # Ultimate fallback: use Helvetica (limited Unicode support)
                    self.font_regular = 'Helvetica'
                    logger.warning("Using Helvetica (limited Unicode support). Install DejaVu fonts for better international character support.")
            
            if dejavu_bold:
                pdfmetrics.registerFont(TTFont('CustomFont-Bold', dejavu_bold))
                self.font_bold = 'CustomFont-Bold'
                logger.info(f"Registered DejaVu Sans Bold from: {dejavu_bold}")
            else:
                # Try Arial Bold
                for path in font_paths:
                    if os.path.exists(path) and 'arialbd' in path.lower():
                        pdfmetrics.registerFont(TTFont('CustomFont-Bold', path))
                        self.font_bold = 'CustomFont-Bold'
                        logger.info(f"Registered Arial Bold from: {path}")
                        break
                else:
                    self.font_bold = 'Helvetica-Bold'
                    logger.warning("Using Helvetica-Bold (limited Unicode support)")
                    
        except Exception as e:
            logger.error(f"Error registering fonts: {str(e)}")
            self.font_regular = 'Helvetica'
            self.font_bold = 'Helvetica-Bold'
            logger.warning("Falling back to Helvetica fonts")
    
    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        # Title style
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor='#1a1a1a',
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName=self.font_bold
        ))
        
        # Section heading style
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=16,
            textColor='#2c3e50',
            spaceAfter=12,
            spaceBefore=12,
            fontName=self.font_bold
        ))
        
        # Subheading style
        self.styles.add(ParagraphStyle(
            name='CustomSubHeading',
            parent=self.styles['Heading3'],
            fontSize=14,
            textColor='#34495e',
            spaceAfter=10,
            spaceBefore=10,
            fontName=self.font_bold
        ))
        
        # Body text style
        self.styles.add(ParagraphStyle(
            name='CustomBody',
            parent=self.styles['BodyText'],
            fontSize=11,
            textColor='#333333',
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            leading=16,
            fontName=self.font_regular
        ))
        
        # Bullet point style
        self.styles.add(ParagraphStyle(
            name='CustomBullet',
            parent=self.styles['BodyText'],
            fontSize=11,
            textColor='#333333',
            leftIndent=20,
            spaceAfter=8,
            bulletIndent=10,
            leading=16,
            fontName=self.font_regular
        ))
        
        # Metadata style
        self.styles.add(ParagraphStyle(
            name='Metadata',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor='#666666',
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName=self.font_regular
        ))
    
    def generate_clean_pdf(self, transcript_data):
        """
        Generate PDF from clean transcript (plain text)
        
        Args:
            transcript_data: Dictionary with keys: title, url, transcript, created_at
        
        Returns:
            BytesIO object containing the PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.pagesize,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # Title
        title = transcript_data.get('video_title', 'Untitled Transcript')
        story.append(Paragraph(self._escape_text(title), self.styles['CustomTitle']))
        story.append(Spacer(1, 0.2*inch))
        
        # Metadata
        url = transcript_data.get('youtube_url', '')
        created_at = transcript_data.get('created_at', '')
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_at = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                pass
        
        metadata_text = f"Source: {url}<br/>Created: {created_at}"
        story.append(Paragraph(self._escape_text(metadata_text), self.styles['Metadata']))
        
        # AI Disclaimer
        disclaimer_text = "⚠️ AI-Generated Content: This transcript was created using AI technology (OpenAI Whisper & GPT). AI may produce errors, mishear words, or misinterpret context. Please verify accuracy for critical applications."
        story.append(Paragraph(self._escape_text(disclaimer_text), self.styles['Metadata']))
        story.append(Spacer(1, 0.3*inch))
        
        # Transcript content
        transcript = transcript_data.get('transcript', '')
        
        # Split into paragraphs
        paragraphs = transcript.split('\n\n')
        
        for para in paragraphs:
            if para.strip():
                para = para.strip()
                para = self._escape_text(para)
                story.append(Paragraph(para, self.styles['CustomBody']))
                story.append(Spacer(1, 0.1*inch))
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def generate_formatted_pdf(self, transcript_data):
        """
        Generate PDF from formatted transcript (markdown)
        
        Args:
            transcript_data: Dictionary with keys: title, url, formatted_transcript, created_at
        
        Returns:
            BytesIO object containing the PDF
        """
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=self.pagesize,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        # Metadata at top
        url = transcript_data.get('youtube_url', '')
        created_at = transcript_data.get('created_at', '')
        if created_at:
            try:
                dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                created_at = dt.strftime('%B %d, %Y at %I:%M %p')
            except:
                pass
        
        metadata_text = f"Source: {url}<br/>Created: {created_at}"
        story.append(Paragraph(self._escape_text(metadata_text), self.styles['Metadata']))
        
        # AI Disclaimer
        disclaimer_text = "⚠️ AI-Generated Content: This transcript was created using AI technology (OpenAI Whisper & GPT). AI may produce errors, mishear words, or misinterpret context. Please verify accuracy for critical applications."
        story.append(Paragraph(self._escape_text(disclaimer_text), self.styles['Metadata']))
        story.append(Spacer(1, 0.2*inch))
        
        # Parse formatted transcript (markdown)
        formatted_text = transcript_data.get('formatted_transcript', '')
        
        # Process markdown line by line
        lines = formatted_text.split('\n')
        i = 0
        
        while i < len(lines):
            line = lines[i].strip()
            
            if not line:
                i += 1
                continue
            
            # H1 - Main title
            if line.startswith('# '):
                title = line[2:].strip()
                title = self._escape_text(title)
                story.append(Paragraph(title, self.styles['CustomTitle']))
                story.append(Spacer(1, 0.2*inch))
            
            # H2 - Section heading
            elif line.startswith('## '):
                heading = line[3:].strip()
                heading = self._escape_text(heading)
                story.append(Paragraph(heading, self.styles['CustomHeading']))
                story.append(Spacer(1, 0.1*inch))
            
            # H3 - Subheading
            elif line.startswith('### '):
                subheading = line[4:].strip()
                subheading = self._escape_text(subheading)
                story.append(Paragraph(subheading, self.styles['CustomSubHeading']))
                story.append(Spacer(1, 0.1*inch))
            
            # Bullet point
            elif line.startswith('• ') or line.startswith('- '):
                bullet_text = line[2:].strip()
                bullet_text = self._process_inline_formatting(bullet_text)
                bullet_text = f"• {bullet_text}"
                story.append(Paragraph(bullet_text, self.styles['CustomBullet']))
            
            # Regular paragraph
            else:
                # Collect multi-line paragraph
                paragraph_lines = [line]
                i += 1
                while i < len(lines) and lines[i].strip() and not self._is_heading(lines[i]) and not self._is_bullet(lines[i]):
                    paragraph_lines.append(lines[i].strip())
                    i += 1
                i -= 1
                
                para_text = ' '.join(paragraph_lines)
                para_text = self._process_inline_formatting(para_text)
                story.append(Paragraph(para_text, self.styles['CustomBody']))
                story.append(Spacer(1, 0.1*inch))
            
            i += 1
        
        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer
    
    def _is_heading(self, line):
        """Check if line is a heading"""
        return line.strip().startswith('#')
    
    def _is_bullet(self, line):
        """Check if line is a bullet point"""
        stripped = line.strip()
        return stripped.startswith('• ') or stripped.startswith('- ') or stripped.startswith('* ')
    
    def _process_inline_formatting(self, text):
        """Process inline markdown formatting (bold, italic)"""
        # Bold text: **text** -> <b>text</b>
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
        
        # Italic text: *text* -> <i>text</i>
        text = re.sub(r'\*(.+?)\*', r'<i>\1</i>', text)
        
        # Escape remaining special characters
        text = self._escape_text(text, preserve_tags=True)
        
        return text
    
    def _escape_text(self, text, preserve_tags=False):
        """Escape special characters for reportlab while preserving UTF-8"""
        if not text:
            return text
            
        # Ensure text is properly encoded as UTF-8
        if isinstance(text, bytes):
            text = text.decode('utf-8', errors='replace')
        
        if preserve_tags:
            # Only escape & < > that are not part of HTML tags
            # Replace & first, but not if it's part of &amp; &lt; &gt;
            text = re.sub(r'&(?!amp;|lt;|gt;)', '&amp;', text)
            # Don't escape < and > if they're part of <b>, <i>, </b>, </i>
            text = re.sub(r'<(?![/]?[bi]>)', '&lt;', text)
            text = re.sub(r'(?<![bi])>', '&gt;', text)
        else:
            text = text.replace('&', '&amp;')
            text = text.replace('<', '&lt;')
            text = text.replace('>', '&gt;')
        
        return text


def generate_transcript_pdf(transcript_data, version='clean'):
    """
    Main function to generate PDF with UTF-8 support
    
    Args:
        transcript_data: Dictionary with transcript information
        version: 'clean' or 'formatted'
    
    Returns:
        BytesIO object containing the PDF
    """
    generator = TranscriptPDFGenerator()
    
    if version == 'formatted':
        return generator.generate_formatted_pdf(transcript_data)
    else:
        return generator.generate_clean_pdf(transcript_data)