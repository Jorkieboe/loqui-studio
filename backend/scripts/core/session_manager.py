import time

class ChatSession:
    def __init__(
        self,
        character_id=None,
        history=None,
        current_node_id=None,
        next_node_id=None,
        possible_next_nodes=None,
        active_flow_id="main",
        open_topics=None,
        last_retrieved_chunks=None
    ):
        self.character_id = character_id
        self.history = history if history is not None else []
        self.current_node_id = current_node_id
        self.next_node_id = next_node_id
        self.possible_next_nodes = possible_next_nodes if possible_next_nodes is not None else []
        self.loop_counters = {}
        self.active_loop_id = None
        self.active_flow_id = active_flow_id if active_flow_id is not None else "main"
        self.open_topics = open_topics if open_topics is not None else []
        self.last_retrieved_chunks = last_retrieved_chunks if last_retrieved_chunks is not None else []

class Session:
    def __init__(self, session_id):
        self.id = session_id
        self.time_created = time.time()
        self.chatsession = ChatSession()

class SessionManager:
    def __init__(self):
        self.sessions = {}

    def create_session(self, session_id) -> Session:
        session = Session(session_id)
        self.sessions[session_id] = session
        return session

    def get_session(self, session_id) -> Session | None:
        return self.sessions.get(session_id)

    def remove_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]