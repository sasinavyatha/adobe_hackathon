import fitz
import json
import re
import os

def extract_headings(pdf_path, output_json):
    doc = fitz.open(pdf_path)

    headings = []
    title = None
    title_buffer = []
    title_found = False

    # Regex patterns
    h1_number_only = re.compile(r'^\d+\.$')
    h1_with_text = re.compile(r'^\d+\.\s?.+')
    h2_pattern = re.compile(r'^\d+\.\d+\s?')
    h3_pattern = re.compile(r'^\d+\.\d+\.\d+\s?')

    ignore_words = {"Version", "Date", "Remarks", "Identifier"}
    ignore_numbers = {"0.1", "0.2", "0.3", "0.7", "0.8", "1.0"}
    seen_headings = set()

    toc_page_num = None
    in_toc_page = False
    pending_h1_number = None

    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]

        for b in blocks:
            if "lines" not in b:
                continue

            for l in b["lines"]:
                for s in l["spans"]:
                    text = s["text"]
                    clean_text = text.strip()
                    if not clean_text:
                        continue

                    if "©" in clean_text or "Copyright" in clean_text:
                        continue
                    if clean_text in ignore_words or clean_text in ignore_numbers:
                        continue
                    if clean_text.startswith("0."):
                        continue
                    if all(ch in ".•" for ch in clean_text):
                        continue
                    if re.fullmatch(r'\d+', clean_text):
                        continue

                    is_bold = "Bold" in s["font"]

                    if page_num == 0 and is_bold:
                        title_buffer.append(text)

                    if clean_text == "Table of Contents" and is_bold:
                        toc_page_num = page_num
                        if clean_text not in seen_headings:
                            headings.append({"level": "H1", "text": clean_text + " ", "page": page_num})
                            seen_headings.add(clean_text)
                        in_toc_page = True
                        continue

                    if in_toc_page and page_num == toc_page_num:
                        if h2_pattern.match(clean_text) or h3_pattern.match(clean_text):
                            continue

                    if is_bold and h1_number_only.match(clean_text):
                        pending_h1_number = clean_text
                        continue

                    if pending_h1_number and is_bold:
                        merged_text = pending_h1_number + " " + clean_text
                        if merged_text not in seen_headings:
                            headings.append({"level": "H1", "text": merged_text + " ", "page": page_num})
                            seen_headings.add(merged_text)
                        pending_h1_number = None
                        continue

                    if is_bold and (h1_with_text.match(clean_text) or
                                    clean_text in ["Revision History", "Acknowledgements", "References"]):
                        if clean_text not in seen_headings:
                            headings.append({"level": "H1", "text": clean_text + " ", "page": page_num})
                            seen_headings.add(clean_text)
                        continue

                    if h2_pattern.match(clean_text):
                        if clean_text not in seen_headings:
                            headings.append({"level": "H2", "text": clean_text + " ", "page": page_num})
                            seen_headings.add(clean_text)
                        continue

                    if h3_pattern.match(clean_text):
                        if clean_text not in seen_headings:
                            headings.append({"level": "H3", "text": clean_text + " ", "page": page_num})
                            seen_headings.add(clean_text)
                        continue

        if page_num == 0 and title_buffer and not title_found:
            title = "".join(title_buffer) + " "
            title_found = True

    result = {
        "title": title if title else "",
        "outline": headings
    }

    os.makedirs(os.path.dirname(output_json), exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)

    print(f"✅ JSON created at: {output_json}")
    return result


if __name__ == "__main__":
    input_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "input")
    output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")

    for filename in os.listdir(input_dir):
        if filename.lower().endswith(".pdf"):
            pdf_file = os.path.join(input_dir, filename)
            json_file = os.path.join(output_dir, filename.replace(".pdf", ".json"))
            extract_headings(pdf_file, json_file)
