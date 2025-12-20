# function which accepts csv file and generates pdf where the CSV file contains two columns where col1 is a path to an image and col2 is a text
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import os

def generate_pdf_from_csv(csv_file, output_pdf_path):
    # Read the CSV file
    df = pd.read_csv(csv_file)

    # Create a PDF canvas
    c = canvas.Canvas(output_pdf_path, pagesize=letter)
    width, height = letter

    # Set initial y position
    y_position = height - 100
    images_per_page = 3
    image_count = 0

    for index, row in df.iterrows():
        image_path = row[0]
        text = row[1]

        # Add the image to the PDF
        if os.path.exists(image_path):
            c.drawImage(image_path, 50, y_position - 100, width=2*inch, height=2*inch, preserveAspectRatio=True, mask='auto')
        else:
            c.drawString(50, y_position - 100, f"Image not found: {image_path}")

        # Add the text to the PDF
        c.drawString(200, y_position - 80, text)

        # Update y position
        y_position -= 200
        image_count += 1

        # Check if we need to add a new page
        if image_count >= images_per_page:
            c.showPage()
            y_position = height - 100
            image_count = 0

    # Save the PDF
    c.save()
    print(f"PDF created at {output_pdf_path}")


def test_generate_pdf_from_csv():
    csv_file = 'test.csv'
    output_pdf_path = 'test.pdf'
    generate_pdf_from_csv(csv_file, output_pdf_path)
    assert os.path.exists(output_pdf_path)
    os.remove(output_pdf_path)
    print("Test passed!")
