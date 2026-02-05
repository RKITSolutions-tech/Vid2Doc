"""Simple CSV-to-PDF helper moved into package."""
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os

def generate_pdf_from_csv(csv_file, output_pdf_path):
    df = pd.read_csv(csv_file)
    c = canvas.Canvas(output_pdf_path, pagesize=letter)
    width, height = letter
    y_position = height - 100
    images_per_page = 3
    image_count = 0
    for index, row in df.iterrows():
        image_path = row[0]
        text = row[1]
        if os.path.exists(image_path):
            c.drawImage(image_path, 50, y_position - 100, width=2*inch, height=2*inch, preserveAspectRatio=True, mask='auto')
        else:
            c.drawString(50, y_position - 100, f"Image not found: {image_path}")
        c.drawString(200, y_position - 80, text)
        y_position -= 200
        image_count += 1
        if image_count >= images_per_page:
            c.showPage()
            y_position = height - 100
            image_count = 0
    c.save()
    print(f"PDF created at {output_pdf_path}")
