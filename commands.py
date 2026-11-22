"""Built-in commands VEXOR can do on your PC instantly, without the AI brain.

handle(text) returns a reply string if the text was a command, otherwise None
(then the question goes to the AI brain instead).
"""
import datetime
import os
import re
import shutil
import subprocess
import sys
import urllib.parse
import webbrowser

IS_WINDOWS = sys.platform.startswith("win")
HOME = os.path.expanduser("~")

# name you say -> what to launch on Windows
APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "calc": "calc.exe",
    "paint": "mspaint.exe",
    "file explorer": "explorer.exe",
    "explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "command prompt": "cmd.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "settings": "ms-settings:",
    "vs code": "code",
    "vscode": "code",
    "visual studio code": "code",
    "chrome": "chrome",
    "edge": "msedge",
    "github desktop": os.path.join(os.environ.get("LOCALAPPDATA", ""), "GitHubDesktop", "GitHubDesktop.exe"),
    "ollama": "ollama app",
}

SITES = {
    "github": "https://github.com",
    "youtube": "https://www.youtube.com",
    "google": "https://www.google.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chatgpt.com",
    "claude": "https://claude.ai",
    "stack overflow": "https://stackoverflow.com",
    "stackoverflow": "https://stackoverflow.com",
    "wikipedia": "https://www.wikipedia.org",
    "roadmap": "https://roadmap.sh",
    "first contributions": "https://github.com/firstcontributions/first-contributions",
    "projects": "https://github.com/practical-tutorials/project-based-learning",
    "build your own x": "https://github.com/codecrafters-io/build-your-own-x",
    "free books": "https://github.com/EbookFoundation/free-programming-books",
    "web dev course": "https://github.com/microsoft/Web-Dev-For-Beginners",
    "ai course": "https://github.com/microsoft/generative-ai-for-beginners",
    "public apis": "https://github.com/public-apis/public-apis",
}

LEARN = """Your learning path (say "open <name>"):
1. first contributions — make your first real GitHub contribution (start here!)
2. roadmap — pick a path: web, AI, backend...
3. web dev course / ai course — free Microsoft courses
4. projects — learn by building real projects
5. build your own x — build your own git, chatbot, game...
6. free books — free programming books
7. public apis — free APIs for your own apps
Want a step-by-step guide? Ask me: "guide me through first contributions"."""

FOLDERS = {
    "downloads": os.path.join(HOME, "Downloads"),
    "documents": os.path.join(HOME, "Documents"),
    "desktop": os.path.join(HOME, "Desktop"),
    "pictures": os.path.join(HOME, "Pictures"),
    "music": os.path.join(HOME, "Music"),
    "videos": os.path.join(HOME, "Videos"),
    "github": os.path.join(HOME, "Documents", "GitHub"),
    "repos": os.path.join(HOME, "Documents", "GitHub"),
}

GIT_TIPS = """Git basics (GitHub Desktop button in brackets):
• Clone = download a repo to your PC  [File → Clone repository]
• Commit = save a snapshot of your changes  [type a summary → Commit to <branch>]
• Push = upload your commits to GitHub  [Push origin]
• Pull / Fetch = get the latest from GitHub  [Fetch origin → Pull origin]
• Branch = a safe copy to try changes  [Branch → New branch]
• Pull request = ask to merge your branch  [Branch → Create pull request]
Tip: say "commit message" and I'll write one from your changes."""

HELP = """Things I can do instantly:
• "open notepad / calculator / vs code / github desktop / chrome"
• "open github / youtube / gmail" (websites) or "go to example.com"
• "open downloads / documents / desktop folder"
• "search for <anything>"  •  "youtube <anything>"
• "what time is it" / "what's the date"
• "git help"  •  "commit message" (writes one from your repo changes)
• "learn" (best GitHub repos & learning path)
• "lock my pc"  •  "clear" (new conversation)
Anything else, just ask — my AI brain will answer."""


def _launch(target):
    if not IS_WINDOWS:
        return False
    try:
        if target.endswith(".exe") and os.path.isabs(target):
            if not os.path.exists(target):
                return False
            subprocess.Popen([target])
        else:
            # 'start' lets Windows find apps, URIs like ms-settings:, and App Paths
            subprocess.Popen(f'start "" "{target}"', shell=True)
        return True
    except OSError:
        return False


def _open_path(path):
    if not os.path.isdir(path):
        return False
    if IS_WINDOWS:
        os.startfile(path)  # noqa: available on Windows only
    else:
        webbrowser.open("file://" + path)
    return True


def handle(text, assistant_name="VEXOR"):
    t = text.lower().strip().rstrip("?.!")
    t = re.sub(rf"^(hey |ok |okay )?{assistant_name.lower()}[,\s]*", "", t).strip()
    if not t:
        return "Yes? I'm listening."

    if t in ("help", "what can you do", "commands"):
        return HELP

    if re.search(r"\b(time is it|the time|current time)\b", t):
        return "It's " + datetime.datetime.now().strftime("%I:%M %p").lstrip("0") + "."
    if re.search(r"\b(the date|today's date|what day)\b", t):
        return "Today is " + datetime.datetime.now().strftime("%A, %d %B %Y") + "."

    if t in ("learn", "learning", "what should i learn", "learning path", "best repos", "best github"):
        return LEARN

    if t in ("git help", "github help", "git basics", "how does git work", "how does github work"):
        return GIT_TIPS

    if re.search(r"\block (my )?(pc|computer|screen)\b", t):
        if IS_WINDOWS:
            subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"])
            return "Locking your PC."
        return "Locking only works on Windows."

    m = re.match(r"^(search( google)? for|google|search|look up)\s+(.+)$", t)
    if m:
        q = m.group(3)
        webbrowser.open("https://www.google.com/search?q=" + urllib.parse.quote_plus(q))
        return f"Searching Google for “{q}”."

    m = re.match(r"^(youtube|play|search youtube for)\s+(.+?)( on youtube)?$", t)
    if m:
        q = m.group(2)
        webbrowser.open("https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(q))
        return f"Searching YouTube for “{q}”."

    m = re.match(r"^(go to|visit)\s+(\S+\.\S+)$", t)
    if m:
        url = m.group(2)
        if not url.startswith("http"):
            url = "https://" + url
        webbrowser.open(url)
        return f"Opening {url}."

    m = re.match(r"^(open|launch|start|run)\s+(my\s+|the\s+)?(.+?)( folder| app| website| site)?$", t)
    if m:
        what, kind = m.group(3).strip(), (m.group(4) or "").strip()
        if kind != "folder" and kind not in ("website", "site") and what in APPS:
            if _launch(APPS[what]):
                return f"Opening {what}."
            if what == "github desktop":
                return "I couldn't find GitHub Desktop. Is it installed?"
        if kind != "app" and what in FOLDERS and (kind == "folder" or what not in SITES):
            if _open_path(FOLDERS[what]):
                return f"Opening your {what} folder."
            return f"I couldn't find your {what} folder."
        if what in SITES:
            webbrowser.open(SITES[what])
            return f"Opening {what}."
        if what in FOLDERS:
            if _open_path(FOLDERS[what]):
                return f"Opening your {what} folder."
        if kind != "folder" and re.match(r"^\S+\.\S+$", what):
            webbrowser.open("https://" + what)
            return f"Opening {what}."
        if kind != "folder" and _launch(what):
            return f"Trying to open {what}."
        return f"I don't know how to open “{what}” yet. Say 'help' to see what I can open."

    return None


# ---------- git helpers (used for "commit message") ----------
def find_git():
    """Find git.exe: on PATH, or the copy bundled inside GitHub Desktop."""
    g = shutil.which("git")
    if g:
        return g
    base = os.path.join(os.environ.get("LOCALAPPDATA", ""), "GitHubDesktop")
    if os.path.isdir(base):
        for d in sorted(os.listdir(base), reverse=True):  # newest app-x.y.z first
            cand = os.path.join(base, d, "resources", "app", "git", "cmd", "git.exe")
            if os.path.exists(cand):
                return cand
    return None


def repo_diff(repo_path, limit=8000):
    """Return (ok, text): the repo's current changes, or an error message."""
    git = find_git()
    if not git:
        return False, "I couldn't find git. Install Git for Windows (git-scm.com) and try again."

    def run(*args):
        flags = 0x08000000 if IS_WINDOWS else 0  # CREATE_NO_WINDOW
        return subprocess.run([git, "-C", repo_path, *args], capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              creationflags=flags)

    check = run("rev-parse", "--is-inside-work-tree")
    if check.returncode != 0:
        return False, "That folder isn't a git repository."
    diff = run("diff", "--staged").stdout or run("diff").stdout
    if not diff.strip():
        new_files = run("ls-files", "--others", "--exclude-standard").stdout.strip()
        if new_files:
            return True, "New files added:\n" + new_files[:limit]
        return False, "No changes found in that repo — nothing to commit."
    return True, diff[:limit]
