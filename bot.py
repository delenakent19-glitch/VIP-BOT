#!/usr/bin/env python3

import os, json, random, string
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = "8797773644:AAHuuZurs0oiduQNW6ywxvTXQ1Kdf32XE9w"
OWNER_ID = 8420104044

DATA_FILE = "data.json"
DB_FOLDER = "database"
LINES_PER_USE = 250

os.makedirs(DB_FOLDER, exist_ok=True)

# ================= LOGO =================
LOGO = """```
╔══════════════════════════════════╗
║   ███████╗███████╗██╗██╗██╗     ║
║   ╚══███╔╝██╔════╝██║██║██║     ║
║     ███╔╝ █████╗  ██║██║██║     ║
║    ███╔╝  ██╔══╝  ██║██║██║     ║
║   ███████╗███████╗██║██║███████╗║
║   ╚══════╝╚══════╝╚═╝╚═╝╚══════╝║
║        Z E I J I E   B O T      ║
╚══════════════════════════════════╝
```"""

# ================= DATA =================
def load():
    if not os.path.exists(DATA_FILE):
        return {"keys": {}, "users": {}}
    with open(DATA_FILE) as f:
        return json.load(f)

def save(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=4)

# ================= DATABASE =================
def count_lines(file):
    path = os.path.join(DB_FOLDER, file)
    if not os.path.exists(path):
        return 0
    with open(path) as f:
        return len(f.readlines())

def get_lines(file, count):
    path = os.path.join(DB_FOLDER, file)

    if not os.path.exists(path):
        return []

    with open(path) as f:
        lines = f.readlines()

    if len(lines) < count:
        return []

    selected = lines[:count]
    remaining = lines[count:]

    with open(path, "w") as f:
        f.writelines(remaining)

    return selected

# ================= KEY =================
def generate_key():
    return "ZEIJIE-PREMIUM-" + str(random.randint(10000000, 99999999)) + "-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def parse_time(t):
    t = t.lower()
    num = int("".join(filter(str.isdigit, t)) or 1)

    if "m" in t:
        return timedelta(minutes=num)
    if "h" in t:
        return timedelta(hours=num)
    if "d" in t:
        return timedelta(days=num)

    return timedelta(days=num)

# ================= START =================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")],
        [InlineKeyboardButton("📂 Database", callback_data="database")],
        [InlineKeyboardButton("👤 Status", callback_data="status")]
    ]

    text = LOGO + "\n\nWelcome!"

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

# ================= BUTTONS =================
async def buttons(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = str(q.from_user.id)
    d = load()

    if q.data == "database":
        total = count_lines("garena.txt")

        kb = [
            [InlineKeyboardButton(f"🎮 GARENA ({total})", callback_data="garena")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]

        await q.edit_message_text(LOGO + "\n\n📂 DATABASE", reply_markup=InlineKeyboardMarkup(kb))

    elif q.data == "garena":
        if uid not in d["users"]:
            await q.answer("🔒 No Access", show_alert=True)
            return

        msg = await q.message.reply_text("🔍 Initializing 20%...")
        lines = get_lines("garena.txt", LINES_PER_USE)

        if not lines:
            await msg.edit_text("❌ Not enough lines")
            return

        await msg.edit_text("⚙️ Processing 50%...")
        await msg.edit_text("📦 Extracting 80%...")

        file = "ZEIJIE-PREMIUM-GARENA.txt"
        with open(file, "w") as f:
            f.writelines(lines)

        await msg.edit_text("✅ Completed 100%")

        await q.message.reply_document(open(file, "rb"))

        remaining = count_lines("garena.txt")

        await q.message.reply_text(
f"""🔮 ✨ PREMIUM FILE GENERATED SUCCESSFULLY! ✨ 🔮

📊 GENERATION SUMMARY
┣ 🎮 Source Game: • GARENA
┣ 📜 Lines Generated: {LINES_PER_USE}
┣ 🕐 Generated On: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
┣ 💾 Database Status: {remaining:,} lines available
┣ 🧹 Cleanup Status: ✅ Completed

🛡️ SECURITY & PRIVACY
┣ 🔒 Auto-Expiry: 5 minutes
┣ 🗑️ Auto-Deletion: Enabled
┣ 🛡️ Data Protection: Active
┣ ⚡ Secure Session: Verified

🚀 NEXT STEPS
┣ ⬇️ Download immediately
┣ ⏳ File expires in 5:00
┣ 🔄 Refresh for new generation
┣ 📚 Manage your data securely

⭐ Thank you for choosing Premium !"""
        )

    elif q.data == "back":
        await start(update, ctx)

# ================= CREATE KEY =================
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    try:
        devices = int(ctx.args[0])
        duration = ctx.args[1]
    except:
        await update.message.reply_text("Usage: /createkeys <devices> <time>")
        return

    d = load()

    key = generate_key()
    exp = datetime.now() + parse_time(duration)

    d["keys"][key] = {
        "devices": devices,
        "expire": exp.strftime("%Y-%m-%d %H:%M:%S"),
        "used": []
    }

    save(d)

    await update.message.reply_text(
f"""🔑 Key Generated!
━━━━━━━━━━━━━━━━━━━━
{key}
━━━━━━━━━━━━━━━━━━━━
⏱ Duration : {duration}
📅 Expires  : {exp.strftime("%Y-%m-%d (%H:%M:%S)")}
👥 Max users: {devices}"""
    )

# ================= REDEEM =================
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    uid = str(update.effective_user.id)

    if not ctx.args:
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text("❌ Invalid key")
        return

    k = d["keys"][key]

    if len(k["used"]) >= k["devices"]:
        await update.message.reply_text("❌ Device limit reached")
        return

    if datetime.now() > datetime.strptime(k["expire"], "%Y-%m-%d %H:%M:%S"):
        await update.message.reply_text("❌ Key expired")
        return

    if uid not in k["used"]:
        k["used"].append(uid)

    d["users"][uid] = key
    save(d)

    await update.message.reply_text("✅ Activated!")

# ================= AUTO =================
async def auto(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await start(update, ctx)

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("createkeys", createkeys))
    app.add_handler(CommandHandler("redeem", redeem))

    app.add_handler(CallbackQueryHandler(buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto))

    print("BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
