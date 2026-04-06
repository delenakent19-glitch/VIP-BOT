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
#  CONFIG
# ══════════════════════════════════════════════════════
BOT_TOKEN     = "8797773644:AAEqK3MGZOu2mQRAJKJZjnW7XRmThbbDiZA"         # <-- Replace with your token
OWNER_ID      = 8420104044                             # <-- Replace with your Telegram ID
CONTACT_ADMIN = "@Zeijie_s"

DATA_FILE     = "data.json"
DB_FOLDER     = "database"
LINES_PER_USE = 250
OUTPUT_PREFIX = "ZEIJIE-VIP-PREMIUM"

GITHUB_TOKEN  = "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"    # <-- Set your GitHub token here
GITHUB_REPO   = "https://github.com/delenakent19-glitch/VIP-BOT"    # <-- Format: "username/repo-name"  e.g. "zeijie/vip-bot"
GITHUB_BRANCH = "main"

os.makedirs(DB_FOLDER, exist_ok=True)

# ══════════════════════════════════════════════════════
#  LOGO
# ══════════════════════════════════════════════════════
LOGO = (
    "╔══════════════════════════════════╗\n"
    "║  ███████╗███████╗██╗ ██╗██╗██╗  ║\n"
    "║  ╚══███╔╝██╔════╝██║ ██║██║██║  ║\n"
    "║    ███╔╝ █████╗  ██║ ██║██║██║  ║\n"
    "║   ███╔╝  ██╔══╝  ██║ ██║██║██║  ║\n"
    "║  ███████╗███████╗╚██████╔╝██║   ║\n"
    "║  ╚══════╝╚══════╝ ╚═════╝ ╚═╝   ║\n"
    "║    ✦  V I P  P R E M I U M  ✦   ║\n"
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
DEFAULT_DATA = {
    "admins": [],
    "keys": {},
    "members": {},
    "stats": {"total_uses": 0}
}

def load() -> dict:
    """Load data.json safely, creating it with defaults if missing."""
    if not os.path.exists(DATA_FILE):
        save(DEFAULT_DATA)
        return DEFAULT_DATA.copy()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Ensure all default keys exist
        for k, v in DEFAULT_DATA.items():
            if k not in data:
                data[k] = v
        return data
    except (json.JSONDecodeError, IOError) as e:
        logger.error("Failed to load data.json: %s — resetting to defaults.", e)
        save(DEFAULT_DATA)
        return DEFAULT_DATA.copy()

def save(data: dict):
    """Save data.json atomically."""
    try:
        tmp = DATA_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)
    except IOError as e:
        logger.error("Failed to save data.json: %s", e)

# ══════════════════════════════════════════════════════
#  PERMISSION HELPERS
# ══════════════════════════════════════════════════════
def is_owner(uid: int) -> bool:
    return uid == OWNER_ID

def is_admin(uid: int) -> bool:
    data = load()
    return uid == OWNER_ID or uid in data.get("admins", [])

def is_member(uid: int) -> bool:
    """Check if user has an active (non-expired) membership key."""
    data = load()
    members = data.get("members", {})
    entry = members.get(str(uid))
    if not entry:
        return False
    expiry_str = entry.get("expiry")
    if not expiry_str:
        return False
    try:
        expiry = datetime.fromisoformat(expiry_str)
        return datetime.now() < expiry
    except ValueError:
        return False

def is_buyer(uid: int) -> bool:
    return is_member(uid) or is_admin(uid)

DB_SUPPORTED_EXTS = {".txt", ".csv", ".log", ".combo", ".list", ".dat", ".text"}

def get_db_files() -> list[str]:
    """Return all supported database files in the database folder."""
    try:
        return [
            f for f in os.listdir(DB_FOLDER)
            if os.path.isfile(os.path.join(DB_FOLDER, f))
            and Path(f).suffix.lower() in DB_SUPPORTED_EXTS
        ]
    except FileNotFoundError:
        os.makedirs(DB_FOLDER, exist_ok=True)
        return []

# ══════════════════════════════════════════════════════
#  KEY GENERATOR
# ══════════════════════════════════════════════════════
def gen_key(length: int = 16) -> str:
    chars = string.ascii_uppercase + string.digits
    return "ZEIJIE-" + "".join(random.choices(chars, k=length))

# ══════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    welcome = random.choice(WELCOME_LINES)

    if is_admin(uid):
        role_tag = "👑 OWNER" if is_owner(uid) else "🛡 ADMIN"
        keyboard = [
            [InlineKeyboardButton("📂 Database", callback_data="menu_db"),
             InlineKeyboardButton("🔑 Gen Key",  callback_data="menu_genkey")],
            [InlineKeyboardButton("👥 Members",  callback_data="menu_members"),
             InlineKeyboardButton("📊 Stats",    callback_data="menu_stats")],
            [InlineKeyboardButton("⚙️ Admin Panel", callback_data="menu_admin")],
        ]
    elif is_buyer(uid):
        role_tag = "💎 VIP MEMBER"
        keyboard = [
            [InlineKeyboardButton("📂 Get Files", callback_data="menu_db")],
            [InlineKeyboardButton("📊 My Status",  callback_data="menu_mystatus")],
        ]
    else:
        role_tag = "👤 GUEST"
        keyboard = [
            [InlineKeyboardButton("🔑 Redeem Key", callback_data="menu_redeem")],
            [InlineKeyboardButton("💬 Contact Admin", url=f"https://t.me/{CONTACT_ADMIN.lstrip('@')}")],
        ]

    markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"<pre>{LOGO}</pre>\n\n"
        f"{welcome}\n\n"
        f"Role: <b>{role_tag}</b>\n"
        f"ID: <code>{uid}</code>",
        parse_mode="HTML",
        reply_markup=markup,
    )

# ══════════════════════════════════════════════════════
#  ADMIN COMMANDS  (owner/admin only)
# ══════════════════════════════════════════════════════
async def cmd_genkey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Admins only.")
        return

    # Usage: /genkey <days>
    try:
        days = int(ctx.args[0]) if ctx.args else 30
    except (ValueError, IndexError):
        days = 30

    key  = gen_key()
    data = load()
    data["keys"][key] = {
        "days": days,
        "created": datetime.now().isoformat(),
        "used_by": None,
    }
    save(data)
    await update.message.reply_text(
        f"✅ Key generated!\n\n<code>{key}</code>\n\nValid for <b>{days} days</b> after redemption.",
        parse_mode="HTML",
    )

async def cmd_addadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text("❌ Owner only.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return
    try:
        target = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return
    data = load()
    if target not in data["admins"]:
        data["admins"].append(target)
        save(data)
    await update.message.reply_text(f"✅ <code>{target}</code> is now an admin.", parse_mode="HTML")

async def cmd_removeadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text("❌ Owner only.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /removeadmin <user_id>")
        return
    try:
        target = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID.")
        return
    data = load()
    if target in data["admins"]:
        data["admins"].remove(target)
        save(data)
    await update.message.reply_text(f"✅ <code>{target}</code> removed from admins.", parse_mode="HTML")

async def cmd_listkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Admins only.")
        return
    data  = load()
    keys  = data.get("keys", {})
    unused = [k for k, v in keys.items() if not v.get("used_by")]
    used   = [k for k, v in keys.items() if v.get("used_by")]
    text = (
        f"🔑 <b>Keys Overview</b>\n\n"
        f"Unused: <b>{len(unused)}</b>\n"
        f"Used:   <b>{len(used)}</b>\n\n"
    )
    if unused:
        text += "📋 Unused keys:\n" + "\n".join(f"<code>{k}</code>" for k in unused[:10])
        if len(unused) > 10:
            text += f"\n…and {len(unused)-10} more."
    await update.message.reply_text(text, parse_mode="HTML")

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Admins only.")
        return
    data    = load()
    members = data.get("members", {})
    active  = sum(1 for m in members.values()
                  if datetime.now() < datetime.fromisoformat(m.get("expiry","2000-01-01")))
    db_files = get_db_files()
    total_lines = 0
    for fn in db_files:
        try:
            with open(os.path.join(DB_FOLDER, fn), encoding="utf-8", errors="ignore") as f:
                total_lines += sum(1 for _ in f)
        except Exception:
            pass
    await update.message.reply_text(
        f"📊 <b>Bot Stats</b>\n\n"
        f"Active members : <b>{active}</b>\n"
        f"Total members  : <b>{len(members)}</b>\n"
        f"DB files       : <b>{len(db_files)}</b>\n"
        f"Total DB lines : <b>{total_lines:,}</b>\n"
        f"Total uses     : <b>{data['stats'].get('total_uses',0)}</b>",
        parse_mode="HTML",
    )

async def cmd_broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Admins only.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    msg  = " ".join(ctx.args)
    data = load()
    sent = failed = 0
    for mid in list(data.get("members", {}).keys()):
        try:
            await ctx.bot.send_message(int(mid), f"📢 <b>ZEIJIE BOT</b>\n\n{msg}", parse_mode="HTML")
            sent += 1
        except Exception:
            failed += 1
    await update.message.reply_text(f"✅ Sent: {sent} | ❌ Failed: {failed}")

async def cmd_dbinfo(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_admin(uid):
        await update.message.reply_text("❌ Admins only.")
        return
    files = get_db_files()
    if not files:
        await update.message.reply_text("⚠️ No database files found in /database folder.")
        return
    lines_info = []
    for fn in files:
        try:
            with open(os.path.join(DB_FOLDER, fn), encoding="utf-8", errors="ignore") as f:
                count = sum(1 for _ in f)
            lines_info.append(f"📄 {fn} — {count:,} lines")
        except Exception as e:
            lines_info.append(f"📄 {fn} — ⚠️ read error: {e}")
    await update.message.reply_text(
        "🗄 <b>Database Files</b>\n\n" + "\n".join(lines_info),
        parse_mode="HTML",
    )

# ══════════════════════════════════════════════════════
#  BUYER / MEMBER COMMANDS
# ══════════════════════════════════════════════════════
async def cmd_redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not ctx.args:
        await update.message.reply_text(
            "Usage: /redeem <KEY>\n\nGet a key from " + CONTACT_ADMIN
        )
        return
    key  = ctx.args[0].strip().upper()
    data = load()
    keys = data.get("keys", {})

    if key not in keys:
        await update.message.reply_text("❌ Invalid key.")
        return
    if keys[key].get("used_by"):
        await update.message.reply_text("❌ Key already used.")
        return

    days   = keys[key].get("days", 30)
    expiry = datetime.now() + timedelta(days=days)
    keys[key]["used_by"] = uid
    keys[key]["used_at"] = datetime.now().isoformat()

    members = data.setdefault("members", {})
    members[str(uid)] = {
        "expiry": expiry.isoformat(),
        "key": key,
    }
    save(data)
    await update.message.reply_text(
        f"✅ Key redeemed!\n\n"
        f"💎 Access granted for <b>{days} days</b>\n"
        f"📅 Expires: <b>{expiry.strftime('%Y-%m-%d %H:%M')}</b>",
        parse_mode="HTML",
    )

async def cmd_get(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Buyer command: get lines from database."""
    uid = update.effective_user.id
    if not is_buyer(uid):
        await update.message.reply_text(
            "❌ VIP access required.\n\nRedeem a key with /redeem <KEY>\n"
            f"Get a key from {CONTACT_ADMIN}"
        )
        return

    files = get_db_files()
    if not files:
        await update.message.reply_text(
            "⚠️ Database is empty.\n\n"
            "The admin has not uploaded any database files yet.\n"
            "📁 Place .txt files inside the <code>database/</code> folder.",
            parse_mode="HTML",
        )
        return

    chosen_file = random.choice(files)
    filepath    = os.path.join(DB_FOLDER, chosen_file)

    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            all_lines = [l.strip() for l in f if l.strip()]
    except Exception as e:
        await update.message.reply_text(f"❌ Error reading database: {e}")
        return

    if not all_lines:
        await update.message.reply_text("⚠️ Database file is empty.")
        return

    sample = random.sample(all_lines, min(LINES_PER_USE, len(all_lines)))
    out    = "\n".join(sample)

    buf      = io.BytesIO(out.encode())
    filename = f"{OUTPUT_PREFIX}-{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
    buf.name = filename

    data = load()
    data["stats"]["total_uses"] = data["stats"].get("total_uses", 0) + 1
    save(data)

    await update.message.reply_document(
        document=buf,
        filename=filename,
        caption=(
            f"<pre>{LOGO}</pre>\n\n"
            f"✅ <b>{len(sample)} lines</b> from <code>{chosen_file}</code>\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ),
        parse_mode="HTML",
    )

async def cmd_mystatus(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    data = load()
    entry = data.get("members", {}).get(str(uid))
    if is_owner(uid):
        await update.message.reply_text("👑 You are the <b>OWNER</b> — permanent access.", parse_mode="HTML")
        return
    if is_admin(uid):
        await update.message.reply_text("🛡 You are an <b>ADMIN</b> — permanent access.", parse_mode="HTML")
        return
    if not entry:
        await update.message.reply_text(
            f"❌ No active membership.\nRedeem a key with /redeem <KEY>\nGet one from {CONTACT_ADMIN}"
        )
        return
    expiry = datetime.fromisoformat(entry["expiry"])
    left   = expiry - datetime.now()
    if left.total_seconds() < 0:
        await update.message.reply_text("❌ Your membership has expired.")
        return
    days_left = left.days
    await update.message.reply_text(
        f"💎 <b>VIP Member</b>\n\n"
        f"Expires: <b>{expiry.strftime('%Y-%m-%d %H:%M')}</b>\n"
        f"Days left: <b>{days_left}</b>",
        parse_mode="HTML",
    )

# ══════════════════════════════════════════════════════
#  HELP COMMAND  — role-aware
# ══════════════════════════════════════════════════════
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    buyer_cmds = (
        "👤 <b>Your Commands</b>\n\n"
        "/start — Main menu\n"
        "/redeem <code>&lt;KEY&gt;</code> — Activate a VIP key\n"
        "/get — Receive premium database lines\n"
        "/mystatus — Check membership status\n"
        "/help — Show this message\n"
    )

    admin_extra = (
        "\n\n🛡 <b>Admin Commands</b>\n\n"
        "/genkey <code>[days]</code> — Generate a key (default 30d)\n"
        "/listkeys — List all keys\n"
        "/addadmin <code>&lt;id&gt;</code> — Add admin (owner only)\n"
        "/removeadmin <code>&lt;id&gt;</code> — Remove admin (owner only)\n"
        "/stats — Bot statistics\n"
        "/dbinfo — Database file info\n"
        "/broadcast <code>&lt;msg&gt;</code> — Message all members\n"
    )

    if is_admin(uid):
        await update.message.reply_text(buyer_cmds + admin_extra, parse_mode="HTML")
    else:
        await update.message.reply_text(buyer_cmds, parse_mode="HTML")

# ══════════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════════
async def handle_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query
    uid = q.from_user.id
    await q.answer()
    data_cb = q.data

    if data_cb == "menu_db":
        if not is_buyer(uid):
            await q.message.reply_text("❌ VIP access required. Use /redeem <KEY>")
            return
        await cmd_get.__wrapped__(update, ctx) if hasattr(cmd_get, "__wrapped__") else await _do_get(q.message, uid, ctx)

    elif data_cb == "menu_genkey":
        if not is_admin(uid):
            await q.message.reply_text("❌ Admins only.")
            return
        key  = gen_key()
        d    = load()
        d["keys"][key] = {"days": 30, "created": datetime.now().isoformat(), "used_by": None}
        save(d)
        await q.message.reply_text(f"✅ Key (30d):\n<code>{key}</code>", parse_mode="HTML")

    elif data_cb == "menu_members":
        if not is_admin(uid):
            await q.message.reply_text("❌ Admins only.")
            return
        d       = load()
        members = d.get("members", {})
        active  = sum(1 for m in members.values()
                      if datetime.now() < datetime.fromisoformat(m.get("expiry","2000-01-01")))
        await q.message.reply_text(
            f"👥 <b>Members</b>\nTotal: {len(members)} | Active: {active}",
            parse_mode="HTML",
        )

    elif data_cb == "menu_stats":
        if not is_admin(uid):
            await q.message.reply_text("❌ Admins only.")
            return
        # reuse stats command
        class FakeMsg:
            async def reply_text(self, *a, **kw):
                await q.message.reply_text(*a, **kw)
        class FakeUpd:
            effective_user = q.from_user
            message = FakeMsg()
        await cmd_stats(FakeUpd(), ctx)

    elif data_cb == "menu_admin":
        if not is_admin(uid):
            await q.message.reply_text("❌ Admins only.")
            return
        await q.message.reply_text("⚙️ Use /help to see all admin commands.", parse_mode="HTML")

    elif data_cb == "menu_redeem":
        await q.message.reply_text(
            f"Send: /redeem <code>&lt;YOUR_KEY&gt;</code>\n\nGet a key from {CONTACT_ADMIN}",
            parse_mode="HTML",
        )

    elif data_cb == "menu_mystatus":
        class FakeMsg:
            async def reply_text(self, *a, **kw):
                await q.message.reply_text(*a, **kw)
        class FakeUpd:
            effective_user = q.from_user
            message = FakeMsg()
        await cmd_mystatus(FakeUpd(), ctx)

async def _do_get(message, uid: int, ctx):
    """Shared logic for /get and inline button."""
    files = get_db_files()
    if not files:
        await message.reply_text(
            "⚠️ Database is empty. No .txt files found in <code>database/</code>.",
            parse_mode="HTML",
        )
        return
    chosen_file = random.choice(files)
    filepath    = os.path.join(DB_FOLDER, chosen_file)
    try:
        with open(filepath, encoding="utf-8", errors="ignore") as f:
            all_lines = [l.strip() for l in f if l.strip()]
    except Exception as e:
        await message.reply_text(f"❌ Error reading database: {e}")
        return
    if not all_lines:
        await message.reply_text("⚠️ Database file is empty.")
        return
    sample   = random.sample(all_lines, min(LINES_PER_USE, len(all_lines)))
    out      = "\n".join(sample)
    buf      = io.BytesIO(out.encode())
    filename = f"{OUTPUT_PREFIX}-{datetime.now().strftime('%Y%m%d%H%M%S')}.txt"
    buf.name = filename
    d = load()
    d["stats"]["total_uses"] = d["stats"].get("total_uses", 0) + 1
    save(d)
    await message.reply_document(
        document=buf,
        filename=filename,
        caption=(
            f"<pre>{LOGO}</pre>\n\n"
            f"✅ <b>{len(sample)} lines</b> from <code>{chosen_file}</code>\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ),
        parse_mode="HTML",
    )

# ══════════════════════════════════════════════════════
#  STARTUP SYNC
# ══════════════════════════════════════════════════════
async def on_startup(app: Application):
    logger.info("Bot starting — syncing from GitHub…")
    await github_pull_file("data.json", DATA_FILE)
    db_files = get_db_files()
    for fn in db_files:
        await github_pull_file(f"database/{fn}", os.path.join(DB_FOLDER, fn))
    # Make sure data.json exists locally after pull
    load()
    logger.info("Startup sync complete.")

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

    # Admin commands
    app.add_handler(CommandHandler("genkey",      cmd_genkey))
    app.add_handler(CommandHandler("addadmin",    cmd_addadmin))
    app.add_handler(CommandHandler("removeadmin", cmd_removeadmin))
    app.add_handler(CommandHandler("listkeys",    cmd_listkeys))
    app.add_handler(CommandHandler("stats",       cmd_stats))
    app.add_handler(CommandHandler("dbinfo",      cmd_dbinfo))
    app.add_handler(CommandHandler("broadcast",   cmd_broadcast))

    # Buyer / member commands
    app.add_handler(CommandHandler("start",       cmd_start))
    app.add_handler(CommandHandler("help",        cmd_help))
    app.add_handler(CommandHandler("redeem",      cmd_redeem))
    app.add_handler(CommandHandler("get",         cmd_get))
    app.add_handler(CommandHandler("mystatus",    cmd_mystatus))

    # Inline buttons
    app.add_handler(CallbackQueryHandler(handle_callback))

    logger.info("ZEIJIE VIP PREMIUM BOT is running…")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

GITHUB_TOKEN  = "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"
GITHUB_REPO   = "https://github.com/delenakent19-glitch/VIP-BOT"
GITHUB_BRANCH = "main"

os.makedirs(DB_FOLDER, exist_ok=True)

# ══════════════════════════════════════════════════════
#  LOGO
# ══════════════════════════════════════════════════════
LOGO = (
    "╔══════════════════════════════════╗\n"
    "║  ███████╗███████╗██╗ ██╗██╗██╗  ║\n"
    "║  ╚══███╔╝██╔════╝██║ ██║██║██║  ║\n"
    "║    ███╔╝ █████╗  ██║ ██║██║██║  ║\n"
    "║   ███╔╝  ██╔══╝  ██║ ██║██║██║  ║\n"
    "║  ███████╗███████╗╚██████╔╝██║   ║\n"
    "║  ╚══════╝╚══════╝ ╚═════╝ ╚═╝   ║\n"
    "║    ✦  V I P  P R E M I U M  ✦   ║\n"
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
    if is_admin(uid, d):
        return True
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    return not is_expired(rd)

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
#  KEY GENERATION
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
        "🔮 PREMIUM FILE GENERATED!\n\n"
        "📊 GENERATION SUMMARY\n"
        f"┣ 🎮 Source     : {disp.upper()}\n"
        f"┣ 📄 File       : {output_filename(disp)}\n"
        f"┣ 📜 Lines      : {sent:,}\n"
        f"┣ 🕐 Generated  : {now}\n"
        f"┣ 💾 Remaining  : {remaining:,} lines\n"
        "┣ 🧹 Cleanup    : Done\n\n"
        "🛡 SECURITY\n"
        "┣ 🔒 Auto-Expiry : 5 minutes\n"
        "┣ 🗑 Auto-Delete : Enabled\n"
        "┣ ⚡ Session     : Verified\n\n"
        "⬇️ Download immediately — file deletes in 5 min\n\n"
        "⭐ Thank you for using ZEIJIE Premium!"
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
    name   = first_name or "Operator"
    user_line = f"👤 {name}"
    if username:
        user_line += f"  (@{username})"
    return (
        f"{LOGO}\n\n"
        f"{line}\n\n"
        f"{user_line}\n"
        f"🔐 Status  : {status}\n"
        f"📞 Support : {CONTACT_ADMIN}"
    )

ACCESS_DENIED_MSG = (
    "🔒 Access Denied\n\n"
    "You cannot access this database.\n"
    "Contact admin to get a key & to access this.\n\n"
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
        await update.message.reply_text(ACCESS_DENIED_MSG, reply_markup=kb_contact())
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "📋 Usage:\n/createkeys <max_users> <duration>\n\n"
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
        await update.message.reply_text("❌ Max users must be a positive integer.")
        return

    raw_dur = " ".join(ctx.args[1:])
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid duration. Use: 10d / 2h / 30m / lifetime"
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
        "│   🔑  KEY GENERATED!        │\n"
        "└─────────────────────────────┘\n\n"
        f"{key}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ Duration  : {dur_label}\n"
        f"📅 Starts    : On redeem\n"
        f"👥 Max Users : {devices}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Timer starts when buyer redeems ✅"
    )

# ══════════════════════════════════════════════════════
#  /bulkkeys <prefix> <count> <duration>
# ══════════════════════════════════════════════════════
async def bulkkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(ACCESS_DENIED_MSG, reply_markup=kb_contact())
        return

    if len(ctx.args) < 3:
        await update.message.reply_text(
            "📋 Usage:\n/bulkkeys <prefix> <count> <duration>\n\n"
            "Example:\n/bulkkeys Zaraki 5 1d\n\n"
            "Each key is one-time use."
        )
        return

    prefix = ctx.args[0].strip()
    try:
        count = int(ctx.args[1])
        if not 1 <= count <= 50:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Count must be between 1 and 50.")
        return

    raw_dur = " ".join(ctx.args[2:])
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid duration. Use: 10d / 2h / 30m / lifetime"
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

    keys_display = "\n".join(k for k in keys)
    await update.message.reply_text(
        f"🎉 {count} Keys Generated Successfully! 🎉\n\n"
        f"{keys_display}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏳ Validity (each) : {dur_label}\n"
        f"📝 Status          : One-time use\n"
        f"📅 Created On      : {now_str}\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "✨ Share these keys with your users to grant them access!"
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
            "🔑 Usage:\n/redeem ZEIJIE-PREMIUM-XXXX\n\n"
            f"📞 No key? Contact: {CONTACT_ADMIN}"
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text(
            f"❌ Invalid key. Check and try again.\n\n📞 Contact: {CONTACT_ADMIN}"
        )
        return

    k = d["keys"][key]

    if uid in k.get("used_by", []):
        await update.message.reply_text("⚠️ This key is already activated on your account.")
        return

    if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
        await update.message.reply_text(
            f"❌ Device limit reached for this key.\n\n📞 Contact: {CONTACT_ADMIN}"
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
        "│   ✅  KEY ACTIVATED!        │\n"
        "└─────────────────────────────┘\n\n"
        f"🔑 {key}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ Duration  : {dur_label}\n"
        f"📅 Expires   : {expiry_display(expires_iso)}\n"
        "📱 Device    : Locked to your account\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "Your access timer has started now. ✅"
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
            "👑 Admin Account\nFull access granted — no key needed."
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            "🔒 No Active Key\n\nUse /redeem <key> to activate access.\n\n"
            f"📞 Contact: {CONTACT_ADMIN}"
        )
        return

    exp     = rd.get("expires")
    expired = is_expired(rd)
    act     = rd.get("activated", "Unknown")

    if expired:
        await update.message.reply_text(
            "⛔ Access Expired\n\n"
            f"🔑 Key     : {rd['key']}\n"
            f"📅 Expired : {expiry_display(exp)}\n\n"
            f"Contact admin: {CONTACT_ADMIN}"
        )
    else:
        await update.message.reply_text(
            "✅ Access Active\n\n"
            f"🔑 Key      : {rd['key']}\n"
            f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
            f"🕐 Started  : {act[:19]}\n"
            f"📅 Expires  : {expiry_display(exp)}"
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
    await update.message.reply_text(f"✅ Admin added: {target}")

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
        await update.message.reply_text(f"✅ Removed: {target}")
    else:
        await update.message.reply_text(f"⚠️ Not an admin: {target}")

# ══════════════════════════════════════════════════════
#  /revokekey <key> — admin only
# ══════════════════════════════════════════════════════
async def revokekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)
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
    save_push(d)
    await update.message.reply_text(f"✅ Key revoked: {key}")

# ══════════════════════════════════════════════════════
#  /customname <filename> <display name> — admin only
# ══════════════════════════════════════════════════════
async def customname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only.")
        return

    files = get_db_files()
    if len(ctx.args) < 2:
        listing = "\n".join(f"  • {f}" for f in files) if files else "  None"
        await update.message.reply_text(
            "📋 Usage:\n/customname <filename.txt> <display name>\n\n"
            "Your DB files:\n" + listing + "\n\n"
            "Example:\n/customname garena.txt GARENA"
        )
        return

    fname     = ctx.args[0].strip()
    disp_name = " ".join(ctx.args[1:]).strip()
    fpath     = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        listing = "\n".join(f"  • {f}" for f in files) if files else "  None"
        await update.message.reply_text(
            f"❌ {fname} not found in database folder.\n\n"
            f"Available:\n{listing}"
        )
        return

    d.setdefault("db_names", {})[fname] = disp_name
    save_push(d)
    await update.message.reply_text(
        f"✅ Custom name set!\n\n"
        f"📁 File : {fname}\n"
        f"🏷 Name : {disp_name}"
    )

# ══════════════════════════════════════════════════════
#  /syncgithub — admin only
# ══════════════════════════════════════════════════════
async def syncgithub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only.")
        return

    if not GITHUB_TOKEN or not GITHUB_REPO:
        await update.message.reply_text(
            "⚠️ GitHub is not configured.\n"
            "Set GITHUB_TOKEN and GITHUB_REPO in the bot config."
        )
        return

    msg = await update.message.reply_text("⏳ Syncing from GitHub…")
    await github_pull_file("data.json", DATA_FILE)
    for fname in get_db_files():
        await github_pull_file(f"database/{fname}", os.path.join(DB_FOLDER, fname))
    await msg.edit_text("✅ Sync complete! Data pulled from GitHub.")

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
            await q.answer("❌ Admins only.", show_alert=True); return
        await q.edit_message_text(
            "⚡ Admin Panel\n\nChoose an option below:",
            reply_markup=kb_admin(),
        )

    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        await q.edit_message_text(
            "🔑 Create Keys\n\n"
            "Single key:\n/createkeys <max_users> <duration>\n\n"
            "Bulk keys:\n/bulkkeys <prefix> <count> <duration>\n\n"
            "Key format: ZEIJIE-PREMIUM-XXXX\n\n"
            "Examples:\n"
            "  /createkeys 1 7d\n"
            "  /bulkkeys Zaraki 5 1d\n\n"
            "Timer starts when buyer redeems.",
            reply_markup=kb_back("admin"),
        )

    elif data == "adm_bulk_info":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        await q.edit_message_text(
            "🎉 Bulk Key Generator\n\n"
            "Command:\n/bulkkeys <prefix> <count> <duration>\n\n"
            "Example:\n/bulkkeys Zaraki 5 1d\n\n"
            "Output:\n"
            "Zaraki-273852\nZaraki-617209\nZaraki-679658\n\n"
            "Each key is one-time use only.",
            reply_markup=kb_back("admin"),
        )

    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        keys     = d.get("keys", {})
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})
        if not keys:
            txt = "🗝 No keys yet.\n\nUse /createkeys or /bulkkeys."
        else:
            lines = [f"🗝 All Keys ({len(keys)}):\n"]
            for k, v in keys.items():
                used_by  = v.get("used_by", [])
                devices  = v.get("devices", 1)
                raw_dur  = v.get("duration", "?")
                used_cnt = len(used_by)
                icon = "🟡 Unused" if used_cnt == 0 else ("🟢 Partial" if used_cnt < devices else "🔵 Full")
                block = (
                    f"{icon}\n🔑 {k}\n"
                    f"   ⏱ {raw_dur}  👥 {used_cnt}/{devices}"
                )
                for u_id in used_by:
                    rd    = redeemed.get(str(u_id))
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    exp_s = expiry_display(rd["expires"]) if rd else "Unknown"
                    block += f"\n   └ {label}: {exp_s}"
                lines.append(block)
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n... truncated"
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        admins = d.get("admins", [])
        txt = (
            "👥 No extra admins."
            if not admins
            else "👥 Admins:\n\n" + "\n".join(f"  • {a}" for a in admins)
        )
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_members":
        if not is_admin(uid, d):
            await q.answer("❌ Admins only.", show_alert=True); return
        members  = d.get("members", {})
        redeemed = d.get("redeemed", {})
        if not members:
            txt = "👥 No members yet."
        else:
            lines = [f"👥 Members ({len(members)}):\n"]
            for m_id, info in members.items():
                uname  = info.get("username", "")
                fname  = info.get("first_name", "")
                label  = f"@{uname}" if uname else (fname or m_id)
                rd     = redeemed.get(m_id)
                acc    = "✅" if has_access(int(m_id), d) else "🔒"
                exp_s  = expiry_display(rd["expires"]) if rd else "No key"
                lines.append(f"{acc} {label} ({m_id})\n   📅 {exp_s}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n... truncated"
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "db":
        files = get_db_files()
        if not files:
            await q.edit_message_text(
                "📂 Database is empty.\n\nUpload .txt files into the database/ folder.",
                reply_markup=kb_back(),
            )
            return
        lines_txt = ["📂 Database Files:\n"]
        for fname in files:
            cnt  = count_lines(os.path.join(DB_FOLDER, fname))
            disp = get_display_name(fname, d)
            lines_txt.append(f"  • {disp} — {cnt:,} lines")
        lines_txt.append("\nTap a file to generate and download.")
        await q.edit_message_text(
            "\n".join(lines_txt),
            reply_markup=kb_db_files(files, d),
        )

    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

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
        )
        asyncio.create_task(_auto_delete(300, sent_msg))
        asyncio.create_task(github_push_file(f"database/{fname}", fpath))

    elif data == "redeem_info":
        await q.edit_message_text(
            "🔑 Redeem a Key\n\n"
            "Send this command:\n/redeem ZEIJIE-PREMIUM-XXXX\n\n"
            f"No key? Contact: {CONTACT_ADMIN}\n\n"
            "Access timer starts the moment you redeem.",
            reply_markup=kb_back(),
        )

    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "👑 Admin Account\nFull access granted — no key needed."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = (
                    "🔒 No Active Key\n\n"
                    "Use /redeem <key> to get access.\n\n"
                    f"📞 Contact: {CONTACT_ADMIN}"
                )
            else:
                exp     = rd.get("expires")
                expired = is_expired(rd)
                act     = rd.get("activated", "Unknown")
                if expired:
                    txt = (
                        "⛔ Access Expired\n\n"
                        f"🔑 Key     : {rd['key']}\n"
                        f"📅 Expired : {expiry_display(exp)}\n\n"
                        f"Contact admin: {CONTACT_ADMIN}"
                    )
                else:
                    txt = (
                        "✅ Access Active\n\n"
                        f"🔑 Key      : {rd['key']}\n"
                        f"⏱ Duration : {rd.get('duration', 'N/A')}\n"
                        f"🕐 Started  : {act[:19]}\n"
                        f"📅 Expires  : {expiry_display(exp)}"
                    )
        await q.edit_message_text(txt, reply_markup=kb_back())

    elif data == "commands":
        await q.edit_message_text(
            "📋 Commands\n\n"
            "👤 User:\n"
            "  /start — Main menu\n"
            "  /redeem <key> — Activate a key\n"
            "  /status — Check your access\n\n"
            "🛡 Admin:\n"
            "  /createkeys <users> <dur> — Create key\n"
            "  /bulkkeys <prefix> <n> <dur> — Bulk keys\n"
            "  /revokekey <key> — Delete a key\n"
            "  /customname <file> <name> — Set DB name\n"
            "  /syncgithub — Pull from GitHub\n"
            "  /addadmin <id> — Add admin (owner)\n"
            "  /removeadmin <id> — Remove admin (owner)",
            reply_markup=kb_back(),
        )

# ══════════════════════════════════════════════════════
#  CATCH-ALL
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
