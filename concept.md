## Problem & Audience

Historical education and cultural interactive exhibits often struggle to bridge the gap between static factual records and engaging, memorable experiences. Textbooks, museum plaques, and standard audio guides provide valuable data but lack the conversational engagement required to foster deep empathy and active curiosity. 

While conversational AI provides a potential solution, current implementations frequently miss the human level:
- **The "Encyclopedia Bot" Trap:** Most historical chatbots are designed as dry, trivia-driven Q&A engines. They can recite birth dates and battle locations but fail to convey a true persona. They lack the vulnerability, internal struggles, personal regrets, and driving desires that make a conversation feel human.
- **Factual Hallucinations:** Standard models regularly invent historical events, dates, and associations, undermining the educational value of the interaction.
- **Persona Drift:** AI agents easily drop their historical persona when prompted with modern references, anachronisms, or safety-testing inputs.
- **Lack of Narrative Control:** Open-ended chat can quickly devolve into aimless small talk, failing to guide users toward key historical milestones, educational lessons, or thematic arcs.

### Why Now: The Generative Shift
Historically, creating interactive characters required developers to manually script every single dialogue path and pre-write specific responses for expected user inputs. These rule-based systems were highly brittle, breaking down whenever a user deviated from a narrow, pre-determined script. 

With the development of advanced Large Language Models (LLMs), we can leverage instructions-based systems capable of generating natural, coherent, and contextually appropriate dialogue on the fly, eliminating the need to pre-script every response. 

To maintain narrative structure, this generative capability is bound to a visual node-based framework. The LLM does not make pathing decisions on its own. Instead, the application's programmatic architecture manages transitions between dialogue states. In the event of a split or branching path on the visual canvas, the system's code evaluates the state and directs the LLM along the chosen path, while the LLM generates the final output within the boundaries of the active node.

### Target Audience

The platform serves three primary segments:
1. **Museums and Cultural Heritage Sites:** Institutions looking to deploy immersive digital exhibits (e.g., "Museum View") where visitors can converse directly with historical figures through localized physical kiosks or mobile web interfaces.
2. **Educators and Students:** History classrooms seeking an interactive learning aid. Students can interview figures from their curriculum, testing their knowledge against historical viewpoints, while educators can track engagement metrics.
3. **AI Creators and Historians:** Developers and subject-matter experts who require a robust, code-free visual drafting environment ("Dev View") to build, configure, and fine-tune complex historical personas and structured dialogue flows.

## Core Principles

To deliver a high-quality educational experience, the platform adheres to five guiding design philosophies:

- **Subjective Humanity Over Sterile Factuality:** 
Characters must express a distinct human perspective, defined by their historical desires, biases, and regrets. Rather than acting as a neutral search engine, the AI should filter facts through their own emotional lens, expressing personal feelings about their legacy and decisions.

- **Instruction-Driven Autonomy Over Static Scripting:** 
The platform rejects rigid, pre-written dialogue trees. Instead, it relies on the processing capacity of modern LLMs to dynamically formulate natural responses. Creators define *how* a character should behave and *what* their active objectives are, leaving the generation of natural prose to the underlying model while structural routing is governed programmatically by the node flow.

- **Historical Authenticity Over Generative Freedom:** 
Characters must operate within defined factual guardrails. When faced with topics outside their historical purview, they should deflect realistically or express ignorance consistent with their time period, rather than hallucinating modern facts or breaking character.

- **Scaffolded Conversational Workspaces:** 
The platform functions as a flexible workspace to design conversational guidelines rather than strict paths. Conversations use node-based templates and variable prompts that establish thematic scaffolding. When splits or decision points occur, the codebase evaluates transition criteria to guide the LLM's context, ensuring structural integrity is maintained.

- **Inclusive Multimodal Accessibility:** 
To accommodate public settings like museums and classrooms, the platform values voice-first interactions. Low-latency speech-to-text (STT) and text-to-speech (TTS) systems are prioritized to make the experience feel natural, immediate, and accessible to users of varying reading levels.

- **Platform and Provider Independence:** 
The architecture avoids vendor lock-in. It maintains a consistent abstraction layer capable of switching between local, self-hosted models (for offline data privacy and cost-effective kiosk deployments) and advanced cloud APIs.

## Key Features

The platform splits its features between an accessible voice-first interface and a flexible, developer-friendly creation suite:

### 1. Voice-Only Experience Mode (Museum View)
- **Character Overview Interface:** An accessible dashboard displaying available historical figures, allowing users to select a character and start speaking immediately. This replaces the rigid carousel with a clean, flexible overview layout.
- **Always-Accessible Voice Interface:** A dedicated voice-only pipeline that uses standard speech interaction (e.g., push-to-talk or continuous listening) to enable immediate, hands-free conversation.
- **Ambient Audio Integration:** Subtle environmental soundscapes and real-time audio state indicators (idle, listening, processing, speaking) to guide visitors without relying heavily on screen text.

### 2. Flexible Visual Dialogue Workspace
- **Top-to-Bottom Flow Layout:** A visual layout canvas where dialogue rules and transitions are connected via lines flowing vertically from top to bottom.
- **Vue Flow Graph Architecture:** The underlying workspace is built on Vue Flow, leveraging Vue 3's reactive system and utilizing a structured canvas state format.
- **Right-Click Context Menu:** Right-clicking anywhere on the canvas opens an interactive context window to quickly search, select, and spawn dialogue, transition rules, and flow nodes.
- **Selection Properties Panel:** Clicking any node on the canvas opens a dedicated properties (props) panel on the side, allowing creators to inspect and configure specific instructions, guidelines, transitions, and variables for that node.

### 3. Comprehensive Character Creator Space (Dev Mode)
- **Standard Chat Application Base:** The primary view of Dev Mode functions as a clean, direct chat application interface, enabling developers to interact with activated historical characters under standard conditions.
- **Dedicated Character Creator Tab:** A separate workspace tab focused entirely on building, structuring, and fine-tuning historical personas.
- **In-Memory Draft State:** Edits to persona properties, constraints, or graph models are stored strictly in volatile memory. Changes do not write to persistent disk storage until the creator clicks the explicit "Save" button.
- **Side-by-Side Live Sandbox Panel:** Within the creation tab, a small, persistent chat interface is displayed directly alongside the editing workspace (form fields and Vue Flow canvas). This side-by-side panel allows creators to:
  - Submit test messages to evaluate changes to prompt structures, variables, or dialogue rules instantly using the transient, unsaved draft state.
  - Retain the editing context without needing to exit the workspace.
- **Structured Persona Workspace:** Form panels dedicated to basic character properties:
  - **Identity details:** Name, description, and profile picture.
  - **Behavioral parameters:** Do's and don'ts.
  - **Contextual parameters:** Setting, personality, core goal, and background info.
- **Dual-Mode Sandbox Toggles:** The side-by-side testing interface supports toggling between standard Text Mode and microphone-driven Voice Mode, outputting the generated audio transcription and logs directly into the sandbox view.

### 4. Precision Retrieval-Augmented Generation (Hybrid RAG)
- **FAISS Semantic Search:** Conducts vector lookups against document corpuses using embeddings, recognizing the semantic meaning behind user queries.
- **Rank-BM25 Scoring:** Supplements semantic search with traditional keyword-based matching to secure accurate lookups of highly specific historical names, dates, and locations.
- **Point of View (POV) Filtering:** Restricts retrieved document chunks based on the specific social standing or historical knowledge limits of the selected character.
- **Reciprocal Rank Fusion (RRF):** Fuses semantic and keyword matches, ordering results to ensure highly relevant context reaches the generation model.

## User Actions & Flows

The platform supports two distinct user roles: **Creators** (operating in Dev Mode) and **Visitors** (operating in Experience Mode).

---

### Creator Flow: Character Persona Lifecycle

```
[Base Chat Interface] ──> [Navigate to Creator Tab] ──> [In-Memory Draft Editing & Testing] ──> [Save & Deploy]
```

#### 1. Navigating the Dev Mode Layout
- **Action:** The Creator enters Dev Mode (`/dev`), landing on a standard chat application interface displaying active characters. To construct or modify a character, they select the separate "Create Character" tab.
- **Effect:** The client updates the view to the Creator workspace while keeping the base chat route accessible via tab selection.

#### 2. Side-by-Side Character Persona Definition
- **Action:** The Creator starts filling out base metadata fields (Name, Background, Personality) or mapping nodes on the Vue Flow canvas, configuring transitions and branching logic parameters between them.
- **Effect:** The client application updates its local state, preserving these configurations in volatile memory as an active draft without writing any modifications to disk. It continuously tracks whether the minimum required fields (Name, Description, Do's, and Don'ts) have been provided.

#### 3. Real-Time Sandbox Validation of Drafts
- **Action:** The Creator attempts to interact with the side-by-side sandbox.
  - **Before minimum criteria are met:** The sandbox text and voice inputs remain locked, displaying a warning message that requires a Name, Description, Do's, and Don'ts before testing can begin.
  - **Once minimum criteria are met:** The sandbox unlocks. The Creator can enter text or hold the spacebar to transmit a voice query into the side-by-side sandbox panel. Optional fields left blank (such as Setting, Personality, Core Goal, or Background Info) are temporarily substituted with a basic fallback variable prompt stating "chat with the user."
- **Effect:** The sandbox transmits the draft payload to the backend session manager. The backend processes the query using this transient draft configuration, displaying the test response directly next to the editor panel without overwriting any physical assets on disk.

#### 4. Explicit Save and Deployment
- **Action:** Once satisfied with the side-by-side validation results, the Creator clicks the "Save" button to write the modifications to disk, and marks the character as active.
- **Effect:** The client commits the in-memory layout, node, and parameter structures to the backend. The backend updates the persistent JSON and YAML configuration files on disk. The character becomes actively selectable in both the standard Dev Mode chat app base and the public Experience Mode overview screen.

---

### Visitor Flow: Voice-Only Historical Conversation

```
[Overview Character Select] ──> [Activate Conversation] ──> [Dialogue Loop] ──> [Automatic Session End]
```

#### 1. Character Selection
- **Action:** A Visitor approaches the kiosk or opens the mobile page, reviews the available figures on the overview screen, and selects a historical character to speak with.
- **Effect:** The frontend initializes a Socket.IO connection and loads the matching voice profiles, background parameters, and RAG configurations.

#### 2. Dialogue Loop
- **Action:** The Visitor holds the spacebar (or touches the screen) and speaks. They release the input to transmit.
- **Effect:**
  1. The audio is captured, streamed, and translated into text via the Whisper engine.
  2. The system checks the visual layout node logic. If a branching condition is met or a split occurs, the program evaluates the state transitions via application code, guiding the LLM onto the designated node. It retrieves historical background using hybrid RAG and processes the response through the LLM.
  3. The response is converted to speech via the TTS engine, streaming real-time audio playback back to the user to maintain a fluid, voice-only conversation.

#### 3. Automatic Session End
- **Action:** The active session terminates automatically under either of the following conditions:
  - **End Node Reached:** The dialogue logic encounters a terminal "End Node" designed in the character's Vue Flow graph.
  - **Inactivity Timeout:** No voice input or user interaction occurs for a configurable duration of time $X$ (as defined in the system settings).
- **Effect:** The frontend terminates the active Socket.IO connection, closes the speech capture pipeline, and redirects the screen back to the character selection overview for the next visitor.

## Data & Tech Constraints

The system architecture matches the updated layout requirements:

```
                  ┌──────────────────────────────────────────────┐
                  │                 VUE 3 CLIENT                 │
                  │  ┌───────────┐  ┌───────────┐  ┌──────────┐  │
                  │  │  Pinia    │  │ Vue Flow  │  │ Character│  │
                  │  │  Store    │  │Canvas/Prop│  │ Selector │  │
                  │  └─────┬─────┘  └─────┬─────┘  └────┬─────┘  │
                  └────────┼──────────────┼─────────────┼────────┘
                           │              │             │
                           │       Socket.IO (WS)       │
                           ▼              ▼             ▼
  ┌──────────────────────────────────────────────────────────────────────┐
  │                           FASTAPI BACKEND                            │
  │                                                                      │
  │   ┌────────────────────┐   ┌──────────────────┐   ┌──────────────┐   │
  │   │   SessionManager   │   │  Inference API   │   │  Assets API  │   │
  │   └─────────┬──────────┘   └────────┬─────────┘   └──────┬───────┘   │
  │             │                       │                    │           │
  │             ▼                       ▼                    ▼           │
  │   ┌────────────────────┐   ┌──────────────────┐   ┌──────────────┐   │
  │   │    ChatSession     │   │  Orchestrator    │   │  RAG Service │   │
  │   │ (Base/Var Prompts) │   │ (LLM Presets/APIs)│  │ (FAISS/BM25) │   │
  │   └─────────┬──────────┘   └──────────────────┘   └──────────────┘   │
  └─────────────┼────────────────────────────────────────────────────────┘
```

### 1. Data Schemas and Formatting
To support manual and visual editing, configuration schemas map directly to JSON and YAML assets:
- **`info.json`**: Tracks system metadata, including ID, target language, visual styling colors, configurable inactivity timeout bounds (`idle_timeout_seconds`), file paths (such as the base profile picture), and index pointers.
- **`prompts.yaml`**: Houses the structured persona and dialogue instructions.
  - **`base_prompt`**: Captures character metadata including required keys (`name`, `description`, `dos`, `donts`) and optional keys (`setting`, `personality`, `goal`, `background_info`).
  - **`nodes`**: Defines node properties, parameters, and variable prompt templates. This schema explicitly supports designated types including `StartNode` for session initiation, `LoopNode` for managing cyclical routing states, and `EndNode` to flag conversational completion.
- **`layout.json`**: Captures visual representation coordinates. Contains node placements, vertical connection links (top-to-bottom flow state, transition rules, and conditional branching targets used by the code to route the session), and workspace configuration values compatible with Vue Flow. It is kept decoupled from backend execution logic to maintain data portability.

### 2. Client-Side Constraints
- **Tabbed Route Management:** The Vue 3 client manages separate routing and UI states for the standard base Chat Application and the dedicated Character Creator Workspace.
- **Side-by-Side Split Panes:** Within the Creator Tab, the client renders a side-by-side flex layout. The left pane presents the editing elements (the Vue Flow canvas and parameter forms), while the right pane renders a small, self-contained chat interface.
- **In-Memory Draft Validation State:** The client state manager (Pinia) retains a complete in-memory draft of the edited character. When a creator opens an existing character, the client initiates a read request through the Assets API, pulls the active configuration files (`info.json`, `prompts.yaml`, and `layout.json`), and populates the Pinia draft store to establish the starting baseline. The client restricts interaction with the adjacent sandbox until the minimum metadata fields (Name, Description, Do's, and Don'ts) are populated. If optional context fields are omitted, the state manager generates a default fallback instruction string ("chat with the user") to bypass validation blocks.
- **Stateful Sandbox Simulation:** The side-by-side testing playground maintains local session state to mimic backend execution. The Pinia store tracks the active node pointer within the Vue Flow canvas and retains a chronological log of conversation history. This stateful tracking is updated reactively as messages are sent and received, ensuring context is preserved across testing iterations.
- **Visual Canvas Interface:** The visual editor, implemented via Vue Flow in Vue 3, must process standard pointer interactions: right-click events to trigger context menus at the mouse cursor position to spawn nodes (including Start, Loop, and End nodes), and node-selection events to update the state of the properties panel. Connections are restricted to a top-to-bottom layout flow, with edges representing conditional transition criteria evaluated by the execution codebase.
- **Overview Navigation:** The client provides a character overview grid or list, optimized for direct voice-session launch in Experience Mode.
- **Automatic Client Reset:** The client manages a local countdown timer initialized with the `idle_timeout_seconds` value. Any voice transmission or screen event resets the timer. If the threshold is exceeded or if an "end-node" terminal signal is received from the server, the client must trigger a cleanup sequence, disconnect from Socket.IO, and redirect to the overview grid.

### 3. Server-Side Constraints
- **In-Memory Schema Validation:** The validation endpoints on the backend enforce the presence of required fields (Name, Description, Do's, and Don'ts) in the workspace payload before initiating a testing session. If the required fields are missing, the server responds with a descriptive client-side error code (422 Unprocessable Entity) and refuses execution.
- **Ephemeral Draft Execution:** The backend supports the execution of ephemeral testing sessions. Instead of loading configuration files from disk, the playground endpoint accepts raw, transient layout and prompt schemas, alongside active context variables (the list of conversation history and the current active node ID) in the request payload. It executes the LLM orchestrator and hybrid RAG against this transient data, processing the logic relative to the client's current conversational state and active node before returning the output. Omitted optional values are assigned a placeholder instruction ("chat with the user") by the backend parser to maintain runtime operations.
- **Node Logic and Lifecycle Evaluation:** The backend orchestrator monitors graph traversal over layout connections. It tracks session initiation from a designated `StartNode`, manages iterative routing states defined by a `LoopNode`, and programmatically steers the LLM's active prompt context at split branches by evaluating conditional rules defined in the node configuration. It triggers a graceful session shutdown upon executing a terminal `EndNode` type (emitting a final packet payload containing the closing response along with an explicit termination directive before releasing session resources).
- **Transactional Save Handling:** The server-side Assets API must only perform write operations on configuration files (`info.json`, `prompts.yaml`, `layout.json`) when receiving an explicit client-initiated commit request, ensuring file integrity is maintained and unsaved drafts are not persisted to storage prematurely.
- **Library Agnosticism:** Graph execution on the backend relies on clean coordinate and connection lists (`layout.json`) rather than frontend-specific Vue Flow models, ensuring the backend logic remains independent of client presentation libraries.
- **Unified Testing Route:** The server-side session manager treats text and voice inputs through unified endpoints, applying transcription to voice streams before routing them to the dialogue pipeline.
- **Memory Optimization:** Lazy-load large models (e.g., local Whisper and TTS pipelines) to ensure efficient server startup and minimize background memory footprints when not actively handling sessions.