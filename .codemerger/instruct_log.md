# Instruction Log: Loqui-Studio

## [2026-11-16 12:11:58] • Instruct Input

I want to make a change to the ragshemes. Not al characters rag schemes have different pov. I want to add a option to POV 'None' that skips the filtering on pov entirely. so i use all chunks

---

## [2026-11-16 12:32:33] • Instruct Input

rag scheme is not found (base) (.venv) PS C:\Users\jorri\fork\Loqui-Studio> python backend/scripts/test_rag.py "heb je suggesties om te lunchen" --scheme breda       
============================================================
                 LOQUI RAG CONSOLE TESTER
============================================================
Query:       heb je suggesties om te lunchen
RAG Scheme:  breda
POV Filter:  None (skipping POV filtering)
Top K:       4
------------------------------------------------------------
[RAG] Initiating hybrid retrieval. Query: 'heb je suggesties om te lunchen', Scheme: 'breda', POV Filter: 'None', Top K: 4
[RAG] Scheme 'breda' not found in cache. Initializing...
[RAG] Metadata file not found at: C:\Users\jorri\fork\Loqui-Studio\backend\assets\rag_schemes\breda\db_metadata.json
[RAG] No chunks loaded for scheme 'breda'. Returning empty results.

--- RETRIEVED CHUNKS ---
No chunks retrieved.

============================================================
(base) (.venv) PS C:\Users\jorri\fork\Loqui-Studio> 


Can you please create some logging that check al available rag schemes. all the rag schemes are in ./backend/assets/rag_schemes there each scheme has it own folder

---

