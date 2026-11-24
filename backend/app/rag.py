"""Knowledge retrieval over company documents (SOPs, policies, tone guides)."""
import hashlib
import re
from pathlib import Path

import numpy as np
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from .embeddings import embed
from .models import KnowledgeChunk, KnowledgeDoc, utcnow

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge"


def _chunks(content: str) -> list[tuple[str, str]]:
    """Split markdown by '## ' headings -> [(heading, text)]."""
    parts = re.split(r"(?m)^##\s+", content)
    out = []
    intro = parts[0].strip()
    title_line = intro.splitlines()[0].lstrip("# ").strip() if intro else ""
    if intro and len(intro) > 60:
        out.append((title_line or "Overview", intro))
    for p in parts[1:]:
        head, _, body = p.partition("\n")
        text = f"{head.strip()}\n{body.strip()}".strip()
        if body.strip():
            out.append((head.strip(), text))
    return out or [("Document", content.strip())]


def upsert_doc(db: Session, title: str, content: str, source: str = "") -> KnowledgeDoc:
    h = hashlib.sha256(content.encode()).hexdigest()
    doc = db.scalar(select(KnowledgeDoc).where(KnowledgeDoc.title == title))
    if doc and doc.content_hash == h:
        return doc
    if doc:
        db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.doc_id == doc.id))
        doc.content, doc.content_hash, doc.source, doc.updated_at = content, h, source, utcnow()
    else:
        doc = KnowledgeDoc(title=title, content=content, content_hash=h, source=source)
        db.add(doc)
    db.flush()
    for heading, text in _chunks(content):
        db.add(KnowledgeChunk(doc_id=doc.id, heading=heading, text=text, embedding=embed(f"{title} {text}")))
    db.commit()
    return doc


def ingest_folder(db: Session, folder: Path = KNOWLEDGE_DIR) -> int:
    n = 0
    for f in sorted(folder.glob("*.md")):
        text = f.read_text(encoding="utf-8")
        title = text.splitlines()[0].lstrip("# ").strip() if text else f.stem
        upsert_doc(db, title, text, source=f.name)
        n += 1
    return n


def search(db: Session, query: str, k: int = 4, min_score: float = 0.05) -> list[dict]:
    rows = db.execute(
        select(KnowledgeChunk.id, KnowledgeChunk.heading, KnowledgeChunk.text, KnowledgeChunk.embedding, KnowledgeDoc.title)
        .join(KnowledgeDoc, KnowledgeDoc.id == KnowledgeChunk.doc_id)
    ).all()
    if not rows:
        return []
    mat = np.asarray([r.embedding for r in rows], dtype=np.float32)
    q = np.asarray(embed(query), dtype=np.float32)
    scores = mat @ q
    top = np.argsort(-scores)[:k]
    return [
        {
            "doc": rows[i].title,
            "heading": rows[i].heading,
            "text": rows[i].text,
            "score": round(float(scores[i]), 3),
        }
        for i in top
        if scores[i] >= min_score
    ]
