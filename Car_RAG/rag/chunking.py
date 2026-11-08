"""Splits documents into chunks. Each chunk keeps its own text and a copy of the document's metadata."""
from dataclasses import dataclass

from rag.loader import Doc


@dataclass
class Chunk:
    id: str            # "<doc id>#<number>", e.g. "of-210-city#2"
    doc_id: str
    text: str          # the original text, exactly as it will be shown to the model
    meta: dict


def chunk_fixed(doc: Doc, size: int = 350, overlap: int = 50) -> list[Chunk]:
    """Baseline: cut every `size` characters, with `overlap` characters repeated between neighbours."""
    chunks = []
    step = size - overlap
    for start in range(0, max(len(doc.text), 1), step):
        piece = doc.text[start:start + size]
        if piece.strip():
            chunks.append(Chunk(f"{doc.id}#{len(chunks)}", doc.id, piece, dict(doc.meta)))
        if start + size >= len(doc.text):
            break
    return chunks


def chunk_by_headings(doc: Doc) -> list[Chunk]:
    lines = doc.text.splitlines()

    title = next(
        (line[2:].strip() for line in lines if line.startswith("# ")),
        doc.id
    )

    chunks = []
    current_heading = None
    current_lines = []

    def save_chunk():
        content = "\n".join(current_lines).strip()

        if not content:
            return

        heading_path = (
            f"{title} › {current_heading}"
            if current_heading
            else title
        )

        text = f"{heading_path}\n{content}"

        meta = dict(doc.meta)
        meta["section"] = current_heading or ""

        chunks.append(
            Chunk(
                id=f"{doc.id}#{len(chunks)}",
                doc_id=doc.id,
                text=text,
                meta=meta
            )
        )

    for line in lines:
        if line.startswith("# "):
            continue

        if line.startswith("## "):
            save_chunk()
            current_heading = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)

    save_chunk()

    return chunks