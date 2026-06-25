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

# [MODIFIED] Retrieve combined English and Dutch stop words from spaCy
try:
    from spacy.lang.en.stop_words import STOP_WORDS as EN_STOP_WORDS
    from spacy.lang.nl.stop_words import STOP_WORDS as NL_STOP_WORDS
    SPACY_STOP_WORDS = EN_STOP_WORDS.union(NL_STOP_WORDS)
except ImportError:
    # Safe static fallback in case dependencies are loading
    SPACY_STOP_WORDS = {
        "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "as", "at",
        "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "did", "do",
        "for", "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "him", "his", "how",
        "i", "if", "in", "into", "is", "it", "its", "me", "more", "most", "my", "myself", "no", "nor", "not", "of",
        "on", "once", "only", "or", "other", "our", "ours", "out", "over", "own", "same", "she", "should", "so",
        "some", "such", "than", "that", "the", "their", "theirs", "them", "then", "there", "these", "they", "this",
        "those", "through", "to", "too", "under", "until", "up", "very", "was", "we", "were", "what", "when", "where",
        "which", "while", "who", "whom", "why", "with", "you", "your", "yours", "yourself", "yourselves",
        "de", "het", "een", "en", "van", "ik", "je", "hij", "we", "ze", "te", "in", "op", "met", "voor", "aan", "om"
    }

def remove_stop_words(text: str) -> List[str]:
    cleaned = text.lower().replace("?", "").replace(".", "").replace(",", "").replace("!", "")
    words = cleaned.split()
    return [w for w in words if w not in SPACY_STOP_WORDS]

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
    from scripts.services.ollama_service import is_ollama_available, load_ollama_config
    ollama_cfg = load_ollama_config()
    ollama_active = ollama_cfg.get("embedding_enabled", True) and is_ollama_available()

    api_key = os.environ.get("OPENAI_API_KEY")
    base_url = None
    model_name = "text-embedding-3-small"

    if ollama_active:
        host = ollama_cfg.get("host", "http://127.0.0.1:11434").rstrip("/")
        base_url = f"{host}/v1"
        model_name = ollama_cfg.get("embedding_model", "nomic-embed-text")
        api_key = "ollama"

    if api_key:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=api_key, base_url=base_url)
            logger.info(f"[RAG] Using embedding model: {model_name}")
            res = client.embeddings.create(input=[f"query: {text}"], model=model_name)
            return res.data[0].embedding
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")

    # Fallback simulation
    words = text.lower().split()
    vec = np.zeros(1536, dtype=np.float32)
    for i, w in enumerate(words):
        h = hash(w) % 1536
        vec[h] += 1.0
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()

class RAGIndex:
    def __init__(self, scheme_id: str):
        self.scheme_id = scheme_id
        self.scheme_dir = os.path.join(RAG_SCHEMES_DIR, scheme_id)
        self.chunks = []
        self.bm25 = None
        self.faiss_index = None
        self.last_loaded_time = 0.0
        self.load_index()

    def load_index(self):
        metadata_path = os.path.join(self.scheme_dir, "db_metadata.json")
        from scripts.utils.logger import PipelineLogger
        if not os.path.exists(metadata_path):
            PipelineLogger.rag(f"Metadata file not found at: {metadata_path}")
            return
        try:
            self.last_loaded_time = os.path.getmtime(metadata_path)
            with open(metadata_path, "r", encoding="utf-8") as f:
                data_loaded = json.load(f)
            raw_chunks = []
            if isinstance(data_loaded, list):
                raw_chunks = data_loaded
            elif isinstance(data_loaded, dict):
                if "chunks" in data_loaded and isinstance(data_loaded["chunks"], list):
                    raw_chunks = data_loaded["chunks"]
                else:
                    raw_chunks = list(data_loaded.values())
            self.chunks = []
            for i, chunk in enumerate(raw_chunks):
                if isinstance(chunk, str):
                    self.chunks.append({
                        "id": f"chunk_{i}",
                        "text": chunk,
                        "pov": ["all"],
                        "metadata": {}
                    })
                elif isinstance(chunk, dict):
                    if "id" not in chunk:
                        chunk["id"] = f"chunk_{i}"
                    if "text" not in chunk:
                        chunk["text"] = ""
                    if "pov" not in chunk:
                        chunk["pov"] = ["all"]
                    if "metadata" not in chunk:
                        chunk["metadata"] = {}
                    self.chunks.append(chunk)
            PipelineLogger.rag(f"Successfully loaded {len(self.chunks)} chunks for scheme '{self.scheme_id}'.")
        except Exception as e:
            PipelineLogger.error(f"Failed to load RAG metadata for {self.scheme_id}", e)
            return
        if not self.chunks:
            PipelineLogger.rag(f"No chunks found in metadata for scheme '{self.scheme_id}'.")
            return
        try:
            tokenized_corpus = [chunk["text"].lower().split() for chunk in self.chunks]
            self.bm25 = BM25Okapi(tokenized_corpus)
            PipelineLogger.rag(f"BM25 initialized successfully for scheme '{self.scheme_id}'.")
        except Exception as e:
            PipelineLogger.error("Failed to initialize BM25", e)
        try:
            import faiss
            db_faiss_path = os.path.join(self.scheme_dir, "db.faiss")
            alt_faiss_path = os.path.join(self.scheme_dir, f"{self.scheme_id}.faiss")
            resolved_path = None
            if os.path.exists(db_faiss_path):
                resolved_path = db_faiss_path
            elif os.path.exists(alt_faiss_path):
                resolved_path = alt_faiss_path
            if resolved_path:
                PipelineLogger.rag(f"Loading existing FAISS index from: {resolved_path}")
                self.faiss_index = faiss.read_index(resolved_path)
            else:
                PipelineLogger.rag("FAISS database file not found. Generating a new one in-memory...")
                embeddings = []
                for chunk in self.chunks:
                    text_val = chunk.get("text", "")
                    emb = get_embedding(text_val)
                    embeddings.append(emb)
                if embeddings:
                    emb_matrix = np.array(embeddings, dtype=np.float32)
                    norms = np.linalg.norm(emb_matrix, axis=1, keepdims=True)
                    norms[norms == 0] = 1.0
                    emb_matrix = emb_matrix / norms

                    dimension = emb_matrix.shape[1]
                    index_ip = faiss.IndexFlatIP(dimension)
                    index_ip.add(emb_matrix)
                    self.faiss_index = index_ip

                    try:
                        faiss.write_index(self.faiss_index, db_faiss_path)
                        PipelineLogger.rag(f"Successfully created and saved FAISS index of dimension {dimension} to {db_faiss_path}")
                    except Exception as save_err:
                        PipelineLogger.error("Failed to save generated FAISS index to disk", save_err)
        except Exception as e:
            PipelineLogger.error("Failed to initialize FAISS index", e)

    def check_and_reload(self):
        metadata_path = os.path.join(self.scheme_dir, "db_metadata.json")
        from scripts.utils.logger import PipelineLogger
        if os.path.exists(metadata_path):
            try:
                mtime = os.path.getmtime(metadata_path)
                if mtime > self.last_loaded_time:
                    PipelineLogger.rag(f"Detected changes in db_metadata.json for scheme '{self.scheme_id}'. Reloading...")
                    self.load_index()
            except Exception as e:
                PipelineLogger.rag(f"Failed to check mtime for {self.scheme_id}: {e}")

_index_cache = {}

def retrieve_hybrid(query: str, scheme_id: str, pov_filter: str = "all", top_k: int = 4) -> List[Dict[str, Any]]:
    global _index_cache
    from scripts.utils.logger import PipelineLogger
    PipelineLogger.rag(f"Initiating hybrid retrieval. Query: '{query}', Scheme: '{scheme_id}', POV Filter: '{pov_filter}', Top K: {top_k}")
    if scheme_id not in _index_cache:
        PipelineLogger.rag(f"Scheme '{scheme_id}' not found in cache. Initializing...")
        _index_cache[scheme_id] = RAGIndex(scheme_id)
    else:
        _index_cache[scheme_id].check_and_reload()

    index = _index_cache[scheme_id]
    if not index.chunks:
        PipelineLogger.rag(f"No chunks loaded for scheme '{scheme_id}'. Returning empty results.")
        return []

    faiss_hits = []
    if index.faiss_index:
        try:
            q_emb = get_embedding(query)
            q_emb_arr = np.array([q_emb], dtype=np.float32)
            if q_emb_arr.shape[1] != index.faiss_index.d:
                PipelineLogger.rag(
                    f"Dimension mismatch: Query vector has {q_emb_arr.shape[1]} dims, "
                    f"but FAISS index expects {index.faiss_index.d} dims. Skipping FAISS search."
                )
            else:
                q_norm = np.linalg.norm(q_emb_arr)
                if q_norm > 0:
                    q_emb_arr = q_emb_arr / q_norm
                scores, indices = index.faiss_index.search(q_emb_arr, len(index.chunks))
                PipelineLogger.rag(f"FAISS dense search completed. Best index match index: {indices[0][0]} with score {scores[0][0]}")
                for score, idx in zip(scores[0], indices[0]):
                    if idx != -1 and idx < len(index.chunks):
                        faiss_hits.append(index.chunks[idx])
        except Exception as e:
            PipelineLogger.error(f"FAISS dense retrieval failed: {e}")
    else:
        PipelineLogger.rag(f"FAISS index not initialized for scheme '{scheme_id}'. Skipping dense retrieval.")

    bm25_hits = []
    if index.bm25:
        try:
            filtered_tokens = remove_stop_words(query)
            if not filtered_tokens:
                filtered_tokens = query.lower().split()
            scores = index.bm25.get_scores(filtered_tokens)
            ranked_indices = np.argsort(scores)[::-1]
            PipelineLogger.rag(f"BM25 sparse search completed. Tokenized query: {filtered_tokens}")
            for idx in ranked_indices:
                if scores[idx] > 0 and idx < len(index.chunks):
                    bm25_hits.append(index.chunks[idx])
            PipelineLogger.rag(f"BM25 found {len(bm25_hits)} matching sparse chunks.")
        except Exception as e:
            PipelineLogger.error(f"BM25 sparse retrieval failed: {e}")
    else:
        PipelineLogger.rag(f"BM25 index not initialized for scheme '{scheme_id}'. Skipping sparse retrieval.")

    candidate_hits = []
    seen_ids = set()
    for chunk in faiss_hits + bm25_hits:
        cid = chunk.get("id")
        if cid not in seen_ids:
            seen_ids.add(cid)
            candidate_hits.append(chunk)

    pov_hits = []
    if candidate_hits:
        matching = []
        non_matching = []
        for chunk in candidate_hits:
            if not isinstance(chunk, dict):
                continue
            chunk_povs = chunk.get("pov", ["all"])
            if not isinstance(chunk_povs, list):
                chunk_povs = [str(chunk_povs)]
            if pov_filter == "all" or "all" in chunk_povs or pov_filter in chunk_povs:
                matching.append(chunk)
            else:
                non_matching.append(chunk)
        pov_hits = matching + non_matching
        PipelineLogger.rag(f"POV Filtering applied: {len(matching)} matching vs {len(non_matching)} non-matching out of {len(candidate_hits)} total candidates.")

    rrf_scores = {}
    def add_to_rrf(ranking_list):
        for rank, chunk in enumerate(ranking_list, start=1):
            if not isinstance(chunk, dict):
                continue
            chunk_id = chunk.get("id", "chunk_unknown")
            if chunk_id not in rrf_scores:
                rrf_scores[chunk_id] = {"chunk": chunk, "score": 0.0}
            rrf_scores[chunk_id]["score"] += 1.0 / (60.0 + rank)

    add_to_rrf(faiss_hits)
    add_to_rrf(bm25_hits)
    add_to_rrf(pov_hits)

    sorted_rrf = sorted(rrf_scores.values(), key=lambda x: x["score"], reverse=True)
    PipelineLogger.rag(f"Reciprocal Rank Fusion computed for {len(rrf_scores)} unique chunks.")

    results = []
    for item in sorted_rrf[:top_k]:
        chunk = item["chunk"]
        if isinstance(chunk, str):
            results.append({
                "id": "chunk_unknown",
                "text": chunk,
                "pov": ["all"],
                "metadata": {}
            })
        elif isinstance(chunk, dict):
            results.append(chunk)

    PipelineLogger.rag(f"Final retrieved chunks (Top {len(results)}): {[c.get('id') for c in results]}")
    return results

def extract_metadata_categories(chunks: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    categories = {
        "locations": set(),
        "tactics": set(),
        "dates": set()
    }
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        meta = chunk.get("metadata", {})
        if not isinstance(meta, dict):
            meta = {}
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
        if isinstance(turn, str):
            formatted_history += f"USER: {turn}\n"
        elif isinstance(turn, dict):
            role = turn.get("role", "user")
            text = turn.get("text", turn.get("content", ""))
            formatted_history += f"{role.upper()}: {text}\n"
    prompt = f"""
        Given the following conversational turn history and the user's latest query,
        rewrite the query to be a self-contained, descriptive search query in the same language.
        Ensure you incorporate the context of the last AI response to fully resolve pronouns,
        references, or implicit details.
        Keep it concise, and do not answer it. Only return the rewritten query text.

        History:
        {formatted_history}

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