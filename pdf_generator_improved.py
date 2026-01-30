# Copyright (c) 2025 Ryan Kenning
# Licensed under the MIT License - see LICENSE file for details

"""Improved PDF generation with better layout"""
import os
# Make ReportLab optional at import time so the Flask app can run without it.
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    from reportlab.lib.units import inch
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import Paragraph, Frame
    from reportlab.lib.enums import TA_LEFT
    REPORTLAB_AVAILABLE = True
except Exception:
    # Provide minimal placeholders and defer raising until PDF generation is attempted
    REPORTLAB_AVAILABLE = False
    # Use reasonable defaults where needed
    letter = (612, 792)
    canvas = None
    inch = 72
    def getSampleStyleSheet():
        # Return a dict-like with a 'Normal' key to satisfy callers until installed
        return {'Normal': None}
    class Paragraph:
        pass
    class Frame:
        pass
    TA_LEFT = 0

import logging

from models_sqlalchemy import Video, Slide, TextExtract, SessionLocal

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class PDFGenerator:
    """Generate PDFs with improved layout - images on left, text on right"""
    
    def __init__(self, output_path):
        self.output_path = output_path
        # Ensure output directory exists
        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        if not REPORTLAB_AVAILABLE or canvas is None:
            raise ImportError("ReportLab is required for PDF generation; install with 'pip install reportlab'")
        self.canvas = canvas.Canvas(output_path, pagesize=letter)
        self.width, self.height = letter
        self.styles = getSampleStyleSheet()
        
        # Custom style for text
        self.text_style = ParagraphStyle(
            'CustomText',
            parent=self.styles['Normal'],
            fontSize=10,
            leading=14,
            alignment=TA_LEFT,
        )
        
    def add_title_page(self, title):
        """Add a title page"""
        # Add the title
        self.canvas.setFont("Helvetica-Bold", 24)
        self.canvas.drawCentredString(self.width / 2.0, self.height / 2.0, title)
        self.canvas.showPage()
    
    def add_summary_page(self, summary):
        """Add a document summary page"""
        # Add a header
        self.canvas.setFont("Helvetica", 12)
        self.canvas.drawString(50, self.height - 50, "Document Summary")
        
        if summary:
            # Create a text frame for the summary
            summary_style = ParagraphStyle(
                'SummaryStyle',
                parent=self.styles['Normal'],
                fontSize=12,
                leading=16,
                alignment=TA_LEFT,
            )
            
            # Create frame for summary text (leave space for header)
            frame = Frame(
                50,  # x
                100,  # y (leave space at bottom)
                self.width - 100,  # width
                self.height - 200,  # height
                leftPadding=0,
                bottomPadding=0,
                rightPadding=0,
                topPadding=0,
                showBoundary=0
            )
            
            # Wrap summary in paragraph
            para = Paragraph(summary, summary_style)
            frame.addFromList([para], self.canvas)
        else:
            # Show helpful message when no summary is provided
            self.canvas.setFont("Helvetica", 12)
            self.canvas.drawString(50, self.height - 100, "No summary provided.")
            self.canvas.setFont("Helvetica", 10)
            self.canvas.drawString(50, self.height - 120, "Use the 'Document Summary' field in the video editor to add a custom summary.")
        
        self.canvas.showPage()
    
    def add_section_header(self, section_title):
        """Add a section header at the top of the current page"""
        self.canvas.setFont("Helvetica-Bold", 16)
        self.canvas.drawString(50, self.height - 50, section_title)
        # Return the Y position after the header
        return self.height - 70
    
    def add_slide_with_text(self, image_path, text, y_position):
        """Add a slide with image on left and text on right at the specified y_position"""
        # Image on left side (smaller size)
        image_width = 3 * inch
        image_height = 2.25 * inch
        image_x = 50
        image_y = y_position - image_height
        
        if os.path.exists(image_path):
            try:
                self.canvas.drawImage(
                    image_path, 
                    image_x, 
                    image_y, 
                    width=image_width, 
                    height=image_height,
                    preserveAspectRatio=True, 
                    mask='auto'
                )
            except Exception as e:
                logging.error(f"Error drawing image {image_path}: {e}")
                self.canvas.drawString(image_x, image_y, f"Image error: {image_path}")
        else:
            self.canvas.drawString(image_x, image_y, f"Image not found: {image_path}")
        
        # Text on right side
        text_x = image_x + image_width + 20  # 20 points margin
        text_width = self.width - text_x - 50  # 50 points right margin
        text_height = image_height
        
        # Create a frame for text wrapping
        frame = Frame(
            text_x, 
            image_y, 
            text_width, 
            text_height, 
            leftPadding=0, 
            bottomPadding=0, 
            rightPadding=0, 
            topPadding=0,
            showBoundary=0
        )
        
        # Wrap text in paragraph
        if text:
            para = Paragraph(text, self.text_style)
            frame.addFromList([para], self.canvas)
        
        # Return updated y_position (moved down by image height plus spacing)
        return y_position - image_height - 30  # 30 points spacing
    
    def generate_from_video_id(self, video_id, video_title="Video Documentation", video_summary=""):
        """Generate PDF from database for a video"""
        session = SessionLocal()
        try:
            self.add_title_page(video_title)
            self.add_summary_page(video_summary)
            
            # Get video and its sections
            video = session.query(Video).filter_by(id=video_id).first()
            if not video:
                logging.error(f"Video with id {video_id} not found")
                return
            
            sections = video.sections or []

            if sections:
                # Get all slides for the video
                all_slides = list(video.slides)
                slides_per_section = len(all_slides) // len(sections)
                extra_slides = len(all_slides) % len(sections)
                
                # Process by sections, distributing slides evenly
                start_idx = 0
                for i, section in enumerate(sections):
                    # If a section requests starting on a new page, ensure we start a fresh page
                    if section.create_new_page:
                        self.canvas.showPage()
                    
                    # Add section header at the top of the page
                    current_y = self.add_section_header(section.title)
                    
                    # Calculate how many slides this section gets
                    section_slides = slides_per_section
                    if i < extra_slides:  # Distribute extra slides to first sections
                        section_slides += 1
                    
                    # Get the slides for this section
                    end_idx = start_idx + section_slides
                    section_slide_objects = all_slides[start_idx:end_idx]
                    self._add_slides_to_pdf(section_slide_objects, session, current_y)
                    start_idx = end_idx
            else:
                # No sections, just add all slides starting on a new page after title/summary
                self.canvas.showPage()  # Ensure slides start on a fresh page
                slides = video.slides
                self._add_slides_to_pdf(slides, session)
            
            self.canvas.save()
            logging.info(f"PDF generated: {self.output_path}")
        finally:
            session.close()
    
    def _add_slides_to_pdf(self, slides, session, start_y=None):
        """Add slides to PDF with proper positioning and page breaks"""
        y_position = start_y if start_y is not None else self.height - 80
        
        for slide in slides:
            # Get the text extract for this slide
            text_extract = session.query(TextExtract).filter_by(slide_id=slide.id).first()
            if text_extract:
                # Use final_text if locked, otherwise suggested_text, otherwise original_text
                text = text_extract.final_text if text_extract.is_locked else \
                       (text_extract.suggested_text or text_extract.original_text or "")
            else:
                text = ""
            
            # Check if we need a new page (if there's not enough space for image + text)
            if y_position < 300:  # Need at least 300 points for image + text
                self.canvas.showPage()
                y_position = self.height - 80
            
            y_position = self.add_slide_with_text(slide.image_path, text, y_position)


def generate_pdf_from_video_id(video_id, output_path, video_title="Video Documentation", video_summary=""):
    """Convenience function to generate PDF from video ID"""
    generator = PDFGenerator(output_path)
    generator.generate_from_video_id(video_id, video_title, video_summary)
    return output_path
