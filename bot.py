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

# ════════════════════════════════════════════════
#  CONFIG  — edit before running
# ════════════════════════════════════════════════
BOT_TOKEN     = "8797773644:AAHuuZurs0oiduQNW6ywxvTXQ1Kdf32XE9w"
OWNER_ID      = 8420104044
DATA_FILE     = "data.json"
DB_FOLDER     = "database"
LINES_PER_USE = 250

os.makedirs(DB_FOLDER, exist_ok=True)

# ════════════════════════════════════════════════
#  LOGO
# ════════════════════════════════════════════════
LOGO = (
    "```\n"
    "╔══════════════════════════════════╗\n"
    "║   ███████╗███████╗██╗██╗██╗     ║\n"
    "║   ╚══███╔╝██╔════╝██║██║██║     ║\n"
    "║     ███╔╝ █████╗  ██║██║██║     ║\n"
    "║    ███╔╝  ██╔══╝  ██║██║██║     ║\n"
    "║   ███████╗███████╗██║██║███████╗║\n"
    "║   ╚══════╝╚══════╝╚═╝╚═╝╚══════╝║\n"
    "║        Z E I J I E   B O T      ║\n"
    "╚══════════════════════════════════╝\n"
    "```"
)

# ════════════════════════════════════════════════
#  WELCOME MESSAGES
# ════════════════════════════════════════════════
WELCOME_LINES = [
    "⚡ *ZEIJIE BOT* is locked, loaded, and ready for action.",
    "🔥 Welcome to *ZEIJIE BOT* — your premium gateway.",
    "🌐 *ZEIJIE BOT* online\\. Precision\\. Power\\. Premium\\.",
    "🛡 *ZEIJIE BOT* activated — built different, built better.",
    "💎 You've entered *ZEIJIE BOT* — where premium lives.",
    "🚀 *ZEIJIE BOT* is live\\. Let's get to work\\.",
    "🎯 *ZEIJIE BOT* standing by — the real deal starts here.",
    "👾 *ZEIJIE BOT* loaded\\. No limits, only premium access\\.",
]

def random_welcome() -> str:
    return random.choice(WELCOME_LINES)

# ════════════════════════════════════════════════
#  MARKDOWN SAFETY
# ════════════════════════════════════════════════
def md_safe(text: str) -> str:
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
        logger.warning("data.json corrupted or unreadable — starting fresh.")
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
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    exp = rd.get("expires")
    if not exp:
        return True
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

# ════════════════════════════════════════════════
#  KEY HELPERS
# ════════════════════════════════════════════════
def generate_key() -> str:
    part1  = "".join(random.choices(string.ascii_uppercase, k=6))
    part2  = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    ts_hex = format(int(datetime.now().timestamp()) & 0xFFFF, "04X")
    extra  = "".join(random.choices(string.ascii_uppercase + string.digits, k=2))
    part3  = ts_hex[:2] + extra + ts_hex[2:]
    return f"ZEIJIE-{part1}-{part2}-{part3}"

def parse_duration(raw: str):
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

# ════════════════════════════════════════════════
#  MESSAGE BUILDERS
# ════════════════════════════════════════════════
def key_message(key: str, duration_label: str, expires_iso, devices: int) -> str:
    exp_str = expiry_display(expires_iso)
    return (
        "🔑 *Key Generated!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"`{key}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ Duration   : {duration_label}\n"
        f"📅 Expires    : {exp_str}\n"
        f"👥 Max users  : {devices}\n\n"
        "_Key saved to database ✅_"
    )

def premium_summary(fname_stem: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "🔮 ✨ PREMIUM FILE GENERATED SUCCESSFULLY! ✨ 🔮\n\n"
        "📊 GENERATION SUMMARY\n"
        f"┣ 🎮 Source      : {fname_stem.upper()}\n"
        f"┣ 📜 Lines       : {sent}\n"
        f"┣ 🕐 Generated   : {now}\n"
        f"┣ 💾 Remaining   : {remaining:,} lines\n"
        "┣ 🧹 Cleanup     : ✅ Done\n\n"
        "🛡 SECURITY\n"
        "┣ 🔒 Auto-Expiry : 5 minutes\n"
        "┣ 🗑 Auto-Delete : Enabled\n"
        "┣ ⚡ Session     : Verified\n\n"
        "⬇️  Download immediately — file deletes in 5 min\n\n"
        "⭐ Thank you for using ZEIJIE Premium!"
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
#  WELCOME TEXT BUILDER
# ════════════════════════════════════════════════
def build_welcome(first_name: str, username, uid, d: dict) -> str:
    status       = "✅ Active" if has_access(uid, d) else "🔒 No Access"
    welcome_line = random_welcome()
    safe_name    = md_safe(first_name or "Operator")
    user_line    = f"👤 *{safe_name}*"
    if username:
        user_line += f"  (@{md_safe(username)})"
    return (
        f"{LOGO}\n\n"
        f"{welcome_line}\n\n"
        f"{user_line}\n"
        f"🔐 Status: {status}"
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
#  /start
# ════════════════════════════════════════════════
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

# ════════════════════════════════════════════════
#  /createkeys <max_users> <duration>  — admin only
# ════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id

    if not is_admin(uid, d):
        await update.message.reply_text("❌ This command is for admins only.")
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "📋 Usage:\n/createkeys <max\\_users> <duration>\n\n"
            "Duration examples:\n"
            "  10d      → 10 days\n"
            "  2h       → 2 hours\n"
            "  30m      → 30 minutes\n"
            "  lifetime → never expires",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        devices = int(ctx.args[0])
        if devices < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Max users must be a positive integer (e.g. 1).")
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
    logger.info("Key created: %s  expires=%s  devices=%s  by=%s", key, expires_iso, devices, uid)

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
        await update.message.reply_text(
            "Usage: `/redeem ZEIJIE-XXXXXX-XXXXXXXX-XXXXXX`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text("❌ Invalid key. Check and try again.")
        return

    k = d["keys"][key]

    if uid in k.get("used_by", []):
        await update.message.reply_text("⚠️ This key is already activated on your account.")
        return

    if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
        await update.message.reply_text("❌ Device limit reached for this key.")
        return

    key_exp = k.get("expires")
    if key_exp:
        try:
            if datetime.fromisoformat(key_exp) < datetime.now():
                await update.message.reply_text("❌ This key has already expired.")
                return
        except ValueError:
            await update.message.reply_text("❌ Key has an invalid expiry date.")
            return

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
    if exp:
        try:
            if datetime.fromisoformat(exp) < datetime.now():
                await update.message.reply_text(
                    "⛔ Your key has *expired*.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
        except ValueError:
            pass

    await update.message.reply_text(
        f"✅ *Active*\n\n"
        f"🔑 `{rd['key']}`\n"
        f"📅 Expires: {expiry_display(exp)}",
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
    if target not in [str(a) for a in d["admins"]]:
        d["admins"].append(target)
        save(d)
        logger.info("Admin added: %s", target)
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
    if target in [str(a) for a in d["admins"]]:
        d["admins"] = [a for a in d["admins"] if str(a) != target]
        save(d)
        logger.info("Admin removed: %s", target)
        await update.message.reply_text(f"✅ Admin removed: `{target}`", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(f"⚠️ User `{target}` is not an admin.", parse_mode=ParseMode.MARKDOWN)

# ════════════════════════════════════════════════
#  /getfile <filename>  — premium users
# ════════════════════════════════════════════════
async def getfile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id

    if not has_access(uid, d):
        await update.message.reply_text(
            "🔒 *Access Denied.*\nRedeem a valid key first: /redeem <key>",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if not ctx.args:
        files = get_db_files()
        if not files:
            await update.message.reply_text("📂 No files in the database folder.")
            return
        listing = "\n".join(f"  • {f}" for f in files)
        await update.message.reply_text(
            f"📂 *Available files:*\n{listing}\n\nUsage: `/getfile <filename>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    fname = ctx.args[0]
    fpath = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        await update.message.reply_text(f"❌ File `{md_safe(fname)}` not found.", parse_mode=ParseMode.MARKDOWN)
        return

    total = count_lines(fpath)
    lines_to_send = min(LINES_PER_USE, total)

    with open(fpath, "r", errors="ignore") as f:
        content = "".join(next(f) for _ in range(lines_to_send))

    buf = io.BytesIO(content.encode("utf-8"))
    buf.name = fname
    remaining = max(0, total - lines_to_send)

    sent_msg = await update.message.reply_document(
        document=buf,
        filename=fname,
        caption=premium_summary(Path(fname).stem, lines_to_send, remaining),
    )

    asyncio.create_task(_auto_delete(300, sent_msg))

# ════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ════════════════════════════════════════════════
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query
    d   = load()
    uid = q.from_user.id
    await q.answer()

    data = q.data

    if data == "home":
        await q.edit_message_text(
            build_welcome(q.from_user.first_name, q.from_user.username, uid, d),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_main(uid, d),
        )

    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            "⚡ *Admin Panel*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_admin(),
        )

    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            "🔑 *Create Key*\n\nUse the command:\n`/createkeys <max_users> <duration>`\n\n"
            "Examples:\n  `/createkeys 1 7d`\n  `/createkeys 5 lifetime`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("admin"),
        )

    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        keys = d.get("keys", {})
        if not keys:
            txt = "🗝 *No keys created yet.*"
        else:
            lines = []
            for k, v in list(keys.items())[-10:]:
                exp = expiry_display(v.get("expires"))
                used = len(v.get("used_by", []))
                dev  = v.get("devices", 1)
                lines.append(f"`{k}`\n  👥 {used}/{dev}  📅 {exp}")
            txt = "🗝 *Recent Keys (last 10):*\n\n" + "\n\n".join(lines)
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("admin"))

    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        admins = d.get("admins", [])
        if not admins:
            txt = "👥 *No extra admins.*\n(Owner always has access)"
        else:
            txt = "👥 *Admins:*\n" + "\n".join(f"  • `{a}`" for a in admins)
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("admin"))

    elif data == "db":
        files = get_db_files()
        if not files:
            txt = "📂 *Database is empty.*"
        else:
            lines = []
            for fname in files:
                cnt = count_lines(os.path.join(DB_FOLDER, fname))
                lines.append(f"  • `{fname}` — {cnt:,} lines")
            txt = "📂 *Database Files:*\n\n" + "\n".join(lines)
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back())

    elif data == "redeem_info":
        await q.edit_message_text(
            "🔑 *Redeem a Key*\n\n"
            "Use the command:\n`/redeem ZEIJIE-XXXXXX-XXXXXXXX-XXXXXX`",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back(),
        )

    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "👑 *Admin Account* — Full access granted."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = "🔒 No active key. Use /redeem <key>"
            else:
                exp = rd.get("expires")
                expired = False
                if exp:
                    try:
                        expired = datetime.fromisoformat(exp) < datetime.now()
                    except ValueError:
                        pass
                if expired:
                    txt = "⛔ Your key has *expired*."
                else:
                    txt = f"✅ *Active*\n\n🔑 `{rd['key']}`\n📅 Expires: {expiry_display(exp)}"
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back())

    elif data == "commands":
        await q.edit_message_text(
            "📋 *Commands*\n\n"
            "👤 *User Commands:*\n"
            "  /start — Main menu\n"
            "  /redeem <key> — Activate a key\n"
            "  /status — Check your access\n"
            "  /getfile <name> — Download a file\n\n"
            "🛡 *Admin Commands:*\n"
            "  /createkeys <users> <duration> — Generate key\n"
            "  /addadmin <id> — Add admin (owner)\n"
            "  /removeadmin <id> — Remove admin (owner)",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back(),
        )

# ════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("createkeys",   createkeys))
    app.add_handler(CommandHandler("redeem",       redeem))
    app.add_handler(CommandHandler("status",       status_cmd))
    app.add_handler(CommandHandler("addadmin",     addadmin))
    app.add_handler(CommandHandler("removeadmin",  removeadmin))
    app.add_handler(CommandHandler("getfile",      getfile))
    app.add_handler(CallbackQueryHandler(button))

    logger.info("ZEIJIE BOT starting…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
