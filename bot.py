#!/usr/bin/env python3

import os, json, random, string, io
from datetime import datetime, timedelta
from pathlib import Path

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from telegram.constants import ParseMode

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
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def save(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

# ================= ACCESS =================
def has_access(uid, d):
    user = d["users"].get(uid)
    if not user:
        return False

    exp = user["expire"]

    if exp == "lifetime":
        return True

    return datetime.now() < datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")

# ================= DATABASE =================
def get_files():
    return sorted(os.listdir(DB_FOLDER))

def process_file(path):
    with open(path, "r", errors="ignore") as f:
        lines = f.readlines()

    if len(lines) < LINES_PER_USE:
        return None, len(lines)

    selected = lines[:LINES_PER_USE]
    remaining = lines[LINES_PER_USE:]

    with open(path, "w") as f:
        f.writelines(remaining)

    return selected, len(remaining)

# ================= KEYBOARD =================
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Database", callback_data="db"),
         InlineKeyboardButton("🔑 Redeem", callback_data="redeem")],
        [InlineKeyboardButton("👤 Status", callback_data="status")]
    ])

# ================= START =================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    d = load()

    status = "✅ Active" if has_access(uid, d) else "🔒 No Access"

    await update.message.reply_text(
        f"{LOGO}\n👋 {update.effective_user.first_name}\n🔐 {status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb()
    )

# ================= CALLBACK =================
async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    d = load()
    uid = str(q.from_user.id)

    if q.data == "db":
        if not has_access(uid, d):
            await q.edit_message_text("🔒 Access required")
            return

        rows = []
        files = get_files()

        for i, f in enumerate(files):
            path = os.path.join(DB_FOLDER, f)
            count = sum(1 for _ in open(path, errors="ignore"))

            rows.append([
                InlineKeyboardButton(
                    f"{Path(f).stem.upper()} ({count:,})",
                    callback_data=f"get_{i}"
                )
            ])

        rows.append([InlineKeyboardButton("🔙 Back", callback_data="back")])

        await q.edit_message_text("📂 DATABASE", reply_markup=InlineKeyboardMarkup(rows))

    elif q.data.startswith("get_"):
        idx = int(q.data.split("_")[1])
        files = get_files()

        path = os.path.join(DB_FOLDER, files[idx])

        msg = await q.message.reply_text("⚙️ Processing...")

        data_lines, remaining = process_file(path)

        if not data_lines:
            await msg.edit_text("❌ Not enough lines")
            return

        bio = io.BytesIO("".join(data_lines).encode())
        bio.name = f"ZEIJIE-PREMIUM-{Path(files[idx]).stem.upper()}.txt"

        await q.message.reply_document(bio)

        await msg.edit_text(
f"""🔮 ✨ PREMIUM FILE GENERATED SUCCESSFULLY! ✨ 🔮

┣ 🎮 {Path(files[idx]).stem.upper()}
┣ 📜 Lines Generated: {LINES_PER_USE}
┣ 💾 Database: {remaining:,}
┣ 🕐 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

🔒 Auto-delete in 5 minutes"""
        )

    elif q.data == "back":
        await q.edit_message_text(LOGO, parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb())

# ================= TIME PARSER =================
def parse_duration(duration):
    duration = duration.lower()

    if duration == "lifetime":
        return "lifetime"

    num = int("".join(filter(str.isdigit, duration)) or 1)

    if "m" in duration:
        return datetime.now() + timedelta(minutes=num)
    elif "h" in duration:
        return datetime.now() + timedelta(hours=num)
    elif "d" in duration:
        return datetime.now() + timedelta(days=num)
    else:
        return datetime.now() + timedelta(days=num)

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

    key = "ZEIJIE-PREMIUM-" + str(random.randint(10000000, 99999999)) + "-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

    exp = parse_duration(duration)

    d = load()

    d["keys"][key] = {
        "devices": devices,
        "expire": exp.strftime("%Y-%m-%d %H:%M:%S") if exp != "lifetime" else "lifetime",
        "used": []
    }

    save(d)

    exp_text = "Lifetime" if exp == "lifetime" else exp.strftime("%Y-%m-%d (%H:%M:%S)")

    await update.message.reply_text(
f"""🔑 Key Generated!
━━━━━━━━━━━━━━━━━━━━
{key}
━━━━━━━━━━━━━━━━━━━━
⏱ Duration : {duration}
📅 Expires  : {exp_text}
👥 Max users: {devices}"""
    )

# ================= REDEEM =================
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    uid = str(update.effective_user.id)

    if not ctx.args:
        return

    key = ctx.args[0]

    if key not in d["keys"]:
        await update.message.reply_text("❌ Invalid key")
        return

    k = d["keys"][key]

    if uid not in k["used"]:
        if len(k["used"]) >= k["devices"]:
            await update.message.reply_text("❌ Device limit reached")
            return
        k["used"].append(uid)

    expire = k["expire"]

    d["users"][uid] = {
        "key": key,
        "expire": expire
    }

    save(d)

    await update.message.reply_text("✅ Activated!")

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("createkeys", createkeys))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CallbackQueryHandler(callback))

    print("BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()    return json.load(open(DATA_FILE))

def save(d):
    json.dump(d, open(DATA_FILE, "w"), indent=2)

# ================= ACCESS =================
def has_access(uid, d):
    user = d["users"].get(uid)
    if not user:
        return False

    exp = user["expire"]

    if exp == "lifetime":
        return True

    return datetime.now() < datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")

# ================= DATABASE =================
def get_files():
    return sorted(os.listdir(DB_FOLDER))

def process_file(path):
    with open(path, "r", errors="ignore") as f:
        lines = f.readlines()

    if len(lines) < LINES_PER_USE:
        return None, len(lines)

    selected = lines[:LINES_PER_USE]
    remaining = lines[LINES_PER_USE:]

    with open(path, "w") as f:
        f.writelines(remaining)

    return selected, len(remaining)

# ================= KEYBOARD =================
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Database", callback_data="db"),
         InlineKeyboardButton("🔑 Redeem", callback_data="redeem")],
        [InlineKeyboardButton("👤 Status", callback_data="status")]
    ])

# ================= START =================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    d = load()

    status = "✅ Active" if has_access(uid, d) else "🔒 No Access"

    await update.message.reply_text(
        f"{LOGO}\n👋 {update.effective_user.first_name}\n🔐 {status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb()
    )

# ================= CALLBACK =================
async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    d = load()
    uid = str(q.from_user.id)

    # ===== DATABASE =====
    if q.data == "db":
        if not has_access(uid, d):
            await q.edit_message_text(
                "🔒 Access required",
                reply_markup=main_kb()  # FIX UI
            )
            return

        rows = []
        files = get_files()

        for i, f in enumerate(files):
            path = os.path.join(DB_FOLDER, f)
            count = sum(1 for _ in open(path, errors="ignore"))

            rows.append([
                InlineKeyboardButton(
                    f"{Path(f).stem.upper()} ({count:,})",
                    callback_data=f"get_{i}"
                )
            ])

        rows.append([InlineKeyboardButton("🔙 Back", callback_data="back")])

        await q.edit_message_text(
            "📂 DATABASE",
            reply_markup=InlineKeyboardMarkup(rows)
        )

    # ===== GET FILE =====
    elif q.data.startswith("get_"):
        idx = int(q.data.split("_")[1])
        files = get_files()

        path = os.path.join(DB_FOLDER, files[idx])

        msg = await q.message.reply_text("⚙️ Processing...")

        data_lines, remaining = process_file(path)

        if not data_lines:
            await msg.edit_text("❌ Not enough lines")
            return

        bio = io.BytesIO("".join(data_lines).encode())
        bio.name = f"ZEIJIE-PREMIUM-{Path(files[idx]).stem.upper()}.txt"

        await q.message.reply_document(bio)

        await msg.edit_text(
f"""🔮 ✨ PREMIUM FILE GENERATED SUCCESSFULLY! ✨ 🔮

┣ 🎮 {Path(files[idx]).stem.upper()}
┣ 📜 Lines Generated: {LINES_PER_USE}
┣ 💾 Database: {remaining:,}
┣ 🕐 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

🔒 Auto-delete in 5 minutes""",
            reply_markup=main_kb()  # FIX UI
        )

    # ===== STATUS =====
    elif q.data == "status":
        user = d["users"].get(uid)

        if not user:
            await q.edit_message_text(
                "🔒 No active key",
                reply_markup=main_kb()
            )
            return

        await q.edit_message_text(
            f"🔑 {user['key']}\n📅 {user['expire']}",
            reply_markup=main_kb()
        )

    # ===== BACK =====
    elif q.data == "back":
        await q.edit_message_text(
            LOGO,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_kb()
        )

# ================= TIME PARSER =================
def parse_duration(duration):
    duration = duration.lower()

    if duration == "lifetime":
        return "lifetime"

    num = int("".join(filter(str.isdigit, duration)) or 1)

    if "m" in duration:
        return datetime.now() + timedelta(minutes=num)
    elif "h" in duration:
        return datetime.now() + timedelta(hours=num)
    elif "d" in duration:
        return datetime.now() + timedelta(days=num)
    else:
        return datetime.now() + timedelta(days=num)

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

    key = "ZEIJIE-PREMIUM-" + str(random.randint(10000000, 99999999)) + "-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

    exp = parse_duration(duration)

    d = load()

    d["keys"][key] = {
        "devices": devices,
        "expire": exp.strftime("%Y-%m-%d %H:%M:%S") if exp != "lifetime" else "lifetime",
        "used": []
    }

    save(d)

    exp_text = "Lifetime" if exp == "lifetime" else exp.strftime("%Y-%m-%d (%H:%M:%S)")

    await update.message.reply_text(
f"""🔑 Key Generated!
━━━━━━━━━━━━━━━━━━━━
{key}
━━━━━━━━━━━━━━━━━━━━
⏱ Duration : {duration}
📅 Expires  : {exp_text}
👥 Max users: {devices}"""
    )

# ================= REDEEM =================
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    uid = str(update.effective_user.id)

    if not ctx.args:
        return

    key = ctx.args[0]

    if key not in d["keys"]:
        await update.message.reply_text("❌ Invalid key")
        return

    k = d["keys"][key]

    if uid not in k["used"]:
        if len(k["used"]) >= k["devices"]:
            await update.message.reply_text("❌ Device limit reached")
            return
        k["used"].append(uid)

    expire = k["expire"]

    d["users"][uid] = {
        "key": key,
        "expire": expire
    }

    save(d)

    await update.message.reply_text("✅ Activated!")

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("createkeys", createkeys))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CallbackQueryHandler(callback))

    print("BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()    return json.load(open(DATA_FILE))

def save(d):
    json.dump(d, open(DATA_FILE, "w"), indent=2)

# ================= ACCESS =================
def has_access(uid, d):
    user = d["users"].get(uid)
    if not user:
        return False

    exp = user["expire"]

    if exp == "lifetime":
        return True

    return datetime.now() < datetime.strptime(exp, "%Y-%m-%d %H:%M:%S")

# ================= DATABASE =================
def get_files():
    return sorted(os.listdir(DB_FOLDER))

def process_file(path):
    with open(path, "r", errors="ignore") as f:
        lines = f.readlines()

    if len(lines) < LINES_PER_USE:
        return None, len(lines)

    selected = lines[:LINES_PER_USE]
    remaining = lines[LINES_PER_USE:]

    with open(path, "w") as f:
        f.writelines(remaining)

    return selected, len(remaining)

# ================= KEYBOARD =================
def main_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📂 Database", callback_data="db"),
         InlineKeyboardButton("🔑 Redeem", callback_data="redeem")],
        [InlineKeyboardButton("👤 Status", callback_data="status")]
    ])

# ================= START =================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    d = load()

    status = "✅ Active" if has_access(uid, d) else "🔒 No Access"

    await update.message.reply_text(
        f"{LOGO}\n👋 {update.effective_user.first_name}\n🔐 {status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_kb()
    )

# ================= CALLBACK =================
async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    d = load()
    uid = str(q.from_user.id)

    if q.data == "db":
        if not has_access(uid, d):
            await q.edit_message_text("🔒 Access required")
            return

        rows = []
        files = get_files()

        for i, f in enumerate(files):
            path = os.path.join(DB_FOLDER, f)
            count = sum(1 for _ in open(path, errors="ignore"))

            rows.append([
                InlineKeyboardButton(
                    f"{Path(f).stem.upper()} ({count:,})",
                    callback_data=f"get_{i}"
                )
            ])

        rows.append([InlineKeyboardButton("🔙 Back", callback_data="back")])

        await q.edit_message_text("📂 DATABASE", reply_markup=InlineKeyboardMarkup(rows))

    elif q.data.startswith("get_"):
        idx = int(q.data.split("_")[1])
        files = get_files()

        path = os.path.join(DB_FOLDER, files[idx])

        msg = await q.message.reply_text("⚙️ Processing...")

        data_lines, remaining = process_file(path)

        if not data_lines:
            await msg.edit_text("❌ Not enough lines")
            return

        bio = io.BytesIO("".join(data_lines).encode())
        bio.name = f"ZEIJIE-PREMIUM-{Path(files[idx]).stem.upper()}.txt"

        await q.message.reply_document(bio)

        await msg.edit_text(
f"""🔮 ✨ PREMIUM FILE GENERATED SUCCESSFULLY! ✨ 🔮

┣ 🎮 {Path(files[idx]).stem.upper()}
┣ 📜 Lines Generated: {LINES_PER_USE}
┣ 💾 Database: {remaining:,}
┣ 🕐 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

🔒 Auto-delete in 5 minutes"""
        )

    elif q.data == "back":
        await q.edit_message_text(LOGO, parse_mode=ParseMode.MARKDOWN, reply_markup=main_kb())

# ================= TIME PARSER =================
def parse_duration(duration):
    duration = duration.lower()

    if duration == "lifetime":
        return "lifetime"

    num = int("".join(filter(str.isdigit, duration)) or 1)

    if "m" in duration:
        return datetime.now() + timedelta(minutes=num)
    elif "h" in duration:
        return datetime.now() + timedelta(hours=num)
    elif "d" in duration:
        return datetime.now() + timedelta(days=num)
    else:
        return datetime.now() + timedelta(days=num)

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

    key = "ZEIJIE-PREMIUM-" + str(random.randint(10000000, 99999999)) + "-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

    exp = parse_duration(duration)

    d = load()

    d["keys"][key] = {
        "devices": devices,
        "expire": exp.strftime("%Y-%m-%d %H:%M:%S") if exp != "lifetime" else "lifetime",
        "used": []
    }

    save(d)

    exp_text = "Lifetime" if exp == "lifetime" else exp.strftime("%Y-%m-%d (%H:%M:%S)")

    await update.message.reply_text(
f"""🔑 Key Generated!
━━━━━━━━━━━━━━━━━━━━
{key}
━━━━━━━━━━━━━━━━━━━━
⏱ Duration : {duration}
📅 Expires  : {exp_text}
👥 Max users: {devices}"""
    )

# ================= REDEEM =================
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    uid = str(update.effective_user.id)

    if not ctx.args:
        return

    key = ctx.args[0]

    if key not in d["keys"]:
        await update.message.reply_text("❌ Invalid key")
        return

    k = d["keys"][key]

    # DEVICE LIMIT
    if uid not in k["used"]:
        if len(k["used"]) >= k["devices"]:
            await update.message.reply_text("❌ Device limit reached")
            return
        k["used"].append(uid)

    expire = k["expire"]

    d["users"][uid] = {
        "key": key,
        "expire": expire
    }

    save(d)

    await update.message.reply_text("✅ Activated!")

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("createkeys", createkeys))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CallbackQueryHandler(callback))

    print("BOT RUNNING...")
    app.run_polling()

if __name__ == "__main__":
    main()
