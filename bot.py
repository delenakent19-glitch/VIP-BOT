#!/usr/bin/env python3

import os, json, random, string, io, asyncio
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.constants import ParseMode

BOT_TOKEN = "8797773644:AAHuuZurs0oiduQNW6ywxvTXQ1Kdf32XE9w"
OWNER_ID = 8420104044

DATA_FILE = "data.json"
DB_FOLDER = "database"
LINES_PER_USE = 250

os.makedirs(DB_FOLDER, exist_ok=True)

# ================= LOGO =================
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

# ================= DATA =================
def load():
    if not os.path.exists(DATA_FILE):
        return {"admins": [], "keys": {}, "members": {}, "redeemed": {}}
    with open(DATA_FILE) as f:
        return json.load(f)

def save(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

def is_admin(uid, d):
    return str(uid) in d["admins"] or uid == OWNER_ID

def has_access(uid, d):
    if is_admin(uid, d):
        return True

    rd = d["redeemed"].get(str(uid))
    if not rd:
        return False

    exp = rd.get("expires")
    if not exp:
        return True

    return datetime.fromisoformat(exp) > datetime.now()

def track(uid, username, first_name, d):
    d["members"][str(uid)] = {
        "username": username or "",
        "first_name": first_name or "",
        "joined": datetime.now().isoformat()
    }

def get_files():
    return sorted(os.listdir(DB_FOLDER))

# ================= UI =================
def kb_main(uid, d):
    rows = []

    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")])

    rows += [
        [
            InlineKeyboardButton("📂 Database", callback_data="db"),
            InlineKeyboardButton("🔑 Redeem", callback_data="redeem_info")
        ],
        [
            InlineKeyboardButton("👤 Status", callback_data="status"),
            InlineKeyboardButton("📋 Commands", callback_data="commands")
        ]
    ]
    return InlineKeyboardMarkup(rows)

# ================= AUTO UI =================
async def auto_ui(update, ctx):
    if not update.message:
        return

    d = load()
    uid = update.effective_user.id

    track(uid, update.effective_user.username, update.effective_user.first_name, d)
    save(d)

    status = "✅ Active" if has_access(uid, d) else "🔒 No Access"

    await update.message.reply_text(
        f"{LOGO}\n👋 *{update.effective_user.first_name}*\n🔐 {status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_main(uid, d)
    )

# ================= START =================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await auto_ui(update, ctx)

# ================= CALLBACK =================
async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    d = load()
    uid = q.from_user.id

    if q.data == "commands":
        await q.edit_message_text("📋 /redeem /createkeys /start")

    elif q.data == "redeem_info":
        await q.edit_message_text("Use:\n/redeem ZEIJIE-PREMIUM-XXXX")

    elif q.data == "status":
        rd = d["redeemed"].get(str(uid))
        if not rd:
            await q.edit_message_text("🔒 No active key")
            return

        exp = rd.get("expires")
        txt = "♾️ Lifetime" if not exp else datetime.fromisoformat(exp).strftime("%Y-%m-%d %H:%M:%S")

        await q.edit_message_text(f"🔑 {rd['key']}\n📅 {txt}")

    elif q.data == "db":
        if not has_access(uid, d):
            await q.edit_message_text("🔒 Access required")
            return

        files = get_files()
        rows = []

        for i, f in enumerate(files):
            path = os.path.join(DB_FOLDER, f)
            count = sum(1 for _ in open(path, errors="ignore"))

            rows.append([
                InlineKeyboardButton(f"{Path(f).stem.upper()} ({count})", callback_data=f"send_{i}")
            ])

        await q.edit_message_text("📂 DATABASE", reply_markup=InlineKeyboardMarkup(rows))

    elif q.data.startswith("send_"):
        if not has_access(uid, d):
            await q.message.reply_text("🔒 Access expired")
            return

        idx = int(q.data.split("_")[1])
        files = get_files()

        fname = files[idx]
        path = os.path.join(DB_FOLDER, fname)

        msg = await q.message.reply_text("🔍 Initializing 20%...")
        await asyncio.sleep(1)
        await msg.edit_text("⚙️ Processing 50%...")
        await asyncio.sleep(1)
        await msg.edit_text("📦 Extracting 80%...")
        await asyncio.sleep(1)
        await msg.edit_text("✅ Completed 100%")

        with open(path, "r", errors="replace") as f:
            lines = f.readlines()

        chunk = lines[:LINES_PER_USE]
        remaining = lines[LINES_PER_USE:]

        with open(path, "w") as f:
            f.writelines(remaining)

        bio = io.BytesIO("".join(chunk).encode())
        bio.name = f"ZEIJIE-PREMIUM-{Path(fname).stem.upper()}.txt"

        await q.message.reply_document(bio)

# ================= CREATE KEY =================
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await auto_ui(update, ctx)

    d = load()

    if not is_admin(update.effective_user.id, d):
        return

    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /createkeys <devices> <duration>")
        return

    devices = int(ctx.args[0])
    duration = ctx.args[1].lower()

    key = "ZEIJIE-PREMIUM-" + "".join(random.choices(string.digits, k=8)) + "-" + "".join(random.choices(string.ascii_uppercase+string.digits, k=4))

    now = datetime.now()

    if duration == "lifetime":
        exp = None
        exp_text = "♾️ Lifetime"
    else:
        num = int("".join(filter(str.isdigit, duration)) or 0)

        if "h" in duration:
            exp = now + timedelta(hours=num)
        elif "m" in duration:
            exp = now + timedelta(minutes=num)
        else:
            exp = now + timedelta(days=num)

        exp_text = exp.strftime("%Y-%m-%d %H:%M:%S")
        exp = exp.isoformat()

    d["keys"][key] = {
        "devices": devices,
        "duration": duration,
        "expires": exp,
        "used_by": []
    }

    save(d)

    await update.message.reply_text(
        f"🔑 Key Generated!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"{key}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⏱ Duration : {duration}\n"
        f"📅 Expires  : {exp_text}\n"
        f"👥 Max users: {devices}"
    )

# ================= REDEEM =================
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await auto_ui(update, ctx)

    d = load()
    uid = str(update.effective_user.id)

    if not ctx.args:
        await update.message.reply_text("Usage: /redeem <key>")
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text("❌ Invalid key")
        return

    k = d["keys"][key]
    k.setdefault("used_by", [])

    if uid in k["used_by"]:
        await update.message.reply_text("⚠️ Already activated")
        return

    if len(k["used_by"]) >= int(k["devices"]):
        await update.message.reply_text("❌ Device limit reached")
        return

    k["used_by"].append(uid)

    d["redeemed"][uid] = {
        "key": key,
        "expires": k.get("expires")
    }

    save(d)

    await update.message.reply_text(
        f"✅ Activated!\n📱 {len(k['used_by'])}/{k['devices']}"
    )

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("createkeys", createkeys))
    app.add_handler(CommandHandler("redeem", redeem))

    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_ui))

    print("🔥 ZEIJIE BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
