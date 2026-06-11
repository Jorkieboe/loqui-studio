import time

class ChatSession:
    def __init__(self, character_id=None, history=None, current_node_id=None, next_node_id=None, possible_next_nodes=None):
        self.character_id = character_id
        self.history = history if history is not None else []
        self.current_node_id = current_node_id
        self.next_node_id = next_node_id
        self.possible_next_nodes = possible_next_nodes if possible_next_nodes is not None else []

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