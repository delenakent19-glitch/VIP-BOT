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
from telegram.constants import ParseMode

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════════════
#  CONFIG
# ══════════════════════════════════════════════════════
BOT_TOKEN     = "8797773644:AAHuuZurs0oiduQNW6ywxvTXQ1Kdf32XE9w"
OWNER_ID      = 8420104044
CONTACT_ADMIN = "@Zeijie_s"

DATA_FILE     = "data.json"
DB_FOLDER     = "database"
LINES_PER_USE = 250
OUTPUT_PREFIX = "ZEIJIE-VIP-PREMIUM"

# ── GitHub sync — fill these to enable cloud backup ──────────────
# SETUP GUIDE:
#   1. Create a GitHub repo (public or private).
#   2. Add your data.json and database/*.txt files to it.
#   3. Go to GitHub → Settings → Developer Settings
#      → Personal Access Tokens → Classic → Generate New Token
#      → Tick "repo" scope → Copy token.
#   4. Paste values below. Leave blank ("") to disable GitHub sync.
GITHUB_TOKEN  = "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"          # e.g. "ghp_xxxxxxxxxxxxxxxx"
GITHUB_REPO   = "https://github.com/delenakent19-glitch/VIP-BOT"          # e.g. "YourUsername/zeijie-data"
GITHUB_BRANCH = "main"
# ─────────────────────────────────────────────────────────────────

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
    """Escape all MarkdownV2 special characters."""
    result = ""
    for ch in str(text):
        if ch in _MD2_SPECIAL:
            result += "\\" + ch
        else:
            result += ch
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

async def github_push_file(repo_path: str, local_path: str):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    try:
        with open(local_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode()
        url     = f"{GH_BASE}/repos/{GITHUB_REPO}/contents/{repo_path}"
        headers = _gh_headers()
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=headers, params={"ref": GITHUB_BRANCH})
            sha  = resp.json().get("sha") if resp.status_code == 200 else None
            payload = {
                "message": f"auto-update {repo_path}",
                "content": content_b64,
                "branch":  GITHUB_BRANCH,
            }
            if sha:
                payload["sha"] = sha
            r2 = await client.put(url, headers=headers, json=payload)
            if r2.status_code in (200, 201):
                logger.info("GH push OK: %s", repo_path)
            else:
                logger.warning("GH push failed %s: %s", repo_path, r2.text[:200])
    except Exception as e:
        logger.error("GH push error: %s", e)

async def github_pull_file(repo_path: str, local_path: str):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    try:
        url     = f"{GH_BASE}/repos/{GITHUB_REPO}/contents/{repo_path}"
        headers = _gh_headers()
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=headers, params={"ref": GITHUB_BRANCH})
            if resp.status_code == 200:
                content = base64.b64decode(resp.json()["content"])
                os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(content)
                logger.info("GH pull OK: %s", repo_path)
    except Exception as e:
        logger.error("GH pull error: %s", e)

# ══════════════════════════════════════════════════════
#  DATA HELPERS
# ══════════════════════════════════════════════════════
def load() -> dict:
    default = {
        "admins": [], "keys": {}, "members": {},
        "redeemed": {}, "db_names": {}
    }
    if not os.path.exists(DATA_FILE):
        return default
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("data.json corrupted — fresh start.")
        return default
    for k, v in default.items():
        d.setdefault(k, v)
    return d

def save(d: dict):
    tmp = DATA_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)
    except OSError as e:
        logger.error("Save failed: %s", e)

def save_push(d: dict):
    """Save locally and push to GitHub in background."""
    save(d)
    asyncio.create_task(github_push_file("data.json", DATA_FILE))

def is_admin(uid, d) -> bool:
    return str(uid) in [str(x) for x in d.get("admins", [])] or int(uid) == OWNER_ID

def is_expired(rd: dict) -> bool:
    exp = rd.get("expires")
    if not exp:
        return False
    try:
        return datetime.fromisoformat(exp) <= datetime.now()
    except ValueError:
        return False

def has_access(uid, d) -> bool:
    """FIXED: expired keys correctly denied."""
    if is_admin(uid, d):
        return True
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    return not is_expired(rd)   # False when expired

def track(uid, username, first_name, d):
    d.setdefault("members", {})[str(uid)] = {
        "username":   username or "",
        "first_name": first_name or "",
        "last_seen":  datetime.now().isoformat(),
    }

def get_db_files() -> list:
    try:
        return sorted(
            f for f in os.listdir(DB_FOLDER)
            if os.path.isfile(os.path.join(DB_FOLDER, f)) and f.endswith(".txt")
        )
    except FileNotFoundError:
        return []

def count_lines(path: str) -> int:
    try:
        with open(path, "r", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def get_display_name(fname: str, d: dict) -> str:
    return d.get("db_names", {}).get(fname, Path(fname).stem)

# ══════════════════════════════════════════════════════
#  KEY GENERATION — Format: ZEIJIE-PREMIUM-XXXX
# ══════════════════════════════════════════════════════
def generate_key() -> str:
    part = "".join(random.choices(string.digits, k=4))
    return f"ZEIJIE-PREMIUM-{part}"

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
        return timedelta(hours=n),   f"{n} hour{'s' if n != 1 else ''}"
    if "m" in dur and "month" not in dur:
        return timedelta(minutes=n), f"{n} minute{'s' if n != 1 else ''}"
    return timedelta(days=n), f"{n} day{'s' if n != 1 else ''}"

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
    d, r  = divmod(secs, 86400)
    h, r  = divmod(r, 3600)
    m, s  = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s and not d: parts.append(f"{s}s")
    return f"{abs_time}  ({''.join(parts) or '< 1s'} left)"

# ══════════════════════════════════════════════════════
#  FILE OUTPUT
# ══════════════════════════════════════════════════════
def output_filename(disp: str) -> str:
    return f"{OUTPUT_PREFIX}-{disp.upper().replace(' ', '_')}.txt"

def file_header(disp: str, lines: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep = "━" * 38
    return (
        f"♨️ ZEIJIE sᴇᴀʀᴄʜᴇʀ Premium Database ♨️\n"
        f"{sep}\n"
        f"📂 Source: • {disp.upper()}\n"
        f"📄 Lines: {lines}\n"
        f"🕒 Generated: {now}\n"
        f"🔥 Quality: Premium Grade\n"
        f"⚡ Auto-Delete: Enabled (lines removed from source)\n"
        f"{sep}\n\n"
    )

def premium_caption(disp: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "🔮 *PREMIUM FILE GENERATED\\!*\n\n"
        "📊 *GENERATION SUMMARY*\n"
        f"┣ 🎮 Source     : {md_safe(disp.upper())}\n"
        f"┣ 📄 File       : `{md_safe(output_filename(disp))}`\n"
        f"┣ 📜 Lines      : {sent:,}\n"
        f"┣ 🕐 Generated  : {md_safe(now)}\n"
        f"┣ 💾 Remaining  : {remaining:,} lines\n"
        "┣ 🧹 Cleanup    : Done\n\n"
        "🛡 *SECURITY*\n"
        "┣ 🔒 Auto\\-Expiry : 5 minutes\n"
        "┣ 🗑 Auto\\-Delete : Enabled\n"
        "┣ ⚡ Session     : Verified\n\n"
        "⬇️ Download immediately — file deletes in 5 min\n\n"
        "⭐ *Thank you for using ZEIJIE Premium\\!*"
    )

# ══════════════════════════════════════════════════════
#  DATABASE CONSUMER
# ══════════════════════════════════════════════════════
def consume_lines(fpath: str, n: int) -> tuple:
    with open(fpath, "r", errors="ignore") as f:
        all_lines = f.readlines()
    to_send  = all_lines[:n]
    leftover = all_lines[n:]
    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(leftover)
    return "".join(to_send), len(leftover)

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
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{CONTACT_ADMIN.lstrip('@')}")],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key",   callback_data="adm_create")],
        [InlineKeyboardButton("🎉 Bulk Keys",    callback_data="adm_bulk_info")],
        [InlineKeyboardButton("🗝 Active Keys",  callback_data="adm_keys")],
        [InlineKeyboardButton("👥 Admins List",  callback_data="adm_list")],
        [InlineKeyboardButton("👥 All Members",  callback_data="adm_members")],
        [InlineKeyboardButton("🔙 Back",         callback_data="home")],
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
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{CONTACT_ADMIN.lstrip('@')}")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")],
    ])

# ══════════════════════════════════════════════════════
#  WELCOME TEXT
# ══════════════════════════════════════════════════════
def build_welcome(first_name, username, uid, d) -> str:
    status = "✅ Active" if has_access(uid, d) else "🔒 No Access"
    line   = random.choice(WELCOME_LINES)
    name   = md_safe(first_name or "Operator")
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

ACCESS_DENIED_MSG = (
    "🔒 *Access Denied*\n\n"
    "You cannot access this database\\.\n"
    "Contact admin to get a key & to access this\\.\n\n"
    f"📞 Admin: {CONTACT_ADMIN}"
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
#  /createkeys <max_users> <duration>
# ══════════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(
            ACCESS_DENIED_MSG, parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_contact()
        )
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "📋 *Usage:*\n`/createkeys <max_users> <duration>`\n\n"
            "*Examples:*\n"
            "  `/createkeys 1 7d`\n"
            "  `/createkeys 3 lifetime`\n\n"
            "_Timer starts when buyer redeems\\._",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        devices = int(ctx.args[0])
        if devices < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Max users must be a positive integer\\.", parse_mode=ParseMode.MARKDOWN_V2)
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
    logger.info("Key created: %s  dur=%s  devices=%s", key, raw_dur, devices)

    await update.message.reply_text(
        "┌─────────────────────────────┐\n"
        "│   🔑  KEY GENERATED\\!       │\n"
        "└─────────────────────────────┘\n\n"
        f"`{md_safe(key)}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*  : {md_safe(dur_label)}\n"
        f"📅 *Starts*    : On redeem\n"
        f"👥 *Max Users* : {devices}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Timer starts when buyer redeems ✅_",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ══════════════════════════════════════════════════════
#  /bulkkeys <prefix> <count> <duration>
# ══════════════════════════════════════════════════════
async def bulkkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(
            ACCESS_DENIED_MSG, parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_contact()
        )
        return

    if len(ctx.args) < 3:
        await update.message.reply_text(
            "📋 *Usage:*\n`/bulkkeys <prefix> <count> <duration>`\n\n"
            "*Example:*\n`/bulkkeys Zaraki 5 1d`\n\n"
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
        await update.message.reply_text("❌ Count must be between 1 and 50\\.", parse_mode=ParseMode.MARKDOWN_V2)
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
    logger.info("Bulk keys: prefix=%s count=%s dur=%s", prefix, count, raw_dur)

    keys_display = "\n".join(f"`{md_safe(k)}`" for k in keys)
    await update.message.reply_text(
        f"🎉 *{count} Keys Generated Successfully\\!* 🎉\n\n"
        f"{keys_display}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ *Validity \\(each\\)* : {md_safe(dur_label)}\n"
        f"📝 *Status*            : One\\-time use\n"
        f"📅 *Created On*        : {md_safe(now_str)}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✨ Share these keys with your users to grant them access\\!",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ══════════════════════════════════════════════════════
#  /redeem <key>
# ══════════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username, update.effective_user.first_name, d)

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
            "❌ Device limit reached for this key\\.\n\n"
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
    logger.info("Redeemed: %s  uid=%s  expires=%s", key, uid, expires_iso)

    await update.message.reply_text(
        "┌─────────────────────────────┐\n"
        "│   ✅  KEY ACTIVATED\\!       │\n"
        "└─────────────────────────────┘\n\n"
        f"🔑 `{md_safe(key)}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*  : {md_safe(dur_label)}\n"
        f"📅 *Expires*   : {md_safe(expiry_display(expires_iso))}\n"
        "📱 *Device*    : Locked to your account\n"
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
    track(int(uid), update.effective_user.username, update.effective_user.first_name, d)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "👑 *Admin Account*\nFull access granted — no key needed\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            "🔒 *No Active Key*\n\nUse `/redeem <key>` to activate access\\.\n\n"
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
            f"_Contact admin: {CONTACT_ADMIN}_",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    else:
        await update.message.reply_text(
            "✅ *Access Active*\n\n"
            f"🔑 Key      : `{md_safe(rd['key'])}`\n"
            f"⏱ Duration : {md_safe(rd.get('duration', 'N/A'))}\n"
            f"🕐 Started  : {md_safe(act[:19])}\n"
            f"📅 Expires  : {md_safe(expiry_display(exp))}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

# ══════════════════════════════════════════════════════
#  /addadmin & /removeadmin — owner only
# ══════════════════════════════════════════════════════
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
        save_push(d)
    await update.message.reply_text(f"✅ Admin added: `{target}`", parse_mode=ParseMode.MARKDOWN_V2)

async def removeadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /removeadmin <user_id>")
        return
    target = str(ctx.args[0])
    if target in [str(a) for a in d["admins"]]:
        d["admins"] = [a for a in d["admins"] if str(a) != target]
        save_push(d)
        await update.message.reply_text(f"✅ Removed: `{target}`", parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(f"⚠️ Not an admin: `{target}`", parse_mode=ParseMode.MARKDOWN_V2)

# ══════════════════════════════════════════════════════
#  /revokekey <key> — admin only
# ══════════════════════════════════════════════════════
async def revokekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)
    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /revokekey <KEY>")
        return
    key = ctx.args[0].strip().upper()
    if key not in d["keys"]:
        await update.message.reply_text("❌ Key not found\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    del d["keys"][key]
    d["redeemed"] = {u: v for u, v in d["redeemed"].items() if v.get("key") != key}
    save_push(d)
    await update.message.reply_text(f"✅ Key revoked: `{md_safe(key)}`", parse_mode=ParseMode.MARKDOWN_V2)

# ══════════════════════════════════════════════════════
#  /customname <filename> <display name> — admin only
# ══════════════════════════════════════════════════════
async def customname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    files = get_db_files()
    if len(ctx.args) < 2:
        listing = "\n".join(f"  • `{f}`" for f in files) if files else "  _None_"
        await update.message.reply_text(
            "📋 *Usage:*\n`/customname <filename.txt> <display name>`\n\n"
            "*Your DB files:*\n" + listing + "\n\n"
            "*Example:*\n`/customname garena.txt GARENA`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    fname     = ctx.args[0].strip()
    disp_name = " ".join(ctx.args[1:]).strip()
    fpath     = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        listing = "\n".join(f"  • `{f}`" for f in files) if files else "  _None_"
        await update.message.reply_text(
            f"❌ `{md_safe(fname)}` not found in database folder\\.\n\n"
            f"*Available:*\n{listing}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    d.setdefault("db_names", {})[fname] = disp_name
    save_push(d)
    await update.message.reply_text(
        f"✅ Custom name set\\!\n\n"
        f"📁 File : `{md_safe(fname)}`\n"
        f"🏷 Name : *{md_safe(disp_name)}*",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ══════════════════════════════════════════════════════
#  /syncgithub — admin only
# ══════════════════════════════════════════════════════
async def syncgithub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    if not GITHUB_TOKEN or not GITHUB_REPO:
        await update.message.reply_text(
            "⚠️ GitHub is not configured\\.\n"
            "Set `GITHUB_TOKEN` and `GITHUB_REPO` in the bot config\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    msg = await update.message.reply_text("⏳ Syncing from GitHub…")
    await github_pull_file("data.json", DATA_FILE)
    for fname in get_db_files():
        await github_pull_file(f"database/{fname}", os.path.join(DB_FOLDER, fname))
    await msg.edit_text("✅ Sync complete\\! Data pulled from GitHub\\.", parse_mode=ParseMode.MARKDOWN_V2)

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
            "⚡ *Admin Panel*\n\nChoose an option below:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_admin(),
        )

    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        await q.edit_message_text(
            "🔑 *Create Keys*\n\n"
            "*Single key:*\n`/createkeys <max_users> <duration>`\n\n"
            "*Bulk keys:*\n`/bulkkeys <prefix> <count> <duration>`\n\n"
            "*Key format:* `ZEIJIE\\-PREMIUM\\-XXXX`\n\n"
            "*Examples:*\n"
            "  `/createkeys 1 7d`\n"
            "  `/bulkkeys Zaraki 5 1d`\n\n"
            "_Timer starts when buyer redeems\\._",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back("admin"),
        )

    elif data == "adm_bulk_info":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        await q.edit_message_text(
            "🎉 *Bulk Key Generator*\n\n"
            "Command:\n`/bulkkeys <prefix> <count> <duration>`\n\n"
            "*Example:*\n`/bulkkeys Zaraki 5 1d`\n\n"
            "Output:\n"
            "`Zaraki\\-273852`\n`Zaraki\\-617209`\n`Zaraki\\-679658`\n\n"
            "_Each key is one\\-time use only\\._",
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
                icon = "🟡 Unused" if used_cnt == 0 else ("🟢 Partial" if used_cnt < devices else "🔵 Full")
                block = (
                    f"{icon}\n🔑 `{md_safe(k)}`\n"
                    f"   ⏱ {md_safe(raw_dur)}  👥 {used_cnt}/{devices}"
                )
                for u_id in used_by:
                    rd    = redeemed.get(str(u_id))
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    exp_s = md_safe(expiry_display(rd["expires"]) if rd else "Unknown")
                    block += f"\n   └ {label}: {exp_s}"
                lines.append(block)
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_\\.\\.\\. truncated_"
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb_back("admin"))

    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        admins = d.get("admins", [])
        txt = (
            "👥 *No extra admins\\.*"
            if not admins
            else "👥 *Admins:*\n\n" + "\n".join(f"  • `{a}`" for a in admins)
        )
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb_back("admin"))

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
                uname  = info.get("username", "")
                fname  = info.get("first_name", "")
                label  = f"@{uname}" if uname else md_safe(fname or m_id)
                rd     = redeemed.get(m_id)
                acc    = "✅" if has_access(int(m_id), d) else "🔒"
                exp_s  = md_safe(expiry_display(rd["expires"]) if rd else "No key")
                lines.append(f"{acc} {label} \\(`{m_id}`\\)\n   📅 {exp_s}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_\\.\\.\\. truncated_"
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb_back("admin"))

    elif data == "db":
        files = get_db_files()
        if not files:
            await q.edit_message_text(
                "📂 *Database is empty\\.*\n\nUpload `.txt` files into the `database/` folder\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb_back(),
            )
            return
        lines_txt = ["📂 *Database Files:*\n"]
        for fname in files:
            cnt  = count_lines(os.path.join(DB_FOLDER, fname))
            disp = get_display_name(fname, d)
            lines_txt.append(f"  • *{md_safe(disp)}* — {cnt:,} lines")
        lines_txt.append("\n_Tap a file to generate and download\\._")
        await q.edit_message_text(
            "\n".join(lines_txt),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_db_files(files, d),
        )

    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

        # ── ACCESS CHECK (expired keys blocked) ──
        if not has_access(uid, d):
            await q.answer(
                "🔒 You cannot access this database. Contact admin to get a key.",
                show_alert=True
            )
            return

        fpath = os.path.join(DB_FOLDER, fname)
        if not os.path.isfile(fpath):
            await q.answer("❌ File not found on server.", show_alert=True); return

        total = count_lines(fpath)
        if total == 0:
            await q.answer("⚠️ Database exhausted. Contact admin.", show_alert=True); return

        lines_to_send = min(LINES_PER_USE, total)
        disp          = get_display_name(fname, d)

        raw_content, remaining = consume_lines(fpath, lines_to_send)
        content  = file_header(disp, lines_to_send) + raw_content
        out_name = output_filename(disp)

        buf      = io.BytesIO(content.encode("utf-8"))
        buf.name = out_name

        sent_msg = await q.message.reply_document(
            document=buf,
            filename=out_name,
            caption=premium_caption(disp, lines_to_send, remaining),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        asyncio.create_task(_auto_delete(300, sent_msg))
        asyncio.create_task(github_push_file(f"database/{fname}", fpath))

    elif data == "redeem_info":
        await q.edit_message_text(
            "🔑 *Redeem a Key*\n\n"
            "Send this command:\n`/redeem ZEIJIE-PREMIUM-XXXX`\n\n"
            f"_No key? Contact: {CONTACT_ADMIN}_\n\n"
            "_Access timer starts the moment you redeem\\._",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back(),
        )

    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "👑 *Admin Account*\nFull access granted — no key needed\\."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = (
                    "🔒 *No Active Key*\n\n"
                    "Use `/redeem <key>` to get access\\.\n\n"
                    f"📞 Contact: {CONTACT_ADMIN}"
                )
            else:
                exp     = rd.get("expires")
                expired = is_expired(rd)
                act     = rd.get("activated", "Unknown")
                if expired:
                    txt = (
                        "⛔ *Access Expired*\n\n"
                        f"🔑 Key     : `{md_safe(rd['key'])}`\n"
                        f"📅 Expired : {md_safe(expiry_display(exp))}\n\n"
                        f"_Contact admin: {CONTACT_ADMIN}_"
                    )
                else:
                    txt = (
                        "✅ *Access Active*\n\n"
                        f"🔑 Key      : `{md_safe(rd['key'])}`\n"
                        f"⏱ Duration : {md_safe(rd.get('duration', 'N/A'))}\n"
                        f"🕐 Started  : {md_safe(act[:19])}\n"
                        f"📅 Expires  : {md_safe(expiry_display(exp))}"
                    )
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb_back())

    elif data == "commands":
        await q.edit_message_text(
            "📋 *Commands*\n\n"
            "👤 *User:*\n"
            "  /start — Main menu\n"
            "  /redeem `<key>` — Activate a key\n"
            "  /status — Check your access\n\n"
            "🛡 *Admin:*\n"
            "  /createkeys `<users> <dur>` — Create key\n"
            "  /bulkkeys `<prefix> <n> <dur>` — Bulk keys\n"
            "  /revokekey `<key>` — Delete a key\n"
            "  /customname `<file> <name>` — Set DB name\n"
            "  /syncgithub — Pull from GitHub\n"
            "  /addadmin `<id>` — Add admin \\(owner\\)\n"
            "  /removeadmin `<id>` — Remove admin \\(owner\\)",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back(),
        )

# ══════════════════════════════════════════════════════
#  CATCH-ALL: any unknown command shows main menu
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
#  MAIN
# ══════════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("createkeys",  createkeys))
    app.add_handler(CommandHandler("bulkkeys",    bulkkeys))
    app.add_handler(CommandHandler("redeem",      redeem))
    app.add_handler(CommandHandler("status",      status_cmd))
    app.add_handler(CommandHandler("addadmin",    addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CommandHandler("revokekey",   revokekey))
    app.add_handler(CommandHandler("customname",  customname))
    app.add_handler(CommandHandler("syncgithub",  syncgithub))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("ZEIJIE BOT starting…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
OUTPUT_PREFIX = "ZEIJIE-VIP-PREMIUM"

# ── GitHub sync — fill these to enable cloud backup ──────────────
# SETUP GUIDE:
#   1. Create a GitHub repo (public or private).
#   2. Add your data.json and database/*.txt files to it.
#   3. Go to GitHub → Settings → Developer Settings
#      → Personal Access Tokens → Classic → Generate New Token
#      → Tick "repo" scope → Copy token.
#   4. Paste values below. Leave blank ("") to disable GitHub sync.
GITHUB_TOKEN  = ""          # e.g. "ghp_xxxxxxxxxxxxxxxx"
GITHUB_REPO   = ""          # e.g. "YourUsername/zeijie-data"
GITHUB_BRANCH = "main"
# ─────────────────────────────────────────────────────────────────

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
    """Escape all MarkdownV2 special characters."""
    result = ""
    for ch in str(text):
        if ch in _MD2_SPECIAL:
            result += "\\" + ch
        else:
            result += ch
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

async def github_push_file(repo_path: str, local_path: str):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    try:
        with open(local_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode()
        url     = f"{GH_BASE}/repos/{GITHUB_REPO}/contents/{repo_path}"
        headers = _gh_headers()
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=headers, params={"ref": GITHUB_BRANCH})
            sha  = resp.json().get("sha") if resp.status_code == 200 else None
            payload = {
                "message": f"auto-update {repo_path}",
                "content": content_b64,
                "branch":  GITHUB_BRANCH,
            }
            if sha:
                payload["sha"] = sha
            r2 = await client.put(url, headers=headers, json=payload)
            if r2.status_code in (200, 201):
                logger.info("GH push OK: %s", repo_path)
            else:
                logger.warning("GH push failed %s: %s", repo_path, r2.text[:200])
    except Exception as e:
        logger.error("GH push error: %s", e)

async def github_pull_file(repo_path: str, local_path: str):
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return
    try:
        url     = f"{GH_BASE}/repos/{GITHUB_REPO}/contents/{repo_path}"
        headers = _gh_headers()
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(url, headers=headers, params={"ref": GITHUB_BRANCH})
            if resp.status_code == 200:
                content = base64.b64decode(resp.json()["content"])
                os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
                with open(local_path, "wb") as f:
                    f.write(content)
                logger.info("GH pull OK: %s", repo_path)
    except Exception as e:
        logger.error("GH pull error: %s", e)

# ══════════════════════════════════════════════════════
#  DATA HELPERS
# ══════════════════════════════════════════════════════
def load() -> dict:
    default = {
        "admins": [], "keys": {}, "members": {},
        "redeemed": {}, "db_names": {}
    }
    if not os.path.exists(DATA_FILE):
        return default
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("data.json corrupted — fresh start.")
        return default
    for k, v in default.items():
        d.setdefault(k, v)
    return d

def save(d: dict):
    tmp = DATA_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)
    except OSError as e:
        logger.error("Save failed: %s", e)

def save_push(d: dict):
    """Save locally and push to GitHub in background."""
    save(d)
    asyncio.create_task(github_push_file("data.json", DATA_FILE))

def is_admin(uid, d) -> bool:
    return str(uid) in [str(x) for x in d.get("admins", [])] or int(uid) == OWNER_ID

def is_expired(rd: dict) -> bool:
    exp = rd.get("expires")
    if not exp:
        return False
    try:
        return datetime.fromisoformat(exp) <= datetime.now()
    except ValueError:
        return False

def has_access(uid, d) -> bool:
    """FIXED: expired keys correctly denied."""
    if is_admin(uid, d):
        return True
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    return not is_expired(rd)   # False when expired

def track(uid, username, first_name, d):
    d.setdefault("members", {})[str(uid)] = {
        "username":   username or "",
        "first_name": first_name or "",
        "last_seen":  datetime.now().isoformat(),
    }

def get_db_files() -> list:
    try:
        return sorted(
            f for f in os.listdir(DB_FOLDER)
            if os.path.isfile(os.path.join(DB_FOLDER, f)) and f.endswith(".txt")
        )
    except FileNotFoundError:
        return []

def count_lines(path: str) -> int:
    try:
        with open(path, "r", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def get_display_name(fname: str, d: dict) -> str:
    return d.get("db_names", {}).get(fname, Path(fname).stem)

# ══════════════════════════════════════════════════════
#  KEY GENERATION — Format: ZEIJIE-PREMIUM-XXXX
# ══════════════════════════════════════════════════════
def generate_key() -> str:
    part = "".join(random.choices(string.digits, k=4))
    return f"ZEIJIE-PREMIUM-{part}"

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
        return timedelta(hours=n),   f"{n} hour{'s' if n != 1 else ''}"
    if "m" in dur and "month" not in dur:
        return timedelta(minutes=n), f"{n} minute{'s' if n != 1 else ''}"
    return timedelta(days=n), f"{n} day{'s' if n != 1 else ''}"

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
    d, r  = divmod(secs, 86400)
    h, r  = divmod(r, 3600)
    m, s  = divmod(r, 60)
    parts = []
    if d: parts.append(f"{d}d")
    if h: parts.append(f"{h}h")
    if m: parts.append(f"{m}m")
    if s and not d: parts.append(f"{s}s")
    return f"{abs_time}  ({''.join(parts) or '< 1s'} left)"

# ══════════════════════════════════════════════════════
#  FILE OUTPUT
# ══════════════════════════════════════════════════════
def output_filename(disp: str) -> str:
    return f"{OUTPUT_PREFIX}-{disp.upper().replace(' ', '_')}.txt"

def file_header(disp: str, lines: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sep = "━" * 38
    return (
        f"♨️ ZEIJIE sᴇᴀʀᴄʜᴇʀ Premium Database ♨️\n"
        f"{sep}\n"
        f"📂 Source: • {disp.upper()}\n"
        f"📄 Lines: {lines}\n"
        f"🕒 Generated: {now}\n"
        f"🔥 Quality: Premium Grade\n"
        f"⚡ Auto-Delete: Enabled (lines removed from source)\n"
        f"{sep}\n\n"
    )

def premium_caption(disp: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "🔮 *PREMIUM FILE GENERATED\\!*\n\n"
        "📊 *GENERATION SUMMARY*\n"
        f"┣ 🎮 Source     : {md_safe(disp.upper())}\n"
        f"┣ 📄 File       : `{md_safe(output_filename(disp))}`\n"
        f"┣ 📜 Lines      : {sent:,}\n"
        f"┣ 🕐 Generated  : {md_safe(now)}\n"
        f"┣ 💾 Remaining  : {remaining:,} lines\n"
        "┣ 🧹 Cleanup    : Done\n\n"
        "🛡 *SECURITY*\n"
        "┣ 🔒 Auto\\-Expiry : 5 minutes\n"
        "┣ 🗑 Auto\\-Delete : Enabled\n"
        "┣ ⚡ Session     : Verified\n\n"
        "⬇️ Download immediately — file deletes in 5 min\n\n"
        "⭐ *Thank you for using ZEIJIE Premium\\!*"
    )

# ══════════════════════════════════════════════════════
#  DATABASE CONSUMER
# ══════════════════════════════════════════════════════
def consume_lines(fpath: str, n: int) -> tuple:
    with open(fpath, "r", errors="ignore") as f:
        all_lines = f.readlines()
    to_send  = all_lines[:n]
    leftover = all_lines[n:]
    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(leftover)
    return "".join(to_send), len(leftover)

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
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{CONTACT_ADMIN.lstrip('@')}")],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key",   callback_data="adm_create")],
        [InlineKeyboardButton("🎉 Bulk Keys",    callback_data="adm_bulk_info")],
        [InlineKeyboardButton("🗝 Active Keys",  callback_data="adm_keys")],
        [InlineKeyboardButton("👥 Admins List",  callback_data="adm_list")],
        [InlineKeyboardButton("👥 All Members",  callback_data="adm_members")],
        [InlineKeyboardButton("🔙 Back",         callback_data="home")],
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
        [InlineKeyboardButton("📞 Contact Admin", url=f"https://t.me/{CONTACT_ADMIN.lstrip('@')}")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")],
    ])

# ══════════════════════════════════════════════════════
#  WELCOME TEXT
# ══════════════════════════════════════════════════════
def build_welcome(first_name, username, uid, d) -> str:
    status = "✅ Active" if has_access(uid, d) else "🔒 No Access"
    line   = random.choice(WELCOME_LINES)
    name   = md_safe(first_name or "Operator")
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

ACCESS_DENIED_MSG = (
    "🔒 *Access Denied*\n\n"
    "You cannot access this database\\.\n"
    "Contact admin to get a key & to access this\\.\n\n"
    f"📞 Admin: {CONTACT_ADMIN}"
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
#  /createkeys <max_users> <duration>
# ══════════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(
            ACCESS_DENIED_MSG, parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_contact()
        )
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "📋 *Usage:*\n`/createkeys <max_users> <duration>`\n\n"
            "*Examples:*\n"
            "  `/createkeys 1 7d`\n"
            "  `/createkeys 3 lifetime`\n\n"
            "_Timer starts when buyer redeems\\._",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    try:
        devices = int(ctx.args[0])
        if devices < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Max users must be a positive integer\\.", parse_mode=ParseMode.MARKDOWN_V2)
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
    logger.info("Key created: %s  dur=%s  devices=%s", key, raw_dur, devices)

    await update.message.reply_text(
        "┌─────────────────────────────┐\n"
        "│   🔑  KEY GENERATED\\!       │\n"
        "└─────────────────────────────┘\n\n"
        f"`{md_safe(key)}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*  : {md_safe(dur_label)}\n"
        f"📅 *Starts*    : On redeem\n"
        f"👥 *Max Users* : {devices}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Timer starts when buyer redeems ✅_",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ══════════════════════════════════════════════════════
#  /bulkkeys <prefix> <count> <duration>
# ══════════════════════════════════════════════════════
async def bulkkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(
            ACCESS_DENIED_MSG, parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_contact()
        )
        return

    if len(ctx.args) < 3:
        await update.message.reply_text(
            "📋 *Usage:*\n`/bulkkeys <prefix> <count> <duration>`\n\n"
            "*Example:*\n`/bulkkeys Zaraki 5 1d`\n\n"
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
        await update.message.reply_text("❌ Count must be between 1 and 50\\.", parse_mode=ParseMode.MARKDOWN_V2)
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
    logger.info("Bulk keys: prefix=%s count=%s dur=%s", prefix, count, raw_dur)

    keys_display = "\n".join(f"`{md_safe(k)}`" for k in keys)
    await update.message.reply_text(
        f"🎉 *{count} Keys Generated Successfully\\!* 🎉\n\n"
        f"{keys_display}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ *Validity \\(each\\)* : {md_safe(dur_label)}\n"
        f"📝 *Status*            : One\\-time use\n"
        f"📅 *Created On*        : {md_safe(now_str)}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✨ Share these keys with your users to grant them access\\!",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ══════════════════════════════════════════════════════
#  /redeem <key>
# ══════════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username, update.effective_user.first_name, d)

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
            "❌ Device limit reached for this key\\.\n\n"
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
    logger.info("Redeemed: %s  uid=%s  expires=%s", key, uid, expires_iso)

    await update.message.reply_text(
        "┌─────────────────────────────┐\n"
        "│   ✅  KEY ACTIVATED\\!       │\n"
        "└─────────────────────────────┘\n\n"
        f"🔑 `{md_safe(key)}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*  : {md_safe(dur_label)}\n"
        f"📅 *Expires*   : {md_safe(expiry_display(expires_iso))}\n"
        "📱 *Device*    : Locked to your account\n"
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
    track(int(uid), update.effective_user.username, update.effective_user.first_name, d)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "👑 *Admin Account*\nFull access granted — no key needed\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            "🔒 *No Active Key*\n\nUse `/redeem <key>` to activate access\\.\n\n"
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
            f"_Contact admin: {CONTACT_ADMIN}_",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
    else:
        await update.message.reply_text(
            "✅ *Access Active*\n\n"
            f"🔑 Key      : `{md_safe(rd['key'])}`\n"
            f"⏱ Duration : {md_safe(rd.get('duration', 'N/A'))}\n"
            f"🕐 Started  : {md_safe(act[:19])}\n"
            f"📅 Expires  : {md_safe(expiry_display(exp))}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )

# ══════════════════════════════════════════════════════
#  /addadmin & /removeadmin — owner only
# ══════════════════════════════════════════════════════
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
        save_push(d)
    await update.message.reply_text(f"✅ Admin added: `{target}`", parse_mode=ParseMode.MARKDOWN_V2)

async def removeadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /removeadmin <user_id>")
        return
    target = str(ctx.args[0])
    if target in [str(a) for a in d["admins"]]:
        d["admins"] = [a for a in d["admins"] if str(a) != target]
        save_push(d)
        await update.message.reply_text(f"✅ Removed: `{target}`", parse_mode=ParseMode.MARKDOWN_V2)
    else:
        await update.message.reply_text(f"⚠️ Not an admin: `{target}`", parse_mode=ParseMode.MARKDOWN_V2)

# ══════════════════════════════════════════════════════
#  /revokekey <key> — admin only
# ══════════════════════════════════════════════════════
async def revokekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)
    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /revokekey <KEY>")
        return
    key = ctx.args[0].strip().upper()
    if key not in d["keys"]:
        await update.message.reply_text("❌ Key not found\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return
    del d["keys"][key]
    d["redeemed"] = {u: v for u, v in d["redeemed"].items() if v.get("key") != key}
    save_push(d)
    await update.message.reply_text(f"✅ Key revoked: `{md_safe(key)}`", parse_mode=ParseMode.MARKDOWN_V2)

# ══════════════════════════════════════════════════════
#  /customname <filename> <display name> — admin only
# ══════════════════════════════════════════════════════
async def customname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    files = get_db_files()
    if len(ctx.args) < 2:
        listing = "\n".join(f"  • `{f}`" for f in files) if files else "  _None_"
        await update.message.reply_text(
            "📋 *Usage:*\n`/customname <filename.txt> <display name>`\n\n"
            "*Your DB files:*\n" + listing + "\n\n"
            "*Example:*\n`/customname garena.txt GARENA`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    fname     = ctx.args[0].strip()
    disp_name = " ".join(ctx.args[1:]).strip()
    fpath     = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        listing = "\n".join(f"  • `{f}`" for f in files) if files else "  _None_"
        await update.message.reply_text(
            f"❌ `{md_safe(fname)}` not found in database folder\\.\n\n"
            f"*Available:*\n{listing}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    d.setdefault("db_names", {})[fname] = disp_name
    save_push(d)
    await update.message.reply_text(
        f"✅ Custom name set\\!\n\n"
        f"📁 File : `{md_safe(fname)}`\n"
        f"🏷 Name : *{md_safe(disp_name)}*",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ══════════════════════════════════════════════════════
#  /syncgithub — admin only
# ══════════════════════════════════════════════════════
async def syncgithub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    if not GITHUB_TOKEN or not GITHUB_REPO:
        await update.message.reply_text(
            "⚠️ GitHub is not configured\\.\n"
            "Set `GITHUB_TOKEN` and `GITHUB_REPO` in the bot config\\.",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    msg = await update.message.reply_text("⏳ Syncing from GitHub…")
    await github_pull_file("data.json", DATA_FILE)
    for fname in get_db_files():
        await github_pull_file(f"database/{fname}", os.path.join(DB_FOLDER, fname))
    await msg.edit_text("✅ Sync complete\\! Data pulled from GitHub\\.", parse_mode=ParseMode.MARKDOWN_V2)

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
            "⚡ *Admin Panel*\n\nChoose an option below:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_admin(),
        )

    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        await q.edit_message_text(
            "🔑 *Create Keys*\n\n"
            "*Single key:*\n`/createkeys <max_users> <duration>`\n\n"
            "*Bulk keys:*\n`/bulkkeys <prefix> <count> <duration>`\n\n"
            "*Key format:* `ZEIJIE\\-PREMIUM\\-XXXX`\n\n"
            "*Examples:*\n"
            "  `/createkeys 1 7d`\n"
            "  `/bulkkeys Zaraki 5 1d`\n\n"
            "_Timer starts when buyer redeems\\._",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back("admin"),
        )

    elif data == "adm_bulk_info":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        await q.edit_message_text(
            "🎉 *Bulk Key Generator*\n\n"
            "Command:\n`/bulkkeys <prefix> <count> <duration>`\n\n"
            "*Example:*\n`/bulkkeys Zaraki 5 1d`\n\n"
            "Output:\n"
            "`Zaraki\\-273852`\n`Zaraki\\-617209`\n`Zaraki\\-679658`\n\n"
            "_Each key is one\\-time use only\\._",
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
                icon = "🟡 Unused" if used_cnt == 0 else ("🟢 Partial" if used_cnt < devices else "🔵 Full")
                block = (
                    f"{icon}\n🔑 `{md_safe(k)}`\n"
                    f"   ⏱ {md_safe(raw_dur)}  👥 {used_cnt}/{devices}"
                )
                for u_id in used_by:
                    rd    = redeemed.get(str(u_id))
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    exp_s = md_safe(expiry_display(rd["expires"]) if rd else "Unknown")
                    block += f"\n   └ {label}: {exp_s}"
                lines.append(block)
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_\\.\\.\\. truncated_"
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb_back("admin"))

    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        admins = d.get("admins", [])
        txt = (
            "👥 *No extra admins\\.*"
            if not admins
            else "👥 *Admins:*\n\n" + "\n".join(f"  • `{a}`" for a in admins)
        )
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb_back("admin"))

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
                uname  = info.get("username", "")
                fname  = info.get("first_name", "")
                label  = f"@{uname}" if uname else md_safe(fname or m_id)
                rd     = redeemed.get(m_id)
                acc    = "✅" if has_access(int(m_id), d) else "🔒"
                exp_s  = md_safe(expiry_display(rd["expires"]) if rd else "No key")
                lines.append(f"{acc} {label} \\(`{m_id}`\\)\n   📅 {exp_s}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_\\.\\.\\. truncated_"
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb_back("admin"))

    elif data == "db":
        files = get_db_files()
        if not files:
            await q.edit_message_text(
                "📂 *Database is empty\\.*\n\nUpload `.txt` files into the `database/` folder\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb_back(),
            )
            return
        lines_txt = ["📂 *Database Files:*\n"]
        for fname in files:
            cnt  = count_lines(os.path.join(DB_FOLDER, fname))
            disp = get_display_name(fname, d)
            lines_txt.append(f"  • *{md_safe(disp)}* — {cnt:,} lines")
        lines_txt.append("\n_Tap a file to generate and download\\._")
        await q.edit_message_text(
            "\n".join(lines_txt),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_db_files(files, d),
        )

    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

        # ── ACCESS CHECK (expired keys blocked) ──
        if not has_access(uid, d):
            await q.answer(
                "🔒 You cannot access this database. Contact admin to get a key.",
                show_alert=True
            )
            return

        fpath = os.path.join(DB_FOLDER, fname)
        if not os.path.isfile(fpath):
            await q.answer("❌ File not found on server.", show_alert=True); return

        total = count_lines(fpath)
        if total == 0:
            await q.answer("⚠️ Database exhausted. Contact admin.", show_alert=True); return

        lines_to_send = min(LINES_PER_USE, total)
        disp          = get_display_name(fname, d)

        raw_content, remaining = consume_lines(fpath, lines_to_send)
        content  = file_header(disp, lines_to_send) + raw_content
        out_name = output_filename(disp)

        buf      = io.BytesIO(content.encode("utf-8"))
        buf.name = out_name

        sent_msg = await q.message.reply_document(
            document=buf,
            filename=out_name,
            caption=premium_caption(disp, lines_to_send, remaining),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        asyncio.create_task(_auto_delete(300, sent_msg))
        asyncio.create_task(github_push_file(f"database/{fname}", fpath))

    elif data == "redeem_info":
        await q.edit_message_text(
            "🔑 *Redeem a Key*\n\n"
            "Send this command:\n`/redeem ZEIJIE-PREMIUM-XXXX`\n\n"
            f"_No key? Contact: {CONTACT_ADMIN}_\n\n"
            "_Access timer starts the moment you redeem\\._",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back(),
        )

    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "👑 *Admin Account*\nFull access granted — no key needed\\."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = (
                    "🔒 *No Active Key*\n\n"
                    "Use `/redeem <key>` to get access\\.\n\n"
                    f"📞 Contact: {CONTACT_ADMIN}"
                )
            else:
                exp     = rd.get("expires")
                expired = is_expired(rd)
                act     = rd.get("activated", "Unknown")
                if expired:
                    txt = (
                        "⛔ *Access Expired*\n\n"
                        f"🔑 Key     : `{md_safe(rd['key'])}`\n"
                        f"📅 Expired : {md_safe(expiry_display(exp))}\n\n"
                        f"_Contact admin: {CONTACT_ADMIN}_"
                    )
                else:
                    txt = (
                        "✅ *Access Active*\n\n"
                        f"🔑 Key      : `{md_safe(rd['key'])}`\n"
                        f"⏱ Duration : {md_safe(rd.get('duration', 'N/A'))}\n"
                        f"🕐 Started  : {md_safe(act[:19])}\n"
                        f"📅 Expires  : {md_safe(expiry_display(exp))}"
                    )
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN_V2, reply_markup=kb_back())

    elif data == "commands":
        await q.edit_message_text(
            "📋 *Commands*\n\n"
            "👤 *User:*\n"
            "  /start — Main menu\n"
            "  /redeem `<key>` — Activate a key\n"
            "  /status — Check your access\n\n"
            "🛡 *Admin:*\n"
            "  /createkeys `<users> <dur>` — Create key\n"
            "  /bulkkeys `<prefix> <n> <dur>` — Bulk keys\n"
            "  /revokekey `<key>` — Delete a key\n"
            "  /customname `<file> <name>` — Set DB name\n"
            "  /syncgithub — Pull from GitHub\n"
            "  /addadmin `<id>` — Add admin \\(owner\\)\n"
            "  /removeadmin `<id>` — Remove admin \\(owner\\)",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back(),
        )

# ══════════════════════════════════════════════════════
#  CATCH-ALL: any unknown command shows main menu
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
#  MAIN
# ══════════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("createkeys",  createkeys))
    app.add_handler(CommandHandler("bulkkeys",    bulkkeys))
    app.add_handler(CommandHandler("redeem",      redeem))
    app.add_handler(CommandHandler("status",      status_cmd))
    app.add_handler(CommandHandler("addadmin",    addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CommandHandler("revokekey",   revokekey))
    app.add_handler(CommandHandler("customname",  customname))
    app.add_handler(CommandHandler("syncgithub",  syncgithub))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("ZEIJIE BOT starting…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
