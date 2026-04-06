#!/usr/bin/env python3

import os, json, random, string, io, asyncio
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

# ═══════════════════════════════════════════════
# CONFIG  — change these before running
# ═══════════════════════════════════════════════
BOT_TOKEN    = "8797773644:AAHuuZurs0oiduQNW6ywxvTXQ1Kdf32XE9w"
OWNER_ID     = 8420104044          # your Telegram numeric ID
DATA_FILE    = "data.json"
DB_FOLDER    = "database"
LINES_PER_USE = 250               # lines sent per database request

os.makedirs(DB_FOLDER, exist_ok=True)

# ═══════════════════════════════════════════════
# LOGO
# ═══════════════════════════════════════════════
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

# ═══════════════════════════════════════════════
# DATA HELPERS
# ═══════════════════════════════════════════════
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
    if is_admin(uid, d):
        return True
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    exp = rd.get("expires")
    if not exp:
        return True
    return datetime.fromisoformat(exp) > datetime.now()

def track(uid, username, first_name, d):
    d.setdefault("members", {})[str(uid)] = {
        "username": username or "",
        "first_name": first_name or "",
        "joined": datetime.now().isoformat()
    }

def get_db_files() -> list:
    """Return only .txt files from the database folder, sorted."""
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

# ═══════════════════════════════════════════════
# KEY HELPERS
# ═══════════════════════════════════════════════
def generate_key() -> str:
    """ZEIJIE-PREMIUM-12345678-ABCD"""
    nums = "".join(random.choices(string.digits, k=8))
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"ZEIJIE-PREMIUM-{nums}-{suffix}"

def parse_duration(duration: str):
    """
    Parse duration string → (timedelta | None, human_label).
    Supports: lifetime, 1h, 30m, 7d, 10days, 2hours, 45mins etc.
    Returns (None, '♾️ Lifetime') for lifetime.
    """
    dur = duration.strip().lower()
    if dur in ("lifetime", "∞", "forever"):
        return None, "♾️ Lifetime"

    num_str = "".join(c for c in dur if c.isdigit())
    if not num_str:
        raise ValueError(f"Cannot parse duration: {duration!r}")
    num = int(num_str)

    if "h" in dur or "hour" in dur:
        return timedelta(hours=num), f"{num} hour{'s' if num != 1 else ''}"
    elif "m" in dur or "min" in dur:
        return timedelta(minutes=num), f"{num} minute{'s' if num != 1 else ''}"
    elif "d" in dur or "day" in dur:
        return timedelta(days=num), f"{num} day{'s' if num != 1 else ''}"
    else:
        # default = days
        return timedelta(days=num), f"{num} day{'s' if num != 1 else ''}"

def expiry_display(exp_iso: str | None) -> str:
    if not exp_iso:
        return "♾️ Lifetime"
    dt = datetime.fromisoformat(exp_iso)
    return dt.strftime("%Y-%m-%d  %H:%M")

# ═══════════════════════════════════════════════
# MESSAGE TEMPLATES
# ═══════════════════════════════════════════════
def key_created_text(key: str, duration_label: str, expires_iso, devices: int) -> str:
    exp_str = expiry_display(expires_iso) if expires_iso else "Never"
    return (
        "🔑 *Key Generated\\!*\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"`{key}`\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ Duration  : {duration_label}\n"
        f"📅 Expires   : {exp_str}\n"
        f"👥 Max users : {devices}"
    )

def premium_text(game: str, sent: int, remaining: int) -> str:
    return (
        "🔮 ✨ *PREMIUM FILE GENERATED SUCCESSFULLY\\!* ✨ 🔮\n\n"
        f"┣ 🎮 {game.upper()}\n"
        f"┣ 📜 Lines Sent     : {sent}\n"
        f"┣ 💾 Lines Remaining: {remaining:,}\n"
        f"┣ 🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "🔒 Auto\\-delete in 5 minutes"
    )

# ═══════════════════════════════════════════════
# KEYBOARDS
# ═══════════════════════════════════════════════
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
        [InlineKeyboardButton("🔑 Create Key",    callback_data="adm_create")],
        [InlineKeyboardButton("👥 List Admins",   callback_data="adm_list")],
        [InlineKeyboardButton("🗝 Active Keys",   callback_data="adm_keys")],
        [InlineKeyboardButton("🔙 Back",          callback_data="home")],
    ])

def kb_back_admin() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="admin")]
    ])

def kb_back_home(uid, d) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back", callback_data="home")]
    ])

# ═══════════════════════════════════════════════
# /start
# ═══════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    save(d)

    status = "✅ Active" if has_access(user.id, d) else "🔒 No Access"
    await update.message.reply_text(
        f"{LOGO}\n\n👋 *{user.first_name}*\n🔐 Status: {status}",
        parse_mode=ParseMode.MARKDOWN_V2,
        reply_markup=kb_main(user.id, d)
    )

# ═══════════════════════════════════════════════
# /createkeys  <devices> <duration>
# Example:  /createkeys 1 10d
#           /createkeys 3 2h
#           /createkeys 1 lifetime
# ═══════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    uid = update.effective_user.id

    if not is_admin(uid, d):
        await update.message.reply_text("❌ Admins only.")
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "Usage: `/createkeys <max\\_users> <duration>`\n\n"
            "Duration examples: `1h` `30m` `7d` `10days` `lifetime`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    try:
        devices = int(ctx.args[0])
        if devices < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Max users must be a positive integer.")
        return

    raw_duration = " ".join(ctx.args[1:])
    try:
        td, duration_label = parse_duration(raw_duration)
    except ValueError as e:
        await update.message.reply_text(f"❌ {e}")
        return

    key = generate_key()
    now = datetime.now()

    if td is None:
        expires_iso = None
    else:
        expires_iso = (now + td).isoformat()

    d["keys"][key] = {
        "devices":    devices,
        "duration":   raw_duration,
        "expires":    expires_iso,
        "used_by":    [],
        "created_by": str(uid),
        "created_at": now.isoformat(),
    }
    save(d)

    await update.message.reply_text(
        key_created_text(key, duration_label, expires_iso, devices),
        parse_mode=ParseMode.MARKDOWN_V2
    )

# ═══════════════════════════════════════════════
# /redeem <key>
# ═══════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    uid = str(update.effective_user.id)
    device_id = uid   # device locked to Telegram user ID

    if not ctx.args:
        await update.message.reply_text(
            "Usage: `/redeem ZEIJIE\\-PREMIUM\\-XXXXXXXX\\-XXXX`",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text("❌ Invalid key\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    k = d["keys"][key]

    # Check if this device already redeemed this key
    if device_id in k["used_by"]:
        await update.message.reply_text(
            "⚠️ This key is already activated on your device\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # Check device limit
    if len(k["used_by"]) >= int(k["devices"]):
        await update.message.reply_text(
            "❌ Device limit reached for this key\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # Check if key itself is expired (based on creation expiry, not per-user)
    key_exp = k.get("expires")
    if key_exp and datetime.fromisoformat(key_exp) < datetime.now():
        await update.message.reply_text(
            "❌ This key has expired\\.", parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    # Activate
    k["used_by"].append(device_id)
    d["redeemed"][uid] = {
        "key":       key,
        "expires":   key_exp,
        "device_id": device_id,
        "activated": datetime.now().isoformat(),
    }
    save(d)

    exp_label = expiry_display(key_exp)
    _, duration_label = parse_duration(k.get("duration", "lifetime"))

    await update.message.reply_text(
        "✅ *Key Activated\\!*\n\n"
        f"🔑 `{key}`\n"
        f"⏱ Duration : {duration_label}\n"
        f"📅 Expires  : {exp_label}\n"
        f"📱 Device   : Locked to your account",
        parse_mode=ParseMode.MARKDOWN_V2
    )

# ═══════════════════════════════════════════════
# /addadmin  (owner only)
# ═══════════════════════════════════════════════
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
    await update.message.reply_text(f"✅ Admin added: `{target}`", parse_mode=ParseMode.MARKDOWN_V2)

# ═══════════════════════════════════════════════
# /removeadmin  (owner only)
# ═══════════════════════════════════════════════
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
    await update.message.reply_text(f"✅ Admin removed: `{target}`", parse_mode=ParseMode.MARKDOWN_V2)

# ═══════════════════════════════════════════════
# /status
# ═══════════════════════════════════════════════
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    uid = str(update.effective_user.id)
    rd = d["redeemed"].get(uid)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "👑 *Admin Account*\nFull access granted\\.",
            parse_mode=ParseMode.MARKDOWN_V2
        )
        return

    if not rd:
        await update.message.reply_text("🔒 No active key\\. Use `/redeem <key>`", parse_mode=ParseMode.MARKDOWN_V2)
        return

    exp = rd.get("expires")
    if exp and datetime.fromisoformat(exp) < datetime.now():
        await update.message.reply_text("⛔ Your key has expired\\.", parse_mode=ParseMode.MARKDOWN_V2)
        return

    await update.message.reply_text(
        f"✅ *Active*\n\n🔑 `{rd['key']}`\n📅 Expires: {expiry_display(exp)}",
        parse_mode=ParseMode.MARKDOWN_V2
    )

# ═══════════════════════════════════════════════
# CALLBACK HANDLER
# ═══════════════════════════════════════════════
async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    d = load()
    uid = q.from_user.id
    data = q.data

    # ── Home ──────────────────────────────────
    if data == "home":
        status = "✅ Active" if has_access(uid, d) else "🔒 No Access"
        await q.edit_message_text(
            f"{LOGO}\n\n👋 *{q.from_user.first_name}*\n🔐 Status: {status}",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_main(uid, d)
        )

    # ── Commands ──────────────────────────────
    elif data == "commands":
        await q.edit_message_text(
            "📋 *COMMANDS*\n\n"
            "/start — Main menu\n"
            "/redeem `<key>` — Activate a key\n"
            "/status — Check your access\n"
            "/createkeys `<users> <duration>` — \\(admin\\)\n"
            "/addadmin `<id>` — \\(owner\\)\n"
            "/removeadmin `<id>` — \\(owner\\)",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="home")
            ]])
        )

    # ── Redeem info ───────────────────────────
    elif data == "redeem_info":
        await q.edit_message_text(
            "🔑 *Redeem a Key*\n\n"
            "Send the command:\n"
            "`/redeem ZEIJIE\\-PREMIUM\\-XXXXXXXX\\-XXXX`",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Back", callback_data="home")
            ]])
        )

    # ── Status ────────────────────────────────
    elif data == "status":
        rd = d["redeemed"].get(str(uid))

        if is_admin(uid, d):
            await q.edit_message_text(
                "👑 *Admin Account*\nFull access granted\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb_back_home(uid, d)
            )
            return

        if not rd:
            await q.edit_message_text(
                "🔒 No active key\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb_back_home(uid, d)
            )
            return

        exp = rd.get("expires")
        if exp and datetime.fromisoformat(exp) < datetime.now():
            await q.edit_message_text(
                "⛔ Your key has *expired*\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb_back_home(uid, d)
            )
            return

        await q.edit_message_text(
            f"✅ *Active*\n\n🔑 `{rd['key']}`\n📅 Expires: {expiry_display(exp)}",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back_home(uid, d)
        )

    # ── Admin Panel ───────────────────────────
    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("⛔ Admins only.", show_alert=True)
            return
        total_keys = len(d.get("keys", {}))
        total_members = len(d.get("members", {}))
        await q.edit_message_text(
            f"⚡ *ADMIN PANEL*\n\n"
            f"🗝 Total keys: {total_keys}\n"
            f"👥 Total users: {total_members}",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_admin()
        )

    # ── Create Key (info) ─────────────────────
    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("⛔ Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            "🔑 *Create a Key*\n\n"
            "Use the command:\n"
            "`/createkeys <max\\_users> <duration>`\n\n"
            "*Duration examples:*\n"
            "• `10d` — 10 days\n"
            "• `2h` — 2 hours\n"
            "• `30m` — 30 minutes\n"
            "• `lifetime` — never expires",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back_admin()
        )

    # ── List Admins ───────────────────────────
    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("⛔ Admins only.", show_alert=True)
            return
        admins = d.get("admins", [])
        lines = [f"• `{a}`" for a in admins] or ["No extra admins\\."]
        await q.edit_message_text(
            "👥 *Admin List*\n\n" + "\n".join(lines),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back_admin()
        )

    # ── Active Keys ───────────────────────────
    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("⛔ Admins only.", show_alert=True)
            return
        keys = d.get("keys", {})
        if not keys:
            await q.edit_message_text(
                "🗝 No keys created yet\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=kb_back_admin()
            )
            return

        lines = []
        for k, v in list(keys.items())[-10:]:   # show last 10
            used = len(v.get("used_by", []))
            max_d = v.get("devices", "?")
            exp = expiry_display(v.get("expires"))
            lines.append(f"`{k}`\n  👥 {used}/{max_d}  📅 {exp}")

        await q.edit_message_text(
            "🗝 *Active Keys* \\(last 10\\)\n\n" + "\n\n".join(lines),
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=kb_back_admin()
        )

    # ── Database list ─────────────────────────
    elif data == "db":
        if not has_access(uid, d):
            await q.edit_message_text(
                "🔒 *Access Required*\n\nRedeem a key first\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔑 Redeem", callback_data="redeem_info"),
                    InlineKeyboardButton("🔙 Back",   callback_data="home"),
                ]])
            )
            return

        files = get_db_files()
        if not files:
            await q.edit_message_text(
                "📂 *Database is empty*\\.",
                parse_mode=ParseMode.MARKDOWN_V2,
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 Back", callback_data="home")
                ]])
            )
            return

        rows = []
        for i, fname in enumerate(files):
            path = os.path.join(DB_FOLDER, fname)
            count = count_lines(path)
            rows.append([
                InlineKeyboardButton(
                    f"🗂 {Path(fname).stem.upper()}  ({count:,} lines)",
                    callback_data=f"send_{i}"
                )
            ])
        rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])

        await q.edit_message_text(
            "📂 *DATABASE*\n\nSelect a file to generate:",
            parse_mode=ParseMode.MARKDOWN_V2,
            reply_markup=InlineKeyboardMarkup(rows)
        )

    # ── Send database file ────────────────────
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

        # Progress messages
        msg = await q.message.reply_text("🔍 Initializing…  20%")
        await asyncio.sleep(0.8)
        await msg.edit_text("⚙️ Processing…  50%")
        await asyncio.sleep(0.8)
        await msg.edit_text("📦 Extracting…  80%")
        await asyncio.sleep(0.8)
        await msg.edit_text("✅ Completed  100%")

        # Read & slice
        with open(path, "r", errors="replace") as f:
            lines = f.readlines()

        total_before = len(lines)
        chunk = lines[:LINES_PER_USE]

        if not chunk:
            await q.message.reply_text("⚠️ This database file is empty\\.", parse_mode=ParseMode.MARKDOWN_V2)
            return

        # ── DECREASE database: remove used lines ──
        remaining_lines = lines[LINES_PER_USE:]
        remaining_count = len(remaining_lines)

        with open(path, "w", errors="replace") as f:
            f.writelines(remaining_lines)

        # Send file
        bio = io.BytesIO("".join(chunk).encode("utf-8", errors="replace"))
        bio.name = f"ZEIJIE-PREMIUM-{Path(fname).stem.upper()}.txt"
        await q.message.reply_document(bio)

        # Stats message
        done = await q.message.reply_text(
            premium_text(Path(fname).stem, len(chunk), remaining_count),
            parse_mode=ParseMode.MARKDOWN_V2
        )

        # Auto-delete after 5 minutes
        await asyncio.sleep(300)
        for m in (done, msg):
            try:
                await m.delete()
            except Exception:
                pass

# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("createkeys",   createkeys))
    app.add_handler(CommandHandler("redeem",       redeem))
    app.add_handler(CommandHandler("status",       status_cmd))
    app.add_handler(CommandHandler("addadmin",     addadmin))
    app.add_handler(CommandHandler("removeadmin",  removeadmin))
    app.add_handler(CallbackQueryHandler(callback))

    print("🔥 ZEIJIE BOT RUNNING")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
