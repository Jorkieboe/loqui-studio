## Architecture Overview

### System Topology & Communication Flow

The system architecture utilizes a split-interface topology designed to operate efficiently in both online cloud environments and fully offline, localized deployments (such as physical museum kiosks). The client interface is a single-page application (SPA) built with Vue 3 and Vite, while the backend is an asynchronous, high-performance ASGI server powered by FastAPI.

```
+-------------------------------------------------------------------------------------------------+
|                                         VUE 3 CLIENT                                            |
|                                                                                                 |
|   +--------------------------+     +--------------------------+     +-----------------------+   |
|   |        Dev View          |     |    Visual Canvas (Rete)  |     |   Experience View     |   |
|   +------------+-------------+     +------------+-------------+     +-----------+-----------+   |
|                |                                |                               |               |
|                |                                |                               |               |
+----------------|--------------------------------|-------------------------------|---------------+
                 |                                |                               |
                 | HTTP REST (JSON / Multipart)   | HTTP Ephemeral Drafts         | Socket.IO (WS)
                 | (Port 5000 /api/*)             | (Port 5000 /api/*)            | (Bi-directional)
                 v                                v                               v
+-------------------------------------------------------------------------------------------------+
|                                        FASTAPI BACKEND                                          |
|                                                                                                 |
|   +--------------------------+     +--------------------------+     +-----------------------+   |
|   |        Assets API        |     |      Inference API       |     |    Session Manager    |   |
|   |                          |     |                          |     |                       |   |
|   |  - Save/Load YAML/JSON   |     |  - Ephemeral testing     |     |  - Socket.IO Server   |   |
|   |  - Media asset uploads   |     |  - REST Chat endpoints   |     |  - WS lifecycle ops   |   |
|   +------------+-------------+     +------------+-------------+     +-----------+-----------+   |
|                |                                |                               |               |
|                +------------------------+-------+-------------------------------+               |
|                                         |                                                       |
|                                         v                                                       |
|                            +--------------------------+                                         |
|                            | Unified Pipeline Engine  |                                         |
|                            |                          |                                         |
|                            |   - FSM Node Traversal   |                                         |
|                            |   - Hybrid RAG Retriever |                                         |
|                            |   - Parameter Injection  |                                         |
|                            +------------+-------------+                                         |
|                                         |                                                       |
|                 +-----------------------+-----------------------+                               |
|                 v                                               v                               |
|   +--------------------------+                     +--------------------------+                 |
|   |   Local AI Pipe (Lazy)   |                     |      Cloud AI Pipes      |                 |
|   |                          |                     |                          |                 |
|   |  - Whisper (STT)         |                     |  - OpenAI / RunPod APIs  |                 |
|   |  - Local Embeddings      |                     |  - Whisper STT (Fallback)|                 |
|   |  - Offline TTS Engine    |                     |  - Cloud TTS             |                 |
|   +--------------------------+                     +--------------------------+                 |
+-------------------------------------------------------------------------------------------------+
```

#### Communication Protocols
- **HTTP REST APIs**: Used for asset-heavy management tasks, metadata listing, history queries, and system configuration. File uploads (e.g., character avatars) are handled via standard HTTP `multipart/form-data`.
- **Socket.IO (WebSockets)**: Handles the high-frequency, bidirectional communication needed for real-time interactions. During Experience Mode, continuous audio state updates, Whisper transcription telemetry, text chunk streaming, and binary audio playback payloads travel over this dedicated low-latency channel.

---

### Key Architectural Decisions

#### Storage Engine
The platform utilizes a structured, directory-based local file system (flat-file database model) where each character's configuration is fully contained within a dedicated assets directory using `info.json`, `prompts.yaml`, and `layout.json`. FAISS vector indices are stored directly on disk alongside these files.

#### Bidirectional Real-Time Communication
The system leverages Socket.IO over ASGI (via python-socketio) for duplex communication. This choice enables native event-driven streaming of both textual metadata and chunked binary audio packages to the client, keeping synchronization logic straightforward and minimizing overhead.

---

### Execution Pipelines

#### Unified Input-to-Output Pipeline
The backend routes conversation traffic through a single, unified pipeline function. This unified function processes text or audio input, steps through the state machine, retrieves contextual data, and generates output streams.

1. **Input Reception & Pre-processing**: 
   - *Experience Mode*: The visitor's voice input is recorded and streamed over Socket.IO. The lazy-loaded Whisper pipeline decodes the audio in memory to generate a textual transcription.
   - *Sandbox Mode*: The creator submits a test message via the sandbox view, sending the textual input directly to the pipeline.
2. **Context Resolution & State Override Injection**:
   - *Experience Mode (Standard)*: The pipeline resolves the current active session state from the `SessionManager` and loads the active configuration directly from the local asset files.
   - *Sandbox Mode (Injected)*: Rather than using a distinct execution path, the sandbox payload injects in-memory layout edits, modified prompt configurations, and custom conversation histories directly into this same pipeline function, bypassing persistent disk reads and writes.
3. **Dialogue Node Parsing**: The pipeline evaluates transition constraints for the current active node ID against the user input.
4. **Contextual Retrieval (Hybrid RAG)**:
   - The search query is rewritten to contextualize historical turn history.
   - An asymmetrical search combines lexical matches (Rank-BM25) and semantic matches (FAISS vector indices) to extract candidate knowledge blocks.
   - Point of View (POV) metadata filters are applied to limit access to information outside the character's perspective.
   - Reciprocal Rank Fusion (RRF) merges and ranks the top results.
5. **Prompt Assembly & LLM Generation**: The system builds the generation payload from the character's base prompt, the active node's guidelines, RAG context, and chat history. The payload is sent to the LLM backend (local or cloud API) as a stream.
6. **Streaming Text & TTS Synthesis**: As the LLM stream outputs text chunks, they are broadcast over Socket.IO to the client's typewriter rendering engine. Concurrently, synthesized Text-to-Speech audio packets are streamed back to the client's audio queue for low-latency playback. In Sandbox Mode, debug telemetry (retrieved RAG chunks, logic path selections, state transitions) is bundled and returned alongside this output.

## Data Models & State

### Persistent Serialization Schemas

The system avoids heavy runtime parsing by decoupling visual coordinate placements from execution logic. Visual positions exist solely within `layout.json`, while operational state parameters are kept in `prompts.yaml` and metadata inside `info.json`.

#### 1. `info.json`
Stores system configuration metadata and asset pointers. Global settings such as runtime mode and conversational timeouts are managed at the system level.
```json
{
  "id": "jan_zizka",
  "name": "Jan Žižka",
  "description": "Bohemian military commander and Hussite leader.",
  "tags": ["RAG", "Historical", "15th-Century"],
  "language": "en",
  "color": "#e24c4c",
  "avatar": "/api/characters/item/jan_zizka/avatar",
  "rag": {
    "ragScheme": "hussite_wars",
    "pov": "hussite_commander",
    "chunksize": 4
  }
}
```

#### 2. `prompts.yaml`
Houses prompt templates and transition mappings, utilizing YAML blocks (`|` and `|-`) to preserve the layout structure of long context instructions.
```yaml
base_prompt: |
  You are Jan Žižka, the Hussite military commander. Speak with the gravitas of a 15th-century veteran. 
  Keep your answers short (max 40 words), but vivid and human.
do:
  - Speak with historical authenticity and directness.
  - Deflect inquiries about technologies postdating the 15th century.
don't:
  - Break character or mention modern references.
  - Invent historical outcomes outside documented records.
context:
  setting: "Bohemian campaign, 1420. Inside an armed military camp near Prague."
  personality: "Stern, deeply pious, tactical, and uncompromising."
  background: "The Hussite Wars have begun. Sigismund is marching on Prague."
  role: "Educate visitors about military innovations and the defensive wagon fort tactics."
var_prompt:
  - id: start
    displayName: Start Session
    node_class: flow
    type: start-node
    next: [target: welcome]
  - id: welcome
    displayName: Welcome Guest
    node_class: prompt
    type: advanced
    goal: "Greet the stranger firmly, identify yourself, and ask what business they have in Prague."
    tone: "Cautious but authoritative"
    example: "Who approaches the camp? I am Žižka. State your allegiance."
    follow_up: "Are you with Sigismund or the Chalice?"
    ext_info: "disabled"
    need_answer: true
    next:
      - target: discuss_tactics
        reason: "User wants to discuss wagon forts or battle strategies"
      - target: discuss_heresy
        reason: "User discusses religious faith or Sigismund"
  - id: discuss_tactics
    displayName: Wagon Forts
    node_class: prompt
    type: advanced
    goal: "Explain how you use standard farm carts as armored defense walls to turn peasants into knights."
    tone: "Tactical and proud"
    ext_info: "fetch"
    need_answer: true
    next:
      - target: conclusion
  - id: deflect
    displayName: Deflect Modernity
    node_class: prompt
    type: deflect
    goal: "Express confusion about modern queries and redirect back to the safety of the Bohemian camp."
    tone: "Irritated and suspicious"
    example: "What sorcery is this 'WiFi' you speak of? Speak sense, or leave our camp."
    next: []
```

#### 3. `layout.json`
Saves Rete/Vue Flow visual placement data, coordinates, and visual connector states.
```json
{
  "nodes": [
    {
      "id": "node_start_idx",
      "label": "start",
      "node_class": "flow",
      "type": "start-node",
      "position": { "x": 150, "y": 100 },
      "data": {}
    },
    {
      "id": "node_welcome_idx",
      "label": "welcome",
      "node_class": "prompt",
      "type": "advanced",
      "position": { "x": 150, "y": 300 },
      "data": {}
    }
  ],
  "connections": [
    {
      "id": "conn_01",
      "source": "node_start_idx",
      "sourceOutput": "out",
      "target": "node_welcome_idx",
      "targetInput": "in",
      "data": { "label": "" }
    }
  ]
}
```

---

### RAG Database Schemas

The system combines FAISS indices with standardized metadata structures to restrict context injection during RAG queries.

#### 1. `db_metadata.json` (List of document segments)
```json
[
  {
    "id": "chunk_01",
    "text": "At the Battle of Sudoměř, Jan Žižka deployed wagon forts to decisively defeat royalist cavalry.",
    "pov": ["hussite_commander", "peasant_soldier", "all"],
    "metadata": {
      "locations": ["Sudoměř"],
      "tactics": ["wagon fort"],
      "dates": ["1420"]
    }
  }
]
```

#### 2. `metadata_struct.json` (Extraction guidelines for the hybrid search engine)
```json
{
  "json_schema": {
    "name": "metadata_extraction_schema",
    "schema": {
      "type": "object",
      "properties": {
        "locations": {
          "type": "array",
          "description": "Specific cities, castles, or terrains discussed.",
          "items": { "type": "string" }
        },
        "tactics": {
          "type": "array",
          "description": "Military methods, configurations, or combat strategies.",
          "items": { "type": "string" }
        },
        "dates": {
          "type": "array",
          "description": "Specific years or seasons mentioned in query.",
          "items": { "type": "string" }
        }
      },
      "required": ["locations", "tactics", "dates"]
    }
  }
}
```

---

### Transient Application State Management

#### 1. Pinia Client-Side Draft State
The frontend local state architecture holds character drafts in memory. Standard editing is restricted if minimum criteria are unmet.

```typescript
interface CharacterDraft {
  id: string | null;
  folderName: string | null;
  name: string | null;
  description: string | null;
  tags: string[];
  avatar: string | null;
  color: string;
  language: string;
  base_prompt: string;
  dos: string[];
  donts: string[];
  context: {
    setting: string;
    personality: string;
    background: string;
    role: string;
  };
  rag: {
    ragScheme: string | null;
    pov?: string;
    chunksize?: number;
  };
  var_prompt: Array<{
    id: string;
    displayName: string;
    node_class: string;
    type: string;
    goal?: string;
    tone?: string;
    example?: string;
    follow_up?: string;
    ext_info?: string;
    need_answer?: boolean;
    next: any[];
  }>;
  nodes: Array<{
    id: string;
    label: string;
    node_class: string;
    type: string;
    position: { x: number; y: number };
    data: any;
  }>;
  connections: Array<{
    id: string;
    source: string;
    sourceOutput: string;
    target: string;
    targetInput: string;
    data: any;
  }>;
}

interface SandboxSession {
  activeNodePointer: string;
  conversationHistory: Array<{ role: string; text: string; step?: string }>;
  isRecording: boolean;
  transcriptionLogs: string[];
}
```

#### 2. Ephemeral Server-Side Testing Architecture
To support real-time previewing without committing database changes, the backend exposes a testing route that forwards inputs directly to the unified pipeline function. This route passes the volatile draft configuration, layout configurations (nodes and connections), and state parameters to replicate production execution.

```
+-------------------------------------------------------------------------------+
|                        EPHEMERAL TESTING PAYLOAD                              |
+-------------------------------------------------------------------------------+
|  {                                                                            |
|    "draft_config": {                                                          |
|       "name": "Jan Žižka",                                                    |
|       "base_prompt": "...",                                                   |
|       "dos": ["..."],                                                         |
|       "donts": ["..."],                                                       |
|       "rag": {                                                                |
|          "ragScheme": "hussite_wars",                                         |
|          "pov": "hussite_commander",                                          |
|          "chunksize": 4                                                       |
|       },                                                                      |
|       "var_prompt": [                                                         |
|          { "id": "welcome", "goal": "Greet guest firmly...", "next": [...] }  |
|       ],                                                                      |
|       "nodes": [                                                              |
|          { "id": "node_welcome_idx", "type": "advanced" }                     |
|       ],                                                                      |
|       "connections": [                                                        |
|          { "source": "node_start_idx", "target": "node_welcome_idx" }          |
|       ]                                                                       |
|    },                                                                         |
|    "session_state": {                                                         |
|       "active_node_id": "node_tactics_idx",                                   |
|       "history": [                                                            |
|          { "role": "user", "text": "How do you build these forts?" }          |
|       ]                                                                       |
|    }                                                                          |
|  }                                                                            |
+-------------------------------------------------------------------------------+
                                       |
                                       v
+-------------------------------------------------------------------------------+
|                          UNIFIED PIPELINE ENGINE                              |
|                         (With Parameter Injection)                            |
+-------------------------------------------------------------------------------+
|  1. Intercepts call and applies 'draft_config' overrides (including visual    |
|     layout maps, connections, and variable prompts) over disk assets.         |
|  2. Verifies minimum metadata fields (Name, Description, Do's, Don'ts).       |
|     - Raises 422 Unprocessable Entity if required entries are missing.        |
|  3. Replaces empty optional fields with standard fallbacks:                   |
|     - "chat with the user"                                                    |
|  4. Executes the standard FSM transition and RAG retrieval loops.             |
|  5. Streams back response and execution telemetry without persistent writes.  |
+-------------------------------------------------------------------------------+
```

## Component Breakdown

### Client-Side Vue 3 Components

```
+-----------------------------------------------------------------------------------------+
|                                    APP.VUE (Main Container)                             |
+-----------------------------------------------------------------------------------------+
                                             |
                        +--------------------+--------------------+
                        v                                         v
+------------------------------------------------+ +--------------------------------------+
|             EXP VIEW (Experience Mode)      | |      CREATOR WORKSPACE (Dev View)      |
+------------------------------------------------+ +--------------------------------------+
|  - Swipe-carousel selector                     | |  - Unified single component workspace |
|  - Voice recorder engine                       | |  - Tabbed interface selector:        |
|  - Ambient audio loops (AmbientAudio)          | |    - Tab A: Character Form           |
|  - Automated inactivity reset controller       | |    - Tab B: Prompt Graph Canvas      |
|  - Automatic websocket teardown on completion  | |  - Pinia memory draft store          |
|                                                | |  - Stateful Sandbox live simulation  |
+------------------------------------------------+ +--------------------------------------+
                                                                      |
                                             +------------------------+------------------------+
                                             v                                                 v
                        +----------------------------------------+        +----------------------------------------+
                        |      CHAR FORM VIEW (Tab A Content)    |        |     PROMPT GRAPH VIEW (Tab B Content)  |
                        +----------------------------------------+        +----------------------------------------+
                        | - Standard profile details form        |        | - Vertical layout workspace (Vue Flow) |
                        | - Avatar resizing and validation       |        | - Drag-and-drop FSM state manager      |
                        | - Lock-state feedback indicator        |        | - Connection transitions evaluator     |
                        +----------------------------------------+        +----------------------------------------+
```

#### 1. `EXPView.vue` (Experience Mode Container)
- **Role**: Standardized interface for public deployments. Handles touch/keyboard actions and guides the visitor through visual states without relying on long, unreadable blocks of on-screen text.
- **Key Mechanics**:
  - Initializes the WebSocket pipeline upon card selection.
  - Listens to spacebar press/release events or touchscreen gestures to trigger voice loops.
  - Manages system-level idle countdowns, automatically resetting to the home screen after periods of inactivity.

#### 2. `CreatorWorkspace.vue` (Unified Developer Workspace)
- **Role**: A single container component representing the entire Creator Mode. It relies on a tabbed layout to split the workflow cleanly between the profile settings form and the node workflow graph.
- **Key Mechanics**:
  - Integrates a tabbed navigation interface with two dedicated states: Tab A ("Character Form") and Tab B ("Prompt Graph").
  - Evaluates character profile validation criteria inside Tab A, dynamic locking of the Tab B workflow selector, and sandbox testing capabilities until the minimum fields are met.
  - Shares and binds the core Pinia draft store state across both tabs to ensure instant synchronization.

#### 3. `CharFormView.vue` (Character Profile Form Tab)
- **Role**: Manages standard character metadata inputs (Name, Tags, Description, Do's, Don'ts) under Tab A of the developer workspace.
- **Key Mechanics**:
  - Evaluates real-time input validation to provide visual feedback indicators and report state completeness to the parent workspace.
  - Manages the client-side avatar upload process, executing image downscaling, resolution checks, and aspect ratio validation prior to upload.

#### 4. `PromptGraphView.vue` (Visual Workflow Canvas Tab)
- **Role**: Renders the prompt topology under Tab B of the developer workspace, managing visual nodes, connector flows, and graph positions via Vue Flow.
- **Key Mechanics**:
  - **Connection Limits**: Restricts connection routes to top-to-bottom structures.
  - **Context Menus**: Listen for right-click events to spawn default nodes (`StartNode`, `LoopNode`, `EndNode`, `BasicPromptNode`, `AdvancedPromptNode`).
  - **Selection Panels**: Translates visual node properties directly into active editing forms, binding reactive properties to Pinia drafts.
  - **Live State Packaging**: Syncs modified nodes, connections, and variable prompts inside the active Pinia draft to be compiled and forwarded directly within the sandbox testing payload.

---

### Server-Side Core Services

```
+-----------------------------------------------------------------------------------+
|                                  FASTAPI RUNTIME                                 |
+-----------------------------------------------------------------------------------+
                                          |
                      +-------------------+-------------------+
                      v                                       v
+-------------------------------------------+ +-------------------------------------+
|              SESSION MANAGER              | |            ASSETS ENGINE            |
+-------------------------------------------+ +-------------------------------------+
|  - Resolves connection paths              | |  - Restricts disk writes to safe    |
|  - Injects overrides for sandbox sessions  | |    user save requests               |
|  - Manages automatic idle cleanups        | |  - Sanitizes and formats text       |
|                                           | |    templates with ruamel.yaml       |
+-------------------------------------------+ +-------------------------------------+
                                          |
                                          v
+-----------------------------------------------------------------------------------+
|                            UNIFIED PIPELINE ENGINE                                |
+-----------------------------------------------------------------------------------+
|  - Performs validation checks on character schemas                                |
|  - Manages FSM visual transitions (Start -> Loop -> Cycle -> End)                 |
|  - Rewrites search queries and ranks documents using hybrid RAG (FAISS + BM25)    |
|  - Evaluates conversational relevance to detect and deflect out-of-bounds queries |
|  - Runs identical logic for both persistent characters and testing overrides      |
+-----------------------------------------------------------------------------------+
```

#### 1. `SessionManager` & `ChatSession` (Execution Router)
- **State Traversal Logic**: The state machine operates independently of frontend components by utilizing clean coordinate lists and transition mappings.
- **Transition Evaluator**:
  - Traversal starts at `StartNode`.
  - When reaching a `LoopNode`, the orchestrator tracks active iteration variables in memory. While `current_iteration <= loop_count`, the generator loops back to the beginning of the designated sub-path.
  - When the loop finishes, the session exits to the target node defined in the second edge output.
  - Reaching an `EndNode` sends a termination signal, prompting the server and client to release session resources and reset the connection.
- **Unified Parameter Injection**: To execute sandbox runs, `SessionManager` captures the temporary draft parameters (including nested `rag` specifications, in-memory layout `nodes` and `connections`, and step-by-step `var_prompt` definitions), overrides the persistent values in a transient memory segment, and routes the processing request directly through the main unified execution function.

#### 2. `RAG Service` (Semantic & Lexical Retriever)
- **Lexical Search (Rank-BM25)**: Evaluates term frequencies to verify historical dates, specific places, and unique commander titles.
- **Semantic Search (FAISS)**: Standard search over dense embeddings to capture context matches even when precise terminology is omitted.
- **Reciprocal Rank Fusion (RRF)**:
  - Compiles candidate documents from both FAISS and Rank-BM25 results.
  - Merges rankings using the formula:
    $$RRF\_Score(d \in D) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$
    *(where $k = 60$, and $r_m(d)$ is the document rank in model $m$)*.
  - Filters results against POV access rules defined under the active character configuration's `rag` metadata before sending the final ranked list to the generation model.

#### 3. `Transcription Service` (Whisper STT Loader)
- **Lazy-Load Strategy**: To keep initial server start times fast and prevent wasted GPU resource allocations on pure administration pages, Whisper initialization is deferred until Experience Mode is active on a client.
- **Hot-Mic Architecture**: The client mic stream remains initialized to avoid hardware cold-start delays, allowing instantly recorded fragments to process immediately.

---

### Trace Analysis: Experience Mode Voice Conversation Loop

#### Protocol Mechanics & Frame Formats

The diagram below traces the end-to-end voice loop, showing how raw audio packets are transcribed, matched with relevant history and RAG context, processed by the LLM, and synthesized into streaming audio feedback.

```
Client (Vue 3 / Vue Flow)             Server (SessionManager / Unified Pipeline / STT / TTS)
       |                                                    |
       |--- 1. [Socket.IO] connect ------------------------>|
       |<-- 2. [Socket.IO] status_update (Whisper state) ---|
       |                                                    |
       |============= Visitor initiates dialogue loop =============|
       |                                                    |
       |--- 3. [Socket.IO] audio_message (WebM packet) ---->|
       |                                                    | [Thread Executor]
       |                                                    |  - Transcribes audio via Whisper
       |<-- 4. [Socket.IO] transcription (text logs) -------|
       |                                                    |
       |                                                    | [Unified Pipeline State Lookup]
       |                                                    |  - Resolves active node
       |                                                    |  - Runs relevance check
       |                                                    |  - [True]: Traverses FSM
       |                                                    |  - [False]: Routes to deflect
       |                                                    |
       |                                                    | [Hybrid RAG Retrieval]
       |                                                    |  - Lexical + Semantic Search
       |                                                    |  - Filter by POV (from rag metadata)
       |                                                    |  - Rank with RRF
       |                                                    |
       |                                                    | [LLM Execution Engine]
       |                                                    |  - Assembles contextual prompts
       |                                                    |  - Requests stream chunks
       |                                                    |
       |<-- 5. [Socket.IO] response_chunk (character text) -|
       |    (Streamed progressively to the typewriter UI)   |
       |                                                    |
       |                                                    | [TTS Synthesis Engine]
       |                                                    |  - Generates vocal audio chunks
       |<-- 6. [Socket.IO] audio_chunk (binary PCM/WAV) ----|
       |    (Buffered sequentially into client playback)    |
       |                                                    |
       |<-- 7. [Socket.IO] response_complete (FSM meta) ----|
       |                                                    |
```

#### Traversing State Machine Boundaries
1. **Transition Verification**: When a user submission is received, the orchestrator evaluates the transition list associated with the active node. If the current step expects an explicit choice (`need_answer` is `true`), the user's input is analyzed using classification prompts to resolve the next logical path.
2. **Deflection Interceptor**:
   If the safety parser flags the input as out-of-bounds (`on_topic` is `false`), the FSM overrides normal node pathing and shifts the active state to the character's global `deflect` node.
3. **Execution Delivery**: The chosen state dictates the guidelines used during LLM assembly. RAG behaviors conform to the parameters set by the active node (`ext_info`: `disabled`, `fetch`, or `reuse`), protecting generation quality while ensuring factual consistency.