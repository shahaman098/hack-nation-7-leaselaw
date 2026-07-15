from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import numpy as np

from hackforge.paths import INDEX_DIR
from hackforge.utils import write_json


DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def structural_text(obj: dict[str, Any] | Any) -> str:
    if hasattr(obj, "model_dump"):
        d = obj.model_dump()
    elif isinstance(obj, dict):
        d = obj
    else:
        d = {"text": str(obj)}
    if d.get("text_for_embed"):
        return str(d["text_for_embed"])
    parts = [
        d.get("primary_user") or d.get("user") or "",
        d.get("painful_workflow") or d.get("problem") or "",
        d.get("imported_mechanism") or d.get("mechanism") or "",
        d.get("last_mile_action") or d.get("action") or "",
        d.get("core_computation") or "",
        d.get("working_title") or d.get("name") or "",
    ]
    return " | ".join(str(p) for p in parts if p)


class EmbedIndex:
    def __init__(self, index_dir: Path | None = None, model_name: str | None = None):
        self.index_dir = Path(index_dir or os.getenv("HACKFORGE_INDEX_DIR", INDEX_DIR))
        self.model_name = model_name or os.getenv("HACKFORGE_EMBED_MODEL", DEFAULT_MODEL)
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self._model = None
        self._index = None
        self._meta: list[dict[str, Any]] = []

    @property
    def meta_path(self) -> Path:
        return self.index_dir / "meta.jsonl"

    @property
    def faiss_path(self) -> Path:
        return self.index_dir / "index.faiss"

    @property
    def info_path(self) -> Path:
        return self.index_dir / "info.json"

    def available(self) -> bool:
        return self.faiss_path.exists() and self.meta_path.exists()

    def _load_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def encode(self, texts: list[str]) -> np.ndarray:
        model = self._load_model()
        emb = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return np.asarray(emb, dtype=np.float32)

    def build(self, records: list[dict[str, Any]], batch_size: int = 64) -> Path:
        import faiss

        if not records:
            raise ValueError("No records to index")
        texts = [structural_text(r) for r in records]
        vectors = []
        for i in range(0, len(texts), batch_size):
            vectors.append(self.encode(texts[i : i + batch_size]))
        mat = np.vstack(vectors)
        index = faiss.IndexFlatIP(mat.shape[1])
        index.add(mat)
        faiss.write_index(index, str(self.faiss_path))
        with self.meta_path.open("w", encoding="utf-8") as f:
            for r in records:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
        write_json(
            self.info_path,
            {
                "model": self.model_name,
                "count": len(records),
                "dim": int(mat.shape[1]),
                "faiss": str(self.faiss_path),
            },
        )
        self._index = index
        self._meta = records
        return self.index_dir

    def load(self) -> None:
        import faiss

        if not self.available():
            raise FileNotFoundError(f"No FAISS index at {self.index_dir}. Run: hackforge corpus build-index")
        self._index = faiss.read_index(str(self.faiss_path))
        self._meta = []
        with self.meta_path.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    self._meta.append(json.loads(line))

    def search(self, query: str | dict[str, Any] | Any, k: int = 8) -> list[dict[str, Any]]:
        if self._index is None:
            if self.available():
                self.load()
            else:
                return []
        q = structural_text(query) if not isinstance(query, str) else query
        vec = self.encode([q])
        scores, idxs = self._index.search(vec, min(k, len(self._meta) or k))
        out = []
        for score, idx in zip(scores[0], idxs[0]):
            if idx < 0 or idx >= len(self._meta):
                continue
            item = dict(self._meta[idx])
            item["similarity"] = float(score)
            out.append(item)
        return out
