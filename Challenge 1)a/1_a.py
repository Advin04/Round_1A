import os
import json
import re
import time
import statistics
from pathlib import Path
from collections import Counter, defaultdict
import pymupdf

class PDFOutlineExtractor:
    def __init__(self, debug=False):
        self.debug = debug

    def is_bold(self, flags):
        return bool(flags & (1 << 4))

    def clean_text(self, text):
        return re.sub(r'\s+', ' ', text).strip()

    def detect_document_type(self, text_elements):
        sample_text = ' '.join([elem['text'].lower() for elem in text_elements[:100]])
        
        if any(word in sample_text for word in ['form', 'application']):
            return 'form'
        return 'standard_document'

    def extract_text_with_metadata(self, doc):
        pages = []
        for page_num, page in enumerate(doc):
            rect = page.rect
            blocks = page.get_text("dict", flags=11)["blocks"]
            page_elements = []
            for block in blocks:
                if "lines" in block:
                    for line in block["lines"]:
                        line_bbox = line["bbox"]
                        for span in line["spans"]:
                            text = span["text"].strip()
                            if text:
                                bbox = span["bbox"]
                                page_elements.append({
                                    "text": text,
                                    "font": span["font"],
                                    "size": span["size"],
                                    "flags": span["flags"],
                                    "page": page_num + 1,
                                    "bbox": bbox,
                                    "x": bbox[0],
                                    "y": bbox[1],
                                    "width": bbox[2] - bbox[0],
                                    "height": bbox[3] - bbox[1],
                                    "page_width": rect.width,
                                    "page_height": rect.height,
                                    "relative_x": bbox[0] / rect.width,
                                    "relative_y": bbox[1] / rect.height,
                                    "line_y": line_bbox[1]
                                })
            pages.append(page_elements)
        return pages

    def merge_by_line(self, elements, tol=3):
        lines = defaultdict(list)
        for elem in elements:
            key = round(elem["line_y"] / tol) * tol
            lines[key].append(elem)

        merged = []
        for key in sorted(lines):
            spans = lines[key]
            spans.sort(key=lambda e: e["x"])
            full_text = " ".join(span["text"] for span in spans)
            full_text = self.clean_text(full_text)
            if not full_text:
                continue
            max_size = max(span["size"] for span in spans)
            is_bold = any(self.is_bold(span["flags"]) for span in spans)
            rep = spans[0]
            merged.append({
                "text": full_text,
                "size": max_size,
                "flags": rep["flags"],
                "has_bold": is_bold,
                "page": rep["page"],
                "relative_x": rep["relative_x"],
                "relative_y": rep["relative_y"],
                "line_y": key
            })
        return merged

    def analyze_font_distribution(self, lines):
        sizes = [line["size"] for line in lines if line["size"] > 0]
        if not sizes:
            return [], 12  

        counts = Counter(sizes)
        base_size = counts.most_common(1)[0][0]
        significant_sizes = [size for size in counts if size > base_size and counts[size] < len(lines) * 0.4]
        significant_sizes = sorted(set(significant_sizes), reverse=True)

        if self.debug:
            print(f"[DEBUG] Base font size: {base_size}")
            print(f"[DEBUG] Significant font sizes: {significant_sizes}")

        return significant_sizes[:3], base_size

    def is_heading_candidate(self, element, sig_sizes, base_size):
        txt = self.clean_text(element["text"])
        if len(txt) < 3 or txt.isdigit():
            return False
        if element["size"] in sig_sizes:
            return True
        if element["has_bold"] and element["size"] >= base_size:
            return True
        if txt.isupper() and len(txt) > 6:
            return True
        if re.match(r'^\d+[\.\)]', txt):
            return True
        if element["relative_y"] < 0.2:
            return True
        return False

    def assign_heading_levels(self, candidates, sig_sizes):
        level_map = {size: f"H{i+1}" for i, size in enumerate(sig_sizes)}
        headings = []
        for c in candidates:
            level = level_map.get(c["size"], "H3")
            txt = self.clean_text(c["text"])
            headings.append({
                "level": level,
                "text": txt,
                "page": c["page"]
            })
        return headings

    def get_title(self, pages):
        if not pages:
            return ""
        first_page = pages[0]
        cand = []
        for e in first_page:
            txt = self.clean_text(e["text"])
            if len(txt) > 10 and e["relative_y"] < 0.3:
                cand.append((e["size"], txt))
        if cand:
            
            return sorted(cand, key=lambda x: x[0], reverse=True)[0][1]
        return ""

    def extract_outline(self, pdf_path):
        try:
            doc = pymupdf.open(pdf_path)
            pages = self.extract_text_with_metadata(doc)
            doc.close()

            title = self.get_title(pages)
            if not title:
                title = Path(pdf_path).stem.replace('_', ' ').title()

            all_elements = [el for page in pages for el in page]
            merged = self.merge_by_line(all_elements)
            sig_sizes, base_size = self.analyze_font_distribution(merged)

            candidates = [el for el in merged if self.is_heading_candidate(el, sig_sizes, base_size)]
            headings = self.assign_heading_levels(candidates, sig_sizes)

        
            seen = set()
            unique_headings = []
            for h in headings:
                key = (h["level"], h["text"])
                if key not in seen and len(h["text"]) > 3:
                    seen.add(key)
                    unique_headings.append(h)

            return {"title": title, "outline": unique_headings}
        except Exception as e:
            print(f"Failed to process {pdf_path}: {e}")
            return {"title": Path(pdf_path).stem, "outline": []}

    def process_and_save(self, pdf_path, output_dir):
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True, parents=True)
        outline = self.extract_outline(pdf_path)
        output_file = output_dir / f"output_{Path(pdf_path).stem}.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(outline, f, indent=2, ensure_ascii=False)
        print(f"Saved outline to {output_file}")

    def process_folder(self, input_dir, output_dir):
        input_dir = Path(input_dir)
        if not input_dir.exists():
            print(f"Input directory {input_dir} not found.")
            return
        pdf_files = list(input_dir.glob("*.pdf"))
        if not pdf_files:
            print(f"No PDFs found in {input_dir}")
            return
        print(f"Processing {len(pdf_files)} PDFs from {input_dir}")
        for pdf in pdf_files:
            print(f"Processing {pdf.name} ...")
            self.process_and_save(pdf, output_dir)
        print(f"All processed. Outputs in {output_dir}")

def main(input_dir="dataset", output_dir="output", debug=False):
    extractor = PDFOutlineExtractor(debug=debug)
    extractor.process_folder(input_dir, output_dir)

main()