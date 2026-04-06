#!/usr/bin/env python3
"""
╔═══════════════════════════════════════╗
║      ░ Z E I J I E   B O T ░         ║
║   File Distribution & Key System     ║
╚═══════════════════════════════════════╝
"""

import os, json, random, string, io
from datetime import datetime, timedelta
from pathlib import Path
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)
from telegram.constants import ParseMode

# ══════════════════════════════════════════════════════════
#  CONFIG  ─  edit these
# ══════════════════════════════════════════════════════════
BOT_TOKEN     = os.getenv("BOT_TOKEN", "8797773644:AAHuuZurs0oiduQNW6ywxvTXQ1Kdf32XE9w")
OWNER_ID      = int(os.getenv("OWNER_ID", "8420104044"))   # your telegram user id
DATA_FILE     = "data.json"
DB_FOLDER     = "database"
LINES_PER_USE = 1000

os.makedirs(DB_FOLDER, exist_ok=True)

# ══════════════════════════════════════════════════════════
#  DATA LAYER
# ══════════════════════════════════════════════════════════
def load():
    if not os.path.exists(DATA_FILE):
        return {"admins": [], "keys": {}, "members": {}, "redeemed": {}}
    with open(DATA_FILE) as f:
        return json.load(f)

def save(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

def is_admin(uid, d):
    return str(uid) in [str(a) for a in d.get("admins", [])] or int(uid) == OWNER_ID

def has_access(uid, d):
    if is_admin(uid, d):
        return True
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    exp = rd.get("expires")
    if exp and datetime.fromisoformat(exp) < datetime.now():
        return False
    return True

def track(uid, username, first_name, d):
    d.setdefault("members", {})[str(uid)] = {
        "username":   username or "",
        "first_name": first_name or "",
        "joined": d["members"].get(str(uid), {}).get("joined", datetime.now().isoformat())
    }

def get_db_files():
    return sorted([
        f for f in os.listdir(DB_FOLDER)
        if os.path.isfile(os.path.join(DB_FOLDER, f))
    ])

# ══════════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════════
def kb_main(uid, d):
    rows = []
    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡  Admin Panel", callback_data="adm_panel")])
    rows += [
        [
            InlineKeyboardButton("📂  Database",    callback_data="db_list"),
            InlineKeyboardButton("🔑  Redeem Key",  callback_data="info_redeem"),
        ],
        [
            InlineKeyboardButton("📋  Commands",    callback_data="info_commands"),
            InlineKeyboardButton("💬  Feedback",    callback_data="info_feedback"),
        ],
        [
            InlineKeyboardButton("👤  My Status",   callback_data="info_status"),
            InlineKeyboardButton("ℹ️   About",       callback_data="info_about"),
        ],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔧  Create Key",    callback_data="adm_mk"),
            InlineKeyboardButton("📋  List Keys",     callback_data="adm_lk"),
        ],
        [
            InlineKeyboardButton("👥  Members",       callback_data="adm_members"),
            InlineKeyboardButton("🆔  Chat ID List",  callback_data="adm_chatids"),
        ],
        [
            InlineKeyboardButton("📨  DM User",       callback_data="adm_dm_info"),
            InlineKeyboardButton("➕  Add Admin",     callback_data="adm_add_info"),
        ],
        [InlineKeyboardButton("🔙  Back to Menu",     callback_data="go_home")],
    ])

def kb_back(target="go_home"):
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙  Back to Menu", callback_data=target)]])

def kb_db(files):
    ICONS = {".txt": "📄", ".csv": "📊", ".json": "🗂", ".log": "📝"}
    rows = []
    for i, f in enumerate(files):
        ext = Path(f).suffix.lower()
        icon = ICONS.get(ext, "📦")
        rows.append([InlineKeyboardButton(f"{icon}  {f}", callback_data=f"send_{i}")])
    rows.append([InlineKeyboardButton("🔙  Back", callback_data="go_home")])
    return InlineKeyboardMarkup(rows)

# ══════════════════════════════════════════════════════════
#  LOGO / TEXTS
# ══════════════════════════════════════════════════════════
LOGO = (
    "```\n"
    "╔══════════════════════════════════╗\n"
    "║  ░██████╗ ██╗  ██╗ █████╗      ║\n"
    "║  ██╔════╝ ██║  ██║██╔══██╗     ║\n"
    "║  ╚█████╗  ███████║███████║     ║\n"
    "║   ╚═══██╗ ██╔══██║██╔══██║     ║\n"
    "║  ██████╔╝ ██║  ██║██║  ██║     ║\n"
    "║  ╚═════╝  ╚═╝  ╚═╝╚═╝  ╚═╝     ║\n"
    "║  ░░░  D O W   B O T  ░░░       ║\n"
    "╚══════════════════════════════════╝\n"
    "```"
)

COMMANDS_TEXT = (
    "```\n"
    "╔══════════════════════════════════╗\n"
    "║        C O M M A N D S          ║\n"
    "╠══════════════════════════════════╣\n"
    "║  USER                           ║\n"
    "║  /start          Main Menu      ║\n"
    "║  /redeem  <key>  Activate key   ║\n"
    "║  /status         Your access    ║\n"
    "║  /feedback <msg> Send feedback  ║\n"
    "║  /commands       This list      ║\n"
    "╠══════════════════════════════════╣\n"
    "║  ADMIN  ⚡                       ║\n"
    "║  /createkeys <dev> <dur>        ║\n"
    "║  /listkeys       All keys       ║\n"
    "║  /addadmin <id>  Add admin      ║\n"
    "║  /chatidlist     All chat IDs   ║\n"
    "║  /listmember     All members    ║\n"
    "║  /dm <id> <msg>  DM a user      ║\n"
    "╚══════════════════════════════════╝\n"
    "```"
)

# ══════════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)
    save(d)

    name   = update.effective_user.first_name or "User"
    badge  = "  ⚡ *ADMIN*" if is_admin(uid, d) else ""
    status = "✅  Active" if has_access(uid, d) else "🔒  No Access"

    text = (
        f"{LOGO}\n"
        f"👋  Welcome, *{name}*!{badge}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🔐  Status: {status}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_Pick an option from the menu below._"
    )
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_main(uid, d))

# ══════════════════════════════════════════════════════════
#  CALLBACK ROUTER
# ══════════════════════════════════════════════════════════
async def on_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q   = update.callback_query
    cid = q.data
    await q.answer()
    d   = load()
    uid = q.from_user.id

    # ── go home ──────────────────────────────────────────
    if cid == "go_home":
        name   = q.from_user.first_name or "User"
        status = "✅  Active" if has_access(uid, d) else "🔒  No Access"
        await q.edit_message_text(
            f"{LOGO}\n"
            f"👋  Welcome, *{name}*!\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔐  Status: {status}\n"
            f"_Pick an option from the menu below._",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=kb_main(uid, d)
        )
        return

    # ── database list ────────────────────────────────────
    if cid == "db_list":
        if not has_access(uid, d):
            await q.edit_message_text(
                "🔒 *Access Denied*\n\nYou need an active key.\nUse `/redeem ZEIJIE-XXXX` to unlock.",
                parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back()
            )
            return
        files = get_db_files()
        if not files:
            await q.edit_message_text("📂 *Database is empty.*\n\nNo files found yet.", parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back())
            return
        txt = (
            "```\n"
            "╔══════════════════════════╗\n"
            "║  📂   D A T A B A S E   ║\n"
            f"║  {len(files)} file(s) available      ║\n"
            "╚══════════════════════════╝\n"
            "```\n"
            f"_Each request sends up to *{LINES_PER_USE:,}* lines._\n"
            "_Choose a file:_"
        )
        await q.edit_message_text(txt, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_db(files))
        return

    # ── send file ────────────────────────────────────────
    if cid.startswith("send_"):
        if not has_access(uid, d):
            await q.answer("🔒 Access denied.", show_alert=True)
            return
        idx   = int(cid.split("_", 1)[1])
        files = get_db_files()
        if idx >= len(files):
            await q.answer("❌ File not found.", show_alert=True)
            return
        fname_file = files[idx]
        fpath = os.path.join(DB_FOLDER, fname_file)
        try:
            with open(fpath, "r", errors="replace") as f:
                all_lines = f.readlines()
            chunk   = all_lines[:LINES_PER_USE]
            content = "".join(chunk)
            bio     = io.BytesIO(content.encode())
            bio.name = fname_file
            caption = (
                f"📄 *{fname_file}*\n"
                f"━━━━━━━━━━━━━━━━━━━\n"
                f"📊 Lines sent:  `{len(chunk):,}` / `{len(all_lines):,}`\n"
                f"👤 Requested by: `{uid}`"
            )
            await q.message.reply_document(document=bio, caption=caption, parse_mode=ParseMode.MARKDOWN)
            await q.edit_message_text(
                f"✅ *File Sent!*\n\n📄 `{fname_file}`\n📊 `{len(chunk):,}` lines delivered.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=kb_back("db_list")
            )
        except Exception as e:
            await q.edit_message_text(f"❌ Error: `{e}`", parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("db_list"))
        return

    # ── info pages ───────────────────────────────────────
    if cid == "info_commands":
        await q.edit_message_text(COMMANDS_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back())
        return

    if cid == "info_redeem":
        await q.edit_message_text(
            "🔑 *Redeem a Key*\n\n"
            "Key format:  `ZEIJIE-AZ99`\n\n"
            "Command:\n`/redeem ZEIJIE-XXXX`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back()
        )
        return

    if cid == "info_feedback":
        await q.edit_message_text(
            "💬 *Send Feedback*\n\n"
            "Use:  `/feedback <your message>`\n\n"
            "_Your message will be forwarded to all admins._",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back()
        )
        return

    if cid == "info_status":
        rd = d.get("redeemed", {}).get(str(uid))
        if rd:
            exp = rd.get("expires", "Never")[:10]
            body = f"✅  Active\n🔑  Key: `{rd['key']}`\n📅  Expires: `{exp}`\n📱  Devices: `{rd.get('devices','?')}`"
        elif is_admin(uid, d):
            body = "⚡  Admin — Unlimited Access"
        else:
            body = "🔒  No active subscription\n\n`/redeem <key>` to activate."
        await q.edit_message_text(
            "```\n╔══════════════════════╗\n║   M Y  S T A T U S  ║\n╚══════════════════════╝\n```\n" + body,
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back()
        )
        return

    if cid == "info_about":
        await q.edit_message_text(
            "```\n"
            "╔═══════════════════════════╗\n"
            "║   S H A D O W   B O T    ║\n"
            "╠═══════════════════════════╣\n"
            "║  File Distribution v1.0  ║\n"
            "║  Key & Admin System      ║\n"
            f"║  {LINES_PER_USE:,} lines / request  ║\n"
            "╚═══════════════════════════╝\n"
            "```",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back()
        )
        return

    # ── admin panel ──────────────────────────────────────
    if cid == "adm_panel":
        if not is_admin(uid, d):
            await q.answer("⛔ Not an admin.", show_alert=True)
            return
        await q.edit_message_text(
            "```\n"
            "╔══════════════════════════════╗\n"
            "║   ⚡   A D M I N   ⚡        ║\n"
            "╠══════════════════════════════╣\n"
            f"║  Members : {len(d.get('members',{})):<19}║\n"
            f"║  Keys    : {len(d.get('keys',{})):<19}║\n"
            f"║  Admins  : {len(d.get('admins',[])):<19}║\n"
            "╚══════════════════════════════╝\n"
            "```",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb_admin()
        )
        return

    if cid == "adm_members":
        if not is_admin(uid, d): return
        members = d.get("members", {})
        if not members:
            body = "👥 *No members yet.*"
        else:
            lines = [f"👤 *{v.get('first_name','?')}* (@{v.get('username','?')}) — `{k}`" for k, v in members.items()]
            body  = f"👥 *Members ({len(members)})*\n━━━━━━━━━━━━━━━\n" + "\n".join(lines)
        await q.edit_message_text(body, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("adm_panel"))
        return

    if cid == "adm_chatids":
        if not is_admin(uid, d): return
        members = d.get("members", {})
        if not members:
            body = "🆔 *No chat IDs yet.*"
        else:
            lines = [f"`{k}` — {v.get('first_name','?')} (@{v.get('username','?')})" for k, v in members.items()]
            body  = "🆔 *Chat ID List*\n━━━━━━━━━━━━━━━\n" + "\n".join(lines)
        await q.edit_message_text(body, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("adm_panel"))
        return

    if cid == "adm_lk":
        if not is_admin(uid, d): return
        keys = d.get("keys", {})
        if not keys:
            body = "🔑 *No keys yet.*"
        else:
            lines = []
            for k, v in keys.items():
                flag = "✅" if v.get("used") else "🟢"
                lines.append(f"{flag} `{k}` | {v.get('devices','?')} dev | {v.get('duration','?')}")
            body = "🔑 *All Keys*\n━━━━━━━━━━━━━━━\n" + "\n".join(lines)
        await q.edit_message_text(body, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("adm_panel"))
        return

    if cid == "adm_mk":
        await q.edit_message_text(
            "🔧 *Create a Key*\n\nCommand:\n`/createkeys <devices> <duration>`\n\nExample:\n`/createkeys 2 30d`\n`/createkeys 1 7d`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("adm_panel")
        )
        return

    if cid == "adm_dm_info":
        await q.edit_message_text(
            "📨 *DM a User*\n\nCommand:\n`/dm <chat_id> <message>`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("adm_panel")
        )
        return

    if cid == "adm_add_info":
        await q.edit_message_text(
            "➕ *Add Admin*\n\nCommand:\n`/addadmin <user_id>`",
            parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back("adm_panel")
        )
        return

# ══════════════════════════════════════════════════════════
#  COMMANDS
# ══════════════════════════════════════════════════════════
async def cmd_redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(update.effective_user.id, update.effective_user.username, update.effective_user.first_name, d)

    if not ctx.args:
        await update.message.reply_text("Usage: `/redeem ZEIJIE-XXXX`", parse_mode=ParseMode.MARKDOWN)
        return

    key  = ctx.args[0].strip()
    keys = d.get("keys", {})

    if key not in keys:
        await update.message.reply_text(
            "```\n╔══════════════════╗\n║   ❌  INVALID    ║\n╚══════════════════╝\n```\nKey not found.",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    if keys[key].get("used"):
        await update.message.reply_text(
            "```\n╔════════════════════╗\n║  ⚠️  ALREADY USED  ║\n╚════════════════════╝\n```",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    dur_str = keys[key].get("duration", "30d")
    days    = int("".join(filter(str.isdigit, dur_str))) * (30 if "m" in dur_str else 1)
    expires = (datetime.now() + timedelta(days=days)).isoformat()

    keys[key]["used"]    = True
    keys[key]["used_by"] = uid
    d.setdefault("redeemed", {})[uid] = {
        "key":     key,
        "devices": keys[key].get("devices", 1),
        "expires": expires
    }
    save(d)

    await update.message.reply_text(
        "```\n"
        "╔═══════════════════════════╗\n"
        "║  ✅  K E Y  R E D E E M  ║\n"
        "╚═══════════════════════════╝\n"
        "```\n"
        f"🔑 Key: `{key}`\n"
        f"📱 Devices: `{keys[key].get('devices', 1)}`\n"
        f"📅 Expires: `{expires[:10]}`\n\n"
        "_Use /start to access the database._",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("⛔ *Admins only.*", parse_mode=ParseMode.MARKDOWN)
        return
    if len(ctx.args) < 2:
        await update.message.reply_text(
            "Usage: `/createkeys <devices> <duration>`\nExample: `/createkeys 2 30d`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    devices  = ctx.args[0]
    duration = ctx.args[1]
    suffix   = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    key      = f"ZEIJIE-{suffix}"

    d.setdefault("keys", {})[key] = {
        "devices":    devices,
        "duration":   duration,
        "used":       False,
        "created_by": str(uid),
        "created_at": datetime.now().isoformat()
    }
    save(d)

    await update.message.reply_text(
        "```\n"
        "╔═══════════════════════════╗\n"
        "║  🔑  K E Y   C R E A T  ║\n"
        "╠═══════════════════════════╣\n"
        f"║  Key:      {key:<16}║\n"
        f"║  Devices:  {devices:<16}║\n"
        f"║  Duration: {duration:<16}║\n"
        "╚═══════════════════════════╝\n"
        "```",
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_feedback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)
    save(d)
    if not ctx.args:
        await update.message.reply_text("Usage: `/feedback <message>`", parse_mode=ParseMode.MARKDOWN)
        return
    msg   = " ".join(ctx.args)
    uname = update.effective_user.username or "?"
    fname = update.effective_user.first_name or "?"
    for admin_id in d.get("admins", []):
        try:
            await ctx.bot.send_message(
                int(admin_id),
                f"💬 *New Feedback*\n━━━━━━━━━━━━━━━\n"
                f"👤 {fname} (@{uname}) `{uid}`\n\n_{msg}_",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
    await update.message.reply_text("✅ *Feedback sent!*\n_Admins have been notified._", parse_mode=ParseMode.MARKDOWN)

async def cmd_addadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("⛔ *No permission.*", parse_mode=ParseMode.MARKDOWN)
        return
    if not ctx.args:
        await update.message.reply_text("Usage: `/addadmin <user_id>`", parse_mode=ParseMode.MARKDOWN)
        return
    new_admin = ctx.args[0]
    if new_admin not in d["admins"]:
        d["admins"].append(new_admin)
        save(d)
        await update.message.reply_text(f"✅ `{new_admin}` added as admin.", parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text("⚠️ Already an admin.", parse_mode=ParseMode.MARKDOWN)

async def cmd_chatidlist(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("⛔ *Admins only.*", parse_mode=ParseMode.MARKDOWN)
        return
    members = d.get("members", {})
    if not members:
        await update.message.reply_text("🆔 No chat IDs yet.", parse_mode=ParseMode.MARKDOWN)
        return
    lines = [f"`{k}` — {v.get('first_name','?')} (@{v.get('username','?')})" for k, v in members.items()]
    await update.message.reply_text(
        "🆔 *Chat ID List*\n━━━━━━━━━━━━━━━\n" + "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_listmember(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("⛔ *Admins only.*", parse_mode=ParseMode.MARKDOWN)
        return
    members = d.get("members", {})
    if not members:
        await update.message.reply_text("👥 No members yet.", parse_mode=ParseMode.MARKDOWN)
        return
    lines = [f"👤 *{v.get('first_name','?')}* (@{v.get('username','?')}) — `{k}`" for k, v in members.items()]
    await update.message.reply_text(
        f"👥 *Members ({len(members)})*\n━━━━━━━━━━━━━━━\n" + "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_dm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("⛔ *Admins only.*", parse_mode=ParseMode.MARKDOWN)
        return
    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: `/dm <chat_id> <message>`", parse_mode=ParseMode.MARKDOWN)
        return
    target  = ctx.args[0]
    message = " ".join(ctx.args[1:])
    try:
        await ctx.bot.send_message(
            int(target),
            f"📨 *Message from Admin:*\n\n{message}",
            parse_mode=ParseMode.MARKDOWN
        )
        await update.message.reply_text(f"✅ Sent to `{target}`.", parse_mode=ParseMode.MARKDOWN)
    except Exception as e:
        await update.message.reply_text(f"❌ Failed: `{e}`", parse_mode=ParseMode.MARKDOWN)

async def cmd_listkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("⛔ *Admins only.*", parse_mode=ParseMode.MARKDOWN)
        return
    keys = d.get("keys", {})
    if not keys:
        await update.message.reply_text("🔑 No keys yet.", parse_mode=ParseMode.MARKDOWN)
        return
    lines = []
    for k, v in keys.items():
        flag = "✅" if v.get("used") else "🟢"
        lines.append(f"{flag} `{k}` | {v.get('devices','?')} dev | {v.get('duration','?')}")
    await update.message.reply_text(
        "🔑 *All Keys*\n━━━━━━━━━━━━━━━\n" + "\n".join(lines),
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    rd  = d.get("redeemed", {}).get(uid)
    if rd:
        exp = rd.get("expires", "Never")[:10]
        body = f"✅  Active\n🔑  Key: `{rd['key']}`\n📅  Expires: `{exp}`\n📱  Devices: `{rd.get('devices','?')}`"
    elif is_admin(int(uid), d):
        body = "⚡  Admin — Unlimited Access"
    else:
        body = "🔒  No active subscription\n\nUse `/redeem <key>` to activate."
    await update.message.reply_text(
        "```\n╔══════════════════════╗\n║   M Y  S T A T U S  ║\n╚══════════════════════╝\n```\n" + body,
        parse_mode=ParseMode.MARKDOWN
    )

async def cmd_commands(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(COMMANDS_TEXT, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_back())

# ══════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════
def main():
    d = load()
    for key in ("admins", "keys", "members", "redeemed"):
        d.setdefault(key, {} if key != "admins" else [])
    save(d)

    app = Application.builder().token(BOT_TOKEN).build()

    handlers = [
        ("start",       cmd_start),
        ("commands",    cmd_commands),
        ("redeem",      cmd_redeem),
        ("feedback",    cmd_feedback),
        ("status",      cmd_status),
        ("createkeys",  cmd_createkeys),
        ("listkeys",    cmd_listkeys),
        ("addadmin",    cmd_addadmin),
        ("chatidlist",  cmd_chatidlist),
        ("listmember",  cmd_listmember),
        ("dm",          cmd_dm),
    ]
    for name, func in handlers:
        app.add_handler(CommandHandler(name, func))

    app.add_handler(CallbackQueryHandler(on_callback))

    print("╔═══════════════════════════╗")
    print("║  ✅  ZEIJIE Bot running   ║")
    print("╚═══════════════════════════╝")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
