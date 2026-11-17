"""Bounded in-memory conversation context, scoped to authenticated user + token + UUID."""
import hashlib
import json
import time


class ConversationStore:
    def __init__(self):
        self.sessions = {}

    @staticmethod
    def key(user_id, token, conversation_id):
        return (user_id, hashlib.sha256(token.encode()).hexdigest(), conversation_id)

    def history(self, key):
        now = time.monotonic()
        for item, (updated, _messages) in list(self.sessions.items()):
            if now - updated > 1200:
                self.sessions.pop(item, None)
        value = self.sessions.get(key)
        return list(value[1]) if value else []

    def append(self, key, question, answer):
        messages = self.history(key)
        # Only accepted server answers and verified IDs are retained, never tool raw payloads/tokens.
        context = getattr(answer, 'context', {})
        text = answer.text[:2400]
        if context:
            text += '\n历史业务对象（须重新查询状态）：' + json.dumps(context, ensure_ascii=False)[:1800]
        messages += [{'role': 'user', 'content': question}, {'role': 'assistant', 'content': text}]
        if len(self.sessions) >= 200 and key not in self.sessions:
            self.sessions.pop(min(self.sessions, key=lambda item: self.sessions[item][0]))
        self.sessions[key] = (time.monotonic(), messages[-6:])
