# KAIRO — your personal desktop assistant

KAIRO (from the Greek *kairos*, "the right moment") is a free assistant for Windows that
chats, talks back, controls your PC, and helps you learn GitHub.

## Install (one time)
1. Unzip this folder somewhere permanent, e.g. `Documents\KAIRO`.
2. Double-click **Setup-KAIRO.bat**. If Windows shows "Windows protected your PC",
   click **More info → Run anyway** (it's a plain-text script; you can open it in Notepad to read it first).
3. If it installs Python or Ollama, it will ask you to **close the window and run Setup again** — do that.
4. Wait for the AI model download (about 2 GB). When it says **Done**, a **KAIRO** icon is on your desktop.

## Starter Kit (optional, recommended)
Double-click **Starter-Kit.bat** to install the best free beginner tools — Git, VS Code,
GitHub CLI, PowerToys, LocalSend — download a practice repo to `Documents\GitHub`,
and open the best learning pages. In KAIRO, type **learn** to see the learning path.

## Use
- Double-click **KAIRO** on your desktop. The first time, it asks your name.
- Type and press Enter, or click **🎤 Talk** (or press Ctrl+Space) and speak.
- Say **help** to see instant commands: open apps/websites/folders, search, time, lock PC.
- **Commit message**: pick a repo folder and KAIRO writes a commit message from your changes
  and copies it — paste it into GitHub Desktop's Summary box.
- Untick **Speak replies** to make it silent.

## Customise
Edit `config.json` in Notepad:
- `assistant_name` — rename your assistant
- `model` — a different Ollama model (download it first with `ollama pull <name>`)
- `voice_rate` — speaking speed

## Good to know
- The AI brain (Ollama) runs on your own PC: free, private, works offline. Answers can be
  wrong sometimes, and it's slower on older PCs.
- Voice *listening* uses Google's free speech service, so it needs internet.
  Voice *speaking* works offline.

## About
Built by Chekri Gadhiraju as a first software project while learning Python, Git and local AI.
Portfolio: https://gchekri04-droid.github.io
