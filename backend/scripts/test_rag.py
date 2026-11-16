import os
import sys
import json
import argparse
from dotenv import load_dotenv

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

load_dotenv()
load_dotenv(os.path.join(BACKEND_DIR, "..", ".env"))
load_dotenv(os.path.join(BACKEND_DIR, ".env"))

from scripts.services.rag_service import retrieve_hybrid, extract_metadata_categories, get_available_rag_schemes

def run_rag_test(query: str, scheme: str, pov: str = None, top_k: int = 4):
    normalized_pov = None if (pov is None or str(pov).strip().lower() in ["none", "null", ""]) else str(pov).strip()

    available_schemes = get_available_rag_schemes()

    print("=" * 60)
    print("                 LOQUI RAG CONSOLE TESTER")
    print("=" * 60)
    print(f"Query:              {query}")
    print(f"RAG Scheme:         {scheme}")
    print(f"Available Schemes:  {', '.join(available_schemes) if available_schemes else 'None found'}")
    if scheme not in available_schemes:
        print(f"[WARNING] Scheme '{scheme}' is NOT in available schemes list!")
    print(f"POV Filter:         {normalized_pov if normalized_pov is not None else 'None (skipping POV filtering)'}")
    print(f"Top K:              {top_k}")
    print("-" * 60)

    chunks = retrieve_hybrid(
        query=query,
        scheme_id=scheme,
        pov_filter=normalized_pov,
        top_k=top_k
    )

    print("\n--- RETRIEVED CHUNKS ---")
    if not chunks:
        print("No chunks retrieved.")
    else:
        for idx, chunk in enumerate(chunks, 1):
            chunk_id = chunk.get("chunk_id") or chunk.get("id", "N/A")
            chunk_pov = chunk.get("pov", [])
            chunk_text = chunk.get("text_content") or chunk.get("text", "")
            chunk_meta = chunk.get("metadata", {})
            breadcrumb = chunk.get("breadcrumb")

            print(f"\n[{idx}] ID: {chunk_id}")
            if breadcrumb:
                print(f"    Breadcrumb: {breadcrumb}")
            print(f"    POV:      {chunk_pov}")
            print(f"    Metadata: {json.dumps(chunk_meta, ensure_ascii=False)}")
            print(f"    Text:     {chunk_text}")

        categories = extract_metadata_categories(chunks)
        print("\n--- EXTRACTED METADATA CATEGORIES ---")
        for cat, values in categories.items():
            print(f"  {cat}: {values}")

    print("\n" + "=" * 60)
    return chunks

def main():
    parser = argparse.ArgumentParser(description="Test RAG retrieval from console with input, scheme, and POV.")
    parser.add_argument("query", nargs="?", default="wagon fort", help="Search input / query text")
    parser.add_argument("--scheme", "-s", default="hussite_wars", help="RAG scheme identifier (default: hussite_wars)")
    parser.add_argument("--pov", "-p", default=None, help="POV filter string. If omitted or 'None', POV filter is skipped")
    parser.add_argument("--top-k", "-k", type=int, default=4, help="Number of chunks to retrieve (default: 4)")

    args = parser.parse_args()
    run_rag_test(query=args.query, scheme=args.scheme, pov=args.pov, top_k=args.top_k)

if __name__ == "__main__":
    main()