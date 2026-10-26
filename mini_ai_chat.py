import os
import sys
import json
import time
import ctypes
import getpass
import urllib.request
import urllib.error

APP_DIR = os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.expanduser("~")),
    "SecretGPT"
)
CONFIG_FILE = os.path.join(APP_DIR, "groq_chat.json")

SYSTEM_PROMPT = (
    "You are a helpful assistant. "
    "Reply in the same language as the user."
)

MAX_TOKENS = 1000
TIMEOUT = 90

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
WHITE = "\033[97m"


def color(text, shade=WHITE):
    return f"{shade}{text}{RESET}"


def enable_colors():
    if os.name != "nt":
        return

    try:
        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_uint()

        if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel.SetConsoleMode(handle, mode.value | 4)
    except Exception:
        pass


def clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def separator(char="─", shade=CYAN, width=68):
    print(color(char * width, shade))


def load_config():
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, dict) else {}

    except (OSError, ValueError):
        return {}


def save_config(config):
    os.makedirs(APP_DIR, exist_ok=True)

    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file, ensure_ascii=False, indent=2)


def read_password(message):
    try:
        return getpass.getpass(message).strip()
    except Exception:
        return input(message).strip()


def setup(config):
    print(color("  SECRETGPT INITIAL SETUP", BOLD + MAGENTA))
    print()

    url = input("  Worker URL: ").strip()

    if not url.startswith(("https://", "http://")):
        raise ValueError("URL must start with https:// or http://")

    password = read_password("  API password: ")

    config["url"] = url.rstrip("/")
    config["password"] = password

    save_config(config)

    return config


def banner(url):
    clear_screen()

    print(color(
        "╔══════════════════════════════════════════════════════════════════╗",
        BOLD + CYAN
    ))
    print(
        color("║", BOLD + CYAN)
        + color("                     S E C R E T G P T  2.0                    ", BOLD + WHITE)
        + color("║", BOLD + CYAN)
    )
    print(
        color("║", BOLD + CYAN)
        + color("                   COLORFUL CONSOLE AI CLIENT                  ", DIM + WHITE)
        + color("║", BOLD + CYAN)
    )
    print(color(
        "╚══════════════════════════════════════════════════════════════════╝",
        BOLD + CYAN
    ))

    print(color("  /help  commands     /settings  setup     /clear  clear     /exit  quit", DIM))
    print(color("  SERVER: ", DIM) + color(url, CYAN))

    separator()


def print_message(role, text):
    if role == "you":
        prefix = color("  YOU  › ", BOLD + GREEN)
    else:
        prefix = color("  AI   › ", BOLD + CYAN)

    lines = str(text).replace("\r", "").split("\n")

    for index, line in enumerate(lines):
        if index == 0:
            print(prefix + line)
        else:
            print(" " * 9 + line)


def show_error(message, status=None, headers=None, body=""):
    print()
    separator("─", RED)

    print(color("  REQUEST FAILED", BOLD + RED))

    if status is not None:
        print(color(f"  HTTP status: {status}", YELLOW))

    print(color(f"  {message}", WHITE))

    if headers:
        ray = headers.get("CF-Ray", "")
        server = headers.get("Server", "")

        if ray:
            print(color(f"  CF-Ray: {ray}", DIM))

        if server:
            print(color(f"  Server: {server}", DIM))

    body = (body or "").strip()

    if body:
        print(color("  SERVER RESPONSE:", YELLOW))

        for line in body[:1500].splitlines():
            print("    " + line)

    lower = body.lower()

    if status == 403 and ("1010" in lower or "error 1010" in lower):
        print()
        print(color("  CLOUDFLARE ERROR 1010", BOLD + RED))
        print("  Cloudflare has blocked this request.")
        print("  This is not necessarily a Groq API-key problem.")
        print("  Check the security events and rules for this hostname.")
        print("  Changing User-Agent alone usually cannot fix this.")

    elif status == 403:
        print("  Check Worker authentication and Cloudflare security rules.")

    elif status == 401:
        print("  Check the API password configured in your Worker.")

    elif status is None:
        print("  Check the URL, DNS, and internet connection.")

    separator("─", RED)
    print()


def request_answer(config, prompt):
    url = config.get("url", "").strip()
    password = config.get("password", "")

    payload = {
        "prompt": prompt,
        "system": SYSTEM_PROMPT,
        "max_tokens": MAX_TOKENS
    }

    data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=data,
        method="POST",
        headers={
            "Authorization": f"Bearer {password}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "SecretGPT-CLI/2.0"
        }
    )

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            raw = response.read().decode("utf-8", errors="replace")

        try:
            result = json.loads(raw)
        except ValueError:
            show_error("Worker returned invalid JSON.", body=raw[:1000])
            return None

        if not isinstance(result, dict):
            show_error("Worker response must be a JSON object.")
            return None

        if "answer" not in result:
            keys = ", ".join(result.keys()) or "(none)"
            show_error(
                f"Missing 'answer' field. Received fields: {keys}",
                body=raw[:1000]
            )
            return None

        return str(result["answer"])

    except urllib.error.HTTPError as error:
        body = error.read().decode("utf-8", errors="replace")

        show_error(
            str(error.reason),
            error.code,
            error.headers,
            body
        )

    except urllib.error.URLError as error:
        show_error(f"Connection or DNS error: {error.reason}")

    except TimeoutError:
        show_error("The request timed out.")

    except KeyboardInterrupt:
        print(color("\n  Request cancelled.", YELLOW))

    except Exception as error:
        show_error(f"{type(error).__name__}: {error}")

    return None


def settings_menu(config):
    print()
    print(color("  SETTINGS", BOLD + MAGENTA))
    print("  1. Change Worker URL")
    print("  2. Change API password")
    print("  3. Change both")
    print("  Enter. Cancel")

    choice = input(color("  > ", CYAN)).strip()

    if choice not in ("1", "2", "3"):
        return config

    if choice in ("1", "3"):
        url = input("  New Worker URL: ").strip()

        if not url.startswith(("https://", "http://")):
            print(color("  Invalid URL.", RED))
            input("  Press Enter...")
            return config

        config["url"] = url.rstrip("/")

    if choice in ("2", "3"):
        config["password"] = read_password("  New API password: ")

    save_config(config)

    print(color("  Settings saved.", GREEN))
    input("  Press Enter...")

    return config


def main():
    enable_colors()

    config = load_config()

    if not config.get("url") or "password" not in config:
        try:
            config = setup(config)

        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            return

        except Exception as error:
            print(color(f"\nSetup error: {error}", RED))
            input("Press Enter to close...")
            return

    history = []

    while True:
        banner(config.get("url", ""))

        for role, text in history[-20:]:
            print_message(role, text)
            print()

        try:
            prompt = input(color("  YOU › ", BOLD + GREEN)).strip()

        except (KeyboardInterrupt, EOFError):
            print("\n" + color("  Bye!", CYAN))
            break

        if not prompt:
            continue

        command = prompt.lower()

        if command in ("/exit", "/quit", "/q"):
            print(color("  Bye!", CYAN))
            break

        if command == "/help":
            print()
            print("  /help      Show commands")
            print("  /clear     Clear chat history")
            print("  /settings  Change URL or password")
            print("  /exit      Exit")
            input("\n  Press Enter...")
            continue

        if command == "/clear":
            history.clear()
            continue

        if command in ("/settings", "/reset"):
            config = settings_menu(config)
            continue

        history.append(("you", prompt))

        print()
        print(color("  ◇ Connecting to Worker...", YELLOW), flush=True)

        started = time.time()
        answer = request_answer(config, prompt)
        elapsed = time.time() - started

        if answer is not None:
            print(color(f"  ✓ Reply received in {elapsed:.1f}s", BOLD + GREEN))
            history.append(("ai", answer))
            print()
            print_message("ai", answer)
        else:
            print(color("  ✗ Request failed. See details above.", BOLD + RED))

        try:
            input("\n" + color("  Press Enter to continue...", DIM))
        except (KeyboardInterrupt, EOFError):
            break


if __name__ == "__main__":
    main()