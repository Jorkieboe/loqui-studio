import os
import json
import logging
from typing import Dict, Any, List, Optional
import numpy as np
from rank_bm25 import BM25Okapi
from scripts.utils.config import RAG_SCHEMES_DIR
from scripts.utils.helpers import is_empty_pov, iter_history_turns
from scripts.utils.logger import PipelineLogger
from spacy.lang.en.stop_words import STOP_WORDS as EN_STOP_WORDS
from spacy.lang.nl.stop_words import STOP_WORDS as NL_STOP_WORDS
from scripts.services.llm_service import api_request, LLMServiceError
from scripts.services.ollama_service import is_ollama_available, load_ollama_config

logger = logging.getLogger(__name__)

class RAGServiceError(RuntimeError):
    pass

SPACY_STOP_WORDS = EN_STOP_WORDS.union(NL_STOP_WORDS)

def remove_stop_words(text: str) -> List[str]:
    cleaned = text.lower().replace("?", "").replace(".", "").replace(",", "").replace("!", "")
    words = cleaned.split()
    return [w for w in words if w not in SPACY_STOP_WORDS]

def init_rag_schemes():
    os.makedirs(RAG_SCHEMES_DIR, exist_ok=True)

init_rag_schemes()

def _extract_raw_chunks(data_loaded: Any) -> list:
    if isinstance(data_loaded, list):
        return data_loaded
    if isinstance(data_loaded, dict):
        if isinstance(data_loaded.get("chunks"), list):
            return data_loaded["chunks"]
        return list(data_loaded.values())
    return []

def get_available_rag_schemes() -> List[str]:
    if not os.path.exists(RAG_SCHEMES_DIR):
        return []
    schemes = [
        d for d in os.listdir(RAG_SCHEMES_DIR)
        if os.path.isdir(os.path.join(RAG_SCHEMES_DIR, d))
    ]
    return sorted(schemes)

def get_scheme_metadata_catalog(scheme_id: str) -> Dict[str, Any]:
    scheme_dir = os.path.join(RAG_SCHEMES_DIR, scheme_id) if scheme_id else ""
    if not scheme_id or not os.path.isdir(scheme_dir):
        return {"scheme_id": scheme_id, "fields": []}

    field_values: Dict[str, set] = {}

    struct_path = os.path.join(scheme_dir, "metadata_struct.json")
    if os.path.isfile(struct_path):
        try:
            with open(struct_path, "r", encoding="utf-8") as f:
                struct_data = json.load(f)
            props = (
                struct_data.get("json_schema", {}).get("schema", {}).get("properties")
                or struct_data.get("properties")
                or {}
            )
            if isinstance(props, dict):
                for prop_key, prop_def in props.items():
                    if prop_key not in field_values:
                        field_values[prop_key] = set()
                    if isinstance(prop_def, dict):
                        for enum_val in prop_def.get("enum", []) or []:
                            if enum_val is not None and str(enum_val).strip():
                                field_values[prop_key].add(str(enum_val).strip())
                        items_def = prop_def.get("items")
                        if isinstance(items_def, dict):
                            for enum_val in items_def.get("enum", []) or []:
                                if enum_val is not None and str(enum_val).strip():
                                    field_values[prop_key].add(str(enum_val).strip())
        except Exception as e:
            PipelineLogger.error(f"Failed to read metadata_struct.json for '{scheme_id}'", e)

    metadata_path = os.path.join(scheme_dir, "db_metadata.json")
    if os.path.isfile(metadata_path):
        try:
            with open(metadata_path, "r", encoding="utf-8") as f:
                data_loaded = json.load(f)
            raw_chunks = _extract_raw_chunks(data_loaded)

            for i, raw_chunk in enumerate(raw_chunks):
                chunk = normalize_chunk(raw_chunk, i)
                meta = chunk.get("metadata", {})
                if not isinstance(meta, dict):
                    continue
                for key, val in meta.items():
                    if key not in field_values:
                        field_values[key] = set()
                    if isinstance(val, list):
                        for item in val:
                            if item is not None and str(item).strip():
                                field_values[key].add(str(item).strip())
                    elif val is not None and str(val).strip():
                        field_values[key].add(str(val).strip())
        except Exception as e:
            PipelineLogger.error(f"Failed to scan db_metadata.json for '{scheme_id}'", e)

    fields = [
        {"key": key, "values": sorted(list(vals), key=lambda s: s.lower())}
        for key, vals in sorted(field_values.items(), key=lambda item: item[0].lower())
    ]
    return {"scheme_id": scheme_id, "fields": fields}

def normalize_metadata_filters(raw_filters: Any) -> Dict[str, List[str]]:
    if not raw_filters or not isinstance(raw_filters, dict):
        return {}
    cleaned: Dict[str, List[str]] = {}
    for key, val in raw_filters.items():
        clean_key = str(key).strip()
        if not clean_key:
            continue
        if isinstance(val, list):
            vals = [str(item).strip() for item in val if item is not None and str(item).strip()]
        elif isinstance(val, str):
            vals = [part.strip() for part in val.split(",") if part.strip()]
        elif val is not None and str(val).strip():
            vals = [str(val).strip()]
        else:
            vals = []
        if vals:
            cleaned[clean_key] = vals
    return cleaned

def chunk_matches_metadata_filters(chunk: Dict[str, Any], filters: Dict[str, List[str]]) -> bool:
    if not filters:
        return True
    meta = chunk.get("metadata", {})
    if not isinstance(meta, dict):
        return False

    meta_ci = {str(mk).lower(): mv for mk, mv in meta.items()}
    for filter_key, expected_vals in filters.items():
        if not expected_vals:
            continue
        expected_lower = {v.lower() for v in expected_vals}
        if filter_key in meta:
            raw_val = meta[filter_key]
        elif filter_key.lower() in meta_ci:
            raw_val = meta_ci[filter_key.lower()]
        else:
            return False

        if isinstance(raw_val, list):
            chunk_vals = {str(x).strip().lower() for x in raw_val if x is not None and str(x).strip()}
        elif raw_val is not None and str(raw_val).strip():
            chunk_vals = {str(raw_val).strip().lower()}
        else:
            chunk_vals = set()

        if not (chunk_vals & expected_lower):
            return False
    return True

def normalize_chunk(raw_chunk: Any, fallback_idx: int = 0) -> Dict[str, Any]:
    if isinstance(raw_chunk, str):
        return {
            "id": f"chunk_{fallback_idx}",
            "chunk_id": f"chunk_{fallback_idx}",
            "text": raw_chunk,
            "text_content": raw_chunk,
            "pov": ["all"],
            "metadata": {}
        }

    if not isinstance(raw_chunk, dict):
        text_val = str(raw_chunk)
        return {
            "id": f"chunk_{fallback_idx}",
            "chunk_id": f"chunk_{fallback_idx}",
            "text": text_val,
            "text_content": text_val,
            "pov": ["all"],
            "metadata": {}
        }

    chunk = dict(raw_chunk)

    # Resolve ID
    cid = chunk.get("chunk_id") or chunk.get("id") or f"chunk_{fallback_idx}"
    chunk["id"] = cid
    chunk["chunk_id"] = cid

    # Resolve Text
    text = chunk.get("text_content") or chunk.get("text") or ""
    chunk["text"] = text
    chunk["text_content"] = text

    # Resolve Metadata
    meta = chunk.get("metadata", {})
    if isinstance(meta, str):
        try:
            parsed_meta = json.loads(meta)
            meta = parsed_meta if isinstance(parsed_meta, dict) else {"raw": parsed_meta}
        except Exception:
            meta = {"raw": meta}
    elif not isinstance(meta, dict):
        meta = {}
    chunk["metadata"] = meta

    # Resolve POV
    pov = chunk.get("pov")
    if pov is None and isinstance(meta, dict) and "pov" in meta:
        pov = meta.get("pov")

    if pov is None or pov == "":
        pov_list = ["all"]
    elif isinstance(pov, str):
        try:
            parsed_pov = json.loads(pov)
            if isinstance(parsed_pov, dict) and "pov" in parsed_pov:
                p = parsed_pov["pov"]
                pov_list = p if isinstance(p, list) else [str(p)]
            elif isinstance(parsed_pov, list):
                pov_list = [str(x) for x in parsed_pov]
            else:
                pov_list = [str(parsed_pov)]
        except Exception:
            pov_list = [pov.strip()]
    elif isinstance(pov, dict):
        p = pov.get("pov", ["all"])
        pov_list = p if isinstance(p, list) else [str(p)]
    elif isinstance(pov, list):
        pov_list = [str(x) for x in pov]
    else:
        pov_list = [str(pov)]

    chunk["pov"] = pov_list if pov_list else ["all"]
    return chunk

def is_e5_model(model_name: str) -> bool:
    return "e5" in (model_name or "").lower()

def get_embedding(text: str, is_query: bool = True) -> List[float]:
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

    is_e5 = is_e5_model(model_name)
    if is_e5:
        if is_query:
            formatted_text = text if text.startswith("query:") else f"query: {text}"
        else:
            formatted_text = text if text.startswith("passage:") else f"passage: {text}"
    else:
        formatted_text = text

    if not api_key:
        msg = "No embedding provider configured: OPENAI_API_KEY is missing and Ollama embedding is not active."
        PipelineLogger.error(msg)
        raise RAGServiceError(msg)

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"[RAG] Using embedding model: {model_name} (is_e5={is_e5}, is_query={is_query})")
        res = client.embeddings.create(input=[formatted_text], model=model_name)
        return res.data[0].embedding
    except Exception as e:
        PipelineLogger.error("Failed to generate embedding", e)
        raise RAGServiceError(f"Failed to generate embedding: {e}") from e

class RAGIndex:
    def __init__(self, scheme_id: str):
        self.scheme_id = scheme_id
        self.scheme_dir = os.path.join(RAG_SCHEMES_DIR, scheme_id)
        self.chunks = []
        self.bm25 = None
        self.faiss_index = None
        self.last_loaded_time = 0.0
        self.error: Optional[str] = None
        self.load_index()

    def load_index(self):
        self.error = None
        self.chunks = []
        self.bm25 = None
        self.faiss_index = None
        available_schemes = get_available_rag_schemes()
        if not os.path.exists(self.scheme_dir):
            msg = (
                f"RAG scheme '{self.scheme_id}' does not exist in {RAG_SCHEMES_DIR}. "
                f"Available schemes: {available_schemes}"
            )
            PipelineLogger.error(msg)
            self.error = msg
            return

        metadata_path = os.path.join(self.scheme_dir, "db_metadata.json")
        if not os.path.exists(metadata_path):
            msg = (
                f"RAG metadata file not found at: {metadata_path}. "
                f"Available schemes in {RAG_SCHEMES_DIR}: {available_schemes}"
            )
            PipelineLogger.error(msg)
            self.error = msg
            return
        try:
            self.last_loaded_time = os.path.getmtime(metadata_path)
            with open(metadata_path, "r", encoding="utf-8") as f:
                data_loaded = json.load(f)
            raw_chunks = _extract_raw_chunks(data_loaded)
            normalized_chunks = [normalize_chunk(c, i) for i, c in enumerate(raw_chunks)]
            if normalized_chunks and all("vector_index" in c and isinstance(c["vector_index"], int) for c in normalized_chunks):
                normalized_chunks.sort(key=lambda x: x["vector_index"])
            self.chunks = normalized_chunks
            PipelineLogger.rag(f"Successfully loaded and normalized {len(self.chunks)} chunks for scheme '{self.scheme_id}'.")
        except Exception as e:
            msg = f"Failed to load RAG metadata for '{self.scheme_id}': {e}"
            PipelineLogger.error(msg, e)
            self.error = msg
            return
        if not self.chunks:
            msg = f"No chunks found in metadata for RAG scheme '{self.scheme_id}'."
            PipelineLogger.error(msg)
            self.error = msg
            return
        try:
            tokenized_corpus = [chunk["text"].lower().split() for chunk in self.chunks]
            self.bm25 = BM25Okapi(tokenized_corpus)
            PipelineLogger.rag(f"BM25 initialized successfully for scheme '{self.scheme_id}'.")
        except Exception as e:
            msg = f"Failed to initialize BM25 for '{self.scheme_id}': {e}"
            PipelineLogger.error(msg, e)
            self.error = msg
            return
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
                    embed_text = chunk.get("breadcrumb") or chunk.get("text_content") or chunk.get("text", "")
                    emb = get_embedding(embed_text, is_query=False)
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
            msg = f"Failed to initialize FAISS index for '{self.scheme_id}': {e}"
            PipelineLogger.error(msg, e)
            self.error = msg

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

def retrieve_hybrid(
    query: str,
    scheme_id: str,
    pov_filter: str = "all",
    top_k: int = 4,
    metadata_filters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    global _index_cache
    if not scheme_id:
        raise RAGServiceError("No RAG scheme is configured.")
    available_schemes = get_available_rag_schemes()
    PipelineLogger.rag(f"Available schemes in {RAG_SCHEMES_DIR}: {available_schemes}")
    PipelineLogger.rag(f"Initiating hybrid retrieval. Query: '{query}', Scheme: '{scheme_id}', POV Filter: '{pov_filter}', Top K: {top_k}")
    if scheme_id not in _index_cache or _index_cache[scheme_id].error is not None:
        PipelineLogger.rag(f"Scheme '{scheme_id}' not found in cache or previously failed. Initializing...")
        _index_cache[scheme_id] = RAGIndex(scheme_id)
    else:
        _index_cache[scheme_id].check_and_reload()

    index = _index_cache[scheme_id]
    if index.error:
        raise RAGServiceError(index.error)
    if not index.chunks:
        raise RAGServiceError(f"No chunks loaded for RAG scheme '{scheme_id}'.")

    normalized_filters = normalize_metadata_filters(metadata_filters)
    if normalized_filters:
        allowed_pairs = [
            (i, chunk) for i, chunk in enumerate(index.chunks)
            if chunk_matches_metadata_filters(chunk, normalized_filters)
        ]
        PipelineLogger.rag(
            f"Metadata pre-filter {normalized_filters}: kept {len(allowed_pairs)}/{len(index.chunks)} chunks before search."
        )
    else:
        allowed_pairs = list(enumerate(index.chunks))

    if not allowed_pairs:
        PipelineLogger.rag("No chunks remain after metadata pre-filter. Skipping embedding and BM25 search.")
        return []

    allowed_indices = [i for i, _ in allowed_pairs]
    allowed_chunks = [c for _, c in allowed_pairs]

    faiss_hits = []
    if not index.faiss_index:
        raise RAGServiceError(f"FAISS index not initialized for RAG scheme '{scheme_id}'.")

    try:
        q_emb = get_embedding(query, is_query=True)
        q_emb_arr = np.array([q_emb], dtype=np.float32)
        if q_emb_arr.shape[1] != index.faiss_index.d:
            raise RAGServiceError(
                f"Dimension mismatch: Query vector has {q_emb_arr.shape[1]} dims, "
                f"but FAISS index expects {index.faiss_index.d} dims."
            )

        q_norm = np.linalg.norm(q_emb_arr)
        if q_norm > 0:
            q_emb_arr = q_emb_arr / q_norm

        if normalized_filters:
            import faiss
            try:
                ids_arr = np.ascontiguousarray(allowed_indices, dtype=np.int64)
                sel = faiss.IDSelectorBatch(len(ids_arr), faiss.swig_ptr(ids_arr))
                params = faiss.SearchParameters(sel=sel)
                scores, indices = index.faiss_index.search(q_emb_arr, len(allowed_indices), params=params)
                for score, idx in zip(scores[0], indices[0]):
                    if idx != -1 and idx < len(index.chunks):
                        faiss_hits.append(index.chunks[idx])
            except Exception:
                reconstructed = np.vstack([index.faiss_index.reconstruct(int(i)) for i in allowed_indices]).astype(np.float32)
                if getattr(index.faiss_index, "metric_type", faiss.METRIC_INNER_PRODUCT) == faiss.METRIC_L2:
                    sub_index = faiss.IndexFlatL2(index.faiss_index.d)
                else:
                    sub_index = faiss.IndexFlatIP(index.faiss_index.d)
                sub_index.add(reconstructed)
                scores, sub_indices = sub_index.search(q_emb_arr, len(allowed_chunks))
                for score, sub_idx in zip(scores[0], sub_indices[0]):
                    if sub_idx != -1 and sub_idx < len(allowed_chunks):
                        faiss_hits.append(allowed_chunks[sub_idx])
        else:
            scores, indices = index.faiss_index.search(q_emb_arr, len(index.chunks))
            PipelineLogger.rag(f"FAISS dense search completed. Best index match index: {indices[0][0]} with score {scores[0][0]}")
            for score, idx in zip(scores[0], indices[0]):
                if idx != -1 and idx < len(index.chunks):
                    faiss_hits.append(index.chunks[idx])
    except RAGServiceError:
        raise
    except Exception as e:
        PipelineLogger.error(f"FAISS dense retrieval failed: {e}")
        raise RAGServiceError(f"FAISS dense retrieval failed: {e}") from e

    bm25_hits = []
    if not index.bm25:
        raise RAGServiceError(f"BM25 index not initialized for RAG scheme '{scheme_id}'.")

    try:
        filtered_tokens = remove_stop_words(query)
        if not filtered_tokens:
            filtered_tokens = query.lower().split()
        if normalized_filters:
            chunks_pool = allowed_chunks
            bm25_engine = BM25Okapi([chunk["text"].lower().split() for chunk in chunks_pool])
            log_suffix = " on filtered chunks"
        else:
            chunks_pool = index.chunks
            bm25_engine = index.bm25
            log_suffix = ""
        scores = bm25_engine.get_scores(filtered_tokens)
        ranked_indices = np.argsort(scores)[::-1]
        PipelineLogger.rag(f"BM25 sparse search completed{log_suffix}. Tokenized query: {filtered_tokens}")
        for idx in ranked_indices:
            if scores[idx] > 0 and idx < len(chunks_pool):
                bm25_hits.append(chunks_pool[idx])
        PipelineLogger.rag(f"BM25 found {len(bm25_hits)} matching sparse chunks.")
    except Exception as e:
        PipelineLogger.error(f"BM25 sparse retrieval failed: {e}")
        raise RAGServiceError(f"BM25 sparse retrieval failed: {e}") from e

    candidate_hits = []
    seen_ids = set()
    for chunk in faiss_hits + bm25_hits:
        cid = chunk.get("id")
        if cid not in seen_ids:
            seen_ids.add(cid)
            candidate_hits.append(chunk)

    skip_pov = is_empty_pov(pov_filter)
    pov_hits = []
    if skip_pov:
        PipelineLogger.rag(f"POV filter is '{pov_filter}'. Skipping POV filtering entirely.")
    elif candidate_hits:
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
    if not skip_pov:
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
    categories = {}
    for chunk in chunks:
        if not isinstance(chunk, dict):
            continue
        meta = chunk.get("metadata", {})
        if isinstance(meta, str):
            try:
                meta = json.loads(meta)
            except Exception:
                meta = {}
        if not isinstance(meta, dict):
            continue
        for key, val in meta.items():
            if key not in categories:
                categories[key] = set()
            if isinstance(val, list):
                for v in val:
                    if v is not None:
                        categories[key].add(str(v))
            elif isinstance(val, (str, int, float, bool)):
                categories[key].add(str(val))
    return {k: sorted(list(v)) for k, v in categories.items()}

def rewrite_query(user_message: str, history: List[Dict[str, str]], current_goal: str = "") -> str:
    # [MODIFIED] Check both history and current_goal before skipping query formulation
    if not history and not current_goal:
        return user_message
    context_turns = history[-3:] if history else []
    formatted_history = ""
    for role, text in iter_history_turns(context_turns):
        formatted_history += f"{role.upper()}: {text}\n"
    goal_part = f"\nCurrent Active Dialogue Goal / Topic:\n{current_goal}\n" if current_goal else ""
    prompt = f"""
        Given the conversational history, the active dialogue goal/topic, and the user's latest query,
        formulate a focused, descriptive search query in the same language for retrieving relevant historical context.
        Combine the user's query with the active dialogue goal/topic so that the search captures both,
        while keeping the user's query leading.
        Keep it concise, and do not answer the query. Only return the search query text.
        {goal_part}
        History:
        {formatted_history}

        New Query: {user_message}

        Search Query:
    """
    try:
        rewritten = api_request([{"role": "user", "content": prompt}], stream=False)
        if rewritten and isinstance(rewritten, str):
            cleaned = rewritten.strip().strip('"').strip("'")
            if cleaned:
                PipelineLogger.rag(f"Combined RAG search query: '{cleaned}'")
                return cleaned
        raise RAGServiceError("RAG query rewriting returned an empty query.")
    except LLMServiceError:
        raise
    except RAGServiceError:
        raise
    except Exception as e:
        logger.error(f"Query rewriting failed: {e}")
        raise RAGServiceError(f"RAG query rewriting failed: {e}") from e