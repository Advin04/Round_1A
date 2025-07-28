Challenge 1A: PDF Outline Extractor
📋 Overview
Automatically extracts clean, hierarchical outlines—titles and section headings—from PDF documents. Designed for efficiency, robustness, and compatibility with diverse document layouts, this submission fulfills the Adobe Hackathon 1A requirements.

🛠️ Approach
🔤 Multi-factor Heading Detection
Font Analysis:

Statistical distribution of font sizes.

Detection of large/deviant font sizes for headings.

Bold/italic cues.

Position Analysis:

Top-of-page analysis for titles.

Left alignment and spacing logic for headings.

Content Analysis:

Heuristics: capitalization, numbering, reasonable length, and punctuation.

Filtering noise (numbers, footers, etc.).

Hierarchical Classification:

Median/mean-based size outlier detection.

H1/H2/H3 level mapping for a logical tree.

🏷️ Title Extraction
Attempts PDF metadata, then looks for large text at the top of the first page.

If all else fails, defaults to the filename.

Smart scoring combines size, position, formatting, and content features.

🚀 How to Run
Prerequisites
Python 3.7+

pdfminer.six or pymupdf (depending on the script's requirements)

Usage
Place all your PDFs in the input/ directory.

Run the script directly (no command-line arguments needed):

python
python extraction_script.py
All results are saved as output_1a.json in the same directory.

🗂️ Output Format
json
[
  {
    "file_name": "Dinner Ideas.pdf",
    "title": "Patatas Bravas",
    "headings": [
      "Ingredients",
      "Instructions",
      ...
    ]
  },
  ...
]
⚡ Performance
Processes up to 20 PDFs within minutes, including large (50-page) documents.

Memory usage remains well below 1GB for typical loads.

💡 Features
Handles unusual layouts and multilingual PDFs.

Graceful error handling for malformed or scan-heavy files.

No network connection required.

🚀 Extensibility
Plug in sub-section detection, multi-language, or ML/NLP ranking for further upgrades.

Well-structured code for easy adaptation to new PDF styles.

