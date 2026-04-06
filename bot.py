#!/usr/bin/env python3

import os, json, random, string, io, asyncio, logging
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════
#  CONFIG
# ════════════════════════════════════════════════
BOT_TOKEN     = "8715472565:AAE-QZgI4V75ak1ZjgQqMLofxFRR2iLaDwA"
OWNER_ID      = 8420104044
ADMIN_USERNAME = "@Zeijie_s"          # Contact admin username
DATA_FILE     = "data.json"
DB_FOLDER     = "database"
LINES_PER_USE = 250
OUTPUT_PREFIX = "ZEIJIE-VIP-PREMIUM"

os.makedirs(DB_FOLDER, exist_ok=True)

# ════════════════════════════════════════════════
#  LOGO
# ════════════════════════════════════════════════
LOGO_GIF_URL = ""

LOGO_TEXT = (
    "```\n"
    "╔══════════════════════════════════╗\n"
    "║   ███████╗███████╗██╗██╗██╗     ║\n"
    "║   ╚══███╔╝██╔════╝██║██║██║     ║\n"
    "║     ███╔╝ █████╗  ██║██║██║     ║\n"
    "║    ███╔╝  ██╔══╝  ██║██║██║     ║\n"
    "║   ███████╗███████╗██║██║███████╗║\n"
    "║   ╚══════╝╚══════╝╚═╝╚═╝╚══════╝║\n"
    "║     V  I  P  ·  P  R  E  M      ║\n"
    "╚══════════════════════════════════╝\n"
    "```"
)

# ════════════════════════════════════════════════
#  WELCOME MESSAGES
# ════════════════════════════════════════════════
WELCOME_LINES = [
    "⚡ *ZEIJIE BOT* is locked, loaded, and ready for action.",
    "🔥 Welcome to *ZEIJIE BOT* — your premium gateway.",
    "🌐 *ZEIJIE BOT* online — Precision · Power · Premium.",
    "🛡 *ZEIJIE BOT* activated — built different, built better.",
    "💎 You've entered *ZEIJIE BOT* — where premium lives.",
    "🚀 *ZEIJIE BOT* is live — Let's get to work.",
    "🎯 *ZEIJIE BOT* standing by — the real deal starts here.",
    "👾 *ZEIJIE BOT* loaded — No limits, only premium access.",
]

def random_welcome() -> str:
    return random.choice(WELCOME_LINES)

# ════════════════════════════════════════════════
#  MARKDOWN SAFETY
# ════════════════════════════════════════════════
def md_safe(text: str) -> str:
    for ch in ("_", "*", "`", "[", "]", "(", ")", "~", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"):
        text = text.replace(ch, f"\\{ch}")
    return text

def md_safe_v1(text: str) -> str:
    """For MARKDOWN (v1) mode."""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text

# ════════════════════════════════════════════════
#  DATA HELPERS
# ════════════════════════════════════════════════
def load() -> dict:
    default = {"admins": [], "keys": {}, "members": {}, "redeemed": {}}
    if not os.path.exists(DATA_FILE):
        return default
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("data.json corrupted — starting fresh.")
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
        logger.error("Failed to save data.json: %s", e)

def is_admin(uid, d) -> bool:
    return str(uid) in [str(x) for x in d.get("admins", [])] or int(uid) == OWNER_ID

def has_access(uid, d) -> bool:
    if is_admin(uid, d):
        return True
    uid_str = str(uid)
    rd = d.get("redeemed", {}).get(uid_str)
    if not rd:
        return False
    exp = rd.get("expires")
    if not exp:
        key = rd.get("key")
        if key and key in d.get("keys", {}):
            return True
        return False
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
    try:
        return sorted(
            f for f in os.listdir(DB_FOLDER)
            if os.path.isfile(os.path.join(DB_FOLDER, f))
        )
    except FileNotFoundError:
        return []

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
    number = "".join(random.choices(string.digits, k=6))
    return f"ZEIJIE-PREMIUM-{number}"

def parse_duration(raw: str):
    dur = raw.strip().lower()
    if dur in ("lifetime", "forever", "inf"):
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

# ════════════════════════════════════════════════
#  EXPIRY DISPLAY
# ════════════════════════════════════════════════
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

    delta      = exp_dt - now
    total_secs = int(delta.total_seconds())
    days_rem   = total_secs // 86400
    hours_rem  = (total_secs % 86400) // 3600
    mins_rem   = (total_secs % 3600)  // 60
    secs_rem   = total_secs % 60

    parts = []
    if days_rem:  parts.append(f"{days_rem}d")
    if hours_rem: parts.append(f"{hours_rem}h")
    if mins_rem:  parts.append(f"{mins_rem}m")
    if secs_rem and not days_rem: parts.append(f"{secs_rem}s")

    remaining_str = " ".join(parts) if parts else "< 1s"
    return f"{abs_time}  ({remaining_str} left)"

# ════════════════════════════════════════════════
#  OUTPUT FILENAME BUILDER
# ════════════════════════════════════════════════
def output_filename(stem: str) -> str:
    clean = stem.upper().replace(" ", "_")
    return f"{OUTPUT_PREFIX}-{clean}.txt"

# ════════════════════════════════════════════════
#  NO ACCESS MESSAGE
# ════════════════════════════════════════════════
def no_access_text() -> str:
    return (
        "🔒 *Access Denied*\n\n"
        "You cannot access this database\\.\n"
        f"Contact admin to get a key & to access this\\.\n\n"
        f"👤 *Admin:* {md_safe(ADMIN_USERNAME)}"
    )

# ════════════════════════════════════════════════
#  MESSAGE BUILDERS
# ════════════════════════════════════════════════
def key_message_single(key: str, duration_label: str, devices: int, created_at: str) -> str:
    return (
        "┌─────────────────────────────┐\n"
        "│  🔑  KEY GENERATED          │\n"
        "└─────────────────────────────┘\n\n"
        f"`{key}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*   : {duration_label}\n"
        f"📅 *Starts*     : On redeem\n"
        f"👥 *Max Users*  : {devices}\n"
        f"📅 *Created On* : {created_at}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Timer starts when the buyer redeems this key ✅_"
    )

def keys_batch_message(keys: list, duration_label: str, created_at: str) -> str:
    count = len(keys)
    key_lines = "\n".join(f"`{k}`" for k in keys)
    return (
        f"🎉 *{count} Key{'s' if count > 1 else ''} Generated Successfully\\!* 🎉\n\n"
        f"{key_lines}\n\n"
        f"⏳ *Validity \\(each\\):* ⏱️ {md_safe(duration_label)}\n"
        f"📝 *Status:* One\\-time use\n"
        f"📅 *Created On:* {md_safe(created_at)}\n\n"
        "✨ _Share these keys with your users to grant them access\\!_"
    )

def premium_summary(fname_stem: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out_name = output_filename(fname_stem)
    return (
        "🔮 *PREMIUM FILE GENERATED\\!*\n\n"
        "📊 *GENERATION SUMMARY*\n"
        f"┣ 🎮 Source     : {md_safe(fname_stem.upper())}\n"
        f"┣ 📄 File       : `{md_safe(out_name)}`\n"
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

# ════════════════════════════════════════════════
#  KEYBOARDS
# ════════════════════════════════════════════════
def kb_main(uid, d) -> InlineKeyboardMarkup:
    rows = []
    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")])
    rows += [
        [
            InlineKeyboardButton("📂 Database",  callback_data="db"),
            InlineKeyboardButton("🔑 Redeem",    callback_data="redeem_info"),
        ],
        [
            InlineKeyboardButton("👤 My Status", callback_data="status"),
            InlineKeyboardButton("📋 Commands",  callback_data="commands"),
        ],
        [
            InlineKeyboardButton("📞 Contact Admin", callback_data="contact_admin"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key",   callback_data="adm_create")],
        [InlineKeyboardButton("🗝 Active Keys",  callback_data="adm_keys")],
        [InlineKeyboardButton("👥 Admins List",  callback_data="adm_list")],
        [InlineKeyboardButton("👥 All Members",  callback_data="adm_members")],
        [InlineKeyboardButton("🔙 Back",         callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "🔙 Back to Admin" if dest == "admin" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

def kb_db_files(files: list) -> InlineKeyboardMarkup:
    rows = []
    for fname in files:
        fpath = os.path.join(DB_FOLDER, fname)
        cnt   = count_lines(fpath)
        label = f"📄 {Path(fname).stem}  ({cnt:,} lines)"
        rows.append([InlineKeyboardButton(label, callback_data=f"dbfile:{fname}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)

# ════════════════════════════════════════════════
#  WELCOME TEXT BUILDER
# ════════════════════════════════════════════════
def build_welcome(first_name: str, username, uid, d: dict) -> str:
    status       = "✅ Active" if has_access(uid, d) else "🔒 No Access"
    welcome_line = random_welcome()
    safe_name    = md_safe(first_name or "Operator")
    user_line    = f"👤 *{safe_name}*"
    if username:
        user_line += f"  \\(@{md_safe(username)}\\)"
    return (
        f"{welcome_line}\n\n"
        f"{user_line}\n"
        f"🔐 Status : {status}"
    )

# ════════════════════════════════════════════════
#  AUTO-DELETE HELPER
# ════════════════════════════════════════════════
async def _auto_delete(delay: int, *messages):
    await asyncio.sleep(delay)
    for m in messages:
        try:
            await m.delete()
        except Exception:
            pass

# ════════════════════════════════════════════════
#  DATABASE DECREASE HELPER
# ════════════════════════════════════════════════
def consume_lines(fpath: str, n: int) -> tuple:
    with open(fpath, "r", errors="ignore") as f:
        all_lines = f.readlines()
    to_send   = all_lines[:n]
    leftover  = all_lines[n:]
    remaining = len(leftover)
    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(leftover)
    return "".join(to_send), remaining

# ════════════════════════════════════════════════
#  SAFE EDIT HELPERS
# ════════════════════════════════════════════════
async def safe_edit(q, text, parse_mode, reply_markup=None):
    """Try edit_message_text, fall back to edit_message_caption."""
    kwargs = {"parse_mode": parse_mode}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    try:
        await q.edit_message_text(text, **kwargs)
    except Exception:
        try:
            await q.edit_message_caption(caption=text, **kwargs)
        except Exception as e:
            logger.warning("safe_edit failed: %s", e)

# ════════════════════════════════════════════════
#  ENSURE USER IS TRACKED (for commands without /start)
# ════════════════════════════════════════════════
async def ensure_tracked(update: Update):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    return d

# ════════════════════════════════════════════════
#  /start — sends GIF + welcome text
# ════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)

    welcome_text = build_welcome(user.first_name, user.username, user.id, d)
    kb           = kb_main(user.id, d)

    try:
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb,
        )
    except Exception as e:
        logger.error("start failed: %s", e)

# ════════════════════════════════════════════════
#  /createkeys — admin only
# ════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(update.effective_user.id, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(
            f"❌ This command is for admins only\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "📋 *Usage:*\n"
            "`/createkeys <count> <max\\_users> <duration>`\n\n"
            "*Or single key:*\n"
            "`/createkeys <max\\_users> <duration>`\n\n"
            "*Duration examples:*\n"
            "  `10d` — 10 days\n"
            "  `2h` — 2 hours\n"
            "  `30m` — 30 minutes\n"
            "  `lifetime` — never expires",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    count   = 1
    devices = 1

    if len(ctx.args) >= 3:
        try:
            count_try   = int(ctx.args[0])
            devices_try = int(ctx.args[1])
            raw_dur     = " ".join(ctx.args[2:])
            count   = count_try
            devices = devices_try
        except ValueError:
            try:
                devices = int(ctx.args[0])
                raw_dur = " ".join(ctx.args[1:])
            except ValueError:
                await update.message.reply_text("❌ Invalid arguments. First arg must be a number.")
                return
    else:
        try:
            devices = int(ctx.args[0])
            raw_dur = " ".join(ctx.args[1:])
        except ValueError:
            await update.message.reply_text("❌ Max users must be a positive integer.")
            return

    if count < 1 or count > 50:
        await update.message.reply_text("❌ Key count must be between 1 and 50.")
        return
    if devices < 1:
        await update.message.reply_text("❌ Max users must be a positive integer.")
        return

    try:
        td, duration_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid duration\\.\n\nExamples: `10d` / `2h` / `30m` / `lifetime`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    created_at     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_keys = []

    for _ in range(count):
        key = generate_key()
        while key in d["keys"]:
            key = generate_key()
        d["keys"][key] = {
            "devices":     devices,
            "duration":    raw_dur,
            "expires":     None,
            "used_by":     [],
            "user_expiry": {},
            "created_by":  str(uid),
            "created_at":  datetime.now().isoformat(),
        }
        generated_keys.append(key)

    save(d)
    logger.info("%d key(s) created: duration=%s devices=%s by=%s", count, raw_dur, devices, uid)

    if count == 1:
        msg = key_message_single(generated_keys[0], duration_label, devices, created_at)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    else:
        msg = keys_batch_message(generated_keys, duration_label, created_at)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

# ════════════════════════════════════════════════
#  /redeem <key>
# ════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if not ctx.args:
        await update.message.reply_text(
            "🔑 *Usage:*\n`/redeem ZEIJIE-PREMIUM-XXXXXX`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text(
            f"❌ *Invalid key\\.*\n\nDouble\\-check and try again\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    k = d["keys"][key]

    if uid in k.get("used_by", []):
        existing_rd = d.get("redeemed", {}).get(uid)
        if existing_rd and existing_rd.get("key") == key:
            exp = existing_rd.get("expires")
            if exp:
                try:
                    if datetime.fromisoformat(exp) <= datetime.now():
                        await update.message.reply_text(
                            f"⛔ *Your key has expired\\.*\n\n"
                            f"Contact admin for a new key: {md_safe(ADMIN_USERNAME)}",
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                        return
                except ValueError:
                    pass
        await update.message.reply_text("⚠️ This key is already activated on your account.")
        return

    if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
        await update.message.reply_text(
            f"❌ Device limit reached for this key\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
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
    save(d)
    logger.info("Key redeemed: %s  by uid=%s  expires=%s", key, uid, expires_iso)

    await update.message.reply_text(
        "┌─────────────────────────────┐\n"
        "│  ✅  KEY ACTIVATED!         │\n"
        "└─────────────────────────────┘\n\n"
        f"`{key}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*   : {dur_label}\n"
        f"📅 *Expires*    : {expiry_display(expires_iso)}\n"
        f"📱 *Device*     : Locked to your account\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Your access timer has started now._ ✅",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /status
# ════════════════════════════════════════════════
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "👑 *Admin Account*\nFull access granted — no key needed.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            f"🔒 *No Active Key*\n\nUse `/redeem <key>` to activate access\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    exp     = rd.get("expires")
    expired = False
    if exp:
        try:
            expired = datetime.fromisoformat(exp) <= datetime.now()
        except ValueError:
            pass

    activated = rd.get("activated", "Unknown")
    if expired:
        txt = (
            "⛔ *Access Expired*\n\n"
            f"🔑 Key     : `{rd['key']}`\n"
            f"📅 Expired : {expiry_display(exp)}\n\n"
            f"_Contact admin for a new key: {ADMIN_USERNAME}_"
        )
        await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)
    else:
        txt = (
            "✅ *Access Active*\n\n"
            f"🔑 Key      : `{rd['key']}`\n"
            f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
            f"🕐 Started  : {activated[:19]}\n"
            f"📅 Expires  : {expiry_display(exp)}"
        )
        await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

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
    if target not in [str(a) for a in d["admins"]]:
        d["admins"].append(target)
        save(d)
        logger.info("Admin added: %s", target)
    await update.message.reply_text(
        f"✅ Admin added: `{target}`", parse_mode=ParseMode.MARKDOWN
    )

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
    if target in [str(a) for a in d["admins"]]:
        d["admins"] = [a for a in d["admins"] if str(a) != target]
        save(d)
        logger.info("Admin removed: %s", target)
        await update.message.reply_text(
            f"✅ Admin removed: `{target}`", parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"⚠️ User `{target}` is not an admin.", parse_mode=ParseMode.MARKDOWN
        )

# ════════════════════════════════════════════════
#  /revokekey <key>  — admin only
# ════════════════════════════════════════════════
async def revokekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /revokekey <KEY>")
        return
    key = ctx.args[0].strip().upper()
    if key not in d["keys"]:
        await update.message.reply_text("❌ Key not found.")
        return
    del d["keys"][key]
    d["redeemed"] = {u: v for u, v in d["redeemed"].items() if v.get("key") != key}
    save(d)
    await update.message.reply_text(
        f"✅ Key revoked: `{key}`\n_All users on this key lost access._",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /getfile <filename>  — premium users
# ════════════════════════════════════════════════
async def getfile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not has_access(uid, d):
        await update.message.reply_text(
            no_access_text(),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    files = get_db_files()
    if not files:
        await update.message.reply_text("📂 No files available in the database.")
        return

    if not ctx.args:
        listing = "\n".join(
            f"  • `{f}` — {count_lines(os.path.join(DB_FOLDER, f)):,} lines"
            for f in files
        )
        await update.message.reply_text(
            f"📂 *Available files:*\n\n{listing}\n\nUsage: `/getfile <filename>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    fname = ctx.args[0].strip()
    fpath = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        await update.message.reply_text(
            f"❌ File `{md_safe_v1(fname)}` not found.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    total = count_lines(fpath)
    if total == 0:
        await update.message.reply_text(
            f"⚠️ `{md_safe_v1(fname)}` is empty or has been exhausted.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    lines_to_send = min(LINES_PER_USE, total)
    content, remaining = consume_lines(fpath, lines_to_send)

    stem     = Path(fname).stem
    out_name = output_filename(stem)
    buf      = io.BytesIO(content.encode("utf-8"))
    buf.name = out_name

    sent_msg = await update.message.reply_document(
        document=buf,
        filename=out_name,
        caption=premium_summary(stem, lines_to_send, remaining),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    asyncio.create_task(_auto_delete(300, sent_msg))

# ════════════════════════════════════════════════
#  /contact — contact admin
# ════════════════════════════════════════════════
async def contact_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    track(update.effective_user.id, update.effective_user.username,
          update.effective_user.first_name, d)
    await update.message.reply_text(
        f"📞 *Contact Admin*\n\n"
        f"For keys, access issues, or support:\n\n"
        f"👤 Admin: {md_safe(ADMIN_USERNAME)}\n\n"
        f"_You cannot access this database without a key\\._\n"
        f"_Contact admin to get a key & gain access\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ════════════════════════════════════════════════
#  UNKNOWN COMMAND HANDLER
#  Lets buyers/admins use commands without /start
# ════════════════════════════════════════════════
async def unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    # Show them the menu so they can navigate
    welcome_text = build_welcome(user.first_name, user.username, user.id, d)
    kb           = kb_main(user.id, d)
    try:
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning("unknown_command reply failed: %s", e)

# ════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ════════════════════════════════════════════════
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    d    = load()
    uid  = q.from_user.id
    data = q.data
    await q.answer()

    track(uid, q.from_user.username, q.from_user.first_name, d)
    save(d)

    # ── Home ──────────────────────────────────────────────────────
    if data == "home":
        welcome_text = build_welcome(q.from_user.first_name, q.from_user.username, uid, d)
        await safe_edit(q, welcome_text, ParseMode.MARKDOWN_V2, kb_main(uid, d))

    # ── Admin Panel ───────────────────────────────────────────────
    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        await safe_edit(
            q,
            "⚡ *Admin Panel*\n\nChoose an option below:",
            ParseMode.MARKDOWN,
            kb_admin(),
        )

    # ── Create Key info ───────────────────────────────────────────
    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        txt = (
            "🔑 *Create Keys*\n\n"
            "Send this command in chat:\n\n"
            "*Single key:*\n"
            "`/createkeys <max\\_users> <duration>`\n\n"
            "*Multiple keys:*\n"
            "`/createkeys <count> <max\\_users> <duration>`\n\n"
            "*Key format:* `ZEIJIE\\-PREMIUM\\-XXXXXX`\n\n"
            "*Examples:*\n"
            "  `/createkeys 1 7d` — 1 key, 7 days\n"
            "  `/createkeys 5 1 1m` — 5 keys, 1 min each\n"
            "  `/createkeys 3 1 lifetime`\n\n"
            "_Timer starts when buyer redeems the key\\._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back("admin"))

    # ── Active Keys ───────────────────────────────────────────────
    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return

        keys     = d.get("keys", {})
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})

        if not keys:
            txt = "🗝 *No keys created yet.*\n\nUse `/createkeys <users> <duration>` to create one."
        else:
            lines = [f"🗝 *All Keys ({len(keys)}):*\n"]
            for k, v in keys.items():
                used_by  = v.get("used_by", [])
                devices  = v.get("devices", 1)
                raw_dur  = v.get("duration", "?")
                used_cnt = len(used_by)

                if used_cnt == 0:
                    status_icon = "🟡 Unused"
                elif used_cnt < devices:
                    status_icon = "🟢 Partial"
                else:
                    status_icon = "🔵 Full"

                block = (
                    f"{status_icon}\n"
                    f"🔑 `{k}`\n"
                    f"   ⏱ Duration : {raw_dur}\n"
                    f"   👥 Used     : {used_cnt}/{devices}"
                )

                for u_id in used_by:
                    rd    = redeemed.get(str(u_id))
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    exp_str = expiry_display(rd["expires"]) if rd else "Unknown"
                    if rd and rd.get("expires"):
                        try:
                            if datetime.fromisoformat(rd["expires"]) <= datetime.now():
                                exp_str += " ⛔ EXPIRED"
                        except ValueError:
                            pass
                    block += f"\n   └ {label}: {exp_str}"

                lines.append(block)

            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_... truncated_"

        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── Admins List ───────────────────────────────────────────────
    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        admins = d.get("admins", [])
        txt = (
            "👥 *No extra admins.*\n_(Owner always has full access)_"
            if not admins
            else "👥 *Admins:*\n\n" + "\n".join(f"  • `{a}`" for a in admins)
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── All Members ───────────────────────────────────────────────
    elif data == "adm_members":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        members  = d.get("members", {})
        redeemed = d.get("redeemed", {})
        if not members:
            txt = "👥 *No members yet.*"
        else:
            lines = [f"👥 *Members ({len(members)}):*\n"]
            for m_id, info in members.items():
                uname   = info.get("username", "")
                fname   = info.get("first_name", "")
                label   = f"@{uname}" if uname else md_safe_v1(fname or m_id)
                rd      = redeemed.get(m_id)
                acc     = "✅" if has_access(int(m_id), d) else "🔒"
                exp_str = expiry_display(rd["expires"]) if rd else "No key"
                lines.append(f"{acc} {label} (`{m_id}`)\n   📅 {exp_str}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_... truncated_"
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── Database ──────────────────────────────────────────────────
    elif data == "db":
        if not has_access(uid, d):
            await safe_edit(q, no_access_text(), ParseMode.MARKDOWN_V2, kb_back())
            return

        files = get_db_files()
        if not files:
            txt = (
                "📂 *Database is empty\\.*\n\n"
                "Upload `.txt` files into the `database/` folder on the server\\."
            )
            await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())
            return

        lines = ["📂 *Database Files:*\n"]
        for fname in files:
            cnt = count_lines(os.path.join(DB_FOLDER, fname))
            lines.append(f"  • `{fname}` — {cnt:,} lines")
        lines.append("\n_Tap a file below to generate and download\\._")
        txt = "\n".join(lines)

        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_db_files(files))

    # ── Database File Selected (download) ─────────────────────────
    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

        if not has_access(uid, d):
            await q.answer(
                "🔒 You cannot access this database. Contact admin to get a key.",
                show_alert=True,
            )
            return

        fpath = os.path.join(DB_FOLDER, fname)
        if not os.path.isfile(fpath):
            await q.answer("❌ File not found on server.", show_alert=True)
            return

        total = count_lines(fpath)
        if total == 0:
            await q.answer(
                "⚠️ This file is empty or exhausted. Contact admin.", show_alert=True
            )
            return

        lines_to_send = min(LINES_PER_USE, total)
        content, remaining = consume_lines(fpath, lines_to_send)

        stem     = Path(fname).stem
        out_name = output_filename(stem)
        buf      = io.BytesIO(content.encode("utf-8"))
        buf.name = out_name

        sent_msg = await q.message.reply_document(
            document=buf,
            filename=out_name,
            caption=premium_summary(stem, lines_to_send, remaining),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        asyncio.create_task(_auto_delete(300, sent_msg))

    # ── Redeem Info ───────────────────────────────────────────────
    elif data == "redeem_info":
        txt = (
            "🔑 *Redeem a Key*\n\n"
            "Send this command:\n`/redeem ZEIJIE-PREMIUM-XXXXXX`\n\n"
            "_Your access timer starts the moment you redeem._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Status ────────────────────────────────────────────────────
    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "👑 *Admin Account*\nFull access granted — no key needed."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = (
                    f"🔒 *No Active Key*\n\nUse `/redeem <key>` to get access\\.\n\n"
                    f"Contact admin: {md_safe(ADMIN_USERNAME)}"
                )
                await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())
                return
            else:
                exp     = rd.get("expires")
                expired = False
                if exp:
                    try:
                        expired = datetime.fromisoformat(exp) <= datetime.now()
                    except ValueError:
                        pass
                activated = rd.get("activated", "Unknown")
                if expired:
                    txt = (
                        "⛔ *Access Expired*\n\n"
                        f"🔑 Key     : `{rd['key']}`\n"
                        f"📅 Expired : {expiry_display(exp)}\n\n"
                        f"_Contact admin for a new key: {ADMIN_USERNAME}_"
                    )
                else:
                    txt = (
                        "✅ *Access Active*\n\n"
                        f"🔑 Key      : `{rd['key']}`\n"
                        f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
                        f"🕐 Started  : {activated[:19]}\n"
                        f"📅 Expires  : {expiry_display(exp)}"
                    )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Commands ──────────────────────────────────────────────────
    elif data == "commands":
        txt = (
            "📋 *Commands*\n\n"
            "👤 *User:*\n"
            "  /start — Main menu\n"
            "  /redeem `<key>` — Activate a key\n"
            "  /status — Check your access\n"
            "  /getfile `<filename>` — Download file\n"
            "  /contact — Contact admin\n\n"
            "🛡 *Admin:*\n"
            "  /createkeys `<count> <users> <dur>` — Bulk create\n"
            "  /createkeys `<users> <duration>` — Single key\n"
            "  /revokekey `<key>` — Delete a key\n"
            "  /addadmin `<id>` — Add admin (owner only)\n"
            "  /removeadmin `<id>` — Remove admin (owner only)\n\n"
            f"📞 *Contact Admin:* {ADMIN_USERNAME}"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Contact Admin ─────────────────────────────────────────────
    elif data == "contact_admin":
        txt = (
            f"📞 *Contact Admin*\n\n"
            f"For keys, access issues, or support:\n\n"
            f"👤 Admin: {md_safe(ADMIN_USERNAME)}\n\n"
            f"_You cannot access this database without a key\\._\n"
            f"_Contact admin to get a key & gain access\\._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())

# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════
async def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("createkeys",   createkeys))
    app.add_handler(CommandHandler("redeem",       redeem))
    app.add_handler(CommandHandler("status",       status_cmd))
    app.add_handler(CommandHandler("addadmin",     addadmin))
    app.add_handler(CommandHandler("removeadmin",  removeadmin))
    app.add_handler(CommandHandler("getfile",      getfile))
    app.add_handler(CommandHandler("revokekey",    revokekey))
    app.add_handler(CommandHandler("contact",      contact_cmd))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(button))

    # Unknown commands — show menu so users don't need /start
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("ZEIJIE BOT starting — polling...")
    await app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    asyncio.run(main())

LOGO_TEXT = (
    "```\n"
    "╔══════════════════════════════════╗\n"
    "║   ███████╗███████╗██╗██╗██╗     ║\n"
    "║   ╚══███╔╝██╔════╝██║██║██║     ║\n"
    "║     ███╔╝ █████╗  ██║██║██║     ║\n"
    "║    ███╔╝  ██╔══╝  ██║██║██║     ║\n"
    "║   ███████╗███████╗██║██║███████╗║\n"
    "║   ╚══════╝╚══════╝╚═╝╚═╝╚══════╝║\n"
    "║     V  I  P  ·  P  R  E  M      ║\n"
    "╚══════════════════════════════════╝\n"
    "```"
)

# ════════════════════════════════════════════════
#  WELCOME MESSAGES
# ════════════════════════════════════════════════
WELCOME_LINES = [
    "⚡ *ZEIJIE BOT* is locked, loaded, and ready for action.",
    "🔥 Welcome to *ZEIJIE BOT* — your premium gateway.",
    "🌐 *ZEIJIE BOT* online — Precision · Power · Premium.",
    "🛡 *ZEIJIE BOT* activated — built different, built better.",
    "💎 You've entered *ZEIJIE BOT* — where premium lives.",
    "🚀 *ZEIJIE BOT* is live — Let's get to work.",
    "🎯 *ZEIJIE BOT* standing by — the real deal starts here.",
    "👾 *ZEIJIE BOT* loaded — No limits, only premium access.",
]

def random_welcome() -> str:
    return random.choice(WELCOME_LINES)

# ════════════════════════════════════════════════
#  MARKDOWN SAFETY
# ════════════════════════════════════════════════
def md_safe(text: str) -> str:
    for ch in ("_", "*", "`", "[", "]", "(", ")", "~", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"):
        text = text.replace(ch, f"\\{ch}")
    return text

def md_safe_v1(text: str) -> str:
    """For MARKDOWN (v1) mode."""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text

# ════════════════════════════════════════════════
#  DATA HELPERS
# ════════════════════════════════════════════════
def load() -> dict:
    default = {"admins": [], "keys": {}, "members": {}, "redeemed": {}}
    if not os.path.exists(DATA_FILE):
        return default
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("data.json corrupted — starting fresh.")
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
        logger.error("Failed to save data.json: %s", e)

def is_admin(uid, d) -> bool:
    return str(uid) in [str(x) for x in d.get("admins", [])] or int(uid) == OWNER_ID

def has_access(uid, d) -> bool:
    if is_admin(uid, d):
        return True
    uid_str = str(uid)
    rd = d.get("redeemed", {}).get(uid_str)
    if not rd:
        return False
    exp = rd.get("expires")
    if not exp:
        key = rd.get("key")
        if key and key in d.get("keys", {}):
            return True
        return False
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
    try:
        return sorted(
            f for f in os.listdir(DB_FOLDER)
            if os.path.isfile(os.path.join(DB_FOLDER, f))
        )
    except FileNotFoundError:
        return []

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
    number = "".join(random.choices(string.digits, k=6))
    return f"ZEIJIE-PREMIUM-{number}"

def parse_duration(raw: str):
    dur = raw.strip().lower()
    if dur in ("lifetime", "forever", "inf"):
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

# ════════════════════════════════════════════════
#  EXPIRY DISPLAY
# ════════════════════════════════════════════════
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

    delta      = exp_dt - now
    total_secs = int(delta.total_seconds())
    days_rem   = total_secs // 86400
    hours_rem  = (total_secs % 86400) // 3600
    mins_rem   = (total_secs % 3600)  // 60
    secs_rem   = total_secs % 60

    parts = []
    if days_rem:  parts.append(f"{days_rem}d")
    if hours_rem: parts.append(f"{hours_rem}h")
    if mins_rem:  parts.append(f"{mins_rem}m")
    if secs_rem and not days_rem: parts.append(f"{secs_rem}s")

    remaining_str = " ".join(parts) if parts else "< 1s"
    return f"{abs_time}  ({remaining_str} left)"

# ════════════════════════════════════════════════
#  OUTPUT FILENAME BUILDER
# ════════════════════════════════════════════════
def output_filename(stem: str) -> str:
    clean = stem.upper().replace(" ", "_")
    return f"{OUTPUT_PREFIX}-{clean}.txt"

# ════════════════════════════════════════════════
#  NO ACCESS MESSAGE
# ════════════════════════════════════════════════
def no_access_text() -> str:
    return (
        "🔒 *Access Denied*\n\n"
        "You cannot access this database\\.\n"
        f"Contact admin to get a key & to access this\\.\n\n"
        f"👤 *Admin:* {md_safe(ADMIN_USERNAME)}"
    )

# ════════════════════════════════════════════════
#  MESSAGE BUILDERS
# ════════════════════════════════════════════════
def key_message_single(key: str, duration_label: str, devices: int, created_at: str) -> str:
    return (
        "┌─────────────────────────────┐\n"
        "│  🔑  KEY GENERATED          │\n"
        "└─────────────────────────────┘\n\n"
        f"`{key}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*   : {duration_label}\n"
        f"📅 *Starts*     : On redeem\n"
        f"👥 *Max Users*  : {devices}\n"
        f"📅 *Created On* : {created_at}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Timer starts when the buyer redeems this key ✅_"
    )

def keys_batch_message(keys: list, duration_label: str, created_at: str) -> str:
    count = len(keys)
    key_lines = "\n".join(f"`{k}`" for k in keys)
    return (
        f"🎉 *{count} Key{'s' if count > 1 else ''} Generated Successfully\\!* 🎉\n\n"
        f"{key_lines}\n\n"
        f"⏳ *Validity \\(each\\):* ⏱️ {md_safe(duration_label)}\n"
        f"📝 *Status:* One\\-time use\n"
        f"📅 *Created On:* {md_safe(created_at)}\n\n"
        "✨ _Share these keys with your users to grant them access\\!_"
    )

def premium_summary(fname_stem: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out_name = output_filename(fname_stem)
    return (
        "🔮 *PREMIUM FILE GENERATED\\!*\n\n"
        "📊 *GENERATION SUMMARY*\n"
        f"┣ 🎮 Source     : {md_safe(fname_stem.upper())}\n"
        f"┣ 📄 File       : `{md_safe(out_name)}`\n"
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

# ════════════════════════════════════════════════
#  KEYBOARDS
# ════════════════════════════════════════════════
def kb_main(uid, d) -> InlineKeyboardMarkup:
    rows = []
    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")])
    rows += [
        [
            InlineKeyboardButton("📂 Database",  callback_data="db"),
            InlineKeyboardButton("🔑 Redeem",    callback_data="redeem_info"),
        ],
        [
            InlineKeyboardButton("👤 My Status", callback_data="status"),
            InlineKeyboardButton("📋 Commands",  callback_data="commands"),
        ],
        [
            InlineKeyboardButton("📞 Contact Admin", callback_data="contact_admin"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key",   callback_data="adm_create")],
        [InlineKeyboardButton("🗝 Active Keys",  callback_data="adm_keys")],
        [InlineKeyboardButton("👥 Admins List",  callback_data="adm_list")],
        [InlineKeyboardButton("👥 All Members",  callback_data="adm_members")],
        [InlineKeyboardButton("🔙 Back",         callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "🔙 Back to Admin" if dest == "admin" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

def kb_db_files(files: list) -> InlineKeyboardMarkup:
    rows = []
    for fname in files:
        fpath = os.path.join(DB_FOLDER, fname)
        cnt   = count_lines(fpath)
        label = f"📄 {Path(fname).stem}  ({cnt:,} lines)"
        rows.append([InlineKeyboardButton(label, callback_data=f"dbfile:{fname}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)

# ════════════════════════════════════════════════
#  WELCOME TEXT BUILDER
# ════════════════════════════════════════════════
def build_welcome(first_name: str, username, uid, d: dict) -> str:
    status       = "✅ Active" if has_access(uid, d) else "🔒 No Access"
    welcome_line = random_welcome()
    safe_name    = md_safe(first_name or "Operator")
    user_line    = f"👤 *{safe_name}*"
    if username:
        user_line += f"  \\(@{md_safe(username)}\\)"
    return (
        f"{welcome_line}\n\n"
        f"{user_line}\n"
        f"🔐 Status : {status}"
    )

# ════════════════════════════════════════════════
#  AUTO-DELETE HELPER
# ════════════════════════════════════════════════
async def _auto_delete(delay: int, *messages):
    await asyncio.sleep(delay)
    for m in messages:
        try:
            await m.delete()
        except Exception:
            pass

# ════════════════════════════════════════════════
#  DATABASE DECREASE HELPER
# ════════════════════════════════════════════════
def consume_lines(fpath: str, n: int) -> tuple:
    with open(fpath, "r", errors="ignore") as f:
        all_lines = f.readlines()
    to_send   = all_lines[:n]
    leftover  = all_lines[n:]
    remaining = len(leftover)
    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(leftover)
    return "".join(to_send), remaining

# ════════════════════════════════════════════════
#  SAFE EDIT HELPERS
# ════════════════════════════════════════════════
async def safe_edit(q, text, parse_mode, reply_markup=None):
    """Try edit_message_text, fall back to edit_message_caption."""
    kwargs = {"parse_mode": parse_mode}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    try:
        await q.edit_message_text(text, **kwargs)
    except Exception:
        try:
            await q.edit_message_caption(caption=text, **kwargs)
        except Exception as e:
            logger.warning("safe_edit failed: %s", e)

# ════════════════════════════════════════════════
#  ENSURE USER IS TRACKED (for commands without /start)
# ════════════════════════════════════════════════
async def ensure_tracked(update: Update):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    return d

# ════════════════════════════════════════════════
#  /start — sends GIF + welcome text
# ════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)

    welcome_text = build_welcome(user.first_name, user.username, user.id, d)
    kb           = kb_main(user.id, d)

    try:
        await update.message.reply_animation(
            animation=LOGO_GIF_URL,
            caption=welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning("GIF send failed (%s), falling back to text.", e)
        try:
            await update.message.reply_text(
                f"{welcome_text}",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb,
            )
        except Exception as e2:
            logger.error("start fallback also failed: %s", e2)

# ════════════════════════════════════════════════
#  /createkeys — admin only
# ════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(update.effective_user.id, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(
            f"❌ This command is for admins only\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "📋 *Usage:*\n"
            "`/createkeys <count> <max\\_users> <duration>`\n\n"
            "*Or single key:*\n"
            "`/createkeys <max\\_users> <duration>`\n\n"
            "*Duration examples:*\n"
            "  `10d` — 10 days\n"
            "  `2h` — 2 hours\n"
            "  `30m` — 30 minutes\n"
            "  `lifetime` — never expires",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    count   = 1
    devices = 1

    if len(ctx.args) >= 3:
        try:
            count_try   = int(ctx.args[0])
            devices_try = int(ctx.args[1])
            raw_dur     = " ".join(ctx.args[2:])
            count   = count_try
            devices = devices_try
        except ValueError:
            try:
                devices = int(ctx.args[0])
                raw_dur = " ".join(ctx.args[1:])
            except ValueError:
                await update.message.reply_text("❌ Invalid arguments. First arg must be a number.")
                return
    else:
        try:
            devices = int(ctx.args[0])
            raw_dur = " ".join(ctx.args[1:])
        except ValueError:
            await update.message.reply_text("❌ Max users must be a positive integer.")
            return

    if count < 1 or count > 50:
        await update.message.reply_text("❌ Key count must be between 1 and 50.")
        return
    if devices < 1:
        await update.message.reply_text("❌ Max users must be a positive integer.")
        return

    try:
        td, duration_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid duration\\.\n\nExamples: `10d` / `2h` / `30m` / `lifetime`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    created_at     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_keys = []

    for _ in range(count):
        key = generate_key()
        while key in d["keys"]:
            key = generate_key()
        d["keys"][key] = {
            "devices":     devices,
            "duration":    raw_dur,
            "expires":     None,
            "used_by":     [],
            "user_expiry": {},
            "created_by":  str(uid),
            "created_at":  datetime.now().isoformat(),
        }
        generated_keys.append(key)

    save(d)
    logger.info("%d key(s) created: duration=%s devices=%s by=%s", count, raw_dur, devices, uid)

    if count == 1:
        msg = key_message_single(generated_keys[0], duration_label, devices, created_at)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    else:
        msg = keys_batch_message(generated_keys, duration_label, created_at)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

# ════════════════════════════════════════════════
#  /redeem <key>
# ════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if not ctx.args:
        await update.message.reply_text(
            "🔑 *Usage:*\n`/redeem ZEIJIE-PREMIUM-XXXXXX`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text(
            f"❌ *Invalid key\\.*\n\nDouble\\-check and try again\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    k = d["keys"][key]

    if uid in k.get("used_by", []):
        existing_rd = d.get("redeemed", {}).get(uid)
        if existing_rd and existing_rd.get("key") == key:
            exp = existing_rd.get("expires")
            if exp:
                try:
                    if datetime.fromisoformat(exp) <= datetime.now():
                        await update.message.reply_text(
                            f"⛔ *Your key has expired\\.*\n\n"
                            f"Contact admin for a new key: {md_safe(ADMIN_USERNAME)}",
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                        return
                except ValueError:
                    pass
        await update.message.reply_text("⚠️ This key is already activated on your account.")
        return

    if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
        await update.message.reply_text(
            f"❌ Device limit reached for this key\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
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
    save(d)
    logger.info("Key redeemed: %s  by uid=%s  expires=%s", key, uid, expires_iso)

    await update.message.reply_text(
        "┌─────────────────────────────┐\n"
        "│  ✅  KEY ACTIVATED!         │\n"
        "└─────────────────────────────┘\n\n"
        f"`{key}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*   : {dur_label}\n"
        f"📅 *Expires*    : {expiry_display(expires_iso)}\n"
        f"📱 *Device*     : Locked to your account\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Your access timer has started now._ ✅",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /status
# ════════════════════════════════════════════════
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "👑 *Admin Account*\nFull access granted — no key needed.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            f"🔒 *No Active Key*\n\nUse `/redeem <key>` to activate access\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    exp     = rd.get("expires")
    expired = False
    if exp:
        try:
            expired = datetime.fromisoformat(exp) <= datetime.now()
        except ValueError:
            pass

    activated = rd.get("activated", "Unknown")
    if expired:
        txt = (
            "⛔ *Access Expired*\n\n"
            f"🔑 Key     : `{rd['key']}`\n"
            f"📅 Expired : {expiry_display(exp)}\n\n"
            f"_Contact admin for a new key: {ADMIN_USERNAME}_"
        )
        await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)
    else:
        txt = (
            "✅ *Access Active*\n\n"
            f"🔑 Key      : `{rd['key']}`\n"
            f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
            f"🕐 Started  : {activated[:19]}\n"
            f"📅 Expires  : {expiry_display(exp)}"
        )
        await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

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
    if target not in [str(a) for a in d["admins"]]:
        d["admins"].append(target)
        save(d)
        logger.info("Admin added: %s", target)
    await update.message.reply_text(
        f"✅ Admin added: `{target}`", parse_mode=ParseMode.MARKDOWN
    )

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
    if target in [str(a) for a in d["admins"]]:
        d["admins"] = [a for a in d["admins"] if str(a) != target]
        save(d)
        logger.info("Admin removed: %s", target)
        await update.message.reply_text(
            f"✅ Admin removed: `{target}`", parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"⚠️ User `{target}` is not an admin.", parse_mode=ParseMode.MARKDOWN
        )

# ════════════════════════════════════════════════
#  /revokekey <key>  — admin only
# ════════════════════════════════════════════════
async def revokekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /revokekey <KEY>")
        return
    key = ctx.args[0].strip().upper()
    if key not in d["keys"]:
        await update.message.reply_text("❌ Key not found.")
        return
    del d["keys"][key]
    d["redeemed"] = {u: v for u, v in d["redeemed"].items() if v.get("key") != key}
    save(d)
    await update.message.reply_text(
        f"✅ Key revoked: `{key}`\n_All users on this key lost access._",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /getfile <filename>  — premium users
# ════════════════════════════════════════════════
async def getfile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not has_access(uid, d):
        await update.message.reply_text(
            no_access_text(),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    files = get_db_files()
    if not files:
        await update.message.reply_text("📂 No files available in the database.")
        return

    if not ctx.args:
        listing = "\n".join(
            f"  • `{f}` — {count_lines(os.path.join(DB_FOLDER, f)):,} lines"
            for f in files
        )
        await update.message.reply_text(
            f"📂 *Available files:*\n\n{listing}\n\nUsage: `/getfile <filename>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    fname = ctx.args[0].strip()
    fpath = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        await update.message.reply_text(
            f"❌ File `{md_safe_v1(fname)}` not found.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    total = count_lines(fpath)
    if total == 0:
        await update.message.reply_text(
            f"⚠️ `{md_safe_v1(fname)}` is empty or has been exhausted.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    lines_to_send = min(LINES_PER_USE, total)
    content, remaining = consume_lines(fpath, lines_to_send)

    stem     = Path(fname).stem
    out_name = output_filename(stem)
    buf      = io.BytesIO(content.encode("utf-8"))
    buf.name = out_name

    sent_msg = await update.message.reply_document(
        document=buf,
        filename=out_name,
        caption=premium_summary(stem, lines_to_send, remaining),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    asyncio.create_task(_auto_delete(300, sent_msg))

# ════════════════════════════════════════════════
#  /contact — contact admin
# ════════════════════════════════════════════════
async def contact_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    track(update.effective_user.id, update.effective_user.username,
          update.effective_user.first_name, d)
    await update.message.reply_text(
        f"📞 *Contact Admin*\n\n"
        f"For keys, access issues, or support:\n\n"
        f"👤 Admin: {md_safe(ADMIN_USERNAME)}\n\n"
        f"_You cannot access this database without a key\\._\n"
        f"_Contact admin to get a key & gain access\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ════════════════════════════════════════════════
#  UNKNOWN COMMAND HANDLER
#  Lets buyers/admins use commands without /start
# ════════════════════════════════════════════════
async def unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    # Show them the menu so they can navigate
    welcome_text = build_welcome(user.first_name, user.username, user.id, d)
    kb           = kb_main(user.id, d)
    try:
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning("unknown_command reply failed: %s", e)

# ════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ════════════════════════════════════════════════
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    d    = load()
    uid  = q.from_user.id
    data = q.data
    await q.answer()

    track(uid, q.from_user.username, q.from_user.first_name, d)
    save(d)

    # ── Home ──────────────────────────────────────────────────────
    if data == "home":
        welcome_text = build_welcome(q.from_user.first_name, q.from_user.username, uid, d)
        await safe_edit(q, welcome_text, ParseMode.MARKDOWN_V2, kb_main(uid, d))

    # ── Admin Panel ───────────────────────────────────────────────
    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        await safe_edit(
            q,
            "⚡ *Admin Panel*\n\nChoose an option below:",
            ParseMode.MARKDOWN,
            kb_admin(),
        )

    # ── Create Key info ───────────────────────────────────────────
    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        txt = (
            "🔑 *Create Keys*\n\n"
            "Send this command in chat:\n\n"
            "*Single key:*\n"
            "`/createkeys <max\\_users> <duration>`\n\n"
            "*Multiple keys:*\n"
            "`/createkeys <count> <max\\_users> <duration>`\n\n"
            "*Key format:* `ZEIJIE\\-PREMIUM\\-XXXXXX`\n\n"
            "*Examples:*\n"
            "  `/createkeys 1 7d` — 1 key, 7 days\n"
            "  `/createkeys 5 1 1m` — 5 keys, 1 min each\n"
            "  `/createkeys 3 1 lifetime`\n\n"
            "_Timer starts when buyer redeems the key\\._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back("admin"))

    # ── Active Keys ───────────────────────────────────────────────
    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return

        keys     = d.get("keys", {})
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})

        if not keys:
            txt = "🗝 *No keys created yet.*\n\nUse `/createkeys <users> <duration>` to create one."
        else:
            lines = [f"🗝 *All Keys ({len(keys)}):*\n"]
            for k, v in keys.items():
                used_by  = v.get("used_by", [])
                devices  = v.get("devices", 1)
                raw_dur  = v.get("duration", "?")
                used_cnt = len(used_by)

                if used_cnt == 0:
                    status_icon = "🟡 Unused"
                elif used_cnt < devices:
                    status_icon = "🟢 Partial"
                else:
                    status_icon = "🔵 Full"

                block = (
                    f"{status_icon}\n"
                    f"🔑 `{k}`\n"
                    f"   ⏱ Duration : {raw_dur}\n"
                    f"   👥 Used     : {used_cnt}/{devices}"
                )

                for u_id in used_by:
                    rd    = redeemed.get(str(u_id))
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    exp_str = expiry_display(rd["expires"]) if rd else "Unknown"
                    if rd and rd.get("expires"):
                        try:
                            if datetime.fromisoformat(rd["expires"]) <= datetime.now():
                                exp_str += " ⛔ EXPIRED"
                        except ValueError:
                            pass
                    block += f"\n   └ {label}: {exp_str}"

                lines.append(block)

            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_... truncated_"

        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── Admins List ───────────────────────────────────────────────
    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        admins = d.get("admins", [])
        txt = (
            "👥 *No extra admins.*\n_(Owner always has full access)_"
            if not admins
            else "👥 *Admins:*\n\n" + "\n".join(f"  • `{a}`" for a in admins)
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── All Members ───────────────────────────────────────────────
    elif data == "adm_members":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        members  = d.get("members", {})
        redeemed = d.get("redeemed", {})
        if not members:
            txt = "👥 *No members yet.*"
        else:
            lines = [f"👥 *Members ({len(members)}):*\n"]
            for m_id, info in members.items():
                uname   = info.get("username", "")
                fname   = info.get("first_name", "")
                label   = f"@{uname}" if uname else md_safe_v1(fname or m_id)
                rd      = redeemed.get(m_id)
                acc     = "✅" if has_access(int(m_id), d) else "🔒"
                exp_str = expiry_display(rd["expires"]) if rd else "No key"
                lines.append(f"{acc} {label} (`{m_id}`)\n   📅 {exp_str}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_... truncated_"
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── Database ──────────────────────────────────────────────────
    elif data == "db":
        if not has_access(uid, d):
            await safe_edit(q, no_access_text(), ParseMode.MARKDOWN_V2, kb_back())
            return

        files = get_db_files()
        if not files:
            txt = (
                "📂 *Database is empty\\.*\n\n"
                "Upload `.txt` files into the `database/` folder on the server\\."
            )
            await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())
            return

        lines = ["📂 *Database Files:*\n"]
        for fname in files:
            cnt = count_lines(os.path.join(DB_FOLDER, fname))
            lines.append(f"  • `{fname}` — {cnt:,} lines")
        lines.append("\n_Tap a file below to generate and download\\._")
        txt = "\n".join(lines)

        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_db_files(files))

    # ── Database File Selected (download) ─────────────────────────
    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

        if not has_access(uid, d):
            await q.answer(
                "🔒 You cannot access this database. Contact admin to get a key.",
                show_alert=True,
            )
            return

        fpath = os.path.join(DB_FOLDER, fname)
        if not os.path.isfile(fpath):
            await q.answer("❌ File not found on server.", show_alert=True)
            return

        total = count_lines(fpath)
        if total == 0:
            await q.answer(
                "⚠️ This file is empty or exhausted. Contact admin.", show_alert=True
            )
            return

        lines_to_send = min(LINES_PER_USE, total)
        content, remaining = consume_lines(fpath, lines_to_send)

        stem     = Path(fname).stem
        out_name = output_filename(stem)
        buf      = io.BytesIO(content.encode("utf-8"))
        buf.name = out_name

        sent_msg = await q.message.reply_document(
            document=buf,
            filename=out_name,
            caption=premium_summary(stem, lines_to_send, remaining),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        asyncio.create_task(_auto_delete(300, sent_msg))

    # ── Redeem Info ───────────────────────────────────────────────
    elif data == "redeem_info":
        txt = (
            "🔑 *Redeem a Key*\n\n"
            "Send this command:\n`/redeem ZEIJIE-PREMIUM-XXXXXX`\n\n"
            "_Your access timer starts the moment you redeem._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Status ────────────────────────────────────────────────────
    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "👑 *Admin Account*\nFull access granted — no key needed."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = (
                    f"🔒 *No Active Key*\n\nUse `/redeem <key>` to get access\\.\n\n"
                    f"Contact admin: {md_safe(ADMIN_USERNAME)}"
                )
                await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())
                return
            else:
                exp     = rd.get("expires")
                expired = False
                if exp:
                    try:
                        expired = datetime.fromisoformat(exp) <= datetime.now()
                    except ValueError:
                        pass
                activated = rd.get("activated", "Unknown")
                if expired:
                    txt = (
                        "⛔ *Access Expired*\n\n"
                        f"🔑 Key     : `{rd['key']}`\n"
                        f"📅 Expired : {expiry_display(exp)}\n\n"
                        f"_Contact admin for a new key: {ADMIN_USERNAME}_"
                    )
                else:
                    txt = (
                        "✅ *Access Active*\n\n"
                        f"🔑 Key      : `{rd['key']}`\n"
                        f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
                        f"🕐 Started  : {activated[:19]}\n"
                        f"📅 Expires  : {expiry_display(exp)}"
                    )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Commands ──────────────────────────────────────────────────
    elif data == "commands":
        txt = (
            "📋 *Commands*\n\n"
            "👤 *User:*\n"
            "  /start — Main menu\n"
            "  /redeem `<key>` — Activate a key\n"
            "  /status — Check your access\n"
            "  /getfile `<filename>` — Download file\n"
            "  /contact — Contact admin\n\n"
            "🛡 *Admin:*\n"
            "  /createkeys `<count> <users> <dur>` — Bulk create\n"
            "  /createkeys `<users> <duration>` — Single key\n"
            "  /revokekey `<key>` — Delete a key\n"
            "  /addadmin `<id>` — Add admin (owner only)\n"
            "  /removeadmin `<id>` — Remove admin (owner only)\n\n"
            f"📞 *Contact Admin:* {ADMIN_USERNAME}"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Contact Admin ─────────────────────────────────────────────
    elif data == "contact_admin":
        txt = (
            f"📞 *Contact Admin*\n\n"
            f"For keys, access issues, or support:\n\n"
            f"👤 Admin: {md_safe(ADMIN_USERNAME)}\n\n"
            f"_You cannot access this database without a key\\._\n"
            f"_Contact admin to get a key & gain access\\._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())

# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("createkeys",   createkeys))
    app.add_handler(CommandHandler("redeem",       redeem))
    app.add_handler(CommandHandler("status",       status_cmd))
    app.add_handler(CommandHandler("addadmin",     addadmin))
    app.add_handler(CommandHandler("removeadmin",  removeadmin))
    app.add_handler(CommandHandler("getfile",      getfile))
    app.add_handler(CommandHandler("revokekey",    revokekey))
    app.add_handler(CommandHandler("contact",      contact_cmd))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(button))

    # Unknown commands — show menu so users don't need /start
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("ZEIJIE BOT starting — polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

LOGO_TEXT = (
    "```\n"
    "╔══════════════════════════════════╗\n"
    "║   ███████╗███████╗██╗██╗██╗     ║\n"
    "║   ╚══███╔╝██╔════╝██║██║██║     ║\n"
    "║     ███╔╝ █████╗  ██║██║██║     ║\n"
    "║    ███╔╝  ██╔══╝  ██║██║██║     ║\n"
    "║   ███████╗███████╗██║██║███████╗║\n"
    "║   ╚══════╝╚══════╝╚═╝╚═╝╚══════╝║\n"
    "║     V  I  P  ·  P  R  E  M      ║\n"
    "╚══════════════════════════════════╝\n"
    "```"
)

# ════════════════════════════════════════════════
#  WELCOME MESSAGES
# ════════════════════════════════════════════════
WELCOME_LINES = [
    "⚡ *ZEIJIE BOT* is locked, loaded, and ready for action.",
    "🔥 Welcome to *ZEIJIE BOT* — your premium gateway.",
    "🌐 *ZEIJIE BOT* online — Precision · Power · Premium.",
    "🛡 *ZEIJIE BOT* activated — built different, built better.",
    "💎 You've entered *ZEIJIE BOT* — where premium lives.",
    "🚀 *ZEIJIE BOT* is live — Let's get to work.",
    "🎯 *ZEIJIE BOT* standing by — the real deal starts here.",
    "👾 *ZEIJIE BOT* loaded — No limits, only premium access.",
]

def random_welcome() -> str:
    return random.choice(WELCOME_LINES)

# ════════════════════════════════════════════════
#  MARKDOWN SAFETY
# ════════════════════════════════════════════════
def md_safe(text: str) -> str:
    for ch in ("_", "*", "`", "[", "]", "(", ")", "~", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"):
        text = text.replace(ch, f"\\{ch}")
    return text

def md_safe_v1(text: str) -> str:
    """For MARKDOWN (v1) mode."""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text

# ════════════════════════════════════════════════
#  DATA HELPERS
# ════════════════════════════════════════════════
def load() -> dict:
    default = {"admins": [], "keys": {}, "members": {}, "redeemed": {}}
    if not os.path.exists(DATA_FILE):
        return default
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("data.json corrupted — starting fresh.")
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
        logger.error("Failed to save data.json: %s", e)

def is_admin(uid, d) -> bool:
    return str(uid) in [str(x) for x in d.get("admins", [])] or int(uid) == OWNER_ID

def has_access(uid, d) -> bool:
    if is_admin(uid, d):
        return True
    uid_str = str(uid)
    rd = d.get("redeemed", {}).get(uid_str)
    if not rd:
        return False
    exp = rd.get("expires")
    if not exp:
        key = rd.get("key")
        if key and key in d.get("keys", {}):
            return True
        return False
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
    try:
        return sorted(
            f for f in os.listdir(DB_FOLDER)
            if os.path.isfile(os.path.join(DB_FOLDER, f))
        )
    except FileNotFoundError:
        return []

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
    number = "".join(random.choices(string.digits, k=6))
    return f"ZEIJIE-PREMIUM-{number}"

def parse_duration(raw: str):
    dur = raw.strip().lower()
    if dur in ("lifetime", "forever", "inf"):
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

# ════════════════════════════════════════════════
#  EXPIRY DISPLAY
# ════════════════════════════════════════════════
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

    delta      = exp_dt - now
    total_secs = int(delta.total_seconds())
    days_rem   = total_secs // 86400
    hours_rem  = (total_secs % 86400) // 3600
    mins_rem   = (total_secs % 3600)  // 60
    secs_rem   = total_secs % 60

    parts = []
    if days_rem:  parts.append(f"{days_rem}d")
    if hours_rem: parts.append(f"{hours_rem}h")
    if mins_rem:  parts.append(f"{mins_rem}m")
    if secs_rem and not days_rem: parts.append(f"{secs_rem}s")

    remaining_str = " ".join(parts) if parts else "< 1s"
    return f"{abs_time}  ({remaining_str} left)"

# ════════════════════════════════════════════════
#  OUTPUT FILENAME BUILDER
# ════════════════════════════════════════════════
def output_filename(stem: str) -> str:
    clean = stem.upper().replace(" ", "_")
    return f"{OUTPUT_PREFIX}-{clean}.txt"

# ════════════════════════════════════════════════
#  NO ACCESS MESSAGE
# ════════════════════════════════════════════════
def no_access_text() -> str:
    return (
        "🔒 *Access Denied*\n\n"
        "You cannot access this database\\.\n"
        f"Contact admin to get a key & to access this\\.\n\n"
        f"👤 *Admin:* {md_safe(ADMIN_USERNAME)}"
    )

# ════════════════════════════════════════════════
#  MESSAGE BUILDERS
# ════════════════════════════════════════════════
def key_message_single(key: str, duration_label: str, devices: int, created_at: str) -> str:
    return (
        "┌─────────────────────────────┐\n"
        "│  🔑  KEY GENERATED          │\n"
        "└─────────────────────────────┘\n\n"
        f"`{key}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*   : {duration_label}\n"
        f"📅 *Starts*     : On redeem\n"
        f"👥 *Max Users*  : {devices}\n"
        f"📅 *Created On* : {created_at}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Timer starts when the buyer redeems this key ✅_"
    )

def keys_batch_message(keys: list, duration_label: str, created_at: str) -> str:
    count = len(keys)
    key_lines = "\n".join(f"`{k}`" for k in keys)
    return (
        f"🎉 *{count} Key{'s' if count > 1 else ''} Generated Successfully\\!* 🎉\n\n"
        f"{key_lines}\n\n"
        f"⏳ *Validity \\(each\\):* ⏱️ {md_safe(duration_label)}\n"
        f"📝 *Status:* One\\-time use\n"
        f"📅 *Created On:* {md_safe(created_at)}\n\n"
        "✨ _Share these keys with your users to grant them access\\!_"
    )

def premium_summary(fname_stem: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out_name = output_filename(fname_stem)
    return (
        "🔮 *PREMIUM FILE GENERATED\\!*\n\n"
        "📊 *GENERATION SUMMARY*\n"
        f"┣ 🎮 Source     : {md_safe(fname_stem.upper())}\n"
        f"┣ 📄 File       : `{md_safe(out_name)}`\n"
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

# ════════════════════════════════════════════════
#  KEYBOARDS
# ════════════════════════════════════════════════
def kb_main(uid, d) -> InlineKeyboardMarkup:
    rows = []
    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")])
    rows += [
        [
            InlineKeyboardButton("📂 Database",  callback_data="db"),
            InlineKeyboardButton("🔑 Redeem",    callback_data="redeem_info"),
        ],
        [
            InlineKeyboardButton("👤 My Status", callback_data="status"),
            InlineKeyboardButton("📋 Commands",  callback_data="commands"),
        ],
        [
            InlineKeyboardButton("📞 Contact Admin", callback_data="contact_admin"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key",   callback_data="adm_create")],
        [InlineKeyboardButton("🗝 Active Keys",  callback_data="adm_keys")],
        [InlineKeyboardButton("👥 Admins List",  callback_data="adm_list")],
        [InlineKeyboardButton("👥 All Members",  callback_data="adm_members")],
        [InlineKeyboardButton("🔙 Back",         callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "🔙 Back to Admin" if dest == "admin" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

def kb_db_files(files: list) -> InlineKeyboardMarkup:
    rows = []
    for fname in files:
        fpath = os.path.join(DB_FOLDER, fname)
        cnt   = count_lines(fpath)
        label = f"📄 {Path(fname).stem}  ({cnt:,} lines)"
        rows.append([InlineKeyboardButton(label, callback_data=f"dbfile:{fname}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)

# ════════════════════════════════════════════════
#  WELCOME TEXT BUILDER
# ════════════════════════════════════════════════
def build_welcome(first_name: str, username, uid, d: dict) -> str:
    status       = "✅ Active" if has_access(uid, d) else "🔒 No Access"
    welcome_line = random_welcome()
    safe_name    = md_safe(first_name or "Operator")
    user_line    = f"👤 *{safe_name}*"
    if username:
        user_line += f"  \\(@{md_safe(username)}\\)"
    return (
        f"{welcome_line}\n\n"
        f"{user_line}\n"
        f"🔐 Status : {status}"
    )

# ════════════════════════════════════════════════
#  AUTO-DELETE HELPER
# ════════════════════════════════════════════════
async def _auto_delete(delay: int, *messages):
    await asyncio.sleep(delay)
    for m in messages:
        try:
            await m.delete()
        except Exception:
            pass

# ════════════════════════════════════════════════
#  DATABASE DECREASE HELPER
# ════════════════════════════════════════════════
def consume_lines(fpath: str, n: int) -> tuple:
    with open(fpath, "r", errors="ignore") as f:
        all_lines = f.readlines()
    to_send   = all_lines[:n]
    leftover  = all_lines[n:]
    remaining = len(leftover)
    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(leftover)
    return "".join(to_send), remaining

# ════════════════════════════════════════════════
#  SAFE EDIT HELPERS
# ════════════════════════════════════════════════
async def safe_edit(q, text, parse_mode, reply_markup=None):
    """Try edit_message_text, fall back to edit_message_caption."""
    kwargs = {"parse_mode": parse_mode}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    try:
        await q.edit_message_text(text, **kwargs)
    except Exception:
        try:
            await q.edit_message_caption(caption=text, **kwargs)
        except Exception as e:
            logger.warning("safe_edit failed: %s", e)

# ════════════════════════════════════════════════
#  ENSURE USER IS TRACKED (for commands without /start)
# ════════════════════════════════════════════════
async def ensure_tracked(update: Update):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    return d

# ════════════════════════════════════════════════
#  /start — sends GIF + welcome text
# ════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)

    welcome_text = build_welcome(user.first_name, user.username, user.id, d)
    kb           = kb_main(user.id, d)

    try:
        await update.message.reply_animation(
            animation=LOGO_GIF_URL,
            caption=welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning("GIF send failed (%s), falling back to text.", e)
        try:
            await update.message.reply_text(
                f"{welcome_text}",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb,
            )
        except Exception as e2:
            logger.error("start fallback also failed: %s", e2)

# ════════════════════════════════════════════════
#  /createkeys — admin only
# ════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(update.effective_user.id, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(
            f"❌ This command is for admins only\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "📋 *Usage:*\n"
            "`/createkeys <count> <max\\_users> <duration>`\n\n"
            "*Or single key:*\n"
            "`/createkeys <max\\_users> <duration>`\n\n"
            "*Duration examples:*\n"
            "  `10d` — 10 days\n"
            "  `2h` — 2 hours\n"
            "  `30m` — 30 minutes\n"
            "  `lifetime` — never expires",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    count   = 1
    devices = 1

    if len(ctx.args) >= 3:
        try:
            count_try   = int(ctx.args[0])
            devices_try = int(ctx.args[1])
            raw_dur     = " ".join(ctx.args[2:])
            count   = count_try
            devices = devices_try
        except ValueError:
            try:
                devices = int(ctx.args[0])
                raw_dur = " ".join(ctx.args[1:])
            except ValueError:
                await update.message.reply_text("❌ Invalid arguments. First arg must be a number.")
                return
    else:
        try:
            devices = int(ctx.args[0])
            raw_dur = " ".join(ctx.args[1:])
        except ValueError:
            await update.message.reply_text("❌ Max users must be a positive integer.")
            return

    if count < 1 or count > 50:
        await update.message.reply_text("❌ Key count must be between 1 and 50.")
        return
    if devices < 1:
        await update.message.reply_text("❌ Max users must be a positive integer.")
        return

    try:
        td, duration_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid duration\\.\n\nExamples: `10d` / `2h` / `30m` / `lifetime`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    created_at     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_keys = []

    for _ in range(count):
        key = generate_key()
        while key in d["keys"]:
            key = generate_key()
        d["keys"][key] = {
            "devices":     devices,
            "duration":    raw_dur,
            "expires":     None,
            "used_by":     [],
            "user_expiry": {},
            "created_by":  str(uid),
            "created_at":  datetime.now().isoformat(),
        }
        generated_keys.append(key)

    save(d)
    logger.info("%d key(s) created: duration=%s devices=%s by=%s", count, raw_dur, devices, uid)

    if count == 1:
        msg = key_message_single(generated_keys[0], duration_label, devices, created_at)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    else:
        msg = keys_batch_message(generated_keys, duration_label, created_at)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

# ════════════════════════════════════════════════
#  /redeem <key>
# ════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if not ctx.args:
        await update.message.reply_text(
            "🔑 *Usage:*\n`/redeem ZEIJIE-PREMIUM-XXXXXX`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text(
            f"❌ *Invalid key\\.*\n\nDouble\\-check and try again\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    k = d["keys"][key]

    if uid in k.get("used_by", []):
        existing_rd = d.get("redeemed", {}).get(uid)
        if existing_rd and existing_rd.get("key") == key:
            exp = existing_rd.get("expires")
            if exp:
                try:
                    if datetime.fromisoformat(exp) <= datetime.now():
                        await update.message.reply_text(
                            f"⛔ *Your key has expired\\.*\n\n"
                            f"Contact admin for a new key: {md_safe(ADMIN_USERNAME)}",
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                        return
                except ValueError:
                    pass
        await update.message.reply_text("⚠️ This key is already activated on your account.")
        return

    if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
        await update.message.reply_text(
            f"❌ Device limit reached for this key\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
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
    save(d)
    logger.info("Key redeemed: %s  by uid=%s  expires=%s", key, uid, expires_iso)

    await update.message.reply_text(
        "┌─────────────────────────────┐\n"
        "│  ✅  KEY ACTIVATED!         │\n"
        "└─────────────────────────────┘\n\n"
        f"`{key}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*   : {dur_label}\n"
        f"📅 *Expires*    : {expiry_display(expires_iso)}\n"
        f"📱 *Device*     : Locked to your account\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Your access timer has started now._ ✅",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /status
# ════════════════════════════════════════════════
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "👑 *Admin Account*\nFull access granted — no key needed.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            f"🔒 *No Active Key*\n\nUse `/redeem <key>` to activate access\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    exp     = rd.get("expires")
    expired = False
    if exp:
        try:
            expired = datetime.fromisoformat(exp) <= datetime.now()
        except ValueError:
            pass

    activated = rd.get("activated", "Unknown")
    if expired:
        txt = (
            "⛔ *Access Expired*\n\n"
            f"🔑 Key     : `{rd['key']}`\n"
            f"📅 Expired : {expiry_display(exp)}\n\n"
            f"_Contact admin for a new key: {ADMIN_USERNAME}_"
        )
        await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)
    else:
        txt = (
            "✅ *Access Active*\n\n"
            f"🔑 Key      : `{rd['key']}`\n"
            f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
            f"🕐 Started  : {activated[:19]}\n"
            f"📅 Expires  : {expiry_display(exp)}"
        )
        await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

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
    if target not in [str(a) for a in d["admins"]]:
        d["admins"].append(target)
        save(d)
        logger.info("Admin added: %s", target)
    await update.message.reply_text(
        f"✅ Admin added: `{target}`", parse_mode=ParseMode.MARKDOWN
    )

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
    if target in [str(a) for a in d["admins"]]:
        d["admins"] = [a for a in d["admins"] if str(a) != target]
        save(d)
        logger.info("Admin removed: %s", target)
        await update.message.reply_text(
            f"✅ Admin removed: `{target}`", parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"⚠️ User `{target}` is not an admin.", parse_mode=ParseMode.MARKDOWN
        )

# ════════════════════════════════════════════════
#  /revokekey <key>  — admin only
# ════════════════════════════════════════════════
async def revokekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /revokekey <KEY>")
        return
    key = ctx.args[0].strip().upper()
    if key not in d["keys"]:
        await update.message.reply_text("❌ Key not found.")
        return
    del d["keys"][key]
    d["redeemed"] = {u: v for u, v in d["redeemed"].items() if v.get("key") != key}
    save(d)
    await update.message.reply_text(
        f"✅ Key revoked: `{key}`\n_All users on this key lost access._",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /getfile <filename>  — premium users
# ════════════════════════════════════════════════
async def getfile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not has_access(uid, d):
        await update.message.reply_text(
            no_access_text(),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    files = get_db_files()
    if not files:
        await update.message.reply_text("📂 No files available in the database.")
        return

    if not ctx.args:
        listing = "\n".join(
            f"  • `{f}` — {count_lines(os.path.join(DB_FOLDER, f)):,} lines"
            for f in files
        )
        await update.message.reply_text(
            f"📂 *Available files:*\n\n{listing}\n\nUsage: `/getfile <filename>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    fname = ctx.args[0].strip()
    fpath = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        await update.message.reply_text(
            f"❌ File `{md_safe_v1(fname)}` not found.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    total = count_lines(fpath)
    if total == 0:
        await update.message.reply_text(
            f"⚠️ `{md_safe_v1(fname)}` is empty or has been exhausted.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    lines_to_send = min(LINES_PER_USE, total)
    content, remaining = consume_lines(fpath, lines_to_send)

    stem     = Path(fname).stem
    out_name = output_filename(stem)
    buf      = io.BytesIO(content.encode("utf-8"))
    buf.name = out_name

    sent_msg = await update.message.reply_document(
        document=buf,
        filename=out_name,
        caption=premium_summary(stem, lines_to_send, remaining),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    asyncio.create_task(_auto_delete(300, sent_msg))

# ════════════════════════════════════════════════
#  /contact — contact admin
# ════════════════════════════════════════════════
async def contact_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    track(update.effective_user.id, update.effective_user.username,
          update.effective_user.first_name, d)
    await update.message.reply_text(
        f"📞 *Contact Admin*\n\n"
        f"For keys, access issues, or support:\n\n"
        f"👤 Admin: {md_safe(ADMIN_USERNAME)}\n\n"
        f"_You cannot access this database without a key\\._\n"
        f"_Contact admin to get a key & gain access\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ════════════════════════════════════════════════
#  UNKNOWN COMMAND HANDLER
#  Lets buyers/admins use commands without /start
# ════════════════════════════════════════════════
async def unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    # Show them the menu so they can navigate
    welcome_text = build_welcome(user.first_name, user.username, user.id, d)
    kb           = kb_main(user.id, d)
    try:
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning("unknown_command reply failed: %s", e)

# ════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ════════════════════════════════════════════════
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    d    = load()
    uid  = q.from_user.id
    data = q.data
    await q.answer()

    track(uid, q.from_user.username, q.from_user.first_name, d)
    save(d)

    # ── Home ──────────────────────────────────────────────────────
    if data == "home":
        welcome_text = build_welcome(q.from_user.first_name, q.from_user.username, uid, d)
        await safe_edit(q, welcome_text, ParseMode.MARKDOWN_V2, kb_main(uid, d))

    # ── Admin Panel ───────────────────────────────────────────────
    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        await safe_edit(
            q,
            "⚡ *Admin Panel*\n\nChoose an option below:",
            ParseMode.MARKDOWN,
            kb_admin(),
        )

    # ── Create Key info ───────────────────────────────────────────
    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        txt = (
            "🔑 *Create Keys*\n\n"
            "Send this command in chat:\n\n"
            "*Single key:*\n"
            "`/createkeys <max\\_users> <duration>`\n\n"
            "*Multiple keys:*\n"
            "`/createkeys <count> <max\\_users> <duration>`\n\n"
            "*Key format:* `ZEIJIE\\-PREMIUM\\-XXXXXX`\n\n"
            "*Examples:*\n"
            "  `/createkeys 1 7d` — 1 key, 7 days\n"
            "  `/createkeys 5 1 1m` — 5 keys, 1 min each\n"
            "  `/createkeys 3 1 lifetime`\n\n"
            "_Timer starts when buyer redeems the key\\._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back("admin"))

    # ── Active Keys ───────────────────────────────────────────────
    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return

        keys     = d.get("keys", {})
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})

        if not keys:
            txt = "🗝 *No keys created yet.*\n\nUse `/createkeys <users> <duration>` to create one."
        else:
            lines = [f"🗝 *All Keys ({len(keys)}):*\n"]
            for k, v in keys.items():
                used_by  = v.get("used_by", [])
                devices  = v.get("devices", 1)
                raw_dur  = v.get("duration", "?")
                used_cnt = len(used_by)

                if used_cnt == 0:
                    status_icon = "🟡 Unused"
                elif used_cnt < devices:
                    status_icon = "🟢 Partial"
                else:
                    status_icon = "🔵 Full"

                block = (
                    f"{status_icon}\n"
                    f"🔑 `{k}`\n"
                    f"   ⏱ Duration : {raw_dur}\n"
                    f"   👥 Used     : {used_cnt}/{devices}"
                )

                for u_id in used_by:
                    rd    = redeemed.get(str(u_id))
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    exp_str = expiry_display(rd["expires"]) if rd else "Unknown"
                    if rd and rd.get("expires"):
                        try:
                            if datetime.fromisoformat(rd["expires"]) <= datetime.now():
                                exp_str += " ⛔ EXPIRED"
                        except ValueError:
                            pass
                    block += f"\n   └ {label}: {exp_str}"

                lines.append(block)

            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_... truncated_"

        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── Admins List ───────────────────────────────────────────────
    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        admins = d.get("admins", [])
        txt = (
            "👥 *No extra admins.*\n_(Owner always has full access)_"
            if not admins
            else "👥 *Admins:*\n\n" + "\n".join(f"  • `{a}`" for a in admins)
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── All Members ───────────────────────────────────────────────
    elif data == "adm_members":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        members  = d.get("members", {})
        redeemed = d.get("redeemed", {})
        if not members:
            txt = "👥 *No members yet.*"
        else:
            lines = [f"👥 *Members ({len(members)}):*\n"]
            for m_id, info in members.items():
                uname   = info.get("username", "")
                fname   = info.get("first_name", "")
                label   = f"@{uname}" if uname else md_safe_v1(fname or m_id)
                rd      = redeemed.get(m_id)
                acc     = "✅" if has_access(int(m_id), d) else "🔒"
                exp_str = expiry_display(rd["expires"]) if rd else "No key"
                lines.append(f"{acc} {label} (`{m_id}`)\n   📅 {exp_str}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_... truncated_"
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── Database ──────────────────────────────────────────────────
    elif data == "db":
        if not has_access(uid, d):
            await safe_edit(q, no_access_text(), ParseMode.MARKDOWN_V2, kb_back())
            return

        files = get_db_files()
        if not files:
            txt = (
                "📂 *Database is empty\\.*\n\n"
                "Upload `.txt` files into the `database/` folder on the server\\."
            )
            await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())
            return

        lines = ["📂 *Database Files:*\n"]
        for fname in files:
            cnt = count_lines(os.path.join(DB_FOLDER, fname))
            lines.append(f"  • `{fname}` — {cnt:,} lines")
        lines.append("\n_Tap a file below to generate and download\\._")
        txt = "\n".join(lines)

        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_db_files(files))

    # ── Database File Selected (download) ─────────────────────────
    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

        if not has_access(uid, d):
            await q.answer(
                "🔒 You cannot access this database. Contact admin to get a key.",
                show_alert=True,
            )
            return

        fpath = os.path.join(DB_FOLDER, fname)
        if not os.path.isfile(fpath):
            await q.answer("❌ File not found on server.", show_alert=True)
            return

        total = count_lines(fpath)
        if total == 0:
            await q.answer(
                "⚠️ This file is empty or exhausted. Contact admin.", show_alert=True
            )
            return

        lines_to_send = min(LINES_PER_USE, total)
        content, remaining = consume_lines(fpath, lines_to_send)

        stem     = Path(fname).stem
        out_name = output_filename(stem)
        buf      = io.BytesIO(content.encode("utf-8"))
        buf.name = out_name

        sent_msg = await q.message.reply_document(
            document=buf,
            filename=out_name,
            caption=premium_summary(stem, lines_to_send, remaining),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        asyncio.create_task(_auto_delete(300, sent_msg))

    # ── Redeem Info ───────────────────────────────────────────────
    elif data == "redeem_info":
        txt = (
            "🔑 *Redeem a Key*\n\n"
            "Send this command:\n`/redeem ZEIJIE-PREMIUM-XXXXXX`\n\n"
            "_Your access timer starts the moment you redeem._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Status ────────────────────────────────────────────────────
    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "👑 *Admin Account*\nFull access granted — no key needed."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = (
                    f"🔒 *No Active Key*\n\nUse `/redeem <key>` to get access\\.\n\n"
                    f"Contact admin: {md_safe(ADMIN_USERNAME)}"
                )
                await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())
                return
            else:
                exp     = rd.get("expires")
                expired = False
                if exp:
                    try:
                        expired = datetime.fromisoformat(exp) <= datetime.now()
                    except ValueError:
                        pass
                activated = rd.get("activated", "Unknown")
                if expired:
                    txt = (
                        "⛔ *Access Expired*\n\n"
                        f"🔑 Key     : `{rd['key']}`\n"
                        f"📅 Expired : {expiry_display(exp)}\n\n"
                        f"_Contact admin for a new key: {ADMIN_USERNAME}_"
                    )
                else:
                    txt = (
                        "✅ *Access Active*\n\n"
                        f"🔑 Key      : `{rd['key']}`\n"
                        f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
                        f"🕐 Started  : {activated[:19]}\n"
                        f"📅 Expires  : {expiry_display(exp)}"
                    )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Commands ──────────────────────────────────────────────────
    elif data == "commands":
        txt = (
            "📋 *Commands*\n\n"
            "👤 *User:*\n"
            "  /start — Main menu\n"
            "  /redeem `<key>` — Activate a key\n"
            "  /status — Check your access\n"
            "  /getfile `<filename>` — Download file\n"
            "  /contact — Contact admin\n\n"
            "🛡 *Admin:*\n"
            "  /createkeys `<count> <users> <dur>` — Bulk create\n"
            "  /createkeys `<users> <duration>` — Single key\n"
            "  /revokekey `<key>` — Delete a key\n"
            "  /addadmin `<id>` — Add admin (owner only)\n"
            "  /removeadmin `<id>` — Remove admin (owner only)\n\n"
            f"📞 *Contact Admin:* {ADMIN_USERNAME}"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Contact Admin ─────────────────────────────────────────────
    elif data == "contact_admin":
        txt = (
            f"📞 *Contact Admin*\n\n"
            f"For keys, access issues, or support:\n\n"
            f"👤 Admin: {md_safe(ADMIN_USERNAME)}\n\n"
            f"_You cannot access this database without a key\\._\n"
            f"_Contact admin to get a key & gain access\\._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())

# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════
async def _clear_telegram_session(retries: int = 6, delay: float = 5.0):
    """
    Delete any active webhook and drop pending updates before polling starts.
    On Railway, the old container may still be polling for a few seconds after
    the new one starts — retrying gives it time to die.
    """
    import httpx
    url    = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteWebhook"
    params = {"drop_pending_updates": "true"}
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, params=params)
                data = resp.json()
            if data.get("ok"):
                logger.info("Telegram session cleared (attempt %d).", attempt)
                return
            logger.warning("clearSession attempt %d: %s", attempt, data)
        except Exception as exc:
            logger.warning("clearSession attempt %d error: %s", attempt, exc)
        logger.info("Waiting %ss before retry…", delay)
        await asyncio.sleep(delay)
    logger.error("Could not clear Telegram session — starting anyway.")


def main():
    # ── Step 1: forcefully clear any previous polling session on Telegram ──
    asyncio.run(_clear_telegram_session())

    # ── Step 2: build and start the bot ────────────────────────────────────
    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("createkeys",   createkeys))
    app.add_handler(CommandHandler("redeem",       redeem))
    app.add_handler(CommandHandler("status",       status_cmd))
    app.add_handler(CommandHandler("addadmin",     addadmin))
    app.add_handler(CommandHandler("removeadmin",  removeadmin))
    app.add_handler(CommandHandler("getfile",      getfile))
    app.add_handler(CommandHandler("revokekey",    revokekey))
    app.add_handler(CommandHandler("contact",      contact_cmd))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(button))

    # Unknown commands — show menu so users don't need /start
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("ZEIJIE BOT starting — polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
os.makedirs(DB_FOLDER, exist_ok=True)

# ════════════════════════════════════════════════
#  LOGO
# ════════════════════════════════════════════════
LOGO_GIF_URL = "https://i.pinimg.com/originals/89/5c/e7/895ce751ba0379700381d17a67086931.gif"

LOGO_TEXT = (
    "```\n"
    "╔══════════════════════════════════╗\n"
    "║   ███████╗███████╗██╗██╗██╗     ║\n"
    "║   ╚══███╔╝██╔════╝██║██║██║     ║\n"
    "║     ███╔╝ █████╗  ██║██║██║     ║\n"
    "║    ███╔╝  ██╔══╝  ██║██║██║     ║\n"
    "║   ███████╗███████╗██║██║███████╗║\n"
    "║   ╚══════╝╚══════╝╚═╝╚═╝╚══════╝║\n"
    "║     V  I  P  ·  P  R  E  M      ║\n"
    "╚══════════════════════════════════╝\n"
    "```"
)

# ════════════════════════════════════════════════
#  WELCOME MESSAGES
# ════════════════════════════════════════════════
WELCOME_LINES = [
    "⚡ *ZEIJIE BOT* is locked, loaded, and ready for action.",
    "🔥 Welcome to *ZEIJIE BOT* — your premium gateway.",
    "🌐 *ZEIJIE BOT* online — Precision · Power · Premium.",
    "🛡 *ZEIJIE BOT* activated — built different, built better.",
    "💎 You've entered *ZEIJIE BOT* — where premium lives.",
    "🚀 *ZEIJIE BOT* is live — Let's get to work.",
    "🎯 *ZEIJIE BOT* standing by — the real deal starts here.",
    "👾 *ZEIJIE BOT* loaded — No limits, only premium access.",
]

def random_welcome() -> str:
    return random.choice(WELCOME_LINES)

# ════════════════════════════════════════════════
#  MARKDOWN SAFETY
# ════════════════════════════════════════════════
def md_safe(text: str) -> str:
    for ch in ("_", "*", "`", "[", "]", "(", ")", "~", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"):
        text = text.replace(ch, f"\\{ch}")
    return text

def md_safe_v1(text: str) -> str:
    """For MARKDOWN (v1) mode."""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text

# ════════════════════════════════════════════════
#  DATA HELPERS
# ════════════════════════════════════════════════
def load() -> dict:
    default = {"admins": [], "keys": {}, "members": {}, "redeemed": {}}
    if not os.path.exists(DATA_FILE):
        return default
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("data.json corrupted — starting fresh.")
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
        logger.error("Failed to save data.json: %s", e)

def is_admin(uid, d) -> bool:
    return str(uid) in [str(x) for x in d.get("admins", [])] or int(uid) == OWNER_ID

def has_access(uid, d) -> bool:
    if is_admin(uid, d):
        return True
    uid_str = str(uid)
    rd = d.get("redeemed", {}).get(uid_str)
    if not rd:
        return False
    exp = rd.get("expires")
    if not exp:
        key = rd.get("key")
        if key and key in d.get("keys", {}):
            return True
        return False
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
    try:
        return sorted(
            f for f in os.listdir(DB_FOLDER)
            if os.path.isfile(os.path.join(DB_FOLDER, f))
        )
    except FileNotFoundError:
        return []

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
    number = "".join(random.choices(string.digits, k=6))
    return f"ZEIJIE-PREMIUM-{number}"

def parse_duration(raw: str):
    dur = raw.strip().lower()
    if dur in ("lifetime", "forever", "inf"):
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

# ════════════════════════════════════════════════
#  EXPIRY DISPLAY
# ════════════════════════════════════════════════
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

    delta      = exp_dt - now
    total_secs = int(delta.total_seconds())
    days_rem   = total_secs // 86400
    hours_rem  = (total_secs % 86400) // 3600
    mins_rem   = (total_secs % 3600)  // 60
    secs_rem   = total_secs % 60

    parts = []
    if days_rem:  parts.append(f"{days_rem}d")
    if hours_rem: parts.append(f"{hours_rem}h")
    if mins_rem:  parts.append(f"{mins_rem}m")
    if secs_rem and not days_rem: parts.append(f"{secs_rem}s")

    remaining_str = " ".join(parts) if parts else "< 1s"
    return f"{abs_time}  ({remaining_str} left)"

# ════════════════════════════════════════════════
#  OUTPUT FILENAME BUILDER
# ════════════════════════════════════════════════
def output_filename(stem: str) -> str:
    clean = stem.upper().replace(" ", "_")
    return f"{OUTPUT_PREFIX}-{clean}.txt"

# ════════════════════════════════════════════════
#  NO ACCESS MESSAGE
# ════════════════════════════════════════════════
def no_access_text() -> str:
    return (
        "🔒 *Access Denied*\n\n"
        "You cannot access this database\\.\n"
        f"Contact admin to get a key & to access this\\.\n\n"
        f"👤 *Admin:* {md_safe(ADMIN_USERNAME)}"
    )

# ════════════════════════════════════════════════
#  MESSAGE BUILDERS
# ════════════════════════════════════════════════
def key_message_single(key: str, duration_label: str, devices: int, created_at: str) -> str:
    return (
        "┌─────────────────────────────┐\n"
        "│  🔑  KEY GENERATED          │\n"
        "└─────────────────────────────┘\n\n"
        f"`{key}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*   : {duration_label}\n"
        f"📅 *Starts*     : On redeem\n"
        f"👥 *Max Users*  : {devices}\n"
        f"📅 *Created On* : {created_at}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Timer starts when the buyer redeems this key ✅_"
    )

def keys_batch_message(keys: list, duration_label: str, created_at: str) -> str:
    count = len(keys)
    key_lines = "\n".join(f"`{k}`" for k in keys)
    return (
        f"🎉 *{count} Key{'s' if count > 1 else ''} Generated Successfully\\!* 🎉\n\n"
        f"{key_lines}\n\n"
        f"⏳ *Validity \\(each\\):* ⏱️ {md_safe(duration_label)}\n"
        f"📝 *Status:* One\\-time use\n"
        f"📅 *Created On:* {md_safe(created_at)}\n\n"
        "✨ _Share these keys with your users to grant them access\\!_"
    )

def premium_summary(fname_stem: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out_name = output_filename(fname_stem)
    return (
        "🔮 *PREMIUM FILE GENERATED\\!*\n\n"
        "📊 *GENERATION SUMMARY*\n"
        f"┣ 🎮 Source     : {md_safe(fname_stem.upper())}\n"
        f"┣ 📄 File       : `{md_safe(out_name)}`\n"
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

# ════════════════════════════════════════════════
#  KEYBOARDS
# ════════════════════════════════════════════════
def kb_main(uid, d) -> InlineKeyboardMarkup:
    rows = []
    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")])
    rows += [
        [
            InlineKeyboardButton("📂 Database",  callback_data="db"),
            InlineKeyboardButton("🔑 Redeem",    callback_data="redeem_info"),
        ],
        [
            InlineKeyboardButton("👤 My Status", callback_data="status"),
            InlineKeyboardButton("📋 Commands",  callback_data="commands"),
        ],
        [
            InlineKeyboardButton("📞 Contact Admin", callback_data="contact_admin"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key",   callback_data="adm_create")],
        [InlineKeyboardButton("🗝 Active Keys",  callback_data="adm_keys")],
        [InlineKeyboardButton("👥 Admins List",  callback_data="adm_list")],
        [InlineKeyboardButton("👥 All Members",  callback_data="adm_members")],
        [InlineKeyboardButton("🔙 Back",         callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "🔙 Back to Admin" if dest == "admin" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

def kb_db_files(files: list) -> InlineKeyboardMarkup:
    rows = []
    for fname in files:
        fpath = os.path.join(DB_FOLDER, fname)
        cnt   = count_lines(fpath)
        label = f"📄 {Path(fname).stem}  ({cnt:,} lines)"
        rows.append([InlineKeyboardButton(label, callback_data=f"dbfile:{fname}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)

# ════════════════════════════════════════════════
#  WELCOME TEXT BUILDER
# ════════════════════════════════════════════════
def build_welcome(first_name: str, username, uid, d: dict) -> str:
    status       = "✅ Active" if has_access(uid, d) else "🔒 No Access"
    welcome_line = random_welcome()
    safe_name    = md_safe(first_name or "Operator")
    user_line    = f"👤 *{safe_name}*"
    if username:
        user_line += f"  \\(@{md_safe(username)}\\)"
    return (
        f"{welcome_line}\n\n"
        f"{user_line}\n"
        f"🔐 Status : {status}"
    )

# ════════════════════════════════════════════════
#  AUTO-DELETE HELPER
# ════════════════════════════════════════════════
async def _auto_delete(delay: int, *messages):
    await asyncio.sleep(delay)
    for m in messages:
        try:
            await m.delete()
        except Exception:
            pass

# ════════════════════════════════════════════════
#  DATABASE DECREASE HELPER
# ════════════════════════════════════════════════
def consume_lines(fpath: str, n: int) -> tuple:
    with open(fpath, "r", errors="ignore") as f:
        all_lines = f.readlines()
    to_send   = all_lines[:n]
    leftover  = all_lines[n:]
    remaining = len(leftover)
    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(leftover)
    return "".join(to_send), remaining

# ════════════════════════════════════════════════
#  SAFE EDIT HELPERS
# ════════════════════════════════════════════════
async def safe_edit(q, text, parse_mode, reply_markup=None):
    """Try edit_message_text, fall back to edit_message_caption."""
    kwargs = {"parse_mode": parse_mode}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    try:
        await q.edit_message_text(text, **kwargs)
    except Exception:
        try:
            await q.edit_message_caption(caption=text, **kwargs)
        except Exception as e:
            logger.warning("safe_edit failed: %s", e)

# ════════════════════════════════════════════════
#  ENSURE USER IS TRACKED (for commands without /start)
# ════════════════════════════════════════════════
async def ensure_tracked(update: Update):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    return d

# ════════════════════════════════════════════════
#  /start — sends GIF + welcome text
# ════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)

    welcome_text = build_welcome(user.first_name, user.username, user.id, d)
    kb           = kb_main(user.id, d)

    try:
        await update.message.reply_animation(
            animation=LOGO_GIF_URL,
            caption=welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning("GIF send failed (%s), falling back to text.", e)
        try:
            await update.message.reply_text(
                f"{welcome_text}",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb,
            )
        except Exception as e2:
            logger.error("start fallback also failed: %s", e2)

# ════════════════════════════════════════════════
#  /createkeys — admin only
# ════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(update.effective_user.id, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(
            f"❌ This command is for admins only\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "📋 *Usage:*\n"
            "`/createkeys <count> <max\\_users> <duration>`\n\n"
            "*Or single key:*\n"
            "`/createkeys <max\\_users> <duration>`\n\n"
            "*Duration examples:*\n"
            "  `10d` — 10 days\n"
            "  `2h` — 2 hours\n"
            "  `30m` — 30 minutes\n"
            "  `lifetime` — never expires",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    count   = 1
    devices = 1

    if len(ctx.args) >= 3:
        try:
            count_try   = int(ctx.args[0])
            devices_try = int(ctx.args[1])
            raw_dur     = " ".join(ctx.args[2:])
            count   = count_try
            devices = devices_try
        except ValueError:
            try:
                devices = int(ctx.args[0])
                raw_dur = " ".join(ctx.args[1:])
            except ValueError:
                await update.message.reply_text("❌ Invalid arguments. First arg must be a number.")
                return
    else:
        try:
            devices = int(ctx.args[0])
            raw_dur = " ".join(ctx.args[1:])
        except ValueError:
            await update.message.reply_text("❌ Max users must be a positive integer.")
            return

    if count < 1 or count > 50:
        await update.message.reply_text("❌ Key count must be between 1 and 50.")
        return
    if devices < 1:
        await update.message.reply_text("❌ Max users must be a positive integer.")
        return

    try:
        td, duration_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid duration\\.\n\nExamples: `10d` / `2h` / `30m` / `lifetime`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    created_at     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_keys = []

    for _ in range(count):
        key = generate_key()
        while key in d["keys"]:
            key = generate_key()
        d["keys"][key] = {
            "devices":     devices,
            "duration":    raw_dur,
            "expires":     None,
            "used_by":     [],
            "user_expiry": {},
            "created_by":  str(uid),
            "created_at":  datetime.now().isoformat(),
        }
        generated_keys.append(key)

    save(d)
    logger.info("%d key(s) created: duration=%s devices=%s by=%s", count, raw_dur, devices, uid)

    if count == 1:
        msg = key_message_single(generated_keys[0], duration_label, devices, created_at)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    else:
        msg = keys_batch_message(generated_keys, duration_label, created_at)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

# ════════════════════════════════════════════════
#  /redeem <key>
# ════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if not ctx.args:
        await update.message.reply_text(
            "🔑 *Usage:*\n`/redeem ZEIJIE-PREMIUM-XXXXXX`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text(
            f"❌ *Invalid key\\.*\n\nDouble\\-check and try again\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    k = d["keys"][key]

    if uid in k.get("used_by", []):
        existing_rd = d.get("redeemed", {}).get(uid)
        if existing_rd and existing_rd.get("key") == key:
            exp = existing_rd.get("expires")
            if exp:
                try:
                    if datetime.fromisoformat(exp) <= datetime.now():
                        await update.message.reply_text(
                            f"⛔ *Your key has expired\\.*\n\n"
                            f"Contact admin for a new key: {md_safe(ADMIN_USERNAME)}",
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                        return
                except ValueError:
                    pass
        await update.message.reply_text("⚠️ This key is already activated on your account.")
        return

    if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
        await update.message.reply_text(
            f"❌ Device limit reached for this key\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
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
    save(d)
    logger.info("Key redeemed: %s  by uid=%s  expires=%s", key, uid, expires_iso)

    await update.message.reply_text(
        "┌─────────────────────────────┐\n"
        "│  ✅  KEY ACTIVATED!         │\n"
        "└─────────────────────────────┘\n\n"
        f"`{key}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*   : {dur_label}\n"
        f"📅 *Expires*    : {expiry_display(expires_iso)}\n"
        f"📱 *Device*     : Locked to your account\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Your access timer has started now._ ✅",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /status
# ════════════════════════════════════════════════
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "👑 *Admin Account*\nFull access granted — no key needed.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            f"🔒 *No Active Key*\n\nUse `/redeem <key>` to activate access\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    exp     = rd.get("expires")
    expired = False
    if exp:
        try:
            expired = datetime.fromisoformat(exp) <= datetime.now()
        except ValueError:
            pass

    activated = rd.get("activated", "Unknown")
    if expired:
        txt = (
            "⛔ *Access Expired*\n\n"
            f"🔑 Key     : `{rd['key']}`\n"
            f"📅 Expired : {expiry_display(exp)}\n\n"
            f"_Contact admin for a new key: {ADMIN_USERNAME}_"
        )
        await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)
    else:
        txt = (
            "✅ *Access Active*\n\n"
            f"🔑 Key      : `{rd['key']}`\n"
            f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
            f"🕐 Started  : {activated[:19]}\n"
            f"📅 Expires  : {expiry_display(exp)}"
        )
        await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

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
    if target not in [str(a) for a in d["admins"]]:
        d["admins"].append(target)
        save(d)
        logger.info("Admin added: %s", target)
    await update.message.reply_text(
        f"✅ Admin added: `{target}`", parse_mode=ParseMode.MARKDOWN
    )

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
    if target in [str(a) for a in d["admins"]]:
        d["admins"] = [a for a in d["admins"] if str(a) != target]
        save(d)
        logger.info("Admin removed: %s", target)
        await update.message.reply_text(
            f"✅ Admin removed: `{target}`", parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"⚠️ User `{target}` is not an admin.", parse_mode=ParseMode.MARKDOWN
        )

# ════════════════════════════════════════════════
#  /revokekey <key>  — admin only
# ════════════════════════════════════════════════
async def revokekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /revokekey <KEY>")
        return
    key = ctx.args[0].strip().upper()
    if key not in d["keys"]:
        await update.message.reply_text("❌ Key not found.")
        return
    del d["keys"][key]
    d["redeemed"] = {u: v for u, v in d["redeemed"].items() if v.get("key") != key}
    save(d)
    await update.message.reply_text(
        f"✅ Key revoked: `{key}`\n_All users on this key lost access._",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /getfile <filename>  — premium users
# ════════════════════════════════════════════════
async def getfile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not has_access(uid, d):
        await update.message.reply_text(
            no_access_text(),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    files = get_db_files()
    if not files:
        await update.message.reply_text("📂 No files available in the database.")
        return

    if not ctx.args:
        listing = "\n".join(
            f"  • `{f}` — {count_lines(os.path.join(DB_FOLDER, f)):,} lines"
            for f in files
        )
        await update.message.reply_text(
            f"📂 *Available files:*\n\n{listing}\n\nUsage: `/getfile <filename>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    fname = ctx.args[0].strip()
    fpath = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        await update.message.reply_text(
            f"❌ File `{md_safe_v1(fname)}` not found.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    total = count_lines(fpath)
    if total == 0:
        await update.message.reply_text(
            f"⚠️ `{md_safe_v1(fname)}` is empty or has been exhausted.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    lines_to_send = min(LINES_PER_USE, total)
    content, remaining = consume_lines(fpath, lines_to_send)

    stem     = Path(fname).stem
    out_name = output_filename(stem)
    buf      = io.BytesIO(content.encode("utf-8"))
    buf.name = out_name

    sent_msg = await update.message.reply_document(
        document=buf,
        filename=out_name,
        caption=premium_summary(stem, lines_to_send, remaining),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    asyncio.create_task(_auto_delete(300, sent_msg))

# ════════════════════════════════════════════════
#  /contact — contact admin
# ════════════════════════════════════════════════
async def contact_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    track(update.effective_user.id, update.effective_user.username,
          update.effective_user.first_name, d)
    await update.message.reply_text(
        f"📞 *Contact Admin*\n\n"
        f"For keys, access issues, or support:\n\n"
        f"👤 Admin: {md_safe(ADMIN_USERNAME)}\n\n"
        f"_You cannot access this database without a key\\._\n"
        f"_Contact admin to get a key & gain access\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ════════════════════════════════════════════════
#  UNKNOWN COMMAND HANDLER
#  Lets buyers/admins use commands without /start
# ════════════════════════════════════════════════
async def unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    # Show them the menu so they can navigate
    welcome_text = build_welcome(user.first_name, user.username, user.id, d)
    kb           = kb_main(user.id, d)
    try:
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning("unknown_command reply failed: %s", e)

# ════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ════════════════════════════════════════════════
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    d    = load()
    uid  = q.from_user.id
    data = q.data
    await q.answer()

    track(uid, q.from_user.username, q.from_user.first_name, d)
    save(d)

    # ── Home ──────────────────────────────────────────────────────
    if data == "home":
        welcome_text = build_welcome(q.from_user.first_name, q.from_user.username, uid, d)
        await safe_edit(q, welcome_text, ParseMode.MARKDOWN_V2, kb_main(uid, d))

    # ── Admin Panel ───────────────────────────────────────────────
    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        await safe_edit(
            q,
            "⚡ *Admin Panel*\n\nChoose an option below:",
            ParseMode.MARKDOWN,
            kb_admin(),
        )

    # ── Create Key info ───────────────────────────────────────────
    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        txt = (
            "🔑 *Create Keys*\n\n"
            "Send this command in chat:\n\n"
            "*Single key:*\n"
            "`/createkeys <max\\_users> <duration>`\n\n"
            "*Multiple keys:*\n"
            "`/createkeys <count> <max\\_users> <duration>`\n\n"
            "*Key format:* `ZEIJIE\\-PREMIUM\\-XXXXXX`\n\n"
            "*Examples:*\n"
            "  `/createkeys 1 7d` — 1 key, 7 days\n"
            "  `/createkeys 5 1 1m` — 5 keys, 1 min each\n"
            "  `/createkeys 3 1 lifetime`\n\n"
            "_Timer starts when buyer redeems the key\\._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back("admin"))

    # ── Active Keys ───────────────────────────────────────────────
    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return

        keys     = d.get("keys", {})
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})

        if not keys:
            txt = "🗝 *No keys created yet.*\n\nUse `/createkeys <users> <duration>` to create one."
        else:
            lines = [f"🗝 *All Keys ({len(keys)}):*\n"]
            for k, v in keys.items():
                used_by  = v.get("used_by", [])
                devices  = v.get("devices", 1)
                raw_dur  = v.get("duration", "?")
                used_cnt = len(used_by)

                if used_cnt == 0:
                    status_icon = "🟡 Unused"
                elif used_cnt < devices:
                    status_icon = "🟢 Partial"
                else:
                    status_icon = "🔵 Full"

                block = (
                    f"{status_icon}\n"
                    f"🔑 `{k}`\n"
                    f"   ⏱ Duration : {raw_dur}\n"
                    f"   👥 Used     : {used_cnt}/{devices}"
                )

                for u_id in used_by:
                    rd    = redeemed.get(str(u_id))
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    exp_str = expiry_display(rd["expires"]) if rd else "Unknown"
                    if rd and rd.get("expires"):
                        try:
                            if datetime.fromisoformat(rd["expires"]) <= datetime.now():
                                exp_str += " ⛔ EXPIRED"
                        except ValueError:
                            pass
                    block += f"\n   └ {label}: {exp_str}"

                lines.append(block)

            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_... truncated_"

        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── Admins List ───────────────────────────────────────────────
    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        admins = d.get("admins", [])
        txt = (
            "👥 *No extra admins.*\n_(Owner always has full access)_"
            if not admins
            else "👥 *Admins:*\n\n" + "\n".join(f"  • `{a}`" for a in admins)
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── All Members ───────────────────────────────────────────────
    elif data == "adm_members":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        members  = d.get("members", {})
        redeemed = d.get("redeemed", {})
        if not members:
            txt = "👥 *No members yet.*"
        else:
            lines = [f"👥 *Members ({len(members)}):*\n"]
            for m_id, info in members.items():
                uname   = info.get("username", "")
                fname   = info.get("first_name", "")
                label   = f"@{uname}" if uname else md_safe_v1(fname or m_id)
                rd      = redeemed.get(m_id)
                acc     = "✅" if has_access(int(m_id), d) else "🔒"
                exp_str = expiry_display(rd["expires"]) if rd else "No key"
                lines.append(f"{acc} {label} (`{m_id}`)\n   📅 {exp_str}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_... truncated_"
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── Database ──────────────────────────────────────────────────
    elif data == "db":
        if not has_access(uid, d):
            await safe_edit(q, no_access_text(), ParseMode.MARKDOWN_V2, kb_back())
            return

        files = get_db_files()
        if not files:
            txt = (
                "📂 *Database is empty\\.*\n\n"
                "Upload `.txt` files into the `database/` folder on the server\\."
            )
            await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())
            return

        lines = ["📂 *Database Files:*\n"]
        for fname in files:
            cnt = count_lines(os.path.join(DB_FOLDER, fname))
            lines.append(f"  • `{fname}` — {cnt:,} lines")
        lines.append("\n_Tap a file below to generate and download\\._")
        txt = "\n".join(lines)

        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_db_files(files))

    # ── Database File Selected (download) ─────────────────────────
    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

        if not has_access(uid, d):
            await q.answer(
                "🔒 You cannot access this database. Contact admin to get a key.",
                show_alert=True,
            )
            return

        fpath = os.path.join(DB_FOLDER, fname)
        if not os.path.isfile(fpath):
            await q.answer("❌ File not found on server.", show_alert=True)
            return

        total = count_lines(fpath)
        if total == 0:
            await q.answer(
                "⚠️ This file is empty or exhausted. Contact admin.", show_alert=True
            )
            return

        lines_to_send = min(LINES_PER_USE, total)
        content, remaining = consume_lines(fpath, lines_to_send)

        stem     = Path(fname).stem
        out_name = output_filename(stem)
        buf      = io.BytesIO(content.encode("utf-8"))
        buf.name = out_name

        sent_msg = await q.message.reply_document(
            document=buf,
            filename=out_name,
            caption=premium_summary(stem, lines_to_send, remaining),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        asyncio.create_task(_auto_delete(300, sent_msg))

    # ── Redeem Info ───────────────────────────────────────────────
    elif data == "redeem_info":
        txt = (
            "🔑 *Redeem a Key*\n\n"
            "Send this command:\n`/redeem ZEIJIE-PREMIUM-XXXXXX`\n\n"
            "_Your access timer starts the moment you redeem._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Status ────────────────────────────────────────────────────
    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "👑 *Admin Account*\nFull access granted — no key needed."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = (
                    f"🔒 *No Active Key*\n\nUse `/redeem <key>` to get access\\.\n\n"
                    f"Contact admin: {md_safe(ADMIN_USERNAME)}"
                )
                await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())
                return
            else:
                exp     = rd.get("expires")
                expired = False
                if exp:
                    try:
                        expired = datetime.fromisoformat(exp) <= datetime.now()
                    except ValueError:
                        pass
                activated = rd.get("activated", "Unknown")
                if expired:
                    txt = (
                        "⛔ *Access Expired*\n\n"
                        f"🔑 Key     : `{rd['key']}`\n"
                        f"📅 Expired : {expiry_display(exp)}\n\n"
                        f"_Contact admin for a new key: {ADMIN_USERNAME}_"
                    )
                else:
                    txt = (
                        "✅ *Access Active*\n\n"
                        f"🔑 Key      : `{rd['key']}`\n"
                        f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
                        f"🕐 Started  : {activated[:19]}\n"
                        f"📅 Expires  : {expiry_display(exp)}"
                    )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Commands ──────────────────────────────────────────────────
    elif data == "commands":
        txt = (
            "📋 *Commands*\n\n"
            "👤 *User:*\n"
            "  /start — Main menu\n"
            "  /redeem `<key>` — Activate a key\n"
            "  /status — Check your access\n"
            "  /getfile `<filename>` — Download file\n"
            "  /contact — Contact admin\n\n"
            "🛡 *Admin:*\n"
            "  /createkeys `<count> <users> <dur>` — Bulk create\n"
            "  /createkeys `<users> <duration>` — Single key\n"
            "  /revokekey `<key>` — Delete a key\n"
            "  /addadmin `<id>` — Add admin (owner only)\n"
            "  /removeadmin `<id>` — Remove admin (owner only)\n\n"
            f"📞 *Contact Admin:* {ADMIN_USERNAME}"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Contact Admin ─────────────────────────────────────────────
    elif data == "contact_admin":
        txt = (
            f"📞 *Contact Admin*\n\n"
            f"For keys, access issues, or support:\n\n"
            f"👤 Admin: {md_safe(ADMIN_USERNAME)}\n\n"
            f"_You cannot access this database without a key\\._\n"
            f"_Contact admin to get a key & gain access\\._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())

# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════
LOCK_FILE = "/tmp/zeijie_bot.lock"

def acquire_lock():
    """Ensure only one bot instance runs at a time using a PID lock file."""
    import fcntl
    lock_fp = open(LOCK_FILE, "w")
    try:
        fcntl.flock(lock_fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        lock_fp.write(str(os.getpid()))
        lock_fp.flush()
        return lock_fp
    except OSError:
        logger.error(
            "Another bot instance is already running (lock held). "
            "Stop it first or delete %s", LOCK_FILE
        )
        raise SystemExit(1)

def main():
    lock_fp = acquire_lock()          # ← blocks duplicate instances

    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("createkeys",   createkeys))
    app.add_handler(CommandHandler("redeem",       redeem))
    app.add_handler(CommandHandler("status",       status_cmd))
    app.add_handler(CommandHandler("addadmin",     addadmin))
    app.add_handler(CommandHandler("removeadmin",  removeadmin))
    app.add_handler(CommandHandler("getfile",      getfile))
    app.add_handler(CommandHandler("revokekey",    revokekey))
    app.add_handler(CommandHandler("contact",      contact_cmd))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(button))

    # Unknown commands — show menu so users don't need /start
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("ZEIJIE BOT starting — polling...")
    try:
        app.run_polling(drop_pending_updates=True)
    finally:
        import fcntl
        fcntl.flock(lock_fp, fcntl.LOCK_UN)
        lock_fp.close()
        try:
            os.remove(LOCK_FILE)
        except OSError:
            pass

if __name__ == "__main__":
    main()

LOGO_TEXT = (
    "```\n"
    "╔══════════════════════════════════╗\n"
    "║   ███████╗███████╗██╗██╗██╗     ║\n"
    "║   ╚══███╔╝██╔════╝██║██║██║     ║\n"
    "║     ███╔╝ █████╗  ██║██║██║     ║\n"
    "║    ███╔╝  ██╔══╝  ██║██║██║     ║\n"
    "║   ███████╗███████╗██║██║███████╗║\n"
    "║   ╚══════╝╚══════╝╚═╝╚═╝╚══════╝║\n"
    "║     V  I  P  ·  P  R  E  M      ║\n"
    "╚══════════════════════════════════╝\n"
    "```"
)

# ════════════════════════════════════════════════
#  WELCOME MESSAGES
# ════════════════════════════════════════════════
WELCOME_LINES = [
    "⚡ *ZEIJIE BOT* is locked, loaded, and ready for action.",
    "🔥 Welcome to *ZEIJIE BOT* — your premium gateway.",
    "🌐 *ZEIJIE BOT* online — Precision · Power · Premium.",
    "🛡 *ZEIJIE BOT* activated — built different, built better.",
    "💎 You've entered *ZEIJIE BOT* — where premium lives.",
    "🚀 *ZEIJIE BOT* is live — Let's get to work.",
    "🎯 *ZEIJIE BOT* standing by — the real deal starts here.",
    "👾 *ZEIJIE BOT* loaded — No limits, only premium access.",
]

def random_welcome() -> str:
    return random.choice(WELCOME_LINES)

# ════════════════════════════════════════════════
#  MARKDOWN SAFETY
# ════════════════════════════════════════════════
def md_safe(text: str) -> str:
    for ch in ("_", "*", "`", "[", "]", "(", ")", "~", ">", "#", "+", "-", "=", "|", "{", "}", ".", "!"):
        text = text.replace(ch, f"\\{ch}")
    return text

def md_safe_v1(text: str) -> str:
    """For MARKDOWN (v1) mode."""
    for ch in ("_", "*", "`", "["):
        text = text.replace(ch, f"\\{ch}")
    return text

# ════════════════════════════════════════════════
#  DATA HELPERS
# ════════════════════════════════════════════════
def load() -> dict:
    default = {"admins": [], "keys": {}, "members": {}, "redeemed": {}}
    if not os.path.exists(DATA_FILE):
        return default
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
    except (json.JSONDecodeError, OSError):
        logger.warning("data.json corrupted — starting fresh.")
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
        logger.error("Failed to save data.json: %s", e)

def is_admin(uid, d) -> bool:
    return str(uid) in [str(x) for x in d.get("admins", [])] or int(uid) == OWNER_ID

def has_access(uid, d) -> bool:
    if is_admin(uid, d):
        return True
    uid_str = str(uid)
    rd = d.get("redeemed", {}).get(uid_str)
    if not rd:
        return False
    exp = rd.get("expires")
    if not exp:
        key = rd.get("key")
        if key and key in d.get("keys", {}):
            return True
        return False
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
    try:
        return sorted(
            f for f in os.listdir(DB_FOLDER)
            if os.path.isfile(os.path.join(DB_FOLDER, f))
        )
    except FileNotFoundError:
        return []

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
    number = "".join(random.choices(string.digits, k=6))
    return f"ZEIJIE-PREMIUM-{number}"

def parse_duration(raw: str):
    dur = raw.strip().lower()
    if dur in ("lifetime", "forever", "inf"):
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

# ════════════════════════════════════════════════
#  EXPIRY DISPLAY
# ════════════════════════════════════════════════
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

    delta      = exp_dt - now
    total_secs = int(delta.total_seconds())
    days_rem   = total_secs // 86400
    hours_rem  = (total_secs % 86400) // 3600
    mins_rem   = (total_secs % 3600)  // 60
    secs_rem   = total_secs % 60

    parts = []
    if days_rem:  parts.append(f"{days_rem}d")
    if hours_rem: parts.append(f"{hours_rem}h")
    if mins_rem:  parts.append(f"{mins_rem}m")
    if secs_rem and not days_rem: parts.append(f"{secs_rem}s")

    remaining_str = " ".join(parts) if parts else "< 1s"
    return f"{abs_time}  ({remaining_str} left)"

# ════════════════════════════════════════════════
#  OUTPUT FILENAME BUILDER
# ════════════════════════════════════════════════
def output_filename(stem: str) -> str:
    clean = stem.upper().replace(" ", "_")
    return f"{OUTPUT_PREFIX}-{clean}.txt"

# ════════════════════════════════════════════════
#  NO ACCESS MESSAGE
# ════════════════════════════════════════════════
def no_access_text() -> str:
    return (
        "🔒 *Access Denied*\n\n"
        "You cannot access this database\\.\n"
        f"Contact admin to get a key & to access this\\.\n\n"
        f"👤 *Admin:* {md_safe(ADMIN_USERNAME)}"
    )

# ════════════════════════════════════════════════
#  MESSAGE BUILDERS
# ════════════════════════════════════════════════
def key_message_single(key: str, duration_label: str, devices: int, created_at: str) -> str:
    return (
        "┌─────────────────────────────┐\n"
        "│  🔑  KEY GENERATED          │\n"
        "└─────────────────────────────┘\n\n"
        f"`{key}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*   : {duration_label}\n"
        f"📅 *Starts*     : On redeem\n"
        f"👥 *Max Users*  : {devices}\n"
        f"📅 *Created On* : {created_at}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Timer starts when the buyer redeems this key ✅_"
    )

def keys_batch_message(keys: list, duration_label: str, created_at: str) -> str:
    count = len(keys)
    key_lines = "\n".join(f"`{k}`" for k in keys)
    return (
        f"🎉 *{count} Key{'s' if count > 1 else ''} Generated Successfully\\!* 🎉\n\n"
        f"{key_lines}\n\n"
        f"⏳ *Validity \\(each\\):* ⏱️ {md_safe(duration_label)}\n"
        f"📝 *Status:* One\\-time use\n"
        f"📅 *Created On:* {md_safe(created_at)}\n\n"
        "✨ _Share these keys with your users to grant them access\\!_"
    )

def premium_summary(fname_stem: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    out_name = output_filename(fname_stem)
    return (
        "🔮 *PREMIUM FILE GENERATED\\!*\n\n"
        "📊 *GENERATION SUMMARY*\n"
        f"┣ 🎮 Source     : {md_safe(fname_stem.upper())}\n"
        f"┣ 📄 File       : `{md_safe(out_name)}`\n"
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

# ════════════════════════════════════════════════
#  KEYBOARDS
# ════════════════════════════════════════════════
def kb_main(uid, d) -> InlineKeyboardMarkup:
    rows = []
    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")])
    rows += [
        [
            InlineKeyboardButton("📂 Database",  callback_data="db"),
            InlineKeyboardButton("🔑 Redeem",    callback_data="redeem_info"),
        ],
        [
            InlineKeyboardButton("👤 My Status", callback_data="status"),
            InlineKeyboardButton("📋 Commands",  callback_data="commands"),
        ],
        [
            InlineKeyboardButton("📞 Contact Admin", callback_data="contact_admin"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key",   callback_data="adm_create")],
        [InlineKeyboardButton("🗝 Active Keys",  callback_data="adm_keys")],
        [InlineKeyboardButton("👥 Admins List",  callback_data="adm_list")],
        [InlineKeyboardButton("👥 All Members",  callback_data="adm_members")],
        [InlineKeyboardButton("🔙 Back",         callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "🔙 Back to Admin" if dest == "admin" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

def kb_db_files(files: list) -> InlineKeyboardMarkup:
    rows = []
    for fname in files:
        fpath = os.path.join(DB_FOLDER, fname)
        cnt   = count_lines(fpath)
        label = f"📄 {Path(fname).stem}  ({cnt:,} lines)"
        rows.append([InlineKeyboardButton(label, callback_data=f"dbfile:{fname}")])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)

# ════════════════════════════════════════════════
#  WELCOME TEXT BUILDER
# ════════════════════════════════════════════════
def build_welcome(first_name: str, username, uid, d: dict) -> str:
    status       = "✅ Active" if has_access(uid, d) else "🔒 No Access"
    welcome_line = random_welcome()
    safe_name    = md_safe(first_name or "Operator")
    user_line    = f"👤 *{safe_name}*"
    if username:
        user_line += f"  \\(@{md_safe(username)}\\)"
    return (
        f"{welcome_line}\n\n"
        f"{user_line}\n"
        f"🔐 Status : {status}"
    )

# ════════════════════════════════════════════════
#  AUTO-DELETE HELPER
# ════════════════════════════════════════════════
async def _auto_delete(delay: int, *messages):
    await asyncio.sleep(delay)
    for m in messages:
        try:
            await m.delete()
        except Exception:
            pass

# ════════════════════════════════════════════════
#  DATABASE DECREASE HELPER
# ════════════════════════════════════════════════
def consume_lines(fpath: str, n: int) -> tuple:
    with open(fpath, "r", errors="ignore") as f:
        all_lines = f.readlines()
    to_send   = all_lines[:n]
    leftover  = all_lines[n:]
    remaining = len(leftover)
    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(leftover)
    return "".join(to_send), remaining

# ════════════════════════════════════════════════
#  SAFE EDIT HELPERS
# ════════════════════════════════════════════════
async def safe_edit(q, text, parse_mode, reply_markup=None):
    """Try edit_message_text, fall back to edit_message_caption."""
    kwargs = {"parse_mode": parse_mode}
    if reply_markup:
        kwargs["reply_markup"] = reply_markup
    try:
        await q.edit_message_text(text, **kwargs)
    except Exception:
        try:
            await q.edit_message_caption(caption=text, **kwargs)
        except Exception as e:
            logger.warning("safe_edit failed: %s", e)

# ════════════════════════════════════════════════
#  ENSURE USER IS TRACKED (for commands without /start)
# ════════════════════════════════════════════════
async def ensure_tracked(update: Update):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    return d

# ════════════════════════════════════════════════
#  /start — sends GIF + welcome text
# ════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)

    welcome_text = build_welcome(user.first_name, user.username, user.id, d)
    kb           = kb_main(user.id, d)

    try:
        await update.message.reply_animation(
            animation=LOGO_GIF_URL,
            caption=welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning("GIF send failed (%s), falling back to text.", e)
        try:
            await update.message.reply_text(
                f"{welcome_text}",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb,
            )
        except Exception as e2:
            logger.error("start fallback also failed: %s", e2)

# ════════════════════════════════════════════════
#  /createkeys — admin only
# ════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(update.effective_user.id, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(
            f"❌ This command is for admins only\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "📋 *Usage:*\n"
            "`/createkeys <count> <max\\_users> <duration>`\n\n"
            "*Or single key:*\n"
            "`/createkeys <max\\_users> <duration>`\n\n"
            "*Duration examples:*\n"
            "  `10d` — 10 days\n"
            "  `2h` — 2 hours\n"
            "  `30m` — 30 minutes\n"
            "  `lifetime` — never expires",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    count   = 1
    devices = 1

    if len(ctx.args) >= 3:
        try:
            count_try   = int(ctx.args[0])
            devices_try = int(ctx.args[1])
            raw_dur     = " ".join(ctx.args[2:])
            count   = count_try
            devices = devices_try
        except ValueError:
            try:
                devices = int(ctx.args[0])
                raw_dur = " ".join(ctx.args[1:])
            except ValueError:
                await update.message.reply_text("❌ Invalid arguments. First arg must be a number.")
                return
    else:
        try:
            devices = int(ctx.args[0])
            raw_dur = " ".join(ctx.args[1:])
        except ValueError:
            await update.message.reply_text("❌ Max users must be a positive integer.")
            return

    if count < 1 or count > 50:
        await update.message.reply_text("❌ Key count must be between 1 and 50.")
        return
    if devices < 1:
        await update.message.reply_text("❌ Max users must be a positive integer.")
        return

    try:
        td, duration_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid duration\\.\n\nExamples: `10d` / `2h` / `30m` / `lifetime`",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    created_at     = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    generated_keys = []

    for _ in range(count):
        key = generate_key()
        while key in d["keys"]:
            key = generate_key()
        d["keys"][key] = {
            "devices":     devices,
            "duration":    raw_dur,
            "expires":     None,
            "used_by":     [],
            "user_expiry": {},
            "created_by":  str(uid),
            "created_at":  datetime.now().isoformat(),
        }
        generated_keys.append(key)

    save(d)
    logger.info("%d key(s) created: duration=%s devices=%s by=%s", count, raw_dur, devices, uid)

    if count == 1:
        msg = key_message_single(generated_keys[0], duration_label, devices, created_at)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
    else:
        msg = keys_batch_message(generated_keys, duration_label, created_at)
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN_V2)

# ════════════════════════════════════════════════
#  /redeem <key>
# ════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if not ctx.args:
        await update.message.reply_text(
            "🔑 *Usage:*\n`/redeem ZEIJIE-PREMIUM-XXXXXX`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text(
            f"❌ *Invalid key\\.*\n\nDouble\\-check and try again\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    k = d["keys"][key]

    if uid in k.get("used_by", []):
        existing_rd = d.get("redeemed", {}).get(uid)
        if existing_rd and existing_rd.get("key") == key:
            exp = existing_rd.get("expires")
            if exp:
                try:
                    if datetime.fromisoformat(exp) <= datetime.now():
                        await update.message.reply_text(
                            f"⛔ *Your key has expired\\.*\n\n"
                            f"Contact admin for a new key: {md_safe(ADMIN_USERNAME)}",
                            parse_mode=ParseMode.MARKDOWN_V2,
                        )
                        return
                except ValueError:
                    pass
        await update.message.reply_text("⚠️ This key is already activated on your account.")
        return

    if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
        await update.message.reply_text(
            f"❌ Device limit reached for this key\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
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
    save(d)
    logger.info("Key redeemed: %s  by uid=%s  expires=%s", key, uid, expires_iso)

    await update.message.reply_text(
        "┌─────────────────────────────┐\n"
        "│  ✅  KEY ACTIVATED!         │\n"
        "└─────────────────────────────┘\n\n"
        f"`{key}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ *Duration*   : {dur_label}\n"
        f"📅 *Expires*    : {expiry_display(expires_iso)}\n"
        f"📱 *Device*     : Locked to your account\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "_Your access timer has started now._ ✅",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /status
# ════════════════════════════════════════════════
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "👑 *Admin Account*\nFull access granted — no key needed.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            f"🔒 *No Active Key*\n\nUse `/redeem <key>` to activate access\\.\n\n"
            f"Contact admin: {md_safe(ADMIN_USERNAME)}",
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    exp     = rd.get("expires")
    expired = False
    if exp:
        try:
            expired = datetime.fromisoformat(exp) <= datetime.now()
        except ValueError:
            pass

    activated = rd.get("activated", "Unknown")
    if expired:
        txt = (
            "⛔ *Access Expired*\n\n"
            f"🔑 Key     : `{rd['key']}`\n"
            f"📅 Expired : {expiry_display(exp)}\n\n"
            f"_Contact admin for a new key: {ADMIN_USERNAME}_"
        )
        await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)
    else:
        txt = (
            "✅ *Access Active*\n\n"
            f"🔑 Key      : `{rd['key']}`\n"
            f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
            f"🕐 Started  : {activated[:19]}\n"
            f"📅 Expires  : {expiry_display(exp)}"
        )
        await update.message.reply_text(txt, parse_mode=ParseMode.MARKDOWN)

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
    if target not in [str(a) for a in d["admins"]]:
        d["admins"].append(target)
        save(d)
        logger.info("Admin added: %s", target)
    await update.message.reply_text(
        f"✅ Admin added: `{target}`", parse_mode=ParseMode.MARKDOWN
    )

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
    if target in [str(a) for a in d["admins"]]:
        d["admins"] = [a for a in d["admins"] if str(a) != target]
        save(d)
        logger.info("Admin removed: %s", target)
        await update.message.reply_text(
            f"✅ Admin removed: `{target}`", parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text(
            f"⚠️ User `{target}` is not an admin.", parse_mode=ParseMode.MARKDOWN
        )

# ════════════════════════════════════════════════
#  /revokekey <key>  — admin only
# ════════════════════════════════════════════════
async def revokekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /revokekey <KEY>")
        return
    key = ctx.args[0].strip().upper()
    if key not in d["keys"]:
        await update.message.reply_text("❌ Key not found.")
        return
    del d["keys"][key]
    d["redeemed"] = {u: v for u, v in d["redeemed"].items() if v.get("key") != key}
    save(d)
    await update.message.reply_text(
        f"✅ Key revoked: `{key}`\n_All users on this key lost access._",
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /getfile <filename>  — premium users
# ════════════════════════════════════════════════
async def getfile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not has_access(uid, d):
        await update.message.reply_text(
            no_access_text(),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        return

    files = get_db_files()
    if not files:
        await update.message.reply_text("📂 No files available in the database.")
        return

    if not ctx.args:
        listing = "\n".join(
            f"  • `{f}` — {count_lines(os.path.join(DB_FOLDER, f)):,} lines"
            for f in files
        )
        await update.message.reply_text(
            f"📂 *Available files:*\n\n{listing}\n\nUsage: `/getfile <filename>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    fname = ctx.args[0].strip()
    fpath = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        await update.message.reply_text(
            f"❌ File `{md_safe_v1(fname)}` not found.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    total = count_lines(fpath)
    if total == 0:
        await update.message.reply_text(
            f"⚠️ `{md_safe_v1(fname)}` is empty or has been exhausted.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    lines_to_send = min(LINES_PER_USE, total)
    content, remaining = consume_lines(fpath, lines_to_send)

    stem     = Path(fname).stem
    out_name = output_filename(stem)
    buf      = io.BytesIO(content.encode("utf-8"))
    buf.name = out_name

    sent_msg = await update.message.reply_document(
        document=buf,
        filename=out_name,
        caption=premium_summary(stem, lines_to_send, remaining),
        parse_mode=ParseMode.MARKDOWN_V2,
    )
    asyncio.create_task(_auto_delete(300, sent_msg))

# ════════════════════════════════════════════════
#  /contact — contact admin
# ════════════════════════════════════════════════
async def contact_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    track(update.effective_user.id, update.effective_user.username,
          update.effective_user.first_name, d)
    await update.message.reply_text(
        f"📞 *Contact Admin*\n\n"
        f"For keys, access issues, or support:\n\n"
        f"👤 Admin: {md_safe(ADMIN_USERNAME)}\n\n"
        f"_You cannot access this database without a key\\._\n"
        f"_Contact admin to get a key & gain access\\._",
        parse_mode=ParseMode.MARKDOWN_V2,
    )

# ════════════════════════════════════════════════
#  UNKNOWN COMMAND HANDLER
#  Lets buyers/admins use commands without /start
# ════════════════════════════════════════════════
async def unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)
    # Show them the menu so they can navigate
    welcome_text = build_welcome(user.first_name, user.username, user.id, d)
    kb           = kb_main(user.id, d)
    try:
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb,
        )
    except Exception as e:
        logger.warning("unknown_command reply failed: %s", e)

# ════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ════════════════════════════════════════════════
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    d    = load()
    uid  = q.from_user.id
    data = q.data
    await q.answer()

    track(uid, q.from_user.username, q.from_user.first_name, d)
    save(d)

    # ── Home ──────────────────────────────────────────────────────
    if data == "home":
        welcome_text = build_welcome(q.from_user.first_name, q.from_user.username, uid, d)
        await safe_edit(q, welcome_text, ParseMode.MARKDOWN_V2, kb_main(uid, d))

    # ── Admin Panel ───────────────────────────────────────────────
    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        await safe_edit(
            q,
            "⚡ *Admin Panel*\n\nChoose an option below:",
            ParseMode.MARKDOWN,
            kb_admin(),
        )

    # ── Create Key info ───────────────────────────────────────────
    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        txt = (
            "🔑 *Create Keys*\n\n"
            "Send this command in chat:\n\n"
            "*Single key:*\n"
            "`/createkeys <max\\_users> <duration>`\n\n"
            "*Multiple keys:*\n"
            "`/createkeys <count> <max\\_users> <duration>`\n\n"
            "*Key format:* `ZEIJIE\\-PREMIUM\\-XXXXXX`\n\n"
            "*Examples:*\n"
            "  `/createkeys 1 7d` — 1 key, 7 days\n"
            "  `/createkeys 5 1 1m` — 5 keys, 1 min each\n"
            "  `/createkeys 3 1 lifetime`\n\n"
            "_Timer starts when buyer redeems the key\\._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back("admin"))

    # ── Active Keys ───────────────────────────────────────────────
    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return

        keys     = d.get("keys", {})
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})

        if not keys:
            txt = "🗝 *No keys created yet.*\n\nUse `/createkeys <users> <duration>` to create one."
        else:
            lines = [f"🗝 *All Keys ({len(keys)}):*\n"]
            for k, v in keys.items():
                used_by  = v.get("used_by", [])
                devices  = v.get("devices", 1)
                raw_dur  = v.get("duration", "?")
                used_cnt = len(used_by)

                if used_cnt == 0:
                    status_icon = "🟡 Unused"
                elif used_cnt < devices:
                    status_icon = "🟢 Partial"
                else:
                    status_icon = "🔵 Full"

                block = (
                    f"{status_icon}\n"
                    f"🔑 `{k}`\n"
                    f"   ⏱ Duration : {raw_dur}\n"
                    f"   👥 Used     : {used_cnt}/{devices}"
                )

                for u_id in used_by:
                    rd    = redeemed.get(str(u_id))
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    exp_str = expiry_display(rd["expires"]) if rd else "Unknown"
                    if rd and rd.get("expires"):
                        try:
                            if datetime.fromisoformat(rd["expires"]) <= datetime.now():
                                exp_str += " ⛔ EXPIRED"
                        except ValueError:
                            pass
                    block += f"\n   └ {label}: {exp_str}"

                lines.append(block)

            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_... truncated_"

        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── Admins List ───────────────────────────────────────────────
    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        admins = d.get("admins", [])
        txt = (
            "👥 *No extra admins.*\n_(Owner always has full access)_"
            if not admins
            else "👥 *Admins:*\n\n" + "\n".join(f"  • `{a}`" for a in admins)
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── All Members ───────────────────────────────────────────────
    elif data == "adm_members":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        members  = d.get("members", {})
        redeemed = d.get("redeemed", {})
        if not members:
            txt = "👥 *No members yet.*"
        else:
            lines = [f"👥 *Members ({len(members)}):*\n"]
            for m_id, info in members.items():
                uname   = info.get("username", "")
                fname   = info.get("first_name", "")
                label   = f"@{uname}" if uname else md_safe_v1(fname or m_id)
                rd      = redeemed.get(m_id)
                acc     = "✅" if has_access(int(m_id), d) else "🔒"
                exp_str = expiry_display(rd["expires"]) if rd else "No key"
                lines.append(f"{acc} {label} (`{m_id}`)\n   📅 {exp_str}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_... truncated_"
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back("admin"))

    # ── Database ──────────────────────────────────────────────────
    elif data == "db":
        if not has_access(uid, d):
            await safe_edit(q, no_access_text(), ParseMode.MARKDOWN_V2, kb_back())
            return

        files = get_db_files()
        if not files:
            txt = (
                "📂 *Database is empty\\.*\n\n"
                "Upload `.txt` files into the `database/` folder on the server\\."
            )
            await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())
            return

        lines = ["📂 *Database Files:*\n"]
        for fname in files:
            cnt = count_lines(os.path.join(DB_FOLDER, fname))
            lines.append(f"  • `{fname}` — {cnt:,} lines")
        lines.append("\n_Tap a file below to generate and download\\._")
        txt = "\n".join(lines)

        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_db_files(files))

    # ── Database File Selected (download) ─────────────────────────
    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

        if not has_access(uid, d):
            await q.answer(
                "🔒 You cannot access this database. Contact admin to get a key.",
                show_alert=True,
            )
            return

        fpath = os.path.join(DB_FOLDER, fname)
        if not os.path.isfile(fpath):
            await q.answer("❌ File not found on server.", show_alert=True)
            return

        total = count_lines(fpath)
        if total == 0:
            await q.answer(
                "⚠️ This file is empty or exhausted. Contact admin.", show_alert=True
            )
            return

        lines_to_send = min(LINES_PER_USE, total)
        content, remaining = consume_lines(fpath, lines_to_send)

        stem     = Path(fname).stem
        out_name = output_filename(stem)
        buf      = io.BytesIO(content.encode("utf-8"))
        buf.name = out_name

        sent_msg = await q.message.reply_document(
            document=buf,
            filename=out_name,
            caption=premium_summary(stem, lines_to_send, remaining),
            parse_mode=ParseMode.MARKDOWN_V2,
        )
        asyncio.create_task(_auto_delete(300, sent_msg))

    # ── Redeem Info ───────────────────────────────────────────────
    elif data == "redeem_info":
        txt = (
            "🔑 *Redeem a Key*\n\n"
            "Send this command:\n`/redeem ZEIJIE-PREMIUM-XXXXXX`\n\n"
            "_Your access timer starts the moment you redeem._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Status ────────────────────────────────────────────────────
    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "👑 *Admin Account*\nFull access granted — no key needed."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = (
                    f"🔒 *No Active Key*\n\nUse `/redeem <key>` to get access\\.\n\n"
                    f"Contact admin: {md_safe(ADMIN_USERNAME)}"
                )
                await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())
                return
            else:
                exp     = rd.get("expires")
                expired = False
                if exp:
                    try:
                        expired = datetime.fromisoformat(exp) <= datetime.now()
                    except ValueError:
                        pass
                activated = rd.get("activated", "Unknown")
                if expired:
                    txt = (
                        "⛔ *Access Expired*\n\n"
                        f"🔑 Key     : `{rd['key']}`\n"
                        f"📅 Expired : {expiry_display(exp)}\n\n"
                        f"_Contact admin for a new key: {ADMIN_USERNAME}_"
                    )
                else:
                    txt = (
                        "✅ *Access Active*\n\n"
                        f"🔑 Key      : `{rd['key']}`\n"
                        f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
                        f"🕐 Started  : {activated[:19]}\n"
                        f"📅 Expires  : {expiry_display(exp)}"
                    )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Commands ──────────────────────────────────────────────────
    elif data == "commands":
        txt = (
            "📋 *Commands*\n\n"
            "👤 *User:*\n"
            "  /start — Main menu\n"
            "  /redeem `<key>` — Activate a key\n"
            "  /status — Check your access\n"
            "  /getfile `<filename>` — Download file\n"
            "  /contact — Contact admin\n\n"
            "🛡 *Admin:*\n"
            "  /createkeys `<count> <users> <dur>` — Bulk create\n"
            "  /createkeys `<users> <duration>` — Single key\n"
            "  /revokekey `<key>` — Delete a key\n"
            "  /addadmin `<id>` — Add admin (owner only)\n"
            "  /removeadmin `<id>` — Remove admin (owner only)\n\n"
            f"📞 *Contact Admin:* {ADMIN_USERNAME}"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN, kb_back())

    # ── Contact Admin ─────────────────────────────────────────────
    elif data == "contact_admin":
        txt = (
            f"📞 *Contact Admin*\n\n"
            f"For keys, access issues, or support:\n\n"
            f"👤 Admin: {md_safe(ADMIN_USERNAME)}\n\n"
            f"_You cannot access this database without a key\\._\n"
            f"_Contact admin to get a key & gain access\\._"
        )
        await safe_edit(q, txt, ParseMode.MARKDOWN_V2, kb_back())

# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("createkeys",   createkeys))
    app.add_handler(CommandHandler("redeem",       redeem))
    app.add_handler(CommandHandler("status",       status_cmd))
    app.add_handler(CommandHandler("addadmin",     addadmin))
    app.add_handler(CommandHandler("removeadmin",  removeadmin))
    app.add_handler(CommandHandler("getfile",      getfile))
    app.add_handler(CommandHandler("revokekey",    revokekey))
    app.add_handler(CommandHandler("contact",      contact_cmd))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(button))

    # Unknown commands — show menu so users don't need /start
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))

    logger.info("ZEIJIE BOT starting — polling...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
