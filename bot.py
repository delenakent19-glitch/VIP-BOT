#!/usr/bin/env python3

import os, json, random, string, io, asyncio
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

# ================= CONFIG =================
BOT_TOKEN = "8797773644:AAHuuZurs0oiduQNW6ywxvTXQ1Kdf32XE9w"
OWNER_ID = 8420104044

DATA_FILE = "data.json"
DB_FOLDER = "database"
LINES_PER_USE = 250

os.makedirs(DB_FOLDER, exist_ok=True)

# ================= LOGO =================
LOGO = """```
╔══════════════════════════════╗
║       Z E I J I E  B O T     ║
╚══════════════════════════════╝
```"""

# ================= DATA =================
def load():
    if not os.path.exists(DATA_FILE):
        return {"admins": [], "keys": {}, "redeemed": {}}
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
    return not exp or datetime.fromisoformat(exp) > datetime.now()

# ================= KEYBOARD =================
def main_kb(uid, d):
    rows = []

    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")])

    rows += [
        [InlineKeyboardButton("📂 Database", callback_data="db")],
        [InlineKeyboardButton("👤 Status", callback_data="status")]
    ]

    return InlineKeyboardMarkup(rows)

def admin_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key", callback_data="adm_create")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")]
    ])

# ================= PREMIUM MESSAGE =================
def premium_text(game, sent, total):
    return (
        "🔮 ✨ *PREMIUM FILE GENERATED SUCCESSFULLY!* ✨ 🔮\n\n"
        f"┣ 🎮 {game.upper()}\n"
        f"┣ 📜 Lines Generated: {sent}\n"
        f"┣ 💾 Database: {total:,}\n"
        f"┣ 🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "🔒 Auto-delete in 5 minutes"
    )

# ================= START =================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    uid = update.effective_user.id

    status = "✅ Active" if has_access(uid, d) else "🔒 No Access"

    await update.message.reply_text(
        f"{LOGO}\n👋 *{update.effective_user.first_name}*\n🔐 {status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb(uid, d)
    )

# ================= CALLBACK =================
async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    d = load()
    uid = q.from_user.id

    if q.data == "home":
        await q.edit_message_text(LOGO, parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb(uid, d))

    elif q.data == "admin":
        if not is_admin(uid, d):
            return
        await q.edit_message_text("⚡ ADMIN PANEL", reply_markup=admin_kb())

    elif q.data == "adm_create":
        await q.edit_message_text(
            "Use:\n/createkeys <devices> <duration>\nExample:\n/createkeys 1 lifetime",
            reply_markup=admin_kb()
        )

    elif q.data == "status":
        rd = d["redeemed"].get(str(uid))
        if not rd:
            await q.edit_message_text("🔒 No active key", reply_markup=main_kb(uid, d))
            return

        exp = rd.get("expires")
        txt = "♾️ Lifetime" if not exp else datetime.fromisoformat(exp).strftime("%Y-%m-%d %H:%M")

        await q.edit_message_text(
            f"🔑 {rd['key']}\n📅 {txt}",
            reply_markup=main_kb(uid, d)
        )

    elif q.data == "db":
        if not has_access(uid, d):
            await q.edit_message_text("🔒 Access required")
            return

        files = sorted(os.listdir(DB_FOLDER))
        rows = []

        for i, f in enumerate(files):
            path = os.path.join(DB_FOLDER, f)
            count = sum(1 for _ in open(path, errors="ignore"))

            rows.append([
                InlineKeyboardButton(f"{Path(f).stem.upper()} ({count:,})", callback_data=f"send_{i}")
            ])

        rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
        await q.edit_message_text("📂 DATABASE", reply_markup=InlineKeyboardMarkup(rows))

    elif q.data.startswith("send_"):
        idx = int(q.data.split("_")[1])
        files = sorted(os.listdir(DB_FOLDER))

        fname = files[idx]
        path = os.path.join(DB_FOLDER, fname)

        # LOADING UI
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

        bio = io.BytesIO("".join(chunk).encode())
        bio.name = f"ZEIJIE-PREMIUM-{Path(fname).stem.upper()}.txt"

        await q.message.reply_document(bio)

        done = await q.message.reply_text(
            premium_text(Path(fname).stem, len(chunk), len(lines)),
            parse_mode=ParseMode.MARKDOWN
        )

        await asyncio.sleep(300)
        try:
            await done.delete()
            await msg.delete()
        except:
            pass

# ================= CREATE KEY =================
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()

    if not is_admin(update.effective_user.id, d):
        return

    if len(ctx.args) < 2:
        await update.message.reply_text("Usage: /createkeys <devices> <duration>")
        return

    devices = int(ctx.args[0])
    duration = ctx.args[1].lower()

    key = "ZEIJIE-PREMIUM-" + "".join(random.choices(string.digits, k=8)) + "-" + "".join(random.choices(string.ascii_uppercase, k=4))

    d["keys"][key] = {
        "devices": devices,
        "duration": duration,
        "used_by": []
    }

    save(d)

    await update.message.reply_text(
        f"🔑 Key Generated!\n━━━━━━━━━━━━━━━━━━━━\n{key}\n━━━━━━━━━━━━━━━━━━━━\n⏱ Duration : {duration}\n👥 Max users: {devices}"
    )

# ================= REDEEM =================
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
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

    if uid in k["used_by"]:
        await update.message.reply_text("⚠️ Already used")
        return

    if len(k["used_by"]) >= int(k["devices"]):
        await update.message.reply_text("❌ Device limit reached")
        return

    k["used_by"].append(uid)

    duration = k["duration"]
    now = datetime.now()

    if duration == "lifetime":
        exp = None
    else:
        num = int("".join(filter(str.isdigit, duration)) or 0)

        if "h" in duration:
            exp = now + timedelta(hours=num)
        elif "m" in duration:
            exp = now + timedelta(minutes=num)
        else:
            exp = now + timedelta(days=num)

        exp = exp.isoformat()

    d["redeemed"][uid] = {"key": key, "expires": exp}
    save(d)

    txt = "♾️ Lifetime" if not exp else datetime.fromisoformat(exp).strftime("%Y-%m-%d %H:%M")

    await update.message.reply_text(f"✅ Activated!\n🔑 {key}\n📅 {txt}")

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("createkeys", createkeys))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CallbackQueryHandler(callback))

    print("🔥 BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
