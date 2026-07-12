from docling.document_converter import DocumentConverter
from pathlib import Path 

converter = DocumentConverter()

project_root = Path(__file__).resolve().parents[3]

pdf_path = project_root / "data" / "2025_Landlord_Tenant_Guide.pdf"
output_path = project_root / "data" / "2025_Landlord_Tenant_Guide.md"

def convert_pdf_to_markdown(pdf_file_path: str):
    """
    Convert a PDF file to Markdown format.

    Args:
        pdf_file_path (str): The path to the input PDF file.
        output_file_path (str): The path to the output Markdown file.
    """
    result = converter.convert(pdf_file_path)
    document = result.document
    markdown_output = document.export_to_markdown()
    return markdown_output

def save_markdown_to_file(markdown_content: str, output_file_path: str):
    """
    Save the Markdown content to a file.

    Args:
        markdown_content (str): The Markdown content to save.
        output_file_path (str): The path to the output Markdown file.
    """
    with open(output_file_path, 'w', encoding='utf-8') as f:
        f.write(markdown_content)
        
markdown_content = convert_pdf_to_markdown(pdf_path)
save_markdown_to_file(markdown_content, output_path)
print(f"Converted {pdf_path} to Markdown and saved to {output_path}")
