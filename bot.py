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
#  CONFIG
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
    "🌐 *ZEIJIE BOT* online — Precision — Power — Premium.",
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
    part1  = "".join(random.choices(string.ascii_uppercase, k=6))
    part2  = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    ts_hex = format(int(datetime.now().timestamp()) & 0xFFFF, "04X")
    extra  = "".join(random.choices(string.ascii_uppercase + string.digits, k=2))
    part3  = ts_hex[:2] + extra + ts_hex[2:]
    return f"ZEIJIE-{part1}-{part2}-{part3}"

def parse_duration(raw: str):
    """
    Returns (timedelta | None, label_str).
    None = lifetime.  Accepts: lifetime, 1h, 30m, 7d, 10days, 2hours
    """
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
#  MESSAGE BUILDERS
# ════════════════════════════════════════════════
def key_message(key: str, duration_label: str, devices: int) -> str:
    return (
        "🔑 *Key Generated!*\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"`{key}`\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ Duration   : {duration_label}\n"
        f"📅 Expires    : Starts on redeem\n"
        f"👥 Max users  : {devices}\n\n"
        "_Timer starts when the buyer redeems this key ✅_"
    )

def premium_summary(fname_stem: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "🔮 PREMIUM FILE GENERATED!\n\n"
        "📊 GENERATION SUMMARY\n"
        f"┣ 🎮 Source    : {fname_stem.upper()}\n"
        f"┣ 📜 Lines     : {sent}\n"
        f"┣ 🕐 Generated : {now}\n"
        f"┣ 💾 Remaining : {remaining:,} lines\n"
        "┣ 🧹 Cleanup   : Done\n\n"
        "🛡 SECURITY\n"
        "┣ 🔒 Auto-Expiry : 5 minutes\n"
        "┣ 🗑 Auto-Delete : Enabled\n"
        "┣ ⚡ Session     : Verified\n\n"
        "⬇️ Download immediately — file deletes in 5 min\n\n"
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
            InlineKeyboardButton("📂 Database",  callback_data="db"),
            InlineKeyboardButton("🔑 Redeem",    callback_data="redeem_info"),
        ],
        [
            InlineKeyboardButton("👤 Status",    callback_data="status"),
            InlineKeyboardButton("📋 Commands",  callback_data="commands"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key",  callback_data="adm_create")],
        [InlineKeyboardButton("🗝 Active Keys", callback_data="adm_keys")],
        [InlineKeyboardButton("👥 Admins List", callback_data="adm_list")],
        [InlineKeyboardButton("👥 All Members", callback_data="adm_members")],
        [InlineKeyboardButton("🔙 Back",        callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "🔙 Back to Admin" if dest == "admin" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

def kb_db_files(files: list) -> InlineKeyboardMarkup:
    rows = []
    for fname in files:
        rows.append([InlineKeyboardButton(f"📄 {fname}", callback_data=f"dbfile:{fname}")])
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
        user_line += f"  (@{md_safe(username)})"
    return (
        f"{LOGO}\n\n"
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
#  Expiry does NOT start here — it starts on /redeem
# ════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id

    if not is_admin(uid, d):
        await update.message.reply_text("❌ This command is for admins only.")
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "📋 *Usage:*\n`/createkeys <max\\_users> <duration>`\n\n"
            "*Duration examples:*\n"
            "  `10d`      — 10 days\n"
            "  `2h`       — 2 hours\n"
            "  `30m`      — 30 minutes\n"
            "  `lifetime` — never expires\n\n"
            "_Timer starts when the buyer redeems the key._",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    try:
        devices = int(ctx.args[0])
        if devices < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Max users must be a positive integer.")
        return

    raw_dur = " ".join(ctx.args[1:])
    try:
        td, duration_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid duration.\n\nExamples: `10d` / `2h` / `30m` / `lifetime`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    key = generate_key()

    # Store key WITHOUT expiry — expiry is calculated at redeem time
    d["keys"][key] = {
        "devices":    devices,
        "duration":   raw_dur,
        "expires":    None,        # filled in per-user at redeem
        "used_by":    [],
        "user_expiry": {},         # uid -> expiry ISO per redeemer
        "created_by": str(uid),
        "created_at": datetime.now().isoformat(),
    }
    save(d)
    logger.info("Key created: %s  duration=%s  devices=%s  by=%s", key, raw_dur, devices, uid)

    await update.message.reply_text(
        key_message(key, duration_label, devices),
        parse_mode=ParseMode.MARKDOWN,
    )

# ════════════════════════════════════════════════
#  /redeem <key>
#  Expiry timer STARTS HERE
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

    # Calculate expiry NOW — timer starts on redeem
    raw_dur = k.get("duration", "lifetime")
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        td, dur_label = None, raw_dur

    now         = datetime.now()
    expires_dt  = (now + td) if td else None
    expires_iso = expires_dt.isoformat() if expires_dt else None

    # Activate the key for this user
    k.setdefault("used_by", []).append(uid)
    k.setdefault("user_expiry", {})[uid] = expires_iso

    d["redeemed"][uid] = {
        "key":       key,
        "duration":  raw_dur,
        "expires":   expires_iso,    # real expiry, starts NOW
        "activated": now.isoformat(),
    }
    save(d)
    logger.info("Key redeemed: %s  by uid=%s  expires=%s", key, uid, expires_iso)

    await update.message.reply_text(
        "✅ *Key Activated!*\n\n"
        f"🔑 `{key}`\n"
        f"⏱ Duration  : {dur_label}\n"
        f"📅 Expires   : {expiry_display(expires_iso)}\n"
        f"📱 Device    : Locked to your account\n\n"
        "_Your access timer has started now._",
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
            "👑 *Admin Account*\nFull access granted.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            "🔒 *No Active Key*\n\nUse `/redeem <key>` to activate access.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    exp = rd.get("expires")
    if exp:
        try:
            if datetime.fromisoformat(exp) < datetime.now():
                await update.message.reply_text(
                    "⛔ Your key has *expired*.\n\nContact admin for a new key.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
        except ValueError:
            pass

    activated = rd.get("activated", "Unknown")
    await update.message.reply_text(
        "✅ *Access Active*\n\n"
        f"🔑 Key      : `{rd['key']}`\n"
        f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
        f"🕐 Started  : {activated[:19]}\n"
        f"📅 Expires  : {expiry_display(exp)}",
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
        f"✅ Key revoked: `{key}`", parse_mode=ParseMode.MARKDOWN
    )

# ════════════════════════════════════════════════
#  /getfile <filename>  — premium users
# ════════════════════════════════════════════════
async def getfile(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id

    if not has_access(uid, d):
        await update.message.reply_text(
            "🔒 *Access Denied.*\n\nRedeem a valid key first:\n`/redeem <key>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    files = get_db_files()
    if not files:
        await update.message.reply_text("📂 No files available in the database.")
        return

    if not ctx.args:
        listing = "\n".join(f"  • `{f}`" for f in files)
        await update.message.reply_text(
            f"📂 *Available files:*\n\n{listing}\n\nUsage: `/getfile <filename>`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    fname = ctx.args[0].strip()
    fpath = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        await update.message.reply_text(
            f"❌ File `{md_safe(fname)}` not found.",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    total         = count_lines(fpath)
    lines_to_send = min(LINES_PER_USE, total)

    with open(fpath, "r", errors="ignore") as f:
        content = "".join(next(f) for _ in range(lines_to_send))

    buf       = io.BytesIO(content.encode("utf-8"))
    buf.name  = fname
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
    q    = update.callback_query
    d    = load()
    uid  = q.from_user.id
    data = q.data
    await q.answer()

    # ── Home ──────────────────────────────────────────────────────
    if data == "home":
        await q.edit_message_text(
            build_welcome(q.from_user.first_name, q.from_user.username, uid, d),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_main(uid, d),
        )

    # ── Admin Panel ───────────────────────────────────────────────
    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            "⚡ *Admin Panel*\n\nChoose an option below:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_admin(),
        )

    # ── Create Key info ───────────────────────────────────────────
    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            "🔑 *Create Key*\n\n"
            "Send this command in chat:\n"
            "`/createkeys <max\\_users> <duration>`\n\n"
            "*Examples:*\n"
            "  `/createkeys 1 7d`\n"
            "  `/createkeys 3 30d`\n"
            "  `/createkeys 1 lifetime`\n\n"
            "_Timer starts when buyer redeems the key._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back("admin"),
        )

    # ── Active Keys ───────────────────────────────────────────────
    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True)
            return

        keys     = d.get("keys", {})
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})

        if not keys:
            txt = (
                "🗝 *No keys created yet.*\n\n"
                "Use `/createkeys <users> <duration>` to create one."
            )
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

                # Show per-user expiry for each redeemer
                for u_id in used_by:
                    rd = redeemed.get(str(u_id))
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    exp_str = expiry_display(rd["expires"]) if rd else "Unknown"
                    block += f"\n   └ {label}: {exp_str}"

                lines.append(block)

            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_... truncated_"

        await q.edit_message_text(
            txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("admin")
        )

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
        await q.edit_message_text(
            txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("admin")
        )

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
                uname    = info.get("username", "")
                fname    = info.get("first_name", "")
                label    = f"@{uname}" if uname else md_safe(fname or m_id)
                rd       = redeemed.get(m_id)
                acc      = "✅" if has_access(int(m_id), d) else "🔒"
                exp_str  = expiry_display(rd["expires"]) if rd else "No key"
                lines.append(f"{acc} {label} (`{m_id}`)\n   📅 {exp_str}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n_... truncated_"
        await q.edit_message_text(
            txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("admin")
        )

    # ── Database ──────────────────────────────────────────────────
    elif data == "db":
        files = get_db_files()
        if not files:
            await q.edit_message_text(
                "📂 *Database is empty.*\n\n"
                "Upload `.txt` files into the `database/` folder on the server.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_back(),
            )
            return

        lines = ["📂 *Database Files:*\n"]
        for fname in files:
            cnt = count_lines(os.path.join(DB_FOLDER, fname))
            lines.append(f"  • `{fname}` — {cnt:,} lines")
        lines.append("\n_Tap a file button below to download it._")

        await q.edit_message_text(
            "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_db_files(files),
        )

    # ── Database File Selected (download) ─────────────────────────
    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

        if not has_access(uid, d):
            await q.answer(
                "🔒 You need an active key to download files.", show_alert=True
            )
            return

        fpath = os.path.join(DB_FOLDER, fname)
        if not os.path.isfile(fpath):
            await q.answer("❌ File not found on server.", show_alert=True)
            return

        total         = count_lines(fpath)
        lines_to_send = min(LINES_PER_USE, total)

        with open(fpath, "r", errors="ignore") as f:
            content = "".join(next(f) for _ in range(lines_to_send))

        buf       = io.BytesIO(content.encode("utf-8"))
        buf.name  = fname
        remaining = max(0, total - lines_to_send)

        sent_msg = await q.message.reply_document(
            document=buf,
            filename=fname,
            caption=premium_summary(Path(fname).stem, lines_to_send, remaining),
        )
        asyncio.create_task(_auto_delete(300, sent_msg))

    # ── Redeem Info ───────────────────────────────────────────────
    elif data == "redeem_info":
        await q.edit_message_text(
            "🔑 *Redeem a Key*\n\n"
            "Send this command:\n`/redeem ZEIJIE-XXXXXX-XXXXXXXX-XXXXXX`\n\n"
            "_Your access timer starts the moment you redeem._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back(),
        )

    # ── Status ────────────────────────────────────────────────────
    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "👑 *Admin Account*\nFull access granted."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = "🔒 *No Active Key*\n\nUse `/redeem <key>` to get access."
            else:
                exp     = rd.get("expires")
                expired = False
                if exp:
                    try:
                        expired = datetime.fromisoformat(exp) < datetime.now()
                    except ValueError:
                        pass
                activated = rd.get("activated", "Unknown")
                if expired:
                    txt = (
                        "⛔ *Access Expired*\n\n"
                        f"🔑 Key     : `{rd['key']}`\n"
                        f"📅 Expired : {expiry_display(exp)}\n\n"
                        "_Contact admin for a new key._"
                    )
                else:
                    txt = (
                        "✅ *Access Active*\n\n"
                        f"🔑 Key      : `{rd['key']}`\n"
                        f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
                        f"🕐 Started  : {activated[:19]}\n"
                        f"📅 Expires  : {expiry_display(exp)}"
                    )
        await q.edit_message_text(
            txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back()
        )

    # ── Commands ──────────────────────────────────────────────────
    elif data == "commands":
        await q.edit_message_text(
            "📋 *Commands*\n\n"
            "👤 *User:*\n"
            "  /start — Main menu\n"
            "  /redeem `<key>` — Activate a key\n"
            "  /status — Check your access\n"
            "  /getfile `<filename>` — Download file\n\n"
            "🛡 *Admin:*\n"
            "  /createkeys `<users> <duration>` — Create key\n"
            "  /revokekey `<key>` — Delete a key\n"
            "  /addadmin `<id>` — Add admin (owner only)\n"
            "  /removeadmin `<id>` — Remove admin (owner only)",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_back(),
        )

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
    app.add_handler(CommandHandler("getfile",     getfile))
    app.add_handler(CommandHandler("revokekey",   revokekey))
    app.add_handler(CallbackQueryHandler(button))

    logger.info("ZEIJIE BOT starting...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
