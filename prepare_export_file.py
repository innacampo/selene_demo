import os
import json
from pypdf import PdfReader


def simple_chunker(text, chunk_size=1000, overlap=100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def prepare_export_file(pdf_folder, output_filename="ingest_me.json"):
    payload = []

    for filename in os.listdir(pdf_folder):
        if filename.endswith(".pdf"):
            reader = PdfReader(os.path.join(pdf_folder, filename))
            full_text = " ".join(
                [p.extract_text() for p in reader.pages if p.extract_text()]
            )
            chunks = simple_chunker(full_text)

            for i, chunk in enumerate(chunks):
                payload.append(
                    {
                        "id": f"{filename}_{i}",
                        "text": chunk,
                        "metadata": {"source": filename},
                    }
                )

    with open(output_filename, "w") as f:
        json.dump(payload, f)
    print(f"Created {output_filename} with {len(payload)} chunks.")


# Usage
prepare_export_file("./my_pdfs")
