#!/usr/bin/env python3

import os, json, random, string, io
from datetime import datetime, timedelta
from pathlib import Path
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)
from telegram.constants import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN", "8797773644:AAHuuZurs0oiduQNW6ywxvTXQ1Kdf32XE9w")
OWNER_ID  = int(os.getenv("OWNER_ID", "8420104044"))

DATA_FILE = "data.json"
DB_FOLDER = "database"
LINES_PER_USE = 1000

os.makedirs(DB_FOLDER, exist_ok=True)

# ════════════════════════════════════════
# LOGO
# ════════════════════════════════════════
LOGO = (
    "```\n"
    "╔══════════════════════════════════╗\n"
    "║  ███████╗███████╗██╗     ██╗     ║\n"
    "║  ╚══███╔╝██╔════╝██║     ██║     ║\n"
    "║    ███╔╝ █████╗  ██║     ██║     ║\n"
    "║   ███╔╝  ██╔══╝  ██║     ██║     ║\n"
    "║  ███████╗███████╗███████╗███████╗║\n"
    "║  ╚══════╝╚══════╝╚══════╝╚══════╝║\n"
    "║        Z E I J I E   B O T       ║\n"
    "╚══════════════════════════════════╝\n"
    "```"
)

# ════════════════════════════════════════
# DATA
# ════════════════════════════════════════
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
        "username": username or "",
        "first_name": first_name or "",
        "joined": d["members"].get(str(uid), {}).get("joined", datetime.now().isoformat())
    }

def get_db_files():
    return sorted([
        f for f in os.listdir(DB_FOLDER)
        if os.path.isfile(os.path.join(DB_FOLDER, f))
    ])

# ════════════════════════════════════════
# DATABASE KEYBOARD (WITH LINE COUNT)
# ════════════════════════════════════════
def kb_db(files):
    ICONS = {".txt": "📄", ".csv": "📊", ".json": "🗂", ".log": "📝"}
    rows = []

    for i, f in enumerate(files):
        ext = Path(f).suffix.lower()
        icon = ICONS.get(ext, "📦")
        fpath = os.path.join(DB_FOLDER, f)

        try:
            with open(fpath, "r", errors="ignore") as file:
                line_count = sum(1 for _ in file)
        except:
            line_count = 0

        name = Path(f).stem.upper()
        display = f"{icon} {name} ({line_count:,})"

        rows.append([InlineKeyboardButton(display, callback_data=f"send_{i}")])

    rows.append([InlineKeyboardButton("🔙 Back", callback_data="go_home")])
    return InlineKeyboardMarkup(rows)

# ════════════════════════════════════════
# START
# ════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username, update.effective_user.first_name, d)
    save(d)

    name = update.effective_user.first_name or "User"
    status = "✅ Active" if has_access(uid, d) else "🔒 No Access"

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Database", callback_data="db")]
    ])

    await update.message.reply_text(
        f"{LOGO}\n👋 *{name}*\n🔐 {status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb
    )

# ════════════════════════════════════════
# CALLBACK
# ════════════════════════════════════════
async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    d = load()
    uid = q.from_user.id

    if q.data == "db":
        if not has_access(uid, d):
            await q.edit_message_text("🔒 No access.")
            return

        files = get_db_files()
        if not files:
            await q.edit_message_text("No files.")
            return

        await q.edit_message_text(
            "📂 Select database:",
            reply_markup=kb_db(files)
        )

    elif q.data.startswith("send_"):
        idx = int(q.data.split("_")[1])
        files = get_db_files()

        fname = files[idx]
        fpath = os.path.join(DB_FOLDER, fname)

        with open(fpath, "r", errors="replace") as f:
            lines = f.readlines()

        chunk = lines[:LINES_PER_USE]
        bio = io.BytesIO("".join(chunk).encode())

        # CUSTOM NAME
        custom_name = f"ZEIJIE-PREMIUM-{Path(fname).stem.upper()}.txt"
        bio.name = custom_name

        await q.message.reply_document(bio)

# ════════════════════════════════════════
# CREATE KEY
# ════════════════════════════════════════
async def cmd_createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    if not is_admin(update.effective_user.id, d):
        return

    devices = ctx.args[0]
    duration = ctx.args[1].lower()

    key = "ZEIJIE-" + "".join(random.choices(string.ascii_uppercase+string.digits, k=4))

    d["keys"][key] = {"devices": devices, "duration": duration, "used": False}
    save(d)

    await update.message.reply_text(f"✅ {key}")

# ════════════════════════════════════════
# REDEEM
# ════════════════════════════════════════
async def cmd_redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    uid = str(update.effective_user.id)
    key = ctx.args[0]

    if key not in d["keys"]:
        await update.message.reply_text("Invalid")
        return

    if d["keys"][key]["used"]:
        await update.message.reply_text("Used")
        return

    dur = d["keys"][key]["duration"]

    if dur == "lifetime":
        exp = None
    else:
        days = int("".join(filter(str.isdigit, dur)))
        exp = (datetime.now()+timedelta(days=days)).isoformat()

    d["keys"][key]["used"] = True
    d["redeemed"][uid] = {"expires": exp}

    save(d)

    txt = "Never ♾️" if not exp else exp[:10]
    await update.message.reply_text(f"✅ Activated\n📅 {txt}")

# ════════════════════════════════════════
# MAIN
# ════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("createkeys", cmd_createkeys))
    app.add_handler(CommandHandler("redeem", cmd_redeem))

    app.add_handler(CallbackQueryHandler(callback))

    print("ZEIJIE BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
