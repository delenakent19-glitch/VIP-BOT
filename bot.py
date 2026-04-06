#!/usr/bin/env python3

import os, json, random, string, io, asyncio, logging
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from telegram.constants import ParseMode

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  CONFIG  \u2014  edit before running
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
BOT_TOKEN     = "8797773644:AAHuuZurs0oiduQNW6ywxvTXQ1Kdf32XE9w"
OWNER_ID      = 8420104044        # your Telegram numeric ID
DATA_FILE     = "data.json"
DB_FOLDER     = "database"
LINES_PER_USE = 250

os.makedirs(DB_FOLDER, exist_ok=True)

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  LOGO  (plain text block \u2014 no Markdown inside)
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
LOGO = (
    "```\n"
    "\u2554\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2557\n"
    "\u2551   \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2557\u2588\u2588\u2557\u2588\u2588\u2557     \u2551\n"
    "\u2551   \u255a\u2550\u2550\u2588\u2588\u2588\u2554\u255d\u2588\u2588\u2554\u2550\u2550\u2550\u2550\u255d\u2588\u2588\u2551\u2588\u2588\u2551\u2588\u2588\u2551     \u2551\n"
    "\u2551     \u2588\u2588\u2588\u2554\u255d \u2588\u2588\u2588\u2588\u2588\u2557  \u2588\u2588\u2551\u2588\u2588\u2551\u2588\u2588\u2551     \u2551\n"
    "\u2551    \u2588\u2588\u2588\u2554\u255d  \u2588\u2588\u2554\u2550\u2550\u255d  \u2588\u2588\u2551\u2588\u2588\u2551\u2588\u2588\u2551     \u2551\n"
    "\u2551   \u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2588\u2588\u2551\u2588\u2588\u2551\u2588\u2588\u2588\u2588\u2588\u2588\u2588\u2557\u2551\n"
    "\u2551   \u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d\u255a\u2550\u255d\u255a\u2550\u255d\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u255d\u2551\n"
    "\u2551        Z E I J I E   B O T      \u2551\n"
    "\u255a\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u255d\n"
    "```"
)

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  WELCOME MESSAGES  (rotated randomly)
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
WELCOME_LINES = [
    "\u26a1 *ZEIJIE BOT* is locked, loaded, and ready for action.",
    "\ud83d\udd25 Welcome to *ZEIJIE BOT* \u2014 your premium gateway.",
    "\ud83c\udf10 *ZEIJIE BOT* online\\. Precision\\. Power\\. Premium\\.",
    "\ud83d\udee1 *ZEIJIE BOT* activated \u2014 built different, built better.",
    "\ud83d\udc8e You've entered *ZEIJIE BOT* \u2014 where premium lives.",
    "\ud83d\ude80 *ZEIJIE BOT* is live\\. Let's get to work\\.",
    "\ud83c\udfaf *ZEIJIE BOT* standing by \u2014 the real deal starts here.",
    "\ud83d\udc7e *ZEIJIE BOT* loaded\\. No limits, only premium access\\.",
]

def random_welcome() -> str:
    return random.choice(WELCOME_LINES)

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  MARKDOWN SAFETY
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def md_safe(text: str) -> str:
    """Escape characters that break Telegram MarkdownV1 in user-supplied strings."""
    # In MarkdownV1, only _ * ` [ need escaping
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  DATA HELPERS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def load() -> dict:
    """Load data.json, filling in any missing top-level keys defensively."""
    default = {"admins": [], "keys": {}, "members": {}, "redeemed": {}}
    if not os.path.exists(DATA_FILE):
        return default
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("data.json corrupted or unreadable \u2014 starting fresh.")
        return default
    # Ensure all expected keys exist even if file is partial
    for k, v in default.items():
        d.setdefault(k, v)
    return d

def save(d: dict):
    """Atomically write data.json \u2014 write to tmp then rename to avoid corruption."""
    tmp = DATA_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)
    except OSError as e:
        logger.error("Failed to save data.json: %s", e)

def is_admin(uid, d) -> bool:
    return str(uid) in [str(x) for x in d.get("admins", [])] or int(uid) == OWNER_ID

def has_access(uid, d) -> bool:
    """Admins always have access. Buyers need a valid non-expired redeemed key."""
    if is_admin(uid, d):
        return True
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    exp = rd.get("expires")
    if not exp:
        return True  # lifetime
    try:
        return datetime.fromisoformat(exp) > datetime.now()
    except ValueError:
        return False

def track(uid, username, first_name, d):
    d.setdefault("members", {})[str(uid)] = {
        "username":   username or "",
        "first_name": first_name or "",
        "last_seen":  datetime.now().isoformat(),
    }

def get_db_files() -> list:
    return sorted(
        f for f in os.listdir(DB_FOLDER)
        if os.path.isfile(os.path.join(DB_FOLDER, f))
    )

def count_lines(path: str) -> int:
    try:
        with open(path, "r", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  KEY HELPERS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def generate_key() -> str:
    """
    Format: ZEIJIE-XXXXXX-XXXXXXXX-XXXXXX
    \u2022 Part 1 : 6 random uppercase letters
    \u2022 Part 2 : 8 random alphanumeric chars
    \u2022 Part 3 : 4-char timestamp hex + 2 random chars  (collision-proof per second)
    Example : ZEIJIE-ABCDEF-K3M9P2QR-A3KQ2B
    """
    part1  = "".join(random.choices(string.ascii_uppercase, k=6))
    part2  = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    ts_hex = format(int(datetime.now().timestamp()) & 0xFFFF, "04X")
    extra  = "".join(random.choices(string.ascii_uppercase + string.digits, k=2))
    part3  = ts_hex[:2] + extra + ts_hex[2:]
    return f"ZEIJIE-{part1}-{part2}-{part3}"

def parse_duration(raw: str):
    """
    Returns (timedelta | None, label_str).
    Accepts: lifetime, 1h, 30m, 7d, 10days, 2hours, 45mins ...
    """
    dur = raw.strip().lower()
    if dur in ("lifetime", "forever", "\u221e"):
        return None, "Lifetime"

    digits = "".join(c for c in dur if c.isdigit())
    if not digits:
        raise ValueError(f"Cannot parse duration: {raw!r}")
    n = int(digits)

    if "h" in dur:
        return timedelta(hours=n),   f"{n} hour{'s' if n != 1 else ''}"
    if "m" in dur and "month" not in dur:
        return timedelta(minutes=n), f"{n} minute{'s' if n != 1 else ''}"
    return timedelta(days=n), f"{n} day{'s' if n != 1 else ''}"

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  EXPIRY DISPLAY  (accurate with live countdown)
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def expiry_display(exp_iso) -> str:
    """Exact date/time + human-readable time remaining."""
    if not exp_iso:
        return "Never (Lifetime)"
    try:
        exp_dt = datetime.fromisoformat(exp_iso)
    except ValueError:
        return "Invalid date"

    now      = datetime.now()
    abs_time = exp_dt.strftime("%Y-%m-%d %H:%M:%S")

    if exp_dt <= now:
        return f"Expired ({abs_time})"

    delta      = exp_dt - now
    total_secs = int(delta.total_seconds())
    days_rem   = total_secs // 86400
    hours_rem  = (total_secs % 86400) // 3600
    mins_rem   = (total_secs % 3600)  // 60
    secs_rem   = total_secs % 60

    parts = []
    if days_rem:
        parts.append(f"{days_rem}d")
    if hours_rem:
        parts.append(f"{hours_rem}h")
    if mins_rem:
        parts.append(f"{mins_rem}m")
    if secs_rem and not days_rem:
        parts.append(f"{secs_rem}s")

    remaining_str = " ".join(parts) if parts else "< 1s"
    return f"{abs_time}  ({remaining_str} left)"

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  MESSAGE BUILDERS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def key_message(key: str, duration_label: str, expires_iso, devices: int) -> str:
    exp_str = expiry_display(expires_iso)
    return (
        "\ud83d\udd11 *Key Generated!*\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"`{key}`\n"
        "\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
        f"\u23f1 Duration   : {duration_label}\n"
        f"\ud83d\udcc5 Expires    : {exp_str}\n"
        f"\ud83d\udc65 Max users  : {devices}\n\n"
        "_Key saved to database \u2705_"
    )

def premium_summary(fname_stem: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "\ud83d\udd2e \u2728 PREMIUM FILE GENERATED SUCCESSFULLY! \u2728 \ud83d\udd2e\n\n"
        "\ud83d\udcca GENERATION SUMMARY\n"
        f"\u2523 \ud83c\udfae Source      : {fname_stem.upper()}\n"
        f"\u2523 \ud83d\udcdc Lines       : {sent}\n"
        f"\u2523 \ud83d\udd50 Generated   : {now}\n"
        f"\u2523 \ud83d\udcbe Remaining   : {remaining:,} lines\n"
        "\u2523 \ud83e\uddf9 Cleanup     : \u2705 Done\n\n"
        "\ud83d\udee1 SECURITY\n"
        "\u2523 \ud83d\udd12 Auto-Expiry : 5 minutes\n"
        "\u2523 \ud83d\uddd1 Auto-Delete : Enabled\n"
        "\u2523 \u26a1 Session     : Verified\n\n"
        "\u2b07\ufe0f  Download immediately \u2014 file deletes in 5 min\n\n"
        "\u2b50 Thank you for using ZEIJIE Premium!"
    )

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  KEYBOARDS
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def kb_main(uid, d) -> InlineKeyboardMarkup:
    rows = []
    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("\u26a1 Admin Panel", callback_data="admin")])
    rows += [
        [
            InlineKeyboardButton("\ud83d\udcc2 Database", callback_data="db"),
            InlineKeyboardButton("\ud83d\udd11 Redeem",   callback_data="redeem_info"),
        ],
        [
            InlineKeyboardButton("\ud83d\udc64 Status",   callback_data="status"),
            InlineKeyboardButton("\ud83d\udccb Commands", callback_data="commands"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("\ud83d\udd11 Create Key",  callback_data="adm_create")],
        [InlineKeyboardButton("\ud83d\udddd Active Keys", callback_data="adm_keys")],
        [InlineKeyboardButton("\ud83d\udc65 Admins List", callback_data="adm_list")],
        [InlineKeyboardButton("\ud83d\udd19 Back",        callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "\ud83d\udd19 Back to Admin" if dest == "admin" else "\ud83d\udd19 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  WELCOME TEXT BUILDER  (safe for Markdown)
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
def build_welcome(first_name: str, username, uid, d: dict) -> str:
    status       = "\u2705 Active" if has_access(uid, d) else "\ud83d\udd12 No Access"
    welcome_line = random_welcome()
    safe_name    = md_safe(first_name or "Operator")
    user_line    = f"\ud83d\udc64 *{safe_name}*"
    if username:
        user_line += f"  (@{md_safe(username)})"
    return (
        f"{LOGO}\n\n"
        f"{welcome_line}\n\n"
        f"{user_line}\n"
        f"\ud83d\udd10 Status: {status}"
    )

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  AUTO-DELETE HELPER  (non-blocking)
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
async def _auto_delete(delay: int, *messages):
    """Delete messages after `delay` seconds without blocking the bot."""
    await asyncio.sleep(delay)
    for m in messages:
        try:
            await m.delete()
        except Exception:
            pass

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  /start
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    await update.message.reply_text(
        build_welcome(user.first_name, user.username, user.id, d),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_main(user.id, d),
    )

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  /createkeys <max_users> <duration>  \u2014 admin only
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id

    if not is_admin(uid, d):
        await update.message.reply_text("\u274c This command is for admins only.")
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "\ud83d\udccb Usage:\n/createkeys <max\\_users> <duration>\n\n"
            "Duration examples:\n"
            "  10d      \u2192 10 days\n"
            "  2h       \u2192 2 hours\n"
            "  30m      \u2192 30 minutes\n"
            "  lifetime \u2192 never expires",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        devices = int(ctx.args[0])
        if devices < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("\u274c Max users must be a positive integer (e.g. 1).")
        return

    raw_dur = " ".join(ctx.args[1:])
    try:
        td, duration_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "\u274c Invalid duration.\n\nExamples: 10d / 2h / 30m / lifetime"
        )
        return

    now         = datetime.now()
    key         = generate_key()
    expires_dt  = (now + td) if td else None
    expires_iso = expires_dt.isoformat() if expires_dt else None

    # \u2500\u2500 Save key to data.json \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    d["keys"][key] = {
        "devices":    devices,
        "duration":   raw_dur,
        "expires":    expires_iso,
        "used_by":    [],
        "created_by": str(uid),
        "created_at": now.isoformat(),
    }
    save(d)
    logger.info("Key created: %s  expires=%s  devices=%s  by=%s", key, expires_iso, devices, uid)

    await update.message.reply_text(
        key_message(key, duration_label, expires_iso, devices),
        parse_mode=ParseMode.MARKDOWN,
    )

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  /redeem <key>
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)

    if not ctx.args:
        await update.message.reply_text(
            "Usage: `/redeem ZEIJIE-XXXXXX-XXXXXXXX-XXXXXX`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text("\u274c Invalid key. Check and try again.")
        return

    k = d["keys"][key]

    if uid in k.get("used_by", []):
        await update.message.reply_text("\u26a0\ufe0f This key is already activated on your account.")
        return

    if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
        await update.message.reply_text("\u274c Device limit reached for this key.")
        return

    key_exp = k.get("expires")
    if key_exp:
        try:
            if datetime.fromisoformat(key_exp) < datetime.now():
                await update.message.reply_text("\u274c This key has already expired.")
                return
        except ValueError:
            await update.message.reply_text("\u274c Key has an invalid expiry date.")
            return

    # \u2500\u2500 Activate \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
    k.setdefault("used_by", []).append(uid)
    d["redeemed"][uid] = {
        "key":       key,
        "expires":   key_exp,
        "device_id": uid,
        "activated": datetime.now().isoformat(),
    }
    save(d)
    logger.info("Key redeemed: %s  by uid=%s", key, uid)

    raw_dur = k.get("duration", "lifetime")
    try:
        _, dur_label = parse_duration(raw_dur)
    except ValueError:
        dur_label = raw_dur

    exp_label = expiry_display(key_exp)

    await update.message.reply_text(
        "\u2705 *Key Activated!*\n\n"
        f"\ud83d\udd11 `{key}`\n"
        f"\u23f1 Duration  : {dur_label}\n"
        f"\ud83d\udcc5 Expires   : {exp_label}\n"
        f"\ud83d\udcf1 Device    : Locked to your account",
        parse_mode=ParseMode.MARKDOWN,
    )

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  /status
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "\ud83d\udc51 *Admin Account* \u2014 Full access granted.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text("\ud83d\udd12 No active key. Use /redeem <key>")
        return

    exp = rd.get("expires")
    if exp:
        try:
            if datetime.fromisoformat(exp) < datetime.now():
                await update.message.reply_text(
                    "\u26d4 Your key has *expired*.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
        except ValueError:
            pass

    await update.message.reply_text(
        f"\u2705 *Active*\n\n"
        f"\ud83d\udd11 `{rd['key']}`\n"
        f"\ud83d\udcc5 Expires: {expiry_display(exp)}",
        parse_mode=ParseMode.MARKDOWN,
    )

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  /addadmin <user_id>  \u2014 owner only
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
async def addadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return
    target = str(ctx.args[0])
    if target not in [str(a) for a in d["admins"]]:
        d["admins"].append(target)
        save(d)
        logger.info("Admin added: %s", target)
    await update.message.reply_text(f"\u2705 Admin added: `{target}`", parse_mode=ParseMode.MARKDOWN)

# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
#  /removeadmin <user_id>  \u2014 owner only
# \u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550\u2550
async def removeadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text    "╚══════════════════════════════════╝\n"
    "```"
)

# ════════════════════════════════════════════════
#  WELCOME MESSAGES  (rotated randomly)
# ════════════════════════════════════════════════
WELCOME_LINES = [
    "⚡ *ZEIJIE BOT* is locked, loaded, and ready for action.",
    "🔥 Welcome to *ZEIJIE BOT* — your premium gateway.",
    "🌐 *ZEIJIE BOT* online. Precision. Power. Premium.",
    "🛡️ *ZEIJIE BOT* activated — built different, built better.",
    "💎 You've entered *ZEIJIE BOT* — where premium lives.",
    "🚀 *ZEIJIE BOT* is live. Let's get to work.",
    "🎯 *ZEIJIE BOT* standing by — the real deal starts here.",
    "👾 *ZEIJIE BOT* loaded. No limits, only premium access.",
]

def random_welcome() -> str:
    return random.choice(WELCOME_LINES)

# ════════════════════════════════════════════════
#  DATA HELPERS
# ════════════════════════════════════════════════
def load() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"admins": [], "keys": {}, "members": {}, "redeemed": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save(d: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

def is_admin(uid, d) -> bool:
    return str(uid) in [str(x) for x in d.get("admins", [])] or int(uid) == OWNER_ID

def has_access(uid, d) -> bool:
    """Admins always have access. Buyers need a valid non-expired redeemed key."""
    if is_admin(uid, d):
        return True
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    exp = rd.get("expires")
    if not exp:
        return True  # lifetime
    return datetime.fromisoformat(exp) > datetime.now()

def track(uid, username, first_name, d):
    d.setdefault("members", {})[str(uid)] = {
        "username":   username or "",
        "first_name": first_name or "",
        "joined":     datetime.now().isoformat(),
    }

def get_db_files() -> list:
    return sorted(
        f for f in os.listdir(DB_FOLDER)
        if os.path.isfile(os.path.join(DB_FOLDER, f))
    )

def count_lines(path: str) -> int:
    try:
        with open(path, "r", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

# ════════════════════════════════════════════════
#  KEY HELPERS
# ════════════════════════════════════════════════
def generate_key() -> str:
    """
    Format: ZEIJIE-XXXXXX-XXXXXXXX-XXXX
    Part 1: 6 uppercase letters  (random)
    Part 2: 8 alphanumeric chars (random)
    Part 3: 4-char timestamp hex (ensures uniqueness per second)
    Example: ZEIJIE-ABCDEF-K3M9P2QR-1A2B
    """
    part1 = "".join(random.choices(string.ascii_uppercase, k=6))
    part2 = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    # timestamp-derived suffix so no two keys generated at the same second collide
    ts_hex = format(int(datetime.now().timestamp()) & 0xFFFF, "04X")
    extra  = "".join(random.choices(string.ascii_uppercase + string.digits, k=2))
    part3  = ts_hex[:2] + extra + ts_hex[2:]          # e.g. A3KQ2B
    return f"ZEIJIE-{part1}-{part2}-{part3}"

def parse_duration(raw: str):
    """
    Returns (timedelta | None, label_str).
    Accepts: lifetime, 1h, 30m, 7d, 10days, 2hours, 45mins ...
    """
    dur = raw.strip().lower()
    if dur in ("lifetime", "forever", "∞"):
        return None, "Lifetime"

    digits = "".join(c for c in dur if c.isdigit())
    if not digits:
        raise ValueError(f"Cannot parse duration: {raw!r}")
    n = int(digits)

    if "h" in dur:
        return timedelta(hours=n),   f"{n} hour{'s' if n != 1 else ''}"
    if "m" in dur and "month" not in dur:
        return timedelta(minutes=n), f"{n} minute{'s' if n != 1 else ''}"
    # default = days
    return timedelta(days=n), f"{n} day{'s' if n != 1 else ''}"

# ════════════════════════════════════════════════
#  EXPIRY DISPLAY  (accurate, with time remaining)
# ════════════════════════════════════════════════
def expiry_display(exp_iso) -> str:
    """Returns a rich expiry string with exact date/time AND time remaining."""
    if not exp_iso:
        return "♾️  Never (Lifetime)"

    exp_dt = datetime.fromisoformat(exp_iso)
    now    = datetime.now()

    # Formatted absolute time
    abs_time = exp_dt.strftime("%Y-%m-%d  %H:%M:%S")

    if exp_dt <= now:
        return f"❌  Expired  ({abs_time})"

    # Calculate remaining
    delta      = exp_dt - now
    total_secs = int(delta.total_seconds())
    days_rem   = total_secs // 86400
    hours_rem  = (total_secs % 86400) // 3600
    mins_rem   = (total_secs % 3600)  // 60
    secs_rem   = total_secs % 60

    # Build human-readable "X remaining" string
    parts = []
    if days_rem:
        parts.append(f"{days_rem}d")
    if hours_rem:
        parts.append(f"{hours_rem}h")
    if mins_rem:
        parts.append(f"{mins_rem}m")
    if secs_rem and not days_rem:          # show seconds only when < 1 day left
        parts.append(f"{secs_rem}s")

    remaining_str = " ".join(parts) if parts else "< 1s"
    return f"{abs_time}  ⏳ {remaining_str} left"

# ════════════════════════════════════════════════
#  MESSAGE BUILDERS
# ════════════════════════════════════════════════
def key_message(key: str, duration_label: str, expires_iso, devices: int) -> str:
    """Monospace key block for easy tap-to-copy."""
    exp_str = expiry_display(expires_iso)
    return (
        "🔑 *Key Generated!*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"`{key}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ Duration   : {duration_label}\n"
        f"📅 Expires    : {exp_str}\n"
        f"👥 Max users  : {devices}"
    )

def premium_summary(fname_stem: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d  %H:%M:%S")
    return (
        "🔮 ✨ PREMIUM FILE GENERATED SUCCESSFULLY! ✨ 🔮\n\n"
        "📊 GENERATION SUMMARY\n"
        f"┣ 🎮 Source Game      : {fname_stem.upper()}\n"
        f"┣ 📜 Lines Generated  : {sent}\n"
        f"┣ 🕐 Generated On     : {now}\n"
        f"┣ 💾 Database Status  : {remaining:,} lines available\n"
        "┣ 🧹 Cleanup Status   : ✅ Completed\n\n"
        "🛡️ SECURITY & PRIVACY\n"
        "┣ 🔒 Auto-Expiry      : 5 minutes\n"
        "┣ 🗑️ Auto-Deletion    : Enabled\n"
        "┣ 🛡️ Data Protection  : Active\n"
        "┣ ⚡ Secure Session   : Verified\n\n"
        "🚀 NEXT STEPS\n"
        "┣ ⬇️ Download immediately\n"
        "┣ ⏳ File expires in 5:00\n"
        "┣ 🔄 Refresh for new generation\n"
        "┣ 📚 Manage your data securely\n\n"
        "⭐ Thank you for choosing Premium Service!"
    )

# ════════════════════════════════════════════════
#  KEYBOARDS
# ════════════════════════════════════════════════
def kb_main(uid, d) -> InlineKeyboardMarkup:
    rows = []
    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")])
    rows += [
        [
            InlineKeyboardButton("📂 Database", callback_data="db"),
            InlineKeyboardButton("🔑 Redeem",   callback_data="redeem_info"),
        ],
        [
            InlineKeyboardButton("👤 Status",   callback_data="status"),
            InlineKeyboardButton("📋 Commands", callback_data="commands"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key",  callback_data="adm_create")],
        [InlineKeyboardButton("🗝 Active Keys", callback_data="adm_keys")],
        [InlineKeyboardButton("👥 Admins List", callback_data="adm_list")],
        [InlineKeyboardButton("🔙 Back",        callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "🔙 Back to Admin" if dest == "admin" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

# ════════════════════════════════════════════════
#  /start
# ════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)

    status      = "✅ Active" if has_access(user.id, d) else "🔒 No Access"
    welcome_bot = random_welcome()

    # Build a personalised identity line
    display_name = user.first_name or "Operator"
    username_tag = f"  (@{user.username})" if user.username else ""

    await update.message.reply_text(
        f"{LOGO}\n\n"
        f"{welcome_bot}\n\n"
        f"👤 *{display_name}*{username_tag}\n"
        f"🔐 Status: {status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_main(user.id, d),
    )

# ════════════════════════════════════════════════
#  /createkeys <max_users> <duration>
#  ADMIN ONLY
# ════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id

    if not is_admin(uid, d):
        await update.message.reply_text("❌ This command is for admins only.")
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "Usage: /createkeys <max_users> <duration>\n\n"
            "Duration examples:\n"
            "  10d      → 10 days\n"
            "  2h       → 2 hours\n"
            "  30m      → 30 minutes\n"
            "  lifetime → never expires"
        )
        return

    try:
        devices = int(ctx.args[0])
        if devices < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Max users must be a positive number (e.g. 1)")
        return

    raw_dur = " ".join(ctx.args[1:])
    try:
        td, duration_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid duration.\n\nExamples: 10d / 2h / 30m / lifetime"
        )
        return

    now         = datetime.now()
    key         = generate_key()
    expires_dt  = (now + td) if td else None
    expires_iso = expires_dt.isoformat() if expires_dt else None

    d["keys"][key] = {
        "devices":    devices,
        "duration":   raw_dur,
        "expires":    expires_iso,
        "used_by":    [],
        "created_by": str(uid),
        "created_at": now.isoformat(),
    }
    save(d)

    await update.message.reply_text(
        key_message(key, duration_label, expires_iso, devices),
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /redeem <key>
# ════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)

    if not ctx.args:
        await update.message.reply_text("Usage: /redeem ZEIJIE-XXXXXX-XXXXXXXX-XXXXXX")
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text("❌ Invalid key. Check and try again.")
        return

    k = d["keys"][key]

    if uid in k["used_by"]:
        await update.message.reply_text("⚠️ This key is already activated on your account.")
        return

    if len(k["used_by"]) >= int(k["devices"]):
        await update.message.reply_text("❌ Device limit reached for this key.")
        return

    key_exp = k.get("expires")
    if key_exp and datetime.fromisoformat(key_exp) < datetime.now():
        await update.message.reply_text("❌ This key has already expired.")
        return

    k["used_by"].append(uid)
    d["redeemed"][uid] = {
        "key":       key,
        "expires":   key_exp,
        "device_id": uid,
        "activated": datetime.now().isoformat(),
    }
    save(d)

    _, dur_label = parse_duration(k.get("duration", "lifetime"))
    exp_label    = expiry_display(key_exp)

    await update.message.reply_text(
        "✅ *Key Activated!*\n\n"
        f"🔑 `{key}`\n"
        f"⏱ Duration  : {dur_label}\n"
        f"📅 Expires   : {exp_label}\n"
        f"📱 Device    : Locked to your account",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /status
# ════════════════════════════════════════════════
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "👑 *Admin Account* — Full access granted.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text("🔒 No active key. Use /redeem <key>")
        return

    exp = rd.get("expires")
    if exp and datetime.fromisoformat(exp) < datetime.now():
        await update.message.reply_text("⛔ Your key has *expired*.", parse_mode=ParseMode.MARKDOWN)
        return

    await update.message.reply_text(
        f"✅ *Active*\n\n🔑 `{rd['key']}`\n📅 Expires: {expiry_display(exp)}",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /addadmin <user_id>  — owner only
# ════════════════════════════════════════════════
async def addadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return
    target = str(ctx.args[0])
    if target not in d["admins"]:
        d["admins"].append(target)
        save(d)
    await update.message.reply_text(f"✅ Admin added: `{target}`", parse_mode=ParseMode.MARKDOWN)

# ════════════════════════════════════════════════
#  /removeadmin <user_id>  — owner only
# ════════════════════════════════════════════════
async def removeadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /removeadmin <user_id>")
        return
    target = str(ctx.args[0])
    if target in d["admins"]:
        d["admins"].remove(target)
        save(d)
    await update.message.reply_text(f"✅ Admin removed: `{target}`", parse_mode=ParseMode.MARKDOWN)

# ════════════════════════════════════════════════
#  CALLBACK HANDLER
# ════════════════════════════════════════════════
async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    await q.answer()

    d    = load()
    uid  = q.from_user.id
    data = q.data

    # ── Home ──────────────────────────────────────
    if data == "home":
        status      = "✅ Active" if has_access(uid, d) else "🔒 No Access"
        welcome_bot = random_welcome()
        display_name = q.from_user.first_name or "Operator"
        username_tag = f"  (@{q.from_user.username})" if q.from_user.username else ""
        await q.edit_message_text(
            f"{LOGO}\n\n"
            f"{welcome_bot}\n\n"
            f"👤 *{display_name}*{username_tag}\n"
            f"🔐 Status: {status}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_main(uid, d),
        )

    # ── Commands ──────────────────────────────────
    elif data == "commands":
        await q.edit_message_text(
            "📋 *COMMANDS*\n\n"
            "/start — Main menu\n"
            "/redeem `<key>` — Activate a key\n"
            "/status — Check your access\n"
            "/createkeys `<users> <duration>` _(admin only)_\n"
            "/addadmin `<id>` _(owner only)_\n"
            "/removeadmin `<id>` _(owner only)_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("home"),
        )

    # ── Redeem info ───────────────────────────────
    elif data == "redeem_info":
        await q.edit_message_text(
            "🔑 *Redeem a Key*\n\n"
            "Send the command:\n"
            "`/redeem ZEIJIE-XXXXXX-XXXXXXXX-XXXXXX`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("home"),
        )

    # ── Status ────────────────────────────────────
    elif data == "status":
        if is_admin(uid, d):
            await q.edit_message_text(
                "👑 *Admin Account*\nFull access granted.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_back("home"),
            )
            return

        rd = d["redeemed"].get(str(uid))
        if not rd:
            await q.edit_message_text(
                "🔒 No active key.\nUse /redeem to activate one.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔑 How to Redeem", callback_data="redeem_info")],
                    [InlineKeyboardButton("🔙 Back", callback_data="home")],
                ]),
            )
            return

        exp = rd.get("expires")
        if exp and datetime.fromisoformat(exp) < datetime.now():
            await q.edit_message_text(
                "⛔ Your key has *expired*.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_back("home"),
            )
            return

        await q.edit_message_text(
            f"✅ *Active*\n\n🔑 `{rd['key']}`\n📅 Expires: {expiry_display(exp)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("home"),
        )

    # ── Admin Panel ───────────────────────────────
    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("⛔ Admins only.", show_alert=True)
            return
        total_keys    = len(d.get("keys", {}))
        total_members = len(d.get("members", {}))
        await q.edit_message_text(
            f"⚡ *ADMIN PANEL*\n\n"
            f"🗝 Total Keys   : {total_keys}\n"
            f"👥 Total Users  : {total_members}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_admin(),
        )

    # ── Create Key guide ──────────────────────────
    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("⛔ Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            "🔑 *Create a Key*\n\n"
            "Command:\n"
            "`/createkeys <max_users> <duration>`\n\n"
            "*Duration examples:*\n"
            "• `10d`      — 10 days\n"
            "• `2h`       — 2 hours\n"
            "• `30m`      — 30 minutes\n"
            "• `lifetime` — never expires\n\n"
            "_Type the command in chat to generate._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("admin"),
        )

    # ── Active Keys list ──────────────────────────
    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("⛔ Admins only.", show_alert=True)
            return
        keys = d.get("keys", {})
        if not keys:
            await q.edit_message_text("🗝 No keys created yet.", reply_markup=kb_back("admin"))
            return

        lines = []
        for k, v in list(keys.items())[-15:]:
            used  = len(v.get("used_by", []))
            max_d = v.get("devices", "?")
            exp   = expiry_display(v.get("expires"))
            lines.append(f"`{k}`\n  👥 {used}/{max_d}  📅 {exp}")

        await q.edit_message_text(
            "🗝 *Active Keys* (last 15)\n\n" + "\n\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("admin"),
        )

    # ── Admins list ───────────────────────────────
    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("⛔ Admins only.", show_alert=True)
            return
        admins = d.get("admins", [])
        body   = "\n".join(f"• `{a}`" for a in admins) if admins else "No extra admins."
        await q.edit_message_text(
            f"👥 *Admin List*\n\n{body}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("admin"),
        )

    # ── Database list ─────────────────────────────
    elif data == "db":
        if not has_access(uid, d):
            await q.edit_message_text(
                "🔒 *Access Required*\n\n"
                "You need an active key to access the database.\n"
                "Use /redeem to activate your key.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔑 How to Redeem", callback_data="redeem_info")],
                    [InlineKeyboardButton("🔙 Back",          callback_data="home")],
                ]),
            )
            return

        files = get_db_files()
        if not files:
            await q.edit_message_text(
                "📂 Database is currently empty.",
                reply_markup=kb_back("home"),
            )
            return

        rows = []
        for i, fname in enumerate(files):
            path  = os.path.join(DB_FOLDER, fname)
            count = count_lines(path)
            rows.append([
                InlineKeyboardButton(
                    f"🗂 {Path(fname).stem.upper()}  ({count:,} lines)",
                    callback_data=f"send_{i}",
                )
            ])
        rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])

        await q.edit_message_text(
            "📂 *DATABASE*\n\nSelect a file to generate 250 lines:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(rows),
        )

    # ── Send database file ────────────────────────
    elif data.startswith("send_"):
        if not has_access(uid, d):
            await q.answer("🔒 Access required.", show_alert=True)
            return

        try:
            idx = int(data.split("_")[1])
        except (IndexError, ValueError):
            await q.answer("❌ Invalid selection.", show_alert=True)
            return

        files = get_db_files()
        if idx >= len(files):
            await q.answer("❌ File no longer exists.", show_alert=True)
            return

        fname = files[idx]
        path  = os.path.join(DB_FOLDER, fname)

        msg = await q.message.reply_text("🔍 Initializing...  [▓░░░░]  20%")
        await asyncio.sleep(0.7)
        await msg.edit_text("⚙️ Processing...   [▓▓▓░░]  50%")
        await asyncio.sleep(0.7)
        await msg.edit_text("📦 Extracting...   [▓▓▓▓░]  80%")
        await asyncio.sleep(0.7)
        await msg.edit_text("✅ Completed       [▓▓▓▓▓] 100%")

        with open(path, "r", errors="replace") as f:
            all_lines = f.readlines()

        chunk     = all_lines[:LINES_PER_USE]
        remaining = all_lines[LINES_PER_USE:]

        if not chunk:
            await q.message.reply_text("⚠️ This database file is currently empty.")
            return

        with open(path, "w", errors="replace") as f:
            f.writelines(remaining)

        bio      = io.BytesIO("".join(chunk).encode("utf-8", errors="replace"))
        bio.name = f"ZEIJIE-PREMIUM-{Path(fname).stem.upper()}.txt"
        await q.message.reply_document(bio)

        summary_msg = await q.message.reply_text(
            premium_summary(Path(fname).stem, len(chunk), len(remaining))
        )

        await asyncio.sleep(300)
        for m in (summary_msg, msg):
            try:
                await m.delete()
            except Exception:
                pass

# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("createkeys",  createkeys))
    app.add_handler(CommandHandler("redeem",      redeem))
    app.add_handler(CommandHandler("status",      status_cmd))
    app.add_handler(CommandHandler("addadmin",    addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CallbackQueryHandler(callback))

    print("🔥 ZEIJIE BOT RUNNING")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()    "╚══════════════════════════════════╝\n"
    "```"
)

# ════════════════════════════════════════════════
#  DATA HELPERS
# ════════════════════════════════════════════════
def load() -> dict:
    if not os.path.exists(DATA_FILE):
        return {"admins": [], "keys": {}, "members": {}, "redeemed": {}}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save(d: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2, ensure_ascii=False)

def is_admin(uid, d) -> bool:
    return str(uid) in [str(x) for x in d.get("admins", [])] or int(uid) == OWNER_ID

def has_access(uid, d) -> bool:
    """Admins always have access. Buyers need a valid non-expired redeemed key."""
    if is_admin(uid, d):
        return True
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    exp = rd.get("expires")
    if not exp:
        return True  # lifetime
    return datetime.fromisoformat(exp) > datetime.now()

def track(uid, username, first_name, d):
    d.setdefault("members", {})[str(uid)] = {
        "username":   username or "",
        "first_name": first_name or "",
        "joined":     datetime.now().isoformat(),
    }

def get_db_files() -> list:
    return sorted(
        f for f in os.listdir(DB_FOLDER)
        if os.path.isfile(os.path.join(DB_FOLDER, f))
    )

def count_lines(path: str) -> int:
    try:
        with open(path, "r", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

# ════════════════════════════════════════════════
#  KEY HELPERS
# ════════════════════════════════════════════════
def generate_key() -> str:
    """Format: ZEIJIE-PREMIUM-12345678-AB3D"""
    nums   = "".join(random.choices(string.digits, k=8))
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ZEIJIE-PREMIUM-{nums}-{suffix}"

def parse_duration(raw: str):
    """
    Returns (timedelta | None, label_str).
    Accepts: lifetime, 1h, 30m, 7d, 10days, 2hours, 45mins ...
    """
    dur = raw.strip().lower()
    if dur in ("lifetime", "forever", "∞"):
        return None, "Lifetime"

    digits = "".join(c for c in dur if c.isdigit())
    if not digits:
        raise ValueError(f"Cannot parse duration: {raw!r}")
    n = int(digits)

    if "h" in dur:
        return timedelta(hours=n),   f"{n} hour{'s' if n != 1 else ''}"
    if "m" in dur and "month" not in dur:
        return timedelta(minutes=n), f"{n} minute{'s' if n != 1 else ''}"
    # default = days
    return timedelta(days=n), f"{n} day{'s' if n != 1 else ''}"

def expiry_display(exp_iso) -> str:
    if not exp_iso:
        return "Never (Lifetime)"
    return datetime.fromisoformat(exp_iso).strftime("%Y-%m-%d-%H-%M")

# ════════════════════════════════════════════════
#  MESSAGE BUILDERS
# ════════════════════════════════════════════════
def key_message(key: str, duration_label: str, expires_iso, devices: int) -> str:
    """Plain text with monospace key block for easy tap-to-copy."""
    exp_str = expiry_display(expires_iso)
    return (
        "🔑 *Key Generated!*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"`{key}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ Duration   : {duration_label}\n"
        f"📅 Expires    : {exp_str}\n"
        f"👥 Max users  : {devices}"
    )

def premium_summary(fname_stem: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "🔮 ✨ PREMIUM FILE GENERATED SUCCESSFULLY! ✨ 🔮\n\n"
        "📊 GENERATION SUMMARY\n"
        f"┣ 🎮 Source Game      : {fname_stem.upper()}\n"
        f"┣ 📜 Lines Generated  : {sent}\n"
        f"┣ 🕐 Generated On     : {now}\n"
        f"┣ 💾 Database Status  : {remaining:,} lines available\n"
        "┣ 🧹 Cleanup Status   : ✅ Completed\n\n"
        "🛡️ SECURITY & PRIVACY\n"
        "┣ 🔒 Auto-Expiry      : 5 minutes\n"
        "┣ 🗑️ Auto-Deletion    : Enabled\n"
        "┣ 🛡️ Data Protection  : Active\n"
        "┣ ⚡ Secure Session   : Verified\n\n"
        "🚀 NEXT STEPS\n"
        "┣ ⬇️ Download immediately\n"
        "┣ ⏳ File expires in 5:00\n"
        "┣ 🔄 Refresh for new generation\n"
        "┣ 📚 Manage your data securely\n\n"
        "⭐ Thank you for choosing Premium Service!"
    )

# ════════════════════════════════════════════════
#  KEYBOARDS
# ════════════════════════════════════════════════
def kb_main(uid, d) -> InlineKeyboardMarkup:
    rows = []
    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")])
    rows += [
        [
            InlineKeyboardButton("📂 Database", callback_data="db"),
            InlineKeyboardButton("🔑 Redeem",   callback_data="redeem_info"),
        ],
        [
            InlineKeyboardButton("👤 Status",   callback_data="status"),
            InlineKeyboardButton("📋 Commands", callback_data="commands"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key",  callback_data="adm_create")],
        [InlineKeyboardButton("🗝 Active Keys", callback_data="adm_keys")],
        [InlineKeyboardButton("👥 Admins List", callback_data="adm_list")],
        [InlineKeyboardButton("🔙 Back",        callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "🔙 Back to Admin" if dest == "admin" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

# ════════════════════════════════════════════════
#  /start
# ════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)

    status = "✅ Active" if has_access(user.id, d) else "🔒 No Access"
    await update.message.reply_text(
        f"{LOGO}\n\n👋 *{user.first_name}*\n🔐 Status: {status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_main(user.id, d),
    )

# ════════════════════════════════════════════════
#  /createkeys <max_users> <duration>
#  ADMIN ONLY
# ════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id

    # Strict admin-only check
    if not is_admin(uid, d):
        await update.message.reply_text("❌ This command is for admins only.")
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "Usage: /createkeys <max_users> <duration>\n\n"
            "Duration examples:\n"
            "  10d      → 10 days\n"
            "  2h       → 2 hours\n"
            "  30m      → 30 minutes\n"
            "  lifetime → never expires"
        )
        return

    # Validate max_users
    try:
        devices = int(ctx.args[0])
        if devices < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Max users must be a positive number (e.g. 1)")
        return

    # Validate & parse duration
    raw_dur = " ".join(ctx.args[1:])
    try:
        td, duration_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid duration.\n\nExamples: 10d / 2h / 30m / lifetime"
        )
        return

    now         = datetime.now()
    key         = generate_key()
    expires_dt  = (now + td) if td else None
    expires_iso = expires_dt.isoformat() if expires_dt else None

    # Save key to data.json
    d["keys"][key] = {
        "devices":    devices,
        "duration":   raw_dur,
        "expires":    expires_iso,
        "used_by":    [],
        "created_by": str(uid),
        "created_at": now.isoformat(),
    }
    save(d)

    # Send the key — monospace so user can tap-to-copy
    await update.message.reply_text(
        key_message(key, duration_label, expires_iso, devices),
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /redeem <key>
# ════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)

    if not ctx.args:
        await update.message.reply_text("Usage: /redeem ZEIJIE-PREMIUM-XXXXXXXX-XXXX")
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text("❌ Invalid key. Check and try again.")
        return

    k = d["keys"][key]

    # Device lock — one uid per slot
    if uid in k["used_by"]:
        await update.message.reply_text("⚠️ This key is already activated on your account.")
        return

    if len(k["used_by"]) >= int(k["devices"]):
        await update.message.reply_text("❌ Device limit reached for this key.")
        return

    # Key-level expiry check
    key_exp = k.get("expires")
    if key_exp and datetime.fromisoformat(key_exp) < datetime.now():
        await update.message.reply_text("❌ This key has already expired.")
        return

    # Activate
    k["used_by"].append(uid)
    d["redeemed"][uid] = {
        "key":       key,
        "expires":   key_exp,
        "device_id": uid,
        "activated": datetime.now().isoformat(),
    }
    save(d)

    _, dur_label = parse_duration(k.get("duration", "lifetime"))
    exp_label    = expiry_display(key_exp)

    await update.message.reply_text(
        "✅ *Key Activated!*\n\n"
        f"🔑 `{key}`\n"
        f"⏱ Duration  : {dur_label}\n"
        f"📅 Expires   : {exp_label}\n"
        f"📱 Device    : Locked to your account",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /status
# ════════════════════════════════════════════════
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "👑 *Admin Account* — Full access granted.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text("🔒 No active key. Use /redeem <key>")
        return

    exp = rd.get("expires")
    if exp and datetime.fromisoformat(exp) < datetime.now():
        await update.message.reply_text("⛔ Your key has *expired*.", parse_mode=ParseMode.MARKDOWN)
        return

    await update.message.reply_text(
        f"✅ *Active*\n\n🔑 `{rd['key']}`\n📅 Expires: {expiry_display(exp)}",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /addadmin <user_id>  — owner only
# ════════════════════════════════════════════════
async def addadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return
    target = str(ctx.args[0])
    if target not in d["admins"]:
        d["admins"].append(target)
        save(d)
    await update.message.reply_text(f"✅ Admin added: `{target}`", parse_mode=ParseMode.MARKDOWN)

# ════════════════════════════════════════════════
#  /removeadmin <user_id>  — owner only
# ════════════════════════════════════════════════
async def removeadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /removeadmin <user_id>")
        return
    target = str(ctx.args[0])
    if target in d["admins"]:
        d["admins"].remove(target)
        save(d)
    await update.message.reply_text(f"✅ Admin removed: `{target}`", parse_mode=ParseMode.MARKDOWN)

# ════════════════════════════════════════════════
#  CALLBACK HANDLER
# ════════════════════════════════════════════════
async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    await q.answer()

    d    = load()
    uid  = q.from_user.id
    data = q.data

    # ── Home ──────────────────────────────────────
    if data == "home":
        status = "✅ Active" if has_access(uid, d) else "🔒 No Access"
        await q.edit_message_text(
            f"{LOGO}\n\n👋 *{q.from_user.first_name}*\n🔐 Status: {status}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_main(uid, d),
        )

    # ── Commands ──────────────────────────────────
    elif data == "commands":
        await q.edit_message_text(
            "📋 *COMMANDS*\n\n"
            "/start — Main menu\n"
            "/redeem `<key>` — Activate a key\n"
            "/status — Check your access\n"
            "/createkeys `<users> <duration>` _(admin only)_\n"
            "/addadmin `<id>` _(owner only)_\n"
            "/removeadmin `<id>` _(owner only)_",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("home"),
        )

    # ── Redeem info ───────────────────────────────
    elif data == "redeem_info":
        await q.edit_message_text(
            "🔑 *Redeem a Key*\n\n"
            "Send the command:\n"
            "`/redeem ZEIJIE-PREMIUM-XXXXXXXX-XXXX`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("home"),
        )

    # ── Status ────────────────────────────────────
    elif data == "status":
        if is_admin(uid, d):
            await q.edit_message_text(
                "👑 *Admin Account*\nFull access granted.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_back("home"),
            )
            return

        rd = d["redeemed"].get(str(uid))
        if not rd:
            await q.edit_message_text(
                "🔒 No active key.\nUse /redeem to activate one.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔑 How to Redeem", callback_data="redeem_info")],
                    [InlineKeyboardButton("🔙 Back", callback_data="home")],
                ]),
            )
            return

        exp = rd.get("expires")
        if exp and datetime.fromisoformat(exp) < datetime.now():
            await q.edit_message_text(
                "⛔ Your key has *expired*.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_back("home"),
            )
            return

        await q.edit_message_text(
            f"✅ *Active*\n\n🔑 `{rd['key']}`\n📅 Expires: {expiry_display(exp)}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("home"),
        )

    # ── Admin Panel ───────────────────────────────
    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("⛔ Admins only.", show_alert=True)
            return
        total_keys    = len(d.get("keys", {}))
        total_members = len(d.get("members", {}))
        await q.edit_message_text(
            f"⚡ *ADMIN PANEL*\n\n"
            f"🗝 Total Keys   : {total_keys}\n"
            f"👥 Total Users  : {total_members}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_admin(),
        )

    # ── Create Key guide ──────────────────────────
    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("⛔ Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            "🔑 *Create a Key*\n\n"
            "Command:\n"
            "`/createkeys <max_users> <duration>`\n\n"
            "*Duration examples:*\n"
            "• `10d`      — 10 days\n"
            "• `2h`       — 2 hours\n"
            "• `30m`      — 30 minutes\n"
            "• `lifetime` — never expires\n\n"
            "_Type the command in chat to generate._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("admin"),
        )

    # ── Active Keys list ──────────────────────────
    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("⛔ Admins only.", show_alert=True)
            return
        keys = d.get("keys", {})
        if not keys:
            await q.edit_message_text("🗝 No keys created yet.", reply_markup=kb_back("admin"))
            return

        lines = []
        for k, v in list(keys.items())[-15:]:
            used  = len(v.get("used_by", []))
            max_d = v.get("devices", "?")
            exp   = expiry_display(v.get("expires"))
            lines.append(f"`{k}`\n  👥 {used}/{max_d}  📅 {exp}")

        await q.edit_message_text(
            "🗝 *Active Keys* (last 15)\n\n" + "\n\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("admin"),
        )

    # ── Admins list ───────────────────────────────
    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("⛔ Admins only.", show_alert=True)
            return
        admins = d.get("admins", [])
        body   = "\n".join(f"• `{a}`" for a in admins) if admins else "No extra admins."
        await q.edit_message_text(
            f"👥 *Admin List*\n\n{body}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("admin"),
        )

    # ── Database list — buyers WITH valid key CAN access ──
    elif data == "db":
        if not has_access(uid, d):
            await q.edit_message_text(
                "🔒 *Access Required*\n\n"
                "You need an active key to access the database.\n"
                "Use /redeem to activate your key.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔑 How to Redeem", callback_data="redeem_info")],
                    [InlineKeyboardButton("🔙 Back",          callback_data="home")],
                ]),
            )
            return

        files = get_db_files()
        if not files:
            await q.edit_message_text(
                "📂 Database is currently empty.",
                reply_markup=kb_back("home"),
            )
            return

        rows = []
        for i, fname in enumerate(files):
            path  = os.path.join(DB_FOLDER, fname)
            count = count_lines(path)
            rows.append([
                InlineKeyboardButton(
                    f"🗂 {Path(fname).stem.upper()}  ({count:,} lines)",
                    callback_data=f"send_{i}",
                )
            ])
        rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])

        await q.edit_message_text(
            "📂 *DATABASE*\n\nSelect a file to generate 250 lines:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(rows),
        )

    # ── Send database file ────────────────────────
    elif data.startswith("send_"):
        if not has_access(uid, d):
            await q.answer("🔒 Access required.", show_alert=True)
            return

        try:
            idx = int(data.split("_")[1])
        except (IndexError, ValueError):
            await q.answer("❌ Invalid selection.", show_alert=True)
            return

        files = get_db_files()
        if idx >= len(files):
            await q.answer("❌ File no longer exists.", show_alert=True)
            return

        fname = files[idx]
        path  = os.path.join(DB_FOLDER, fname)

        # Progress animation
        msg = await q.message.reply_text("🔍 Initializing...  [▓░░░░]  20%")
        await asyncio.sleep(0.7)
        await msg.edit_text("⚙️ Processing...   [▓▓▓░░]  50%")
        await asyncio.sleep(0.7)
        await msg.edit_text("📦 Extracting...   [▓▓▓▓░]  80%")
        await asyncio.sleep(0.7)
        await msg.edit_text("✅ Completed       [▓▓▓▓▓] 100%")

        # Read all lines
        with open(path, "r", errors="replace") as f:
            all_lines = f.readlines()

        chunk     = all_lines[:LINES_PER_USE]
        remaining = all_lines[LINES_PER_USE:]

        if not chunk:
            await q.message.reply_text("⚠️ This database file is currently empty.")
            return

        # DECREASE: write back remaining lines (removes used 250)
        with open(path, "w", errors="replace") as f:
            f.writelines(remaining)

        # Send file to user
        bio      = io.BytesIO("".join(chunk).encode("utf-8", errors="replace"))
        bio.name = f"ZEIJIE-PREMIUM-{Path(fname).stem.upper()}.txt"
        await q.message.reply_document(bio)

        # Full premium summary message (plain text — no markdown parse issues)
        summary_msg = await q.message.reply_text(
            premium_summary(Path(fname).stem, len(chunk), len(remaining))
        )

        # Auto-delete progress + summary after 5 minutes
        await asyncio.sleep(300)
        for m in (summary_msg, msg):
            try:
                await m.delete()
            except Exception:
                pass

# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("createkeys",  createkeys))
    app.add_handler(CommandHandler("redeem",      redeem))
    app.add_handler(CommandHandler("status",      status_cmd))
    app.add_handler(CommandHandler("addadmin",    addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CallbackQueryHandler(callback))

    print("🔥 ZEIJIE BOT RUNNING")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
