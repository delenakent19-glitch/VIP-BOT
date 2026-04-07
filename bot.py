#!/usr/bin/env python3
"""
╔══════════════════════════════════════╗
║        ZEIJIE VIP PREMIUM BOT        ║
║         by @Zeijie_s                 ║
╚══════════════════════════════════════╝
"""

import os, json, random, string, io, asyncio, logging, base64
from datetime import datetime, timedelta
from pathlib import Path

import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════
#  CONFIG  <- fill in your values before running
# ══════════════════════════════════════════════════════
BOT_TOKEN     = "8797773644:AAEqK3MGZOu2mQRAJKJZjnW7XRmThbbDiZA"   # from @BotFather
OWNER_ID      = 8420104044                       # your Telegram numeric ID
CONTACT_ADMIN = "@Zeijie_s"

DATA_FILE     = "data.json"
DB_FOLDER     = "database"
LINES_PER_USE = 250
OUTPUT_PREFIX = "ZEIJIE-VIP-PREMIUM"

# GitHub sync — leave blank ("") to disable
GITHUB_TOKEN  = "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"      # e.g. "ghp_xxxxxxxxxxxx"
GITHUB_REPO   = "https://github.com/delenakent19-glitch/VIP-BOT"      # "username/repo-name"  — NOT the full URL
GITHUB_BRANCH = "main"

# All file extensions accepted as database files
DB_SUPPORTED_EXTS = {
    ".txt", ".csv", ".log", ".combo",
    ".list", ".dat", ".text", ".conf",
}

os.makedirs(DB_FOLDER, exist_ok=True)

# ══════════════════════════════════════════════════════
#  LOGO  (plain text, no markdown)
# ══════════════════════════════════════════════════════
LOGO = (
    "╔══════════════════════════════════╗\n"
    "║  ZEIJIE  VIP  PREMIUM  BOT       ║\n"
    "║    ✦  V I P  P R E M I U M  ✦   ║\n"
    "║         by @Zeijie_s             ║\n"
    "╚══════════════════════════════════╝"
)

WELCOME_LINES = [
    "⚡ ZEIJIE BOT — locked, loaded, and ready.",
    "🔥 Welcome to ZEIJIE BOT — your premium gateway.",
    "🌐 ZEIJIE BOT online — Precision · Power · Premium.",
    "🛡 ZEIJIE BOT activated — built different, built better.",
    "💎 You've entered ZEIJIE BOT — where premium lives.",
    "🚀 ZEIJIE BOT is live — Let's get to work.",
    "🎯 ZEIJIE BOT standing by — the real deal starts here.",
    "👾 ZEIJIE BOT loaded — No limits, only premium access.",
]

# ══════════════════════════════════════════════════════
#  GITHUB SYNC
# ══════════════════════════════════════════════════════
GH_BASE = "https://api.github.com"

def _gh_headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

def _gh_repo() -> str:
    """Accept both 'user/repo' and full GitHub URL."""
    r = GITHUB_REPO.strip()
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if r.startswith(prefix):
            r = r[len(prefix):]
    return r.rstrip("/")

async def github_push_file(repo_path: str, local_path: str):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    repo = _gh_repo()
    try:
        with open(local_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode()
        url = f"{GH_BASE}/repos/{repo}/contents/{repo_path}"
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=_gh_headers(),
                                    params={"ref": GITHUB_BRANCH})
            sha  = resp.json().get("sha") if resp.status_code == 200 else None
            payload: dict = {
                "message": f"auto-update {repo_path}",
                "content": content_b64,
                "branch":  GITHUB_BRANCH,
            }
            if sha:
                payload["sha"] = sha
            r2 = await client.put(url, headers=_gh_headers(), json=payload)
            if r2.status_code in (200, 201):
                logger.info("GH push OK: %s", repo_path)
            else:
                logger.warning("GH push failed %s: %s", repo_path, r2.text[:200])
    except Exception as e:
        logger.error("GH push error: %s", e)

async def github_pull_file(repo_path: str, local_path: str):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    repo = _gh_repo()
    try:
        url = f"{GH_BASE}/repos/{repo}/contents/{repo_path}"
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=_gh_headers(),
                                    params={"ref": GITHUB_BRANCH})
            if resp.status_code == 200:
                content = base64.b64decode(resp.json().get("content", ""))
                os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(content)
                logger.info("GH pull OK: %s", repo_path)
            else:
                logger.warning("GH pull skipped %s — status %s",
                               repo_path, resp.status_code)
    except Exception as e:
        logger.error("GH pull error: %s", e)

# ══════════════════════════════════════════════════════
#  DATA HELPERS
# ══════════════════════════════════════════════════════
_DEFAULT: dict = {
    "admins":   [],
    "keys":     {},
    "members":  {},
    "redeemed": {},
    "db_names": {},
}

def load() -> dict:
    if not os.path.exists(DATA_FILE):
        _write_default()
        return _DEFAULT.copy()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        for k, v in _DEFAULT.items():
            d.setdefault(k, v)
        return d
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("data.json load failed (%s) — resetting.", e)
        _write_default()
        return _DEFAULT.copy()

def _write_default():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(_DEFAULT, f, indent=2)
    except OSError as e:
        logger.error("Could not create data.json: %s", e)

def save(d: dict):
    tmp = DATA_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)
    except OSError as e:
        logger.error("Save failed: %s", e)

def save_push(d: dict):
    save(d)
    asyncio.create_task(github_push_file("data.json", DATA_FILE))

def track(uid, username, first_name, d):
    d.setdefault("members", {})[str(uid)] = {
        "username":   username or "",
        "first_name": first_name or "",
        "last_seen":  datetime.now().isoformat(),
    }

# ══════════════════════════════════════════════════════
#  PERMISSION HELPERS
# ══════════════════════════════════════════════════════
def is_owner(uid) -> bool:
    return int(uid) == OWNER_ID

def is_admin(uid, d: dict) -> bool:
    return is_owner(uid) or str(uid) in [str(x) for x in d.get("admins", [])]

def is_expired(rd: dict) -> bool:
    exp = rd.get("expires")
    if not exp:
        return False
    try:
        return datetime.fromisoformat(exp) <= datetime.now()
    except ValueError:
        return False

def has_access(uid, d: dict) -> bool:
    if is_admin(uid, d):
        return True
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    return not is_expired(rd)

# ══════════════════════════════════════════════════════
#  DATABASE FILE HELPERS
# ══════════════════════════════════════════════════════
def get_db_files() -> list:
    try:
        return sorted(
            f for f in os.listdir(DB_FOLDER)
            if os.path.isfile(os.path.join(DB_FOLDER, f))
            and Path(f).suffix.lower() in DB_SUPPORTED_EXTS
        )
    except FileNotFoundError:
        os.makedirs(DB_FOLDER, exist_ok=True)
        return []

def count_lines(path: str) -> int:
    try:
        with open(path, "r", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def get_display_name(fname: str, d: dict) -> str:
    return d.get("db_names", {}).get(fname, Path(fname).stem)

def consume_lines(fpath: str, n: int) -> tuple:
    with open(fpath, "r", errors="ignore") as f:
        all_lines = f.readlines()
    to_send  = all_lines[:n]
    leftover = all_lines[n:]
    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(leftover)
    return "".join(to_send), len(leftover)

# ══════════════════════════════════════════════════════
#  KEY HELPERS
# ══════════════════════════════════════════════════════
def generate_key() -> str:
    return "ZEIJIE-PREMIUM-" + "".join(random.choices(string.digits, k=4))

def generate_bulk_keys(prefix: str, count: int) -> list:
    keys, used = [], set()
    while len(keys) < count:
        num = "".join(random.choices(string.digits, k=6))
        if num not in used:
            used.add(num)
            keys.append(f"{prefix}-{num}")
    return keys

def parse_duration(raw: str):
    dur = raw.strip().lower()
    if dur in ("lifetime", "forever", "inf"):
        return None, "Lifetime"
    digits = "".join(c for c in dur if c.isdigit())
    if not digits:
        raise ValueError(f"Cannot parse: {raw!r}")
    n = int(digits)
    if "h" in dur:
        return timedelta(hours=n),   f"{n} hour{'s' if n!=1 else ''}"
    if "m" in dur and "month" not in dur:
        return timedelta(minutes=n), f"{n} minute{'s' if n!=1 else ''}"
    return timedelta(days=n), f"{n} day{'s' if n!=1 else ''}"

def expiry_display(exp_iso) -> str:
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
    delta = exp_dt - now
    secs  = int(delta.total_seconds())
    d2, r = divmod(secs, 86400)
    h,  r = divmod(r, 3600)
    m,  s = divmod(r, 60)
    parts = []
    if d2: parts.append(f"{d2}d")
    if h:  parts.append(f"{h}h")
    if m:  parts.append(f"{m}m")
    if s and not d2: parts.append(f"{s}s")
    return f"{abs_time}  ({''.join(parts) or '< 1s'} left)"

# ══════════════════════════════════════════════════════
#  OUTPUT HELPERS
# ══════════════════════════════════════════════════════
def output_filename(disp: str) -> str:
    return f"{OUTPUT_PREFIX}-{disp.upper().replace(' ','_')}.txt"

def file_header(disp: str, lines: int) -> str:
    sep = "=" * 38
    return (
        f"ZEIJIE Premium Database\n{sep}\n"
        f"Source    : {disp.upper()}\n"
        f"Lines     : {lines}\n"
        f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{sep}\n\n"
    )

# ══════════════════════════════════════════════════════
#  AUTO-DELETE
# ══════════════════════════════════════════════════════
async def _auto_delete(delay: int, *msgs):
    await asyncio.sleep(delay)
    for m in msgs:
        try:
            await m.delete()
        except Exception:
            pass

# ══════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════
def kb_main(uid, d) -> InlineKeyboardMarkup:
    rows = []
    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")])
    rows += [
        [
            InlineKeyboardButton("📂 Database",   callback_data="db"),
            InlineKeyboardButton("🔑 Redeem Key", callback_data="redeem_info"),
        ],
        [
            InlineKeyboardButton("👤 My Status",  callback_data="status"),
            InlineKeyboardButton("📋 Commands",   callback_data="commands"),
        ],
        [InlineKeyboardButton("📞 Contact Admin",
                              url=f"https://t.me/{CONTACT_ADMIN.lstrip('@')}")],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key",  callback_data="adm_create")],
        [InlineKeyboardButton("🎉 Bulk Keys",   callback_data="adm_bulk_info")],
        [InlineKeyboardButton("🗝 Active Keys", callback_data="adm_keys")],
        [InlineKeyboardButton("👥 Admins List", callback_data="adm_list")],
        [InlineKeyboardButton("👥 All Members", callback_data="adm_members")],
        [InlineKeyboardButton("🔙 Back",        callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "Back to Admin" if dest == "admin" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

def kb_db_files(files: list, d: dict) -> InlineKeyboardMarkup:
    rows = []
    for fname in files:
        cnt  = count_lines(os.path.join(DB_FOLDER, fname))
        disp = get_display_name(fname, d)
        rows.append([InlineKeyboardButton(
            f"📄 {disp}  ({cnt:,} lines)", callback_data=f"dbfile:{fname}"
        )])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def kb_contact() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Contact Admin",
                              url=f"https://t.me/{CONTACT_ADMIN.lstrip('@')}")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")],
    ])

# ══════════════════════════════════════════════════════
#  WELCOME TEXT  (plain text only)
# ══════════════════════════════════════════════════════
ACCESS_DENIED = (
    "Access Denied\n\n"
    "You do not have access.\n"
    f"Contact admin to get a key: {CONTACT_ADMIN}"
)

def build_welcome(first_name, username, uid, d) -> str:
    status    = "Active" if has_access(uid, d) else "No Access"
    line      = random.choice(WELCOME_LINES)
    name      = first_name or "Operator"
    user_line = f"User: {name}"
    if username:
        user_line += f"  (@{username})"
    return (
        f"{LOGO}\n\n"
        f"{line}\n\n"
        f"{user_line}\n"
        f"Status  : {status}\n"
        f"Support : {CONTACT_ADMIN}"
    )

# ══════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    await update.message.reply_text(
        build_welcome(user.first_name, user.username, user.id, d),
        reply_markup=kb_main(user.id, d),
    )

# ══════════════════════════════════════════════════════
#  /help  — role-aware: buyers never see admin commands
# ══════════════════════════════════════════════════════
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id

    user_cmds = (
        "Your Commands\n"
        "--------------\n"
        "/start     - Main menu\n"
        "/redeem    - Activate a VIP key\n"
        "/status    - Check your access status\n"
        "/help      - Show this message\n"
    )
    admin_cmds = (
        "\nAdmin Commands\n"
        "--------------\n"
        "/createkeys  <users> <dur>   - Create key\n"
        "/bulkkeys    <prefix> <n> <dur> - Bulk keys\n"
        "/revokekey   <key>           - Delete a key\n"
        "/customname  <file> <name>   - Set DB display name\n"
        "/syncgithub                  - Pull from GitHub\n"
        "/addadmin    <id>            - Add admin (owner only)\n"
        "/removeadmin <id>            - Remove admin (owner only)\n"
    )

    text = user_cmds + (admin_cmds if is_admin(uid, d) else "")
    await update.message.reply_text(text)

# ══════════════════════════════════════════════════════
#  /redeem <key>
# ══════════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if not ctx.args:
        await update.message.reply_text(
            "Usage: /redeem ZEIJIE-PREMIUM-XXXX\n\n"
            f"No key? Contact: {CONTACT_ADMIN}"
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text(
            "Invalid key. Check and try again.\n\n"
            f"Contact: {CONTACT_ADMIN}"
        )
        return

    k = d["keys"][key]

    if uid in k.get("used_by", []):
        await update.message.reply_text(
            "This key is already activated on your account."
        )
        return

    if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
        await update.message.reply_text(
            f"Device limit reached.\n\nContact: {CONTACT_ADMIN}"
        )
        return

    raw_dur = k.get("duration", "lifetime")
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        td, dur_label = None, raw_dur

    now         = datetime.now()
    expires_dt  = (now + td) if td else None
    expires_iso = expires_dt.isoformat() if expires_dt else None

    k.setdefault("used_by", []).append(uid)
    k.setdefault("user_expiry", {})[uid] = expires_iso
    d["redeemed"][uid] = {
        "key":       key,
        "duration":  raw_dur,
        "expires":   expires_iso,
        "activated": now.isoformat(),
    }
    save_push(d)

    await update.message.reply_text(
        "KEY ACTIVATED\n"
        "=============\n\n"
        f"Key      : {key}\n"
        f"Duration : {dur_label}\n"
        f"Expires  : {expiry_display(expires_iso)}\n"
        f"Device   : Locked to your account\n\n"
        "Your access timer has started."
    )

# ══════════════════════════════════════════════════════
#  /status
# ══════════════════════════════════════════════════════
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "Admin Account\nFull access — no key needed."
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            "No Active Key\n\n"
            "Use /redeem <key> to activate access.\n\n"
            f"Contact: {CONTACT_ADMIN}"
        )
        return

    exp     = rd.get("expires")
    expired = is_expired(rd)
    act     = rd.get("activated", "Unknown")

    if expired:
        await update.message.reply_text(
            "Access Expired\n\n"
            f"Key     : {rd['key']}\n"
            f"Expired : {expiry_display(exp)}\n\n"
            f"Contact: {CONTACT_ADMIN}"
        )
    else:
        await update.message.reply_text(
            "Access Active\n\n"
            f"Key      : {rd['key']}\n"
            f"Duration : {rd.get('duration', 'N/A')}\n"
            f"Started  : {act[:19]}\n"
            f"Expires  : {expiry_display(exp)}"
        )

# ══════════════════════════════════════════════════════
#  ADMIN: /createkeys <max_users> <duration>
# ══════════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(ACCESS_DENIED,
                                        reply_markup=kb_contact())
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "Usage: /createkeys <max_users> <duration>\n\n"
            "Examples:\n"
            "  /createkeys 1 7d\n"
            "  /createkeys 3 lifetime\n\n"
            "Timer starts when buyer redeems."
        )
        return

    try:
        devices = int(ctx.args[0])
        if devices < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Max users must be a positive integer.")
        return

    raw_dur = " ".join(ctx.args[1:])
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "Invalid duration. Use: 10d / 2h / 30m / lifetime"
        )
        return

    key = generate_key()
    d["keys"][key] = {
        "devices":     devices,
        "duration":    raw_dur,
        "used_by":     [],
        "user_expiry": {},
        "created_by":  str(uid),
        "created_at":  datetime.now().isoformat(),
    }
    save_push(d)

    await update.message.reply_text(
        "KEY GENERATED\n"
        "=============\n\n"
        f"{key}\n\n"
        f"Duration  : {dur_label}\n"
        f"Max Users : {devices}\n\n"
        "Timer starts when buyer redeems."
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /bulkkeys <prefix> <count> <duration>
# ══════════════════════════════════════════════════════
async def bulkkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(ACCESS_DENIED,
                                        reply_markup=kb_contact())
        return

    if len(ctx.args) < 3:
        await update.message.reply_text(
            "Usage: /bulkkeys <prefix> <count> <duration>\n\n"
            "Example: /bulkkeys ZEIJIE 5 1d\n\n"
            "Each key is one-time use."
        )
        return

    prefix = ctx.args[0].strip()
    try:
        count = int(ctx.args[1])
        if not 1 <= count <= 50:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Count must be 1 to 50.")
        return

    raw_dur = " ".join(ctx.args[2:])
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "Invalid duration. Use: 10d / 2h / 30m / lifetime"
        )
        return

    keys    = generate_bulk_keys(prefix, count)
    now_iso = datetime.now().isoformat()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for k in keys:
        d["keys"][k] = {
            "devices":     1,
            "duration":    raw_dur,
            "used_by":     [],
            "user_expiry": {},
            "created_by":  str(uid),
            "created_at":  now_iso,
        }
    save_push(d)

    keys_display = "\n".join(keys)
    await update.message.reply_text(
        f"{count} Keys Generated\n"
        "==================\n\n"
        f"{keys_display}\n\n"
        f"Validity : {dur_label}\n"
        f"Created  : {now_str}"
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /revokekey <key>
# ══════════════════════════════════════════════════════
async def revokekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("Admins only.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /revokekey <KEY>")
        return
    key = ctx.args[0].strip().upper()
    if key not in d["keys"]:
        await update.message.reply_text("Key not found.")
        return
    del d["keys"][key]
    d["redeemed"] = {u: v for u, v in d["redeemed"].items()
                     if v.get("key") != key}
    save_push(d)
    await update.message.reply_text(f"Key revoked: {key}")

# ══════════════════════════════════════════════════════
#  ADMIN: /customname <filename> <display name>
# ══════════════════════════════════════════════════════
async def customname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("Admins only.")
        return

    files = get_db_files()
    if len(ctx.args) < 2:
        listing = "\n".join(f"  {f}" for f in files) if files else "  None"
        await update.message.reply_text(
            "Usage: /customname <filename> <display name>\n\n"
            f"Available files:\n{listing}"
        )
        return

    fname     = ctx.args[0].strip()
    disp_name = " ".join(ctx.args[1:]).strip()
    fpath     = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        listing = "\n".join(f"  {f}" for f in files) if files else "  None"
        await update.message.reply_text(
            f"{fname} not found.\n\nAvailable:\n{listing}"
        )
        return

    d.setdefault("db_names", {})[fname] = disp_name
    save_push(d)
    await update.message.reply_text(
        f"Name set!\nFile : {fname}\nName : {disp_name}"
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /syncgithub
# ══════════════════════════════════════════════════════
async def syncgithub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("Admins only.")
        return
    if not GITHUB_TOKEN or not GITHUB_REPO:
        await update.message.reply_text(
            "GitHub not configured.\n"
            "Set GITHUB_TOKEN and GITHUB_REPO in the bot config."
        )
        return
    msg = await update.message.reply_text("Syncing from GitHub...")
    await github_pull_file("data.json", DATA_FILE)
    for fname in get_db_files():
        await github_pull_file(f"database/{fname}",
                               os.path.join(DB_FOLDER, fname))
    await msg.edit_text("Sync complete! Data pulled from GitHub.")

# ══════════════════════════════════════════════════════
#  OWNER: /addadmin  /removeadmin
# ══════════════════════════════════════════════════════
async def addadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Owner only.")
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return
    target = str(ctx.args[0])
    if target not in [str(a) for a in d["admins"]]:
        d["admins"].append(target)
        save_push(d)
    await update.message.reply_text(f"Admin added: {target}")

async def removeadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Owner only.")
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /removeadmin <user_id>")
        return
    target = str(ctx.args[0])
    if target in [str(a) for a in d["admins"]]:
        d["admins"] = [a for a in d["admins"] if str(a) != target]
        save_push(d)
        await update.message.reply_text(f"Removed: {target}")
    else:
        await update.message.reply_text(f"Not an admin: {target}")

# ══════════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════════
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    d    = load()
    uid  = q.from_user.id
    data = q.data
    track(uid, q.from_user.username, q.from_user.first_name, d)
    save(d)
    await q.answer()

    if data == "home":
        await q.edit_message_text(
            build_welcome(q.from_user.first_name, q.from_user.username, uid, d),
            reply_markup=kb_main(uid, d),
        )

    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            "Admin Panel\n\nChoose an option:",
            reply_markup=kb_admin(),
        )

    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            "Create Keys\n\n"
            "Single:\n  /createkeys <max_users> <duration>\n\n"
            "Bulk:\n  /bulkkeys <prefix> <count> <duration>\n\n"
            "Examples:\n"
            "  /createkeys 1 7d\n"
            "  /bulkkeys ZEIJIE 5 1d\n\n"
            "Timer starts when buyer redeems.",
            reply_markup=kb_back("admin"),
        )

    elif data == "adm_bulk_info":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            "Bulk Key Generator\n\n"
            "Command:\n  /bulkkeys <prefix> <count> <duration>\n\n"
            "Example:\n  /bulkkeys ZEIJIE 5 1d\n\n"
            "Each key is one-time use.",
            reply_markup=kb_back("admin"),
        )

    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        keys     = d.get("keys", {})
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})
        if not keys:
            txt = "No keys yet.\n\nUse /createkeys or /bulkkeys."
        else:
            lines = [f"All Keys ({len(keys)}):\n"]
            for k, v in keys.items():
                used_by  = v.get("used_by", [])
                devices  = v.get("devices", 1)
                raw_dur  = v.get("duration", "?")
                used_cnt = len(used_by)
                status   = ("Unused" if used_cnt == 0
                            else "Partial" if used_cnt < devices
                            else "Full")
                block = (
                    f"[{status}] {k}\n"
                    f"  Duration: {raw_dur}  Users: {used_cnt}/{devices}"
                )
                for u_id in used_by:
                    rd    = redeemed.get(str(u_id))
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    exp_s = expiry_display(rd["expires"]) if rd else "Unknown"
                    block += f"\n  - {label}: {exp_s}"
                lines.append(block)
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n... truncated"
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        admins = d.get("admins", [])
        txt = (
            "No extra admins." if not admins
            else "Admins:\n\n" + "\n".join(f"  {a}" for a in admins)
        )
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_members":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        members  = d.get("members", {})
        redeemed = d.get("redeemed", {})
        if not members:
            txt = "No members yet."
        else:
            lines = [f"Members ({len(members)}):\n"]
            for m_id, info in members.items():
                uname = info.get("username", "")
                fname = info.get("first_name", "")
                label = f"@{uname}" if uname else (fname or m_id)
                rd    = redeemed.get(m_id)
                acc   = "Active" if has_access(int(m_id), d) else "Expired"
                exp_s = expiry_display(rd["expires"]) if rd else "No key"
                lines.append(f"[{acc}] {label} (id:{m_id})\n  Expires: {exp_s}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n... truncated"
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "db":
        files = get_db_files()
        if not files:
            exts = ", ".join(sorted(DB_SUPPORTED_EXTS))
            await q.edit_message_text(
                "Database is empty.\n\n"
                f"Place files inside the database/ folder.\n"
                f"Supported types: {exts}",
                reply_markup=kb_back(),
            )
            return
        rows = [f"Database Files ({len(files)} found):\n"]
        for fname in files:
            cnt  = count_lines(os.path.join(DB_FOLDER, fname))
            disp = get_display_name(fname, d)
            rows.append(f"  {disp}  ({cnt:,} lines)")
        rows.append("\nTap a file below to download.")
        await q.edit_message_text(
            "\n".join(rows),
            reply_markup=kb_db_files(files, d),
        )

    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

        if not has_access(uid, d):
            await q.answer(
                "Access denied. Contact admin to get a key.",
                show_alert=True,
            )
            return

        fpath = os.path.join(DB_FOLDER, fname)
        if not os.path.isfile(fpath):
            await q.answer("File not found on server.", show_alert=True)
            return

        total = count_lines(fpath)
        if total == 0:
            await q.answer("Database exhausted. Contact admin.",
                           show_alert=True)
            return

        lines_to_send          = min(LINES_PER_USE, total)
        disp                   = get_display_name(fname, d)
        raw_content, remaining = consume_lines(fpath, lines_to_send)
        content                = file_header(disp, lines_to_send) + raw_content
        out_name               = output_filename(disp)
        buf                    = io.BytesIO(content.encode("utf-8"))
        buf.name               = out_name

        caption = (
            f"ZEIJIE Premium File\n\n"
            f"Source    : {disp.upper()}\n"
            f"Lines     : {lines_to_send:,}\n"
            f"Remaining : {remaining:,}\n"
            f"Time      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            "File auto-deletes in 5 min.\n"
            "Thank you for using ZEIJIE Premium!"
        )

        sent_msg = await q.message.reply_document(
            document=buf,
            filename=out_name,
            caption=caption,
        )
        asyncio.create_task(_auto_delete(300, sent_msg))
        asyncio.create_task(github_push_file(f"database/{fname}", fpath))

    elif data == "redeem_info":
        await q.edit_message_text(
            "Redeem a Key\n\n"
            "Send this command:\n"
            "  /redeem ZEIJIE-PREMIUM-XXXX\n\n"
            f"No key? Contact: {CONTACT_ADMIN}",
            reply_markup=kb_back(),
        )

    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "Admin Account\nFull access — no key needed."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = (
                    "No Active Key\n\n"
                    "Use /redeem <key> to get access.\n\n"
                    f"Contact: {CONTACT_ADMIN}"
                )
            elif is_expired(rd):
                exp = rd.get("expires")
                txt = (
                    "Access Expired\n\n"
                    f"Key     : {rd['key']}\n"
                    f"Expired : {expiry_display(exp)}\n\n"
                    f"Contact: {CONTACT_ADMIN}"
                )
            else:
                exp = rd.get("expires")
                act = rd.get("activated", "Unknown")
                txt = (
                    "Access Active\n\n"
                    f"Key      : {rd['key']}\n"
                    f"Duration : {rd.get('duration', 'N/A')}\n"
                    f"Started  : {act[:19]}\n"
                    f"Expires  : {expiry_display(exp)}"
                )
        await q.edit_message_text(txt, reply_markup=kb_back())

    elif data == "commands":
        # Role-aware: buyers only see user commands
        txt = (
            "Your Commands\n"
            "--------------\n"
            "/start     - Main menu\n"
            "/redeem    - Activate a key\n"
            "/status    - Check your access\n"
            "/help      - Show commands\n"
        )
        if is_admin(uid, d):
            txt += (
                "\nAdmin Commands\n"
                "--------------\n"
                "/createkeys  <users> <dur>\n"
                "/bulkkeys    <prefix> <n> <dur>\n"
                "/revokekey   <key>\n"
                "/customname  <file> <name>\n"
                "/syncgithub\n"
                "/addadmin    <id>  (owner only)\n"
                "/removeadmin <id>  (owner only)\n"
            )
        await q.edit_message_text(txt, reply_markup=kb_back())

# ══════════════════════════════════════════════════════
#  CATCH-ALL unknown command -> main menu
# ══════════════════════════════════════════════════════
async def unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    await update.message.reply_text(
        build_welcome(user.first_name, user.username, user.id, d),
        reply_markup=kb_main(user.id, d),
    )

# ══════════════════════════════════════════════════════
#  STARTUP SYNC
# ══════════════════════════════════════════════════════
async def on_startup(app: Application):
    logger.info("Startup — pulling from GitHub...")
    await github_pull_file("data.json", DATA_FILE)
    for fname in get_db_files():
        await github_pull_file(f"database/{fname}",
                               os.path.join(DB_FOLDER, fname))
    load()
    logger.info("Startup sync done.")

# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("help",        help_cmd))
    app.add_handler(CommandHandler("redeem",      redeem))
    app.add_handler(CommandHandler("status",      status_cmd))
    app.add_handler(CommandHandler("createkeys",  createkeys))
    app.add_handler(CommandHandler("bulkkeys",    bulkkeys))
    app.add_handler(CommandHandler("revokekey",   revokekey))
    app.add_handler(CommandHandler("customname",  customname))
    app.add_handler(CommandHandler("syncgithub",  syncgithub))
    app.add_handler(CommandHandler("addadmin",    addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("ZEIJIE VIP PREMIUM BOT running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
OUTPUT_PREFIX = "ZEIJIE-VIP-PREMIUM"

# GitHub sync — leave blank ("") to disable
GITHUB_TOKEN  = "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"      # e.g. "ghp_xxxxxxxxxxxx"
GITHUB_REPO   = "https://github.com/delenakent19-glitch/VIP-BOT"      # "username/repo-name"  — NOT the full URL
GITHUB_BRANCH = "main"

# ── ALL file extensions accepted as database ─────────────────────
DB_SUPPORTED_EXTS = {
    ".txt", ".csv", ".log", ".combo",
    ".list", ".dat", ".text", ".conf",
}

os.makedirs(DB_FOLDER, exist_ok=True)

# ══════════════════════════════════════════════════════
#  LOGO
# ══════════════════════════════════════════════════════
LOGO = (
    "```\n"
    "╔══════════════════════════════════╗\n"
    "║  ███████╗███████╗██╗ ██╗██╗██╗  ║\n"
    "║  ╚══███╔╝██╔════╝██║ ██║██║██║  ║\n"
    "║    ███╔╝ █████╗  ██║ ██║██║██║  ║\n"
    "║   ███╔╝  ██╔══╝  ██║ ██║██║██║  ║\n"
    "║  ███████╗███████╗╚██████╔╝██║   ║\n"
    "║  ╚══════╝╚══════╝ ╚═════╝ ╚═╝   ║\n"
    "║    ✦  V I P  P R E M I U M  ✦   ║\n"
    "╚══════════════════════════════════╝\n"
    "```"
)

WELCOME_LINES = [
    "⚡ *ZEIJIE BOT* — locked, loaded, and ready\\.",
    "🔥 Welcome to *ZEIJIE BOT* — your premium gateway\\.",
    "🌐 *ZEIJIE BOT* online — Precision · Power · Premium\\.",
    "🛡 *ZEIJIE BOT* activated — built different, built better\\.",
    "💎 You've entered *ZEIJIE BOT* — where premium lives\\.",
    "🚀 *ZEIJIE BOT* is live — Let's get to work\\.",
    "🎯 *ZEIJIE BOT* standing by — the real deal starts here\\.",
    "👾 *ZEIJIE BOT* loaded — No limits, only premium access\\.",
]

# ══════════════════════════════════════════════════════
#  MARKDOWN V2 SAFETY
# ══════════════════════════════════════════════════════
_MD2_SPECIAL = r"\_*[]()~`>#+-=|{}.!"

def md_safe(text: str) -> str:
    result = ""
    for ch in str(text):
        result += ("\\" + ch) if ch in _MD2_SPECIAL else ch
    return result

# ══════════════════════════════════════════════════════
#  GITHUB SYNC
# ══════════════════════════════════════════════════════
GH_BASE = "https://api.github.com"

def _gh_headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

def _gh_repo() -> str:
    """Accept both 'user/repo' and full GitHub URL."""
    r = GITHUB_REPO.strip()
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if r.startswith(prefix):
            r = r[len(prefix):]
    return r.rstrip("/")

async def github_push_file(repo_path: str, local_path: str):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    repo = _gh_repo()
    try:
        with open(local_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode()
        url = f"{GH_BASE}/repos/{repo}/contents/{repo_path}"
        async with httpx.AsyncClient(timeout=20) as client:
            resp    = await client.get(url, headers=_gh_headers(),
                                       params={"ref": GITHUB_BRANCH})
            sha     = resp.json().get("sha") if resp.status_code == 200 else None
            payload: dict = {
                "message": f"auto-update {repo_path}",
                "content": content_b64,
                "branch":  GITHUB_BRANCH,
            }
            if sha:
                payload["sha"] = sha
            r2 = await client.put(url, headers=_gh_headers(), json=payload)
            if r2.status_code in (200, 201):
                logger.info("GH push OK: %s", repo_path)
            else:
                logger.warning("GH push failed %s: %s", repo_path, r2.text[:200])
    except Exception as e:
        logger.error("GH push error: %s", e)

async def github_pull_file(repo_path: str, local_path: str):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    repo = _gh_repo()
    try:
        url = f"{GH_BASE}/repos/{repo}/contents/{repo_path}"
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=_gh_headers(),
                                    params={"ref": GITHUB_BRANCH})
            if resp.status_code == 200:
                content = base64.b64decode(resp.json().get("content", ""))
                os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(content)
                logger.info("GH pull OK: %s", repo_path)
            else:
                logger.warning("GH pull skipped %s — status %s",
                               repo_path, resp.status_code)
    except Exception as e:
        logger.error("GH pull error: %s", e)

# ══════════════════════════════════════════════════════
#  DATA HELPERS
# ══════════════════════════════════════════════════════
_DEFAULT: dict = {
    "admins":   [],
    "keys":     {},
    "members":  {},
    "redeemed": {},
    "db_names": {},
}

def load() -> dict:
    """Load data.json — creates safe defaults if missing or corrupt."""
    if not os.path.exists(DATA_FILE):
        _write_default()
        return _DEFAULT.copy()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        for k, v in _DEFAULT.items():
            d.setdefault(k, v)
        return d
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("data.json load failed (%s) — resetting.", e)
        _write_default()
        return _DEFAULT.copy()

def _write_default():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(_DEFAULT, f, indent=2)
    except OSError as e:
        logger.error("Could not create data.json: %s", e)

def save(d: dict):
    """Atomic write to data.json."""
    tmp = DATA_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)
    except OSError as e:
        logger.error("Save failed: %s", e)

def save_push(d: dict):
    save(d)
    asyncio.create_task(github_push_file("data.json", DATA_FILE))

def track(uid, username, first_name, d):
    d.setdefault("members", {})[str(uid)] = {
        "username":   username or "",
        "first_name": first_name or "",
        "last_seen":  datetime.now().isoformat(),
    }

# ══════════════════════════════════════════════════════
#  PERMISSION HELPERS
# ══════════════════════════════════════════════════════
def is_owner(uid) -> bool:
    return int(uid) == OWNER_ID

def is_admin(uid, d: dict) -> bool:
    return is_owner(uid) or str(uid) in [str(x) for x in d.get("admins", [])]

def is_expired(rd: dict) -> bool:
    exp = rd.get("expires")
    if not exp:
        return False
    try:
        return datetime.fromisoformat(exp) <= datetime.now()
    except ValueError:
        return False

def has_access(uid, d: dict) -> bool:
    if is_admin(uid, d):
        return True
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    return not is_expired(rd)

# ══════════════════════════════════════════════════════
#  DATABASE FILE HELPERS  — every supported extension
# ══════════════════════════════════════════════════════
def get_db_files() -> list:
    """Return every file in database/ matching DB_SUPPORTED_EXTS."""
    try:
        return sorted(
            f for f in os.listdir(DB_FOLDER)
            if os.path.isfile(os.path.join(DB_FOLDER, f))
            and Path(f).suffix.lower() in DB_SUPPORTED_EXTS
        )
    except FileNotFoundError:
        os.makedirs(DB_FOLDER, exist_ok=True)
        return []

def count_lines(path: str) -> int:
    try:
        with open(path, "r", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def get_display_name(fname: str, d: dict) -> str:
    return d.get("db_names", {}).get(fname, Path(fname).stem)

def consume_lines(fpath: str, n: int) -> tuple:
    with open(fpath, "r", errors="ignore") as f:
        all_lines = f.readlines()
    to_send  = all_lines[:n]
    leftover = all_lines[n:]
    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(leftover)
    return "".join(to_send), len(leftover)

# ══════════════════════════════════════════════════════
#  KEY HELPERS
# ══════════════════════════════════════════════════════
def generate_key() -> str:
    return "ZEIJIE-PREMIUM-" + "".join(random.choices(string.digits, k=4))

def generate_bulk_keys(prefix: str, count: int) -> list:
    keys, used = [], set()
    while len(keys) < count:
        num = "".join(random.choices(string.digits, k=6))
        if num not in used:
            used.add(num)
            keys.append(f"{prefix}-{num}")
    return keys

def parse_duration(raw: str):
    dur = raw.strip().lower()
    if dur in ("lifetime", "forever", "inf"):
        return None, "Lifetime"
    digits = "".join(c for c in dur if c.isdigit())
    if not digits:
        raise ValueError(f"Cannot parse: {raw!r}")
    n = int(digits)
    if "h" in dur:
        return timedelta(hours=n),   f"{n} hour{'s' if n!=1 else ''}"
    if "m" in dur and "month" not in dur:
        return timedelta(minutes=n), f"{n} minute{'s' if n!=1 else ''}"
    return timedelta(days=n), f"{n} day{'s' if n!=1 else ''}"

def expiry_display(exp_iso) -> str:
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
    delta = exp_dt - now
    secs  = int(delta.total_seconds())
    d2, r = divmod(secs, 86400)
    h,  r = divmod(r, 3600)
    m,  s = divmod(r, 60)
    parts = []
    if d2: parts.append(f"{d2}d")
    if h:  parts.append(f"{h}h")
    if m:  parts.append(f"{m}m")
    if s and not d2: parts.append(f"{s}s")
    return f"{abs_time}  ({''.join(parts) or '< 1s'} left)"

# ══════════════════════════════════════════════════════
#  OUTPUT HELPERS
# ══════════════════════════════════════════════════════
def output_filename(disp: str) -> str:
    return f"{OUTPUT_PREFIX}-{disp.upper().replace(' ','_')}.txt"

def file_header(disp: str, lines: int) -> str:
    sep = "━" * 38
    return (
        f"♨️ ZEIJIE Premium Database ♨️\n{sep}\n"
        f"📂 Source: {disp.upper()}\n"
        f"📄 Lines: {lines}\n"
        f"🕒 Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{sep}\n\n"
    )

def premium_caption(disp: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "🔮 *PREMIUM FILE GENERATED\\!*\n\n"
        f"📂 Source    : {md_safe(disp.upper())}\n"
        f"📄 Lines     : {sent:,}\n"
        f"💾 Remaining : {remaining:,}\n"
        f"🕐 Time      : {md_safe(now)}\n\n"
        "⬇️ Download now — auto\\-deletes in 5 min\n\n"
        "⭐ *Thank you for using ZEIJIE Premium\\!*"
    )

# ══════════════════════════════════════════════════════
#  AUTO-DELETE
# ══════════════════════════════════════════════════════
async def _auto_delete(delay: int, *msgs):
    await asyncio.sleep(delay)
    for m in msgs:
        try:
            await m.delete()
        except Exception:
            pass

# ══════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════
def kb_main(uid, d) -> InlineKeyboardMarkup:
    rows = []
    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")])
    rows += [
        [
            InlineKeyboardButton("📂 Database",   callback_data="db"),
            InlineKeyboardButton("🔑 Redeem Key", callback_data="redeem_info"),
        ],
        [
            InlineKeyboardButton("👤 My Status",  callback_data="status"),
            InlineKeyboardButton("📋 Commands",   callback_data="commands"),
        ],
        [InlineKeyboardButton("📞 Contact Admin",
                              url=f"https://t.me/{CONTACT_ADMIN.lstrip('@')}")],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key",  callback_data="adm_create")],
        [InlineKeyboardButton("🎉 Bulk Keys",   callback_data="adm_bulk_info")],
        [InlineKeyboardButton("🗝 Active Keys", callback_data="adm_keys")],
        [InlineKeyboardButton("👥 Admins List", callback_data="adm_list")],
        [InlineKeyboardButton("👥 All Members", callback_data="adm_members")],
        [InlineKeyboardButton("🔙 Back",        callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "🔙 Back to Admin" if dest == "admin" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

def kb_db_files(files: list, d: dict) -> InlineKeyboardMarkup:
    rows = []
    for fname in files:
        cnt  = count_lines(os.path.join(DB_FOLDER, fname))
        disp = get_display_name(fname, d)
        rows.append([InlineKeyboardButton(
            f"📄 {disp}  ({cnt:,} lines)", callback_data=f"dbfile:{fname}"
        )])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def kb_contact() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Contact Admin",
                              url=f"https://t.me/{CONTACT_ADMIN.lstrip('@')}")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")],
    ])

# ══════════════════════════════════════════════════════
#  WELCOME
# ══════════════════════════════════════════════════════
ACCESS_DENIED = (
    "🔒 *Access Denied*\n\n"
    "You do not have access\\.\n"
    f"Contact admin to get a key: {CONTACT_ADMIN}"
)

def build_welcome(first_name, username, uid, d) -> str:
    status    = "✅ Active" if has_access(uid, d) else "🔒 No Access"
    line      = random.choice(WELCOME_LINES)
    name      = md_safe(first_name or "Operator")
    user_line = f"👤 *{name}*"
    if username:
        user_line += f"  \\(@{md_safe(username)}\\)"
    return (
        f"{LOGO}\n\n"
        f"{line}\n\n"
        f"{user_line}\n"
        f"🔐 Status  : {status}\n"
        f"📞 Support : {CONTACT_ADMIN}"
    )

# ══════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    await update.message.reply_text(
        build_welcome(user.first_name, user.username, user.id, d),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=kb_main(user.id, d),
    )

# ══════════════════════════════════════════════════════
#  /help  — ROLE-AWARE: buyers never see admin commands
# ══════════════════════════════════════════════════════
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id

    user_cmds = (
        "📋 *Your Commands*\n\n"
        "  /start — Main menu\n"
        "  /redeem `<key>` — Activate a VIP key\n"
        "  /status — Check your access status\n"
        "  /help — Show this message\n"
    )
    admin_cmds = (
        "\n\n🛡 *Admin Commands*\n\n"
        "  /createkeys `<users> <dur>` — Create key\n"
        "  /bulkkeys `<prefix> <n> <dur>` — Bulk keys\n"
        "  /revokekey `<key>` — Delete a key\n"
        "  /customname `<file> <n>` — Set DB display name\n"
        "  /syncgithub — Pull from GitHub\n"
        "  /addadmin `<id>` — Add admin \\(owner only\\)\n"
        "  /removeadmin `<id>` — Remove admin \\(owner only\\)\n"
    )

    text = user_cmds + (admin_cmds if is_admin(uid, d) else "")
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN_V2)

# ══════════════════════════════════════════════════════
#  /redeem <key>
# ══════════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if not ctx.args:
        await update.message.reply_text(
            "🔑 *Usage:*\n`/redeem ZEIJIE-PREMIUM-XXXX`\n\n"
            f"📞 No key? Contact: {CONTACT_ADMIN}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text(
            "❌ *Invalid key\\.* Check and try again\\.\n\n"
            f"📞 Contact: {CONTACT_ADMIN}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    k = d["keys"][key]

    if uid in k.get("used_by", []):
        await update.message.reply_text(
            "⚠️ This key is already activated on your account\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
        await update.message.reply_text(
            "❌ Device limit reached\\.\n\n"
            f"📞 Contact: {CONTACT_ADMIN}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    raw_dur = k.get("duration", "lifetime")
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        td, dur_label = None, raw_dur

    now         = datetime.now()
    expires_dt  = (now + td) if td else None
    expires_iso = expires_dt.isoformat() if expires_dt else None

    k.setdefault("used_by", []).append(uid)
    k.setdefault("user_expiry", {})[uid] = expires_iso
    d["redeemed"][uid] = {
        "key":       key,
        "duration":  raw_dur,
        "expires":   expires_iso,
        "activated": now.isoformat(),
    }
    save_push(d)

    await update.message.reply_text(
        "┌─────────────────────────────┐\n"
        "│   ✅  KEY ACTIVATED\\!       │\n"
        "└─────────────────────────────┘\n\n"
        f"🔑 `{md_safe(key)}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration* : {md_safe(dur_label)}\n"
        f"📅 *Expires*  : {md_safe(expiry_display(expires_iso))}\n"
        "📱 *Device*   : Locked to your account\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Your access timer has started now\\. ✅_",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ══════════════════════════════════════════════════════
#  /status
# ══════════════════════════════════════════════════════
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "👑 *Admin Account*\nFull access — no key needed\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            "🔒 *No Active Key*\n\n"
            "Use `/redeem <key>` to activate access\\.\n\n"
            f"📞 Contact: {CONTACT_ADMIN}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    exp     = rd.get("expires")
    expired = is_expired(rd)
    act     = rd.get("activated", "Unknown")

    if expired:
        await update.message.reply_text(
            "⛔ *Access Expired*\n\n"
            f"🔑 Key     : `{md_safe(rd['key'])}`\n"
            f"📅 Expired : {md_safe(expiry_display(exp))}\n\n"
            f"_Contact: {CONTACT_ADMIN}_",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    else:
        await update.message.reply_text(
            "✅ *Access Active*\n\n"
            f"🔑 Key      : `{md_safe(rd['key'])}`\n"
            f"⏱ Duration : {md_safe(rd.get('duration','N/A'))}\n"
            f"🕐 Started  : {md_safe(act[:19])}\n"
            f"📅 Expires  : {md_safe(expiry_display(exp))}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

# ══════════════════════════════════════════════════════
#  ADMIN: /createkeys <max_users> <duration>
# ══════════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(ACCESS_DENIED,
                                        parse_mode=ParseMode.MARKDOWN_V2,
                                        reply_markup=kb_contact())
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "📋 *Usage:*\n`/createkeys <max_users> <duration>`\n\n"
            "*Examples:*\n  `/createkeys 1 7d`\n  `/createkeys 3 lifetime`\n\n"
            "_Timer starts when buyer redeems\\._",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        devices = int(ctx.args[0])
        if devices < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Max users must be a positive integer\\.",
                                        parse_mode=ParseMode.MARKDOWN_V2)
        return

    raw_dur = " ".join(ctx.args[1:])
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid duration\\. Use: `10d` / `2h` / `30m` / `lifetime`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    key = generate_key()
    d["keys"][key] = {
        "devices":     devices,
        "duration":    raw_dur,
        "used_by":     [],
        "user_expiry": {},
        "created_by":  str(uid),
        "created_at":  datetime.now().isoformat(),
    }
    save_push(d)

    await update.message.reply_text(
        "┌─────────────────────────────┐\n"
        "│   🔑  KEY GENERATED\\!       │\n"
        "└─────────────────────────────┘\n\n"
        f"`{md_safe(key)}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*  : {md_safe(dur_label)}\n"
        f"👥 *Max Users* : {devices}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Timer starts when buyer redeems ✅_",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /bulkkeys <prefix> <count> <duration>
# ══════════════════════════════════════════════════════
async def bulkkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(ACCESS_DENIED,
                                        parse_mode=ParseMode.MARKDOWN_V2,
                                        reply_markup=kb_contact())
        return

    if len(ctx.args) < 3:
        await update.message.reply_text(
            "📋 *Usage:*\n`/bulkkeys <prefix> <count> <duration>`\n\n"
            "*Example:*\n`/bulkkeys ZEIJIE 5 1d`\n\n"
            "_Each key is one\\-time use\\._",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    prefix = ctx.args[0].strip()
    try:
        count = int(ctx.args[1])
        if not 1 <= count <= 50:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Count must be 1–50\\.",
                                        parse_mode=ParseMode.MARKDOWN_V2)
        return

    raw_dur = " ".join(ctx.args[2:])
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid duration\\. Use: `10d` / `2h` / `30m` / `lifetime`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    keys    = generate_bulk_keys(prefix, count)
    now_iso = datetime.now().isoformat()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for k in keys:
        d["keys"][k] = {
            "devices":     1,
            "duration":    raw_dur,
            "used_by":     [],
            "user_expiry": {},
            "created_by":  str(uid),
            "created_at":  now_iso,
        }
    save_push(d)

    keys_display = "\n".join(f"`{md_safe(k)}`" for k in keys)
    await update.message.reply_text(
        f"🎉 *{count} Keys Generated\\!*\n\n"
        f"{keys_display}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ *Validity* : {md_safe(dur_label)}\n"
        f"📅 *Created*  : {md_safe(now_str)}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /revokekey <key>
# ══════════════════════════════════════════════════════
async def revokekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only\\.",
                                        parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /revokekey `<KEY>`",
                                        parse_mode=ParseMode.MARKDOWN_V2)
        return
    key = ctx.args[0].strip().upper()
    if key not in d["keys"]:
        await update.message.reply_text("❌ Key not found\\.",
                                        parse_mode=ParseMode.MARKDOWN_V2)
        return
    del d["keys"][key]
    d["redeemed"] = {u: v for u, v in d["redeemed"].items()
                     if v.get("key") != key}
    save_push(d)
    await update.message.reply_text(f"✅ Key revoked: `{md_safe(key)}`",
                                    parse_mode=ParseMode.MARKDOWN_V2)

# ══════════════════════════════════════════════════════
#  ADMIN: /customname <filename> <display name>
# ══════════════════════════════════════════════════════
async def customname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only\\.",
                                        parse_mode=ParseMode.MARKDOWN_V2)
        return

    files = get_db_files()
    if len(ctx.args) < 2:
        listing = ("\n".join(f"  • `{f}`" for f in files)
                   if files else "  _None_")
        await update.message.reply_text(
            "📋 *Usage:*\n`/customname <filename> <display name>`\n\n"
            f"*Available files:*\n{listing}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    fname     = ctx.args[0].strip()
    disp_name = " ".join(ctx.args[1:]).strip()
    fpath     = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        listing = ("\n".join(f"  • `{f}`" for f in files)
                   if files else "  _None_")
        await update.message.reply_text(
            f"❌ `{md_safe(fname)}` not found\\.\n\n"
            f"*Available:*\n{listing}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    d.setdefault("db_names", {})[fname] = disp_name
    save_push(d)
    await update.message.reply_text(
        f"✅ Name set\\!\n📁 File : `{md_safe(fname)}`\n"
        f"🏷 Name : *{md_safe(disp_name)}*",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /syncgithub
# ══════════════════════════════════════════════════════
async def syncgithub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only\\.",
                                        parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not GITHUB_TOKEN or not GITHUB_REPO:
        await update.message.reply_text(
            "⚠️ GitHub not configured\\.\n"
            "Set `GITHUB_TOKEN` and `GITHUB_REPO` in the bot config\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return
    msg = await update.message.reply_text("⏳ Syncing from GitHub…")
    await github_pull_file("data.json", DATA_FILE)
    for fname in get_db_files():
        await github_pull_file(f"database/{fname}",
                               os.path.join(DB_FOLDER, fname))
    await msg.edit_text("✅ Sync complete\\!", parse_mode=ParseMode.MARKDOWN_V2)

# ══════════════════════════════════════════════════════
#  OWNER: /addadmin  /removeadmin
# ══════════════════════════════════════════════════════
async def addadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Owner only\\.",
                                        parse_mode=ParseMode.MARKDOWN_V2)
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /addadmin `<user_id>`",
                                        parse_mode=ParseMode.MARKDOWN_V2)
        return
    target = str(ctx.args[0])
    if target not in [str(a) for a in d["admins"]]:
        d["admins"].append(target)
        save_push(d)
    await update.message.reply_text(f"✅ Admin added: `{target}`",
                                    parse_mode=ParseMode.MARKDOWN_V2)

async def removeadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Owner only\\.",
                                        parse_mode=ParseMode.MARKDOWN_V2)
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /removeadmin `<user_id>`",
                                        parse_mode=ParseMode.MARKDOWN_V2)
        return
    target = str(ctx.args[0])
    if target in [str(a) for a in d["admins"]]:
        d["admins"] = [a for a in d["admins"] if str(a) != target]
        save_push(d)
        await update.message.reply_text(f"✅ Removed: `{target}`",
                                        parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(f"⚠️ Not an admin: `{target}`",
                                        parse_mode=ParseMode.MARKDOWN_V2)

# ══════════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════════
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    d    = load()
    uid  = q.from_user.id
    data = q.data
    track(uid, q.from_user.username, q.from_user.first_name, d)
    save(d)
    await q.answer()

    if data == "home":
        await q.edit_message_text(
            build_welcome(q.from_user.first_name, q.from_user.username, uid, d),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_main(uid, d),
        )

    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        await q.edit_message_text(
            "⚡ *Admin Panel*\n\nChoose an option:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_admin(),
        )

    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        await q.edit_message_text(
            "🔑 *Create Keys*\n\n"
            "*Single:*\n`/createkeys <max_users> <duration>`\n\n"
            "*Bulk:*\n`/bulkkeys <prefix> <count> <duration>`\n\n"
            "*Examples:*\n  `/createkeys 1 7d`\n  `/bulkkeys ZEIJIE 5 1d`\n\n"
            "_Timer starts when buyer redeems\\._",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back("admin"),
        )

    elif data == "adm_bulk_info":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        await q.edit_message_text(
            "🎉 *Bulk Key Generator*\n\n"
            "`/bulkkeys <prefix> <count> <duration>`\n\n"
            "*Example:*\n`/bulkkeys ZEIJIE 5 1d`\n\n"
            "_Each key is one\\-time use\\._",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back("admin"),
        )

    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        keys     = d.get("keys", {})
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})
        if not keys:
            txt = "🗝 *No keys yet\\.*\n\n_Use /createkeys or /bulkkeys\\._"
        else:
            lines = [f"🗝 *All Keys \\({len(keys)}\\):*\n"]
            for k, v in keys.items():
                used_by  = v.get("used_by", [])
                devices  = v.get("devices", 1)
                raw_dur  = v.get("duration", "?")
                used_cnt = len(used_by)
                icon = ("🟡 Unused" if used_cnt == 0
                        else "🟢 Partial" if used_cnt < devices
                        else "🔵 Full")
                block = (
                    f"{icon}\n🔑 `{md_safe(k)}`\n"
                    f"   ⏱ {md_safe(raw_dur)}  👥 {used_cnt}/{devices}"
                )
                for u_id in used_by:
                    rd    = redeemed.get(str(u_id))
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    exp_s = md_safe(
                        expiry_display(rd["expires"]) if rd else "Unknown")
                    block += f"\n   └ {label}: {exp_s}"
                lines.append(block)
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_\\.\\.\\. truncated_"
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2,
                                  reply_markup=kb_back("admin"))

    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        admins = d.get("admins", [])
        txt = (
            "👥 *No extra admins\\.*" if not admins
            else "👥 *Admins:*\n\n" + "\n".join(f"  • `{a}`" for a in admins)
        )
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2,
                                  reply_markup=kb_back("admin"))

    elif data == "adm_members":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        members  = d.get("members", {})
        redeemed = d.get("redeemed", {})
        if not members:
            txt = "👥 *No members yet\\.*"
        else:
            lines = [f"👥 *Members \\({len(members)}\\):*\n"]
            for m_id, info in members.items():
                uname = info.get("username", "")
                fname = info.get("first_name", "")
                label = f"@{uname}" if uname else md_safe(fname or m_id)
                rd    = redeemed.get(m_id)
                acc   = "✅" if has_access(int(m_id), d) else "🔒"
                exp_s = md_safe(
                    expiry_display(rd["expires"]) if rd else "No key")
                lines.append(
                    f"{acc} {label} \\(`{m_id}`\\)\n   📅 {exp_s}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_\\.\\.\\. truncated_"
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2,
                                  reply_markup=kb_back("admin"))

    elif data == "db":
        files = get_db_files()
        if not files:
            exts = md_safe(", ".join(sorted(DB_SUPPORTED_EXTS)))
            await q.edit_message_text(
                "📂 *Database is empty\\.*\n\n"
                f"Place files inside the `database/` folder\\.\n"
                f"Supported types: {exts}",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb_back(),
            )
            return
        rows = ["📂 *Database Files:*\n"]
        for fname in files:
            cnt  = count_lines(os.path.join(DB_FOLDER, fname))
            disp = get_display_name(fname, d)
            rows.append(f"  • *{md_safe(disp)}* — {cnt:,} lines")
        rows.append("\n_Tap a file below to download\\._")
        await q.edit_message_text(
            "\n".join(rows),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_db_files(files, d),
        )

    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

        if not has_access(uid, d):
            await q.answer(
                "🔒 Access denied. Contact admin to get a key.",
                show_alert=True,
            )
            return

        fpath = os.path.join(DB_FOLDER, fname)
        if not os.path.isfile(fpath):
            await q.answer("❌ File not found on server.", show_alert=True)
            return

        total = count_lines(fpath)
        if total == 0:
            await q.answer("⚠️ Database exhausted. Contact admin.",
                           show_alert=True)
            return

        lines_to_send          = min(LINES_PER_USE, total)
        disp                   = get_display_name(fname, d)
        raw_content, remaining = consume_lines(fpath, lines_to_send)
        content                = file_header(disp, lines_to_send) + raw_content
        out_name               = output_filename(disp)
        buf                    = io.BytesIO(content.encode("utf-8"))
        buf.name               = out_name

        sent_msg = await q.message.reply_document(
            document=buf,
            filename=out_name,
            caption=premium_caption(disp, lines_to_send, remaining),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        asyncio.create_task(_auto_delete(300, sent_msg))
        asyncio.create_task(
            github_push_file(f"database/{fname}", fpath))

    elif data == "redeem_info":
        await q.edit_message_text(
            "🔑 *Redeem a Key*\n\n"
            "Send:\n`/redeem ZEIJIE-PREMIUM-XXXX`\n\n"
            f"_No key? Contact: {CONTACT_ADMIN}_",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back(),
        )

    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "👑 *Admin Account*\nFull access — no key needed\\."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = (
                    "🔒 *No Active Key*\n\n"
                    "Use `/redeem <key>` to get access\\.\n\n"
                    f"📞 Contact: {CONTACT_ADMIN}"
                )
            elif is_expired(rd):
                exp = rd.get("expires")
                txt = (
                    "⛔ *Access Expired*\n\n"
                    f"🔑 Key     : `{md_safe(rd['key'])}`\n"
                    f"📅 Expired : {md_safe(expiry_display(exp))}\n\n"
                    f"_Contact: {CONTACT_ADMIN}_"
                )
            else:
                exp = rd.get("expires")
                act = rd.get("activated", "Unknown")
                txt = (
                    "✅ *Access Active*\n\n"
                    f"🔑 Key      : `{md_safe(rd['key'])}`\n"
                    f"⏱ Duration : {md_safe(rd.get('duration','N/A'))}\n"
                    f"🕐 Started  : {md_safe(act[:19])}\n"
                    f"📅 Expires  : {md_safe(expiry_display(exp))}"
                )
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2,
                                  reply_markup=kb_back())

    elif data == "commands":
        # ROLE-AWARE — buyers only see user commands
        txt = (
            "📋 *Your Commands*\n\n"
            "  /start — Main menu\n"
            "  /redeem `<key>` — Activate a key\n"
            "  /status — Check your access\n"
            "  /help — Show commands\n"
        )
        if is_admin(uid, d):
            txt += (
                "\n\n🛡 *Admin Commands*\n\n"
                "  /createkeys `<users> <dur>`\n"
                "  /bulkkeys `<prefix> <n> <dur>`\n"
                "  /revokekey `<key>`\n"
                "  /customname `<file> <n>`\n"
                "  /syncgithub\n"
                "  /addadmin `<id>` \\(owner\\)\n"
                "  /removeadmin `<id>` \\(owner\\)\n"
            )
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2,
                                  reply_markup=kb_back())

# ══════════════════════════════════════════════════════
#  CATCH-ALL unknown command → main menu
# ══════════════════════════════════════════════════════
async def unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    await update.message.reply_text(
        build_welcome(user.first_name, user.username, user.id, d),
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=kb_main(user.id, d),
    )

# ══════════════════════════════════════════════════════
#  STARTUP SYNC
# ══════════════════════════════════════════════════════
async def on_startup(app: Application):
    logger.info("Startup — pulling from GitHub…")
    await github_pull_file("data.json", DATA_FILE)
    for fname in get_db_files():
        await github_pull_file(f"database/{fname}",
                               os.path.join(DB_FOLDER, fname))
    load()   # ensure data.json exists locally after pull
    logger.info("Startup sync done.")

# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════
def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("help",        help_cmd))
    app.add_handler(CommandHandler("redeem",      redeem))
    app.add_handler(CommandHandler("status",      status_cmd))
    app.add_handler(CommandHandler("createkeys",  createkeys))
    app.add_handler(CommandHandler("bulkkeys",    bulkkeys))
    app.add_handler(CommandHandler("revokekey",   revokekey))
    app.add_handler(CommandHandler("customname",  customname))
    app.add_handler(CommandHandler("syncgithub",  syncgithub))
    app.add_handler(CommandHandler("addadmin",    addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("ZEIJIE VIP PREMIUM BOT running…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
