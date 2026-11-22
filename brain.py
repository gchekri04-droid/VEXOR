"""VEXOR's brain: talks to a free local AI model through Ollama (https://ollama.com).

Ollama runs on your own PC, so there is no API key and no cost per message.
"""
import json
import urllib.error
import urllib.request

OLLAMA_URL = "http://localhost:11434"
MAX_HISTORY = 20  # messages kept in memory so replies stay fast


class Brain:
    def __init__(self, model, system_prompt, url=OLLAMA_URL):
        self.model = model
        self.url = url.rstrip("/")
        self.system_prompt = system_prompt
        self.history = []

    # ---------- status ----------
    def installed_models(self):
        """Return the list of model names Ollama has downloaded, or None if Ollama is not running."""
        try:
            with urllib.request.urlopen(self.url + "/api/tags", timeout=3) as r:
                data = json.load(r)
            return [m.get("name", "") for m in data.get("models", [])]
        except (urllib.error.URLError, OSError, ValueError):
            return None

    def status(self):
        """Returns (ok, message) describing whether the brain is ready."""
        models = self.installed_models()
        if models is None:
            return False, "Ollama is not running. Start the Ollama app, then click 'Reconnect'."
        base = self.model.split(":")[0]
        if not any(m == self.model or m.split(":")[0] == base for m in models):
            return False, f"Model '{self.model}' not downloaded. Run:  ollama pull {self.model}"
        return True, f"Brain online ({self.model})"

    # ---------- chat ----------
    def reset(self):
        self.history = []

    def chat_stream(self, user_text):
        """Yield the reply piece by piece as the model writes it."""
        self.history.append({"role": "user", "content": user_text})
        self.history = self.history[-MAX_HISTORY:]
        messages = [{"role": "system", "content": self.system_prompt}] + self.history
        reply = []
        for piece in self._stream(messages):
            reply.append(piece)
            yield piece
        self.history.append({"role": "assistant", "content": "".join(reply)})

    def ask_once(self, prompt):
        """One-off question that is not stored in the conversation history."""
        messages = [{"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}]
        return "".join(self._stream(messages)).strip()

    def _stream(self, messages):
        body = json.dumps({"model": self.model, "messages": messages, "stream": True}).encode()
        req = urllib.request.Request(self.url + "/api/chat", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=300) as r:
            for line in r:
                line = line.strip()
                if not line:
                    continue
                chunk = json.loads(line)
                if "error" in chunk:
                    raise RuntimeError(chunk["error"])
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    yield piece
                if chunk.get("done"):
                    break
