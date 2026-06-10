import os
import json
import logging
from typing import Dict, Any, List
import numpy as np
from rank_bm25 import BM25Okapi

logger = logging.getLogger(__name__)

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ASSETS_DIR = os.path.join(BACKEND_DIR, "assets")
RAG_SCHEMES_DIR = os.path.join(ASSETS_DIR, "rag_schemes")

def init_rag_schemes():
    os.makedirs(RAG_SCHEMES_DIR, exist_ok=True)
    hussite_dir = os.path.join(RAG_SCHEMES_DIR, "hussite_wars")
    if not os.path.exists(hussite_dir):
        os.makedirs(hussite_dir, exist_ok=True)
        hussite_data = [
            {
                "id": "chunk_01",
                "text": "At the Battle of Sudoměř in 1420, Jan Žižka deployed wagon forts to decisively defeat royalist cavalry forces.",
                "pov": ["hussite_commander", "peasant_soldier", "all"],
                "metadata": {
                    "locations": ["Sudoměř"],
                    "tactics": ["wagon fort"],
                    "dates": ["1420"]
                }
            },
            {
                "id": "chunk_02",
                "text": "The wagon fort (vozová hradba) was an armored mobile wall consisting of standard peasant carts chained together to defend infantry.",
                "pov": ["hussite_commander", "all"],
                "metadata": {
                    "locations": ["Bohemia"],
                    "tactics": ["wagon fort"],
                    "dates": []
                }
            },
            {
                "id": "chunk_03",
                "text": "In 1421, at the Battle of Kutná Hora, Žižka executed the first documented tactical breakthrough of a cavalry encirclement using mobile wagon fort artillery.",
                "pov": ["hussite_commander", "all"],
                "metadata": {
                    "locations": ["Kutná Hora"],
                    "tactics": ["wagon fort", "artillery"],
                    "dates": ["1421"]
                }
            }
        ]
        with open(os.path.join(hussite_dir, "db_metadata.json"), "w", encoding="utf-8") as f:
            json.dump(hussite_data, f, indent=2)

init_rag_schemes()

def get_embedding(text: str) -> List[float]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        words = text.lower().split()
        vec = np.zeros(1536, dtype=np.float32)
        for i, w in enumerate(words):
            h = hash(w) % 1536
            vec[h] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        res = client.embeddings.create(input=[text], model="text-embedding-3-small")
        return res.data[0].embedding
    except Exception as e:
        logger.error(f"Failed to generate OpenAI embedding: {e}")
        return np.zeros(1536, dtype=np.float32).tolist()

class RAGIndex:
    def __init__(self, scheme_id: str):
        self.scheme_id = scheme_id
        self.scheme_dir = os.path.join(RAG_SCHEMES_DIR, scheme_id)
        self.chunks = []
        self.bm25 = None
        self.faiss_index = None
        self.load_index()

    def load_index(self):
        metadata_path = os.path.join(self.scheme_dir, "db_metadata.json")
        if not os.path.exists(metadata_path):
            return

        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                self.chunks = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load RAG metadata for {self.scheme_id}: {e}")
            return

        if not self.chunks:
            return

        try:
            tokenized_corpus = [chunk["text"].lower().split() for chunk in self.chunks]
            self.bm25 = BM25Okapi(tokenized_corpus)
        except Exception as e:
            logger.error(f"Failed to initialize BM25: {e}")

        try:
            import faiss
            dimension = 1536
            self.faiss_index = faiss.IndexFlatIP(dimension)

            faiss_path = os.path.join(self.scheme_dir, "index.faiss")
            if os.path.exists(faiss_path):
                self.faiss_index = faiss.read_index(faiss_path)
            else:
                embeddings = []
                for chunk in self.chunks:
                    emb = chunk.get("embedding")
                    if not emb:
                        emb = get_embedding(chunk["text"])
                        chunk["embedding"] = emb
                    embeddings.append(emb)

                if embeddings:
                    emb_matrix = np.array(embeddings, dtype=np.float32)
                    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
                    norms[norms == 0] = 1.0
                    emb_matrix = emb_matrix / norms
                    self.faiss_index.add(emb_matrix)
        except Exception as e:
            logger.error(f"Failed to initialize FAISS index: {e}")

def retrieve_hybrid(query: str, scheme_id: str, pov_filter: str = "all", top_k: int = 4) -> List[Dict[str, Any]]:
    index = RAGIndex(scheme_id)
    if not index.chunks:
        return []

    faiss_hits = []
    if index.faiss_index:
        try:
            q_emb = get_embedding(query)
            q_emb_arr = np.array([q_emb], dtype=np.float32)
            q_norm = np.linalg.norm(q_emb_arr)
            if q_norm > 0:
                q_emb_arr = q_emb_arr / q_norm
            scores, indices = index.faiss_index.search(q_emb_arr, len(index.chunks))
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1:
                    faiss_hits.append(index.chunks[idx])
        except Exception as e:
            logger.error(f"FAISS dense retrieval failed: {e}")

    bm25_hits = []
    if index.bm25:
        try:
            q_tokens = query.lower().split()
            scores = index.bm25.get_scores(q_tokens)
            ranked_indices = np.argsort(scores)[::-1]
            for idx in ranked_indices:
                if scores[idx] > 0:
                    bm25_hits.append(index.chunks[idx])
        except Exception as e:
            logger.error(f"BM25 sparse retrieval failed: {e}")

    rrf_scores = {}

    def update_rrf(hits):
        for rank, chunk in enumerate(hits, start=1):
            chunk_id = chunk["id"]
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = {"chunk": chunk, "score": 0.0}
            rrf_scores[chunk_id]["score"] += 1.0 / (60.0 + rank)

    update_rrf(faiss_hits)
    update_rrf(bm25_hits)

    sorted_rrf = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)

    filtered_results = []
    for item in sorted_rrf:
        chunk = item["chunk"]
        chunk_povs = chunk.get("pov", ["all"])
        if pov_filter == "all" or "all" in chunk_povs or pov_filter in chunk_povs:
            filtered_results.append(chunk)

    return filtered_results[:top_k]

def extract_metadata_categories(chunks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    categories = {
        "locations": set(),
        "tactics": set(),
        "dates": set()
    }
    for chunk in chunks:
        meta = chunk.get("metadata", {})
        for key in ["locations", "tactics", "dates"]:
            vals = meta.get(key, [])
            if isinstance(vals, list):
                for val in vals:
                    categories[key].add(str(val))

    return {k: sorted(list(v)) for k, v in categories.items()}

def rewrite_query(user_message: str, history: List[Dict[str, str]]) -> str:
    if not history:
        return user_message

    context_turns = history[-3:]
    formatted_history = ""
    for turn in context_turns:
        role = turn.get("role", "user")
        text = turn.get("text", turn.get("content", ""))
        formatted_history += f"{role.upper()}: {text}\n"

    prompt = f"""
        Given the following conversational turn history and a new query,
        rewrite the new query to be a self-contained, descriptive search query in the same language. 
        Keep it concise, and do not answer it. Only return the rewritten query text.
        History: {formatted_history}
        New Query: {user_message}
        Rewritten Query:
    """


    try:
        from scripts.services.llm_service import api_request
        rewritten = api_request([{"role": "user", "content": prompt}], stream=False)
        if rewritten and isinstance(rewritten, str):
            return rewritten.strip()
    except Exception as e:
        logger.error(f"Query rewriting failed: {e}")
    return user_message