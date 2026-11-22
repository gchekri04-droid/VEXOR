"""VEXOR — your personal desktop assistant.

Run:  python vexor.py   (or double-click Start-VEXOR.bat)
"""
import json
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, simpledialog

import commands
from brain import Brain
from voice import Voice

HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(HERE, "config.json")
DEFAULT_CONFIG = {
    "assistant_name": "VEXOR",
    "your_name": "",
    "model": "llama3.2",
    "speak_replies": True,
    "voice_rate": 185,
}

# ---- colours (dark "HUD" theme) ----
BG, PANEL, ACCENT, TEXT, DIM, USER, ERR = (
    "#0b1120", "#111a2e", "#22d3ee", "#e2e8f0", "#64748b", "#a78bfa", "#f87171")


def load_config():
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def system_prompt(cfg):
    who = cfg["your_name"] or "the user"
    return (
        f"You are {cfg['assistant_name']}, a friendly, sharp personal AI assistant running on "
        f"{who}'s Windows PC. Address them as {who}. Keep answers short and clear (2-5 sentences) "
        "unless asked for detail, because replies may be read aloud. "
        f"{who} is new to GitHub and coding: explain git and GitHub simply, step by step, "
        "mentioning the matching GitHub Desktop button when relevant. "
        "If you are not sure of something, say so honestly instead of guessing."
    )


class VexorApp:
    def __init__(self, root):
        self.root = root
        self.cfg = load_config()
        self.name = self.cfg["assistant_name"]
        self.brain = Brain(self.cfg["model"], system_prompt(self.cfg))
        self.voice = Voice(rate=self.cfg["voice_rate"])
        self.ui_q = queue.Queue()
        self.busy = False

        root.title(f"{self.name} — Personal Assistant")
        root.geometry("760x620")
        root.minsize(520, 420)
        root.configure(bg=BG)
        self._build_ui()
        root.after(50, self._drain_ui_queue)

        if not self.cfg["your_name"]:
            root.after(300, self._ask_name)
        else:
            self._greet()
        self._check_brain()

    # ================= UI =================
    def _build_ui(self):
        top = tk.Frame(self.root, bg=BG)
        top.pack(fill="x", padx=16, pady=(14, 6))
        tk.Label(top, text=f"◉ {self.name}", fg=ACCENT, bg=BG,
                 font=("Segoe UI", 20, "bold")).pack(side="left")
        self.status = tk.Label(top, text="Starting…", fg=DIM, bg=BG, font=("Segoe UI", 10))
        self.status.pack(side="left", padx=14)

        self.speak_var = tk.BooleanVar(value=self.cfg["speak_replies"])
        tk.Checkbutton(top, text="Speak replies", variable=self.speak_var, command=self._toggle_speak,
                       fg=TEXT, bg=BG, selectcolor=PANEL, activebackground=BG,
                       activeforeground=TEXT, font=("Segoe UI", 10)).pack(side="right")

        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=16, pady=(0, 6))
        for label, cmd in (("Commit message", self._commit_message), ("Git help", lambda: self._submit("git help")),
                           ("Commands", lambda: self._submit("help")), ("New chat", self._new_chat),
                           ("Reconnect", self._check_brain)):
            self._button(bar, label, cmd, small=True).pack(side="left", padx=(0, 6))

        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=16, pady=12)  # packed first so it is never cut off
        self.chat = tk.Text(self.root, bg=PANEL, fg=TEXT, wrap="word", relief="flat",
                            font=("Segoe UI", 11), padx=14, pady=12, state="disabled",
                            insertbackground=TEXT)
        self.chat.pack(fill="both", expand=True, padx=16)
        self.chat.tag_configure("you", foreground=USER, font=("Segoe UI", 11, "bold"))
        self.chat.tag_configure("bot", foreground=ACCENT, font=("Segoe UI", 11, "bold"))
        self.chat.tag_configure("err", foreground=ERR)
        self.chat.tag_configure("dim", foreground=DIM)

        self.entry = tk.Entry(bottom, bg=PANEL, fg=TEXT, relief="flat", font=("Segoe UI", 12),
                              insertbackground=TEXT)
        self.entry.pack(side="left", fill="x", expand=True, ipady=8)
        self.entry.bind("<Return>", lambda e: self._submit())
        self.entry.focus_set()
        self.mic_btn = self._button(bottom, "🎤 Talk", self._listen)
        self.mic_btn.pack(side="left", padx=(8, 0))
        self._button(bottom, "Send ➤", self._submit).pack(side="left", padx=(8, 0))
        self.root.bind("<Control-space>", lambda e: self._listen())

    def _button(self, parent, text, cmd, small=False):
        return tk.Button(parent, text=text, command=cmd, bg="#1e293b", fg=TEXT, relief="flat",
                         activebackground=ACCENT, activeforeground=BG, cursor="hand2",
                         font=("Segoe UI", 9 if small else 11), padx=10, pady=3 if small else 6)

    # thread-safe UI updates: worker threads put callables on ui_q
    def _ui(self, fn, *args):
        self.ui_q.put((fn, args))

    def _drain_ui_queue(self):
        try:
            while True:
                fn, args = self.ui_q.get_nowait()
                fn(*args)
        except queue.Empty:
            pass
        self.root.after(50, self._drain_ui_queue)

    def _write(self, text, tag=None):
        self.chat.configure(state="normal")
        self.chat.insert("end", text, tag)
        self.chat.see("end")
        self.chat.configure(state="disabled")

    def _say(self, text, tag=None, speak=True):
        self._write(f"{self.name}: ", "bot")
        self._write(text + "\n\n", tag)
        if speak and self.speak_var.get():
            self.voice.speak(text)

    def _set_status(self, text, colour=DIM):
        self.status.configure(text=text, fg=colour)

    # ================= behaviour =================
    def _ask_name(self):
        name = simpledialog.askstring(self.name, f"Hi! I'm {self.name}. What should I call you?",
                                      parent=self.root)
        self.cfg["your_name"] = (name or "").strip()
        save_config(self.cfg)
        self.brain.system_prompt = system_prompt(self.cfg)
        self._greet()

    def _greet(self):
        who = self.cfg["your_name"]
        self._say(f"Hello{', ' + who if who else ''}. {self.name} online. "
                  "Type or press Talk (Ctrl+Space). Say 'help' to see what I can do.")

    def _toggle_speak(self):
        self.cfg["speak_replies"] = self.speak_var.get()
        save_config(self.cfg)

    def _new_chat(self):
        self.brain.reset()
        self.chat.configure(state="normal")
        self.chat.delete("1.0", "end")
        self.chat.configure(state="disabled")
        self._say("Fresh start. What's next?", speak=False)

    def _check_brain_quiet(self):
        def work():
            ok, msg = self.brain.status()
            self._ui(self._set_status, ("● " if ok else "○ ") + msg, ACCENT if ok else ERR)
        threading.Thread(target=work, daemon=True).start()

    def _check_brain(self):
        def work():
            ok, msg = self.brain.status()
            self._ui(self._set_status, ("● " if ok else "○ ") + msg, ACCENT if ok else ERR)
            if not ok:
                self._ui(self._say, "My AI brain is offline, but commands still work. " + msg, "err", False)
        threading.Thread(target=work, daemon=True).start()

    def _submit(self, text=None):
        text = (text if text is not None else self.entry.get()).strip()
        if not text or self.busy:
            return
        self.entry.delete(0, "end")
        self._write("You: ", "you")
        self._write(text + "\n\n")

        if text.lower().strip(" .!") in ("clear", "new chat", "reset"):
            self._new_chat()
            return
        if "commit message" in text.lower():
            self._commit_message()
            return
        reply = commands.handle(text, self.name)
        if reply is not None:
            self._say(reply)
            return
        self._ask_brain(text)

    def _ask_brain(self, text):
        self.busy = True
        self._set_status("Thinking… (the first answer can take a minute)", ACCENT)
        self._write(f"{self.name}: ", "bot")
        speak = self.speak_var.get()  # read Tk variables on the UI thread only

        def work():
            parts = []
            try:
                for piece in self.brain.chat_stream(text):
                    parts.append(piece)
                    self._ui(self._write, piece)
                self._ui(self._write, "\n\n")
                if speak:
                    self.voice.speak("".join(parts))
                self._ui(self._set_status, f"● Brain online ({self.brain.model})", ACCENT)
            except Exception as e:
                self.brain.history = self.brain.history[:-1]  # drop the unanswered question
                self._ui(self._write, f"I couldn't reach my AI brain ({e}).\n"
                                      "Make sure the Ollama app is running, then click Reconnect.\n\n", "err")
                self._ui(self._set_status, "○ Brain offline", ERR)
            finally:
                self.busy = False
        threading.Thread(target=work, daemon=True).start()

    def _listen(self):
        if self.busy:
            return
        if not self.voice.can_listen:
            self._say("Voice input isn't available: " + self.voice.listen_error, "err", False)
            return
        self.busy = True
        self.mic_btn.configure(text="● Listening", bg=ERR)
        self._set_status("Listening… speak now", ACCENT)

        def work():
            text, err = self.voice.listen()
            self.busy = False
            self._ui(self.mic_btn.configure, {"text": "🎤 Talk", "bg": "#1e293b"})
            self._ui(self._check_brain_quiet)
            if text:
                self._ui(self._submit, text)
            else:
                self._ui(self._say, err, "err", False)
        threading.Thread(target=work, daemon=True).start()

    def _commit_message(self):
        if self.busy:
            return
        start = os.path.join(os.path.expanduser("~"), "Documents", "GitHub")
        repo = filedialog.askdirectory(title="Pick the repository folder",
                                       initialdir=start if os.path.isdir(start) else None)
        if not repo:
            return
        ok, diff = commands.repo_diff(repo)
        if not ok:
            self._say(diff, "err")
            return
        self.busy = True
        self._set_status("Writing commit message…", ACCENT)

        def work():
            try:
                msg = self.brain.ask_once(
                    "Write a git commit message for these changes. Line 1: a summary under 60 "
                    "characters in imperative mood (e.g. 'Add login page'). Then a blank line and "
                    "up to 3 short bullet points. Output ONLY the message.\n\n" + diff)
                self._ui(self._say, "Here's a commit message — paste it into GitHub Desktop's "
                                    "Summary/Description boxes:", None, False)
                self._ui(self._write, msg + "\n\n", "dim")
                self._ui(self._copy, msg)
                self._ui(self._set_status, "Commit message copied to clipboard ✓", ACCENT)
            except Exception as e:
                self._ui(self._say, f"I couldn't reach my AI brain ({e}). Is Ollama running?", "err", False)
            finally:
                self.busy = False
        threading.Thread(target=work, daemon=True).start()

    def _copy(self, text):
        self.root.clipboard_clear()
        self.root.clipboard_append(text)


def main():
    root = tk.Tk()
    VexorApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
