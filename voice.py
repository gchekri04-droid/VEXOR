"""VEXOR's voice.

Speaking: on Windows, uses the built-in Windows speech engine (System.Speech) in a
separate PowerShell process, so it can never block VEXOR's window. Elsewhere, falls back to pyttsx3.
Listening: SpeechRecognition (Google's free web speech service, needs internet).

Both are optional: if they aren't installed, VEXOR still works by typing.
"""
import queue
import subprocess
import sys
import threading

IS_WINDOWS = sys.platform.startswith("win")

pyttsx3 = None
if not IS_WINDOWS:  # on Windows we use the built-in speech engine instead (see below)
    try:
        import pyttsx3
    except Exception:  # not installed or no voice engine
        pyttsx3 = None

try:
    import speech_recognition as sr
except Exception:
    sr = None


class Voice:
    def __init__(self, rate=185):
        self.rate = rate
        self.can_speak = IS_WINDOWS or pyttsx3 is not None
        self.can_listen = False
        self.listen_error = ""
        if sr is None:
            self.listen_error = "SpeechRecognition not installed"
        else:
            try:
                sr.Microphone.list_microphone_names()  # needs PyAudio
                self.can_listen = True
            except Exception as e:
                self.listen_error = f"Microphone unavailable ({e.__class__.__name__}). Is PyAudio installed?"
        self._q = queue.Queue()
        if self.can_speak:
            threading.Thread(target=self._speaker_loop, daemon=True).start()

    # ---------- speaking ----------
    def speak(self, text):
        if self.can_speak and text.strip():
            self._q.put(text)

    def _speaker_loop(self):
        while True:
            text = self._q.get()
            try:
                if IS_WINDOWS:
                    self._speak_windows(text)
                else:
                    engine = pyttsx3.init()
                    engine.setProperty("rate", self.rate)
                    engine.say(text)
                    engine.runAndWait()
                    engine.stop()
            except Exception:
                pass

    def _speak_windows(self, text):
        # Map words-per-minute to the Windows speech rate scale (-10 .. 10, 0 = normal).
        rate = max(-10, min(10, round((self.rate - 170) / 15)))
        script = ("[Console]::InputEncoding = [Text.Encoding]::UTF8; "
                  "Add-Type -AssemblyName System.Speech; "
                  "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
                  f"$s.Rate = {rate}; "
                  "$s.Speak([Console]::In.ReadToEnd())")
        subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
                       input=text.encode("utf-8"), creationflags=0x08000000,  # no console window
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=300)

    # ---------- listening ----------
    def listen(self, timeout=6, phrase_limit=15):
        """Record from the microphone and return (text, error)."""
        if not self.can_listen:
            return None, self.listen_error
        r = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                r.adjust_for_ambient_noise(source, duration=0.5)
                audio = r.listen(source, timeout=timeout, phrase_time_limit=phrase_limit)
            return r.recognize_google(audio), None
        except sr.WaitTimeoutError:
            return None, "I didn't hear anything."
        except sr.UnknownValueError:
            return None, "Sorry, I couldn't understand that."
        except sr.RequestError:
            return None, "Speech service unreachable — check your internet."
        except Exception as e:
            return None, f"Microphone error: {e}"
