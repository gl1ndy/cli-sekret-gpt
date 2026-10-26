import os, json, urllib.request, urllib.error, threading, ctypes, msvcrt, time
from ctypes import wintypes

CFG = "groq_chat.json"
def settings():
    if os.path.exists(CFG):
        try: return json.load(open(CFG, encoding="utf-8"))
        except Exception: pass
    s = {"url": input("API URL: ").strip().rstrip("/"), "password": input("API password: ").strip()}
    json.dump(s, open(CFG, "w", encoding="utf-8"), indent=2)
    return s

if os.name != "nt":
    print("This mini app's hotkeys currently require Windows."); raise SystemExit

user32, kernel32 = ctypes.windll.user32, ctypes.windll.kernel32
hwnd = kernel32.GetConsoleWindow()
reset = threading.Event()

def hotkeys():
    user32.RegisterHotKey(None, 1, 0x0002 | 0x0001, 0x48)  # Ctrl+Alt+H
    user32.RegisterHotKey(None, 2, 0x0002 | 0x0001, 0x52)  # Ctrl+Alt+R
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == 0x0312:
            if msg.wParam == 1: user32.ShowWindow(hwnd, 0 if user32.IsWindowVisible(hwnd) else 5)
            if msg.wParam == 2: reset.set()
    user32.UnregisterHotKey(None, 1); user32.UnregisterHotKey(None, 2)

threading.Thread(target=hotkeys, daemon=True).start()

def read_line():
    chars = []
    while True:
        if reset.is_set(): return None
        if msvcrt.kbhit():
            ch = msvcrt.getwch()
            if ch in ("\\r", "\\n"):
                print(); return "".join(chars).strip()
            if ch == "\\003": raise KeyboardInterrupt
            if ch == "\\b":
                if chars: chars.pop(); print("\\b \\b", end="", flush=True)
            elif ch in ("\\x00", "\\xe0"):
                msvcrt.getwch()
            else:
                chars.append(ch); print(ch, end="", flush=True)
        else: time.sleep(0.03)

chat = []
while True:
    cfg = settings()
    while not reset.is_set():
        os.system("cls")
        print(" MINI AI CHAT   |   Ctrl+Alt+H: hide/show   |   Ctrl+Alt+R: reset settings")
        print("-" * 68)
        for role, text in chat: print(f"\n{role}:\n{text}")
        print("\n" + "-" * 68 + "\nYou: ", end="", flush=True)
        try: prompt = read_line()
        except (EOFError, KeyboardInterrupt): raise SystemExit
        if reset.is_set(): break
        if not prompt: continue
        if prompt.lower() in ("/exit", "/quit"): raise SystemExit
        chat.append(("You", prompt))
        body = json.dumps({"prompt": prompt, "system": "Answer clearly.", "max_tokens": 1000}).encode()
        req = urllib.request.Request(cfg["url"], data=body, headers={
            "Authorization": "Bearer " + cfg["password"], "Content-Type": "application/json"
        })
        try:
            with urllib.request.urlopen(req, timeout=90) as r: data = json.loads(r.read())
            answer = data.get("answer", json.dumps(data, ensure_ascii=False))
        except urllib.error.HTTPError as e:
            answer = f"HTTP {e.code}: {e.read().decode(errors='replace')}"
        except Exception as e: answer = f"Error: {e}"
        chat.append(("AI", answer))
    if reset.is_set():
        reset.clear()
        try: os.remove(CFG)
        except FileNotFoundError: pass
        chat.clear()
