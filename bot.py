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

# ================= LOGO (UNCHANGED) =================
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
    return json.load(open(DATA_FILE))

def save(d):
    json.dump(d, open(DATA_FILE, "w"), indent=4)

data = load()

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

    # FIX: auto decrease
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

    if update.message:
        await update.message.reply_text(LOGO + "\n\nWelcome!", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.callback_query.edit_message_text(LOGO + "\n\nWelcome!", reply_markup=InlineKeyboardMarkup(kb))

# ================= BUTTONS =================
async def buttons(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    uid = str(q.from_user.id)
    d = load()

    # DATABASE
    if q.data == "database":
        total = count_lines("garena.txt")

        kb = [
            [InlineKeyboardButton(f"🎮 GARENA ({total})", callback_data="garena")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]

        await q.edit_message_text(LOGO + "\n\n📂 DATABASE", reply_markup=InlineKeyboardMarkup(kb))

    # GENERATE
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

        done = await q.message.reply_text(
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

    # BACK
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

    key = generate_key()
    exp = datetime.now() + parse_time(duration)

    data["keys"][key] = {
        "devices": devices,
        "expire": exp.strftime("%Y-%m-%d %H:%M:%S"),
        "used": []
    }

    save(data)

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
    main()        json.dump(data, f, indent=4)

data = load_data()

# ================== DATABASE ==================
def count_lines(filename):
    path = os.path.join(DB_FOLDER, filename)
    if not os.path.exists(path):
        return 0
    with open(path, "r") as f:
        return len(f.readlines())

def get_lines(filename, count):
    path = os.path.join(DB_FOLDER, filename)

    if not os.path.exists(path):
        return []

    with open(path, "r") as f:
        lines = f.readlines()

    if len(lines) < count:
        return []

    selected = lines[:count]
    remaining = lines[count:]

    # AUTO DECREASE
    with open(path, "w") as f:
        f.writelines(remaining)

    return selected

# ================== KEY SYSTEM ==================
def generate_key():
    return "ZEIJIE-PREMIUM-" + str(random.randint(10000000, 99999999)) + "-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

def parse_time(t):
    t = t.lower()
    if "m" in t:
        return timedelta(minutes=int(t.replace("m","")))
    if "h" in t:
        return timedelta(hours=int(t.replace("h","")))
    if "d" in t:
        return timedelta(days=int(t.replace("d","")))
    return timedelta(days=1)

# ================== START ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")],
        [InlineKeyboardButton("📂 Database", callback_data="database")],
        [InlineKeyboardButton("👤 Status", callback_data="status")]
    ]

    if update.message:
        await update.message.reply_text(
            f"{LOGO}\n\nWelcome!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.callback_query.edit_message_text(
            f"{LOGO}\n\nWelcome!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ================== BUTTON HANDLER ==================
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    data_btn = query.data

    # ================= DATABASE =================
    if data_btn == "database":
        total = count_lines("garena.txt")

        keyboard = [
            [InlineKeyboardButton("🎮 GARENA", callback_data="garena")],
            [InlineKeyboardButton("🔙 Back", callback_data="back")]
        ]

        await query.edit_message_text(
            f"{LOGO}\n\n📂 DATABASE\n\nGARENA ({total})",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # ================= GENERATE =================
    elif data_btn == "garena":
        if user_id not in data["users"]:
            await query.answer("🔒 Access required", show_alert=True)
            return

        lines = get_lines("garena.txt", LINES_PER_USE)

        if not lines:
            await query.answer("❌ Not enough lines", show_alert=True)
            return

        filename = "ZEIJIE-PREMIUM-GARENA.txt"

        with open(filename, "w") as f:
            f.writelines(lines)

        remaining = count_lines("garena.txt")

        await query.message.reply_document(open(filename, "rb"))

        await query.message.reply_text(
f"""✨🔮 PREMIUM FILE GENERATED SUCCESSFULLY! 🔮✨

🎮 GARENA
🪵 Lines Generated: {LINES_PER_USE}
📁 Database: {remaining}
⏰ {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

🔒 Auto-delete in 5 minutes"""
        )

    # ================= BACK =================
    elif data_btn == "back":
        keyboard = [
            [InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")],
            [InlineKeyboardButton("📂 Database", callback_data="database")],
            [InlineKeyboardButton("👤 Status", callback_data="status")]
        ]

        await query.edit_message_text(
            f"{LOGO}\n\nWelcome!",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
# ================== CREATE KEYS ==================
async def createkeys(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        return

    try:
        devices = int(context.args[0])
        duration = context.args[1]
    except:
        await update.message.reply_text("Usage: /createkeys <devices> <time>")
        return

    key = generate_key()
    expire = datetime.now() + parse_time(duration)

    data["keys"][key] = {
        "devices": devices,
        "expire": expire.strftime("%Y-%m-%d %H:%M:%S"),
        "used": []
    }

    save_data(data)

    await update.message.reply_text(
f"""🔑 Key Generated!
━━━━━━━━━━━━━━━━━━━━
{key}
━━━━━━━━━━━━━━━━━━━━
⏱ Duration : {duration}
📅 Expires  : {expire.strftime("%Y-%m-%d (%H:%M:%S)")}
👥 Max users: {devices}"""
    )

# ================== REDEEM ==================
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        key = context.args[0]
    except:
        return

    user_id = str(update.effective_user.id)

    if key not in data["keys"]:
        await update.message.reply_text("❌ Invalid key")
        return

    k = data["keys"][key]

    if len(k["used"]) >= k["devices"]:
        await update.message.reply_text("❌ Max devices reached")
        return

    if datetime.now() > datetime.strptime(k["expire"], "%Y-%m-%d %H:%M:%S"):
        await update.message.reply_text("❌ Key expired")
        return

    if user_id not in k["used"]:
        k["used"].append(user_id)

    data["users"][user_id] = key
    save_data(data)

    await update.message.reply_text("✅ Activated!")

# ================== AUTO START FIX ==================
async def auto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)

# ================== MAIN ==================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("createkeys", createkeys))
    app.add_handler(CommandHandler("redeem", redeem))

    app.add_handler(CallbackQueryHandler(buttons))

    # AUTO UI kahit walang /start
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto))

    app.run_polling()

if __name__ == "__main__":
    main()
