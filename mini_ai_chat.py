import os, json, urllib.request, urllib.error, threading, ctypes, msvcrt, time
from ctypes import wintypes

BASE = os.path.join(os.environ["LOCALAPPDATA"], "SecretGPT")
CFG = os.path.join(BASE, "groq_chat.json")
os.makedirs(BASE, exist_ok=True)

def settings():
    try:
        with open(CFG, encoding="utf-8") as f:
            s = json.load(f)
        if s.get("url") and s.get("password"):
            return s
    except (OSError, ValueError, TypeError):
        pass

    print("=== SecretGPT Setup ===")
    url = input("API URL: ").strip().rstrip("/")
    password = input("API password: ").strip()

    if not url.startswith(("https://", "http://")) or not password:
        print("Invalid URL or empty password.")
        raise SystemExit(1)

    with open(CFG, "w", encoding="utf-8") as f:
        json.dump({"url": url, "password": password}, f, indent=2)

    return {"url": url, "password": password}


if os.name != "nt":
    raise SystemExit("Windows only.")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
hwnd = kernel32.GetConsoleWindow()
reset = threading.Event()


def hotkeys():
    user32.RegisterHotKey(None, 1, 0x0002 | 0x0001, 0x48)  # Ctrl+Alt+H
    user32.RegisterHotKey(None, 2, 0x0002 | 0x0001, 0x52)  # Ctrl+Alt+R

    msg = wintypes.MSG()

    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        if msg.message == 0x0312:
            if msg.wParam == 1:
                user32.ShowWindow(
                    hwnd, 0 if user32.IsWindowVisible(hwnd) else 5
                )
            elif msg.wParam == 2:
                reset.set()

    user32.UnregisterHotKey(None, 1)
    user32.UnregisterHotKey(None, 2)


threading.Thread(target=hotkeys, daemon=True).start()


def read_line():
    chars = []

    while True:
        if reset.is_set():
            return None

        if msvcrt.kbhit():
            ch = msvcrt.getwch()

            if ch in ("\r", "\n"):
                print()
                return "".join(chars).strip()

            if ch == "\003":
                raise KeyboardInterrupt

            if ch == "\b":
                if chars:
                    chars.pop()
                    print("\b \b", end="", flush=True)

            elif ch in ("\x00", "\xe0"):
                msvcrt.getwch()

            else:
                chars.append(ch)
                print(ch, end="", flush=True)

        else:
            time.sleep(0.03)


chat = []

while True:
    cfg = settings()

    while not reset.is_set():
        os.system("cls")

        print(" SECRETGPT  |  Ctrl+Alt+H: Hide/Show")
        print(" Ctrl+Alt+R: Reset settings  |  /exit: Quit")
        print("=" * 72)

        for role, text in chat:
            print(f"\n{role}:\n{text}")

        print("\n" + "=" * 72)
        print("\nYou: ", end="", flush=True)

        try:
            prompt = read_line()
        except (EOFError, KeyboardInterrupt):
            raise SystemExit

        if reset.is_set() or prompt is None:
            break

        if not prompt:
            continue

        if prompt.lower() in ("/exit", "/quit"):
            raise SystemExit

        chat.append(("You", prompt))

        body = json.dumps({
            "prompt": prompt,
            "system": "You are a helpful assistant. Answer in the language used by the user.",
            "max_tokens": 1000
        }).encode("utf-8")

        req = urllib.request.Request(
            cfg["url"],
            data=body,
            headers={
                "Authorization": "Bearer " + cfg["password"],
                "Content-Type": "application/json"
            },
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=90) as response:
                data = json.loads(response.read().decode("utf-8"))

            answer = data.get(
                "answer", json.dumps(data, ensure_ascii=False)
            )

        except urllib.error.HTTPError as e:
            answer = f"HTTP {e.code}: {e.read().decode(errors='replace')}"

        except Exception as e:
            answer = f"Error: {e}"

        chat.append(("AI", answer))

    if reset.is_set():
        reset.clear()

        try:
            os.remove(CFG)
        except FileNotFoundError:
            pass

        chat.clear()