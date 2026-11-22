"""VEXOR — your personal desktop assistant.

Run:  python vexor.py   (or double-click Start-VEXOR.bat)
"""
import json
import logging
import os
import queue
import threading
import tkinter as tk
from tkinter import filedialog, simpledialog

import commands
import hud
from brain import Brain
from voice import Voice

HERE = os.path.dirname(os.path.abspath(__file__))
logging.basicConfig(filename=os.path.join(HERE, "vexor.log"), level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("vexor")
CONFIG_PATH = os.path.join(HERE, "config.json")
DEFAULT_CONFIG = {
    "assistant_name": "VEXOR",
    "your_name": "",
    "model": "llama3.2",
    "speak_replies": True,
    "voice_rate": 185,
}

# ---- colours (futuristic HUD theme, shared with hud.py) ----
BG, PANEL, ACCENT, TEXT, DIM, USER, ERR = hud.BG, hud.PANEL, hud.CYAN, hud.TEXT, hud.MUTED, hud.VIOLET, hud.ERR


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
        root.geometry("820x660")
        root.minsize(560, 460)
        root.configure(bg=BG)
        hud.fade_in(root)
        self.f_disp = hud.pick_font(root, "Bahnschrift", "Segoe UI Semibold", "DejaVu Sans")
        self.f_body = hud.pick_font(root, "Segoe UI", "Inter", "DejaVu Sans")
        self.f_mono = hud.pick_font(root, "Cascadia Mono", "Consolas", "DejaVu Sans Mono")
        self.f_serif = hud.pick_font(root, "Constantia", "Georgia", "DejaVu Serif")
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
        top.pack(fill="x", padx=18, pady=(14, 8))
        self.core = hud.Core(top, size=46)
        self.core.pack(side="left")
        titles = tk.Frame(top, bg=BG)
        titles.pack(side="left", padx=(10, 0))
        tk.Label(titles, text=" ".join(self.name), fg=TEXT, bg=BG, font=(self.f_serif, 21)).pack(anchor="w")
        self.status = tk.Label(titles, text="STARTING…", fg=DIM, bg=BG, font=(self.f_mono, 9))
        self.status.pack(anchor="w")

        self.speak_var = tk.BooleanVar(value=self.cfg["speak_replies"])
        tk.Checkbutton(top, text="Speak replies", variable=self.speak_var, command=self._toggle_speak,
                       fg=DIM, bg=BG, selectcolor=PANEL, activebackground=BG, highlightthickness=0, bd=0,
                       activeforeground=TEXT, font=(self.f_body, 10)).pack(side="right")

        hud.Trace(self.root, height=2).pack(fill="x", padx=18)

        bar = tk.Frame(self.root, bg=BG)
        bar.pack(fill="x", padx=18, pady=(10, 8))
        for label, cmd in (("Commit message", self._commit_message), ("Git help", lambda: self._submit("git help")),
                           ("Commands", lambda: self._submit("help")), ("New chat", self._new_chat),
                           ("Reconnect", self._check_brain)):
            self._button(bar, label, cmd, small=True).pack(side="left", padx=(0, 6))

        bottom = tk.Frame(self.root, bg=BG)
        bottom.pack(side="bottom", fill="x", padx=18, pady=14)  # packed first so it is never cut off
        frame = tk.Frame(self.root, bg=hud.LINE, padx=1, pady=1)  # 1px border around the chat
        frame.pack(fill="both", expand=True, padx=18)
        self.chat = tk.Text(frame, bg=PANEL, fg=TEXT, wrap="word", relief="flat", bd=0,
                            font=(self.f_body, 11), padx=16, pady=14, state="disabled",
                            insertbackground=TEXT, spacing1=2, spacing3=2, highlightthickness=0)
        self.chat.pack(fill="both", expand=True)
        self.chat.tag_configure("you", foreground=hud.GOLD, font=(self.f_body, 11, "bold"))
        self.chat.tag_configure("bot", foreground=ACCENT, font=(self.f_body, 11, "bold"))
        self.chat.tag_configure("err", foreground=ERR)
        self.chat.tag_configure("dim", foreground=DIM, font=(self.f_mono, 10))
        self.dots = hud.Dots(self.chat)

        self.entry_box = tk.Frame(bottom, bg=hud.LINE, padx=1, pady=1)
        self.entry_box.pack(side="left", fill="x", expand=True)
        self.entry = tk.Entry(self.entry_box, bg=hud.PANEL2, fg=TEXT, relief="flat", bd=0, font=(self.f_body, 12),
                              insertbackground=ACCENT, highlightthickness=0)
        self.entry.pack(fill="x", ipady=10, ipadx=10)
        self.entry.bind("<Return>", lambda e: self._submit())
        self.entry.bind("<FocusIn>", lambda e: self.entry_box.configure(bg=ACCENT))
        self.entry.bind("<FocusOut>", lambda e: self.entry_box.configure(bg=hud.LINE))
        self.entry.focus_set()
        self.mic_btn = self._button(bottom, "🎤  Talk", self._listen)
        self.mic_btn.pack(side="left", padx=(8, 0), fill="y")
        self._button(bottom, "Send  ➤", self._submit, primary=True).pack(side="left", padx=(8, 0), fill="y")
        self.root.bind("<Control-space>", lambda e: self._listen())

    def _button(self, parent, text, cmd, small=False, primary=False):
        return hud.GlowButton(parent, text, cmd, font=(self.f_body, 9 if small else 11, "bold" if primary else "normal"),
                              primary=primary, padx=12 if small else 16, pady=5 if small else 9)

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

    def _set_status(self, text, colour=DIM, state=None):
        self.status.configure(text=text.upper(), fg=colour)
        if state is None:
            low = text.lower()
            state = ("think" if "thinking" in low or "writing" in low else "listen" if "listening" in low
                     else "offline" if ("offline" in low or "not running" in low or "not downloaded" in low) else "idle")
        self.core.set_state(state)

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
        self.dots.start()
        speak = self.speak_var.get()  # read Tk variables on the UI thread only

        def work():
            parts = []
            log.info("question sent to brain (%d chars)", len(text))
            try:
                for piece in self.brain.chat_stream(text):
                    if not parts:
                        log.info("first words received")
                        self._ui(self.dots.stop)
                    parts.append(piece)
                    self._ui(self._write, piece)
                self._ui(self.dots.stop)
                self._ui(self._write, "\n\n")
                if speak:
                    self.voice.speak("".join(parts))
                self._ui(self._set_status, f"● Brain online ({self.brain.model})", ACCENT)
                log.info("answer complete (%d chars)", len("".join(parts)))
            except Exception as e:
                log.exception("brain request failed")
                self._ui(self.dots.stop)
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
        self.mic_btn.configure(text="●  Listening")
        self.mic_btn.set_colors(ERR)
        self._set_status("Listening… speak now", ACCENT)

        def work():
            text, err = self.voice.listen()
            self.busy = False
            self._ui(self.mic_btn.configure, {"text": "🎤  Talk"})
            self._ui(self.mic_btn.set_colors, hud.PANEL2, hud.blend(hud.PANEL2, hud.CYAN, 0.28))
            if text:
                self._ui(self._submit, text)  # sets "Thinking…" itself
            else:
                self._ui(self._check_brain_quiet)
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
