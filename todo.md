<SECTION name="Environment Setup & Base Workspace Setup">

## Environment Setup & Base Workspace Setup

**Goal:** Establish a robust local developer workspace with a unified build environment, verified dependency configurations, and basic health-check connectivity between the FastAPI server and the Vue 3 Vite application.

- [x] **Dependency Alignment & Hardware Check:**
  - [x] Set up the virtual environment directory structure (`venv`) using `uv` to ensure fast, deterministic package installation.
  - [x] Verify `requirements.txt` installs correctly, accounting for deep-learning libraries such as PyTorch, Hugging Face Transformers (Whisper), and local performance packages (`faiss-cpu`, `rank-bm25`).
  - [x] Adapt `go.bat` to detect system-level CUDA drivers; dynamically select the appropriate PyTorch index URL (e.g., `cu121` or `cpu`) during setup.
- [x] **FastAPI Application Initialization:**
  - [x] Create the primary ASGI app entry point in `backend/main.py`.
  - [x] Mount the FastAPI static files directory targeting compiled Vite assets in `frontend/dist`.
  - [x] Implement a system-level configuration endpoint `/config` that reads static variables directly from `config.json`.
- [x] **Client-Side Project Scaffolding:**
  - [x] Configure `frontend/package.json` with structural plugins including `@vueuse/motion`, `pinia`, `vue-router`, `vue-tippy`, and `socket.io-client`.
  - [x] Implement path aliases in `jsconfig.json` mapping `@/*` to `./src/*`.
  - [x] Set up the Vite configuration in `frontend/vite.config.mjs` to proxy backend requests (`/api` and `/socket.io`) to local address `http://0.0.0.0:5000`.
- [x] **Testing Point 1: Verify Base Workspace Connection**
  - [x] Run `go.bat` to verify backend startup and client-side package compilation.
  - [x] Confirm that accessing `http://localhost:5173/` loads the baseline layout and retrieves JSON metadata successfully from the backend `/config` endpoint.

</SECTION>

<SECTION name="Flat-File Asset Storage & Schema Management">

## Flat-File Asset Storage & Schema Management

**Goal:** Implement the flat-file JSON and YAML asset storage engine on the backend, configuring safe parsing logic to handle character specifications without database overhead.

- [x] **Local Storage Directory Architecture:**
  - [x] Create assets structures within `backend/assets/characters/` and `backend/assets/rag_schemes/`.
  - [x] Define the default character blueprint within `backend/assets/characters/example/` containing base files: `info.json`, `prompts.yaml`, and `layout.json`.
- [x] **`info.json` & `layout.json` Structural Adapters:**
  - [x] Implement file utilities to serialize metadata variables (e.g., visual accents, `idle_timeout_seconds`, and index pointers) to JSON.
  - [x] Program parser routines in `backend/scripts/api/character.py` to write and read the Vue Flow JSON graph schema (nodes, edges, and positions) directly to and from `layout.json`.
- [x] **Block-Style Prompt Serialization (`prompts.yaml`):**
  - [x] Configure the `ruamel.yaml` parser instance to enforce strict mapping controls, proper sequence indents, and clean vertical offsets.
  - [x] Create custom string presenters (`LiteralDumper`) to force block-style styles (`|` and `|-`) when persisting long character descriptions or narrative constraints to disk.
- [x] **Testing Point 2: Verify Asset Serialization**
  - [x] Create a mock character via file duplication.
  - [x] Execute programmatic modifications to the YAML structure and verify that comments, multi-line block strings, and custom sequences are written to disk without formatting loss.

</SECTION>

<SECTION name="State Machine, Hybrid RAG, & LLM Orchestration Engine">

## State Machine, Hybrid RAG, & LLM Orchestration Engine

**Goal:** Develop the backend orchestration logic, implementing state-machine step parsing, hybrid RAG context assembly, and OpenAI-compatible API execution with modular parameter configurations.

- [x] **Step 1: Input Evaluation & State Machine Step Parsing (`chatsession.py`):**
  - [x] Receive the raw user message input from the active session router.
  - [x] Parse and evaluate which dialog node or step to follow by direct traversal of the Vue Flow node and edge list stored in the layout schema.
  - [x] Program safety-relevance checkers (`validate_response`) to validate conversation bounds. If input is off-topic, redirect context dynamically to the global `deflect` node.
  - [x] Program `pick_step` using structured JSON schemas to classify user responses when choosing paths at branching split connections.
- [x] **Step 2: Contextual Search Query Rewriting (`rag_service.py`):**
  - [x] If RAG is enabled, program query-contextualization routines (`rewrite_query`) to combine the user's raw message and the last AI response (conversational turn history) into a focused search query.
- [x] **Step 3: Document Retrieval and Search Pipelines (`rag_service.py`):**
  - [x] Execute asymmetrical dense FAISS index lookups and Rank-BM25 sparse searches over the compiled query.
  - [x] Apply POV filters to restrict chunk matches and rank the final document results using the RRF algorithm:
    $$RRF\_Score(d \in D) = \sum_{m \in M} \frac{1}{60 + r_m(d)}$$
  - [x] Extract contextual categories from the document candidates using defined extraction metadata guidelines.
- [x] **Step 4: Structured Dialogue Payload Assembly (`orchestrator.py`):**
  - [x] Assemble all compiled elements: the base system instructions (`base_prompt`), the active state prompt parameters (`var_prompt`), chronological conversation history lists, and the retrieved RAG background context documents.
- [x] **Step 5: Grounded LLM Client Execution (`llm_service.py`):**
  - [x] Send the fully assembled payload to `llm_service.py` to trigger text generation or stream-parsing delta outputs.
  - [x] Implement `api_request` to dispatch conversational payloads to target endpoint formats (local API, RunPod, or OpenAI).
  - [x] Incorporate model parameter presets from `config.json` to dynamically override max tokens, temperature, penalties, and stop tokens.
  - [x] Integrate stream processing and SSE-line parsing (`data: ` delta outputs) to stream responses chunk-by-chunk to the calling application thread.
  - [x] Integrate a token-counting utility using `tiktoken` to log exact input and output lengths prior to and during generation.
- [x] **Testing Point 3: Verify RAG, FSM, and LLM Orchestration**
  - [x] Execute a test script to confirm that the state machine, hybrid retrieval, and `llm_service` process a query simultaneously.
  - [x] Verify that model payloads contain parsed system rules, active settings, and RAG context blocks.
  - [x] Confirm that the local client receives streamed text chunks from the selected model preset without error.

</SECTION>

<SECTION name="Bidirectional Event Channels & Speech Pipelines">

## Bidirectional Event Channels & Speech Pipelines

**Goal:** Implement low-latency Socket.IO communication and establish lazy-loaded, thread-safe speech-to-text (STT) and text-to-speech (TTS) engines.

- [x] **Socket.IO Real-Time Dispatcher:**
  - [x] Establish the async socket server instance (`sio`) inside `backend/main.py` with custom buffer limits to handle binary streaming.
  - [x] Set up event listeners to capture WebM mic arrays, handle disconnect triggers, and route new chat requests.
- [x] **Unified Generation Pipeline Orchestrator:**
  - [x] Program the backend session routing loop to process messages through a single execution path.
  - [x] Implement parameter injection overrides for sandbox mode. This enables running prompts, transient graph nodes, and custom variable prompts from memory without making persistent writes to disk.
  - [x] Create state models in `backend/scripts/core/context.py` to package context parameters cleanly.
- [x] **Lazy-Loaded Speech Processing Engines:**
  - [x] Set up the Hugging Face Whisper pipeline to load on a separate thread, preventing main-thread blocking on startup.
  - [x] Implement audio decoding routines inside `backend/scripts/services/transcription_service.py` to convert incoming WebM chunks into 16kHz float32 arrays via FFmpeg.
  - [x] Integrate local TTS routines to stream generated audio back to the client.
- [x] **Testing Point 4: Verify Bidirectional Pipeline**
  - [x] Use tool simulations to stream a raw audio file into the WebSocket pipeline.
  - [x] Verify that Whisper processes the stream in memory, that the orchestrator executes, and that text chunks and binary audio play back as expected.

</SECTION>

<SECTION name="Developer Workspace UI & Visual Node Canvas">

## Developer Workspace UI & Visual Node Canvas

**Goal:** Build the Dev View application, implementing Pinia state management, modular configuration form inputs, and the visual Vue Flow interactive canvas.

- [ ] **In-Memory Draft Store (Pinia):**
  - [ ] Implement `frontend/src/stores/store.js` to manage transient character models with snake_case properties (`current_character`, `character_state`, `is_transitioning`, `whisper_enabled`, `whisper_ready`, `selected_connection_id`, `graph_editor`, `can_message`).
  - [ ] Write schema baseline loaders to pull current layouts (`info.json`, `prompts.yaml`, and the Vue Flow structure in `layout.json`) and populate the active Pinia store.
  - [ ] Establish validation logic to restrict sandbox access until the minimum fields (Name, Description, Do's, and Don'ts) are populated. Write standard fallback variables ("chat with the user") to replace optional omitted configurations.
- [ ] **Unified Creator Layout (`creator_workspace.vue`):**
  - [ ] Build a split-screen flex UI displaying editing fields on the left pane and the sandbox tester on the right pane.
  - [ ] Implement tabbed route navigation to switch views between the character profile settings form (Tab A) and the node workflow graph (Tab B).
- [ ] **Tab A: Character Profile Form & Image Sanitizer:**
  - [ ] Implement text areas for settings and personality traits.
  - [ ] Build client-side image validation. This includes checking aspect ratios and downscaling custom images to a maximum resolution of 500x500 pixels before uploading.
- [ ] **Tab B: Vue Flow Workspace & Context Components:**
  - [ ] Build the vertical top-to-bottom visual canvas in `prompt_graph_view.vue`.
  - [ ] Implement right-click context menu listeners to spawn node types: `start_node`, `loop_node`, `end_node`, and advanced prompts.
  - [ ] Set up properties panel bindings to reactively synchronize visual node states directly with the Pinia draft.
- [ ] **Testing Point 5: Verify Developer Workspace UI**
  - [ ] Access `/dev` in browser, open Tab A, upload an image, and verify downscaling limits.
  - [ ] Open Tab B, draw edges between nodes, edit parameters in the properties panel, and confirm that the local Pinia draft store updates reactively.

</SECTION>

<SECTION name="Stateful Sandbox & Museum View (Experience Mode)">

## Stateful Sandbox & Museum View (Experience Mode)

**Goal:** Build out the physical kiosk Experience Mode, implementing active session resets, ambient audio transitions, and sandbox telemetry logs.

- [ ] **Stateful Sandbox Live Simulation Panel:**
  - [ ] Build the side-by-side sandbox view inside the Dev Workspace with dual-mode toggles (Text Mode / Voice Mode).
  - [ ] Program active tracking variables into the Pinia store to monitor active nodes and output logs directly next to the editor panel.
  - [ ] Configure execution routes to send transient draft configurations and custom turn history directly to the backend testing endpoints.
- [ ] **Kiosk Carousel & Always-Accessible Voice Interface:**
  - [ ] Build the public character overview landing layout in `experience_view.vue`.
  - [ ] Set up voice recorders using `Hot Mic` stream states to eliminate hardware capture delays on touch activations.
  - [ ] Add real-time audio state cues (idle, listening, thinking, speaking) with localized transitions.
- [ ] **System Idle Reset & Audio Context Managers:**
  - [ ] Implement local countdown timers initialized with the target `idle_timeout_seconds` configuration. Ensure user actions reset this timer.
  - [ ] Set up auto-reset handlers to disconnect WebSocket pipelines and clear cache files when a terminal `end_node` is reached or when the idle timer expires.
  - [ ] Integrate background audio mixers to loop ambient soundscapes with smooth volume fades.
- [ ] **Testing Point 6: Verify Stateful Kiosk & Sandbox**
  - [ ] Build a complex loop on the graph, save the changes, and launch the kiosk interface.
  - [ ] Run a voice session. Verify that transitions occur along defined paths, that the background environment audio plays, and that idle timeouts reset the view to the selection screen.

</SECTION>

<SECTION name="Deployment">

## Deployment

**Goal:** Package, optimize, and deploy the finished application.

- [ ] **Frontend Production Compilation:**
  - [ ] Run Vite production compiler scripts to output optimized code.
  - [ ] Confirm file trees generated in `frontend/dist/` resolve paths properly.
- [ ] **Server Deployment Configuration:**
  - [ ] Set up environment files (`.env`) for production use.
  - [ ] Configure safe production logging parameters, process limits, and CORS access headers.
- [ ] **Verification & Kiosk Simulation Testing:**
  - [ ] Start the production ASGI server.
  - [ ] Verify local system audio, offline database access, and GPU performance capabilities.

</SECTION>