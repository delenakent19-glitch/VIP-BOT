#!/usr/bin/env python3

import os, json, random, string, io, asyncio
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
        return {"admins": [], "keys": {}, "members": {}, "redeemed": {}}
    with open(DATA_FILE) as f:
        return json.load(f)

def save(d):
    with open(DATA_FILE, "w") as f:
        json.dump(d, f, indent=2)

def is_admin(uid, d):
    return str(uid) in d.get("admins", []) or uid == OWNER_ID

def has_access(uid, d):
    if is_admin(uid, d):
        return True
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    exp = rd.get("expires")
    return not exp or datetime.fromisoformat(exp) > datetime.now()

def track(uid, username, first_name, d):
    d.setdefault("members", {})[str(uid)] = {
        "username": username or "",
        "first_name": first_name or "",
        "joined": datetime.now().isoformat()
    }

# ================= DATABASE =================
def get_files():
    return sorted(os.listdir(DB_FOLDER))

def get_chunk_and_update(path):
    if not os.path.exists(path):
        return [], 0

    with open(path, "r", errors="ignore") as f:
        lines = f.readlines()

    if len(lines) < LINES_PER_USE:
        return [], len(lines)

    chunk = lines[:LINES_PER_USE]
    remaining = lines[LINES_PER_USE:]

    # AUTO DECREASE
    with open(path, "w") as f:
        f.writelines(remaining)

    return chunk, len(remaining)

# ================= TIME PARSER =================
def parse_duration(duration):
    duration = duration.lower()
    now = datetime.now()

    if duration == "lifetime":
        return None

    num = int("".join(filter(str.isdigit, duration)) or 1)

    if "m" in duration:
        exp = now + timedelta(minutes=num)
    elif "h" in duration:
        exp = now + timedelta(hours=num)
    elif "d" in duration:
        exp = now + timedelta(days=num)
    else:
        exp = now + timedelta(days=num)

    return exp

# ================= TEXT =================
def premium_text(game, sent, total):
    return (
        "🔮 ✨ *PREMIUM FILE GENERATED SUCCESSFULLY!* ✨ 🔮\n\n"
        f"┣ 🎮 {game.upper()}\n"
        f"┣ 📜 Lines Generated: {sent}\n"
        f"┣ 💾 Database: {total:,}\n"
        f"┣ 🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        "🔒 Auto-delete in 5 minutes"
    )

# ================= KEYBOARDS =================
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

def kb_admin():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔑 Create Key", callback_data="adm_create")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")]
    ])

# ================= START =================
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d = load()
    user = update.effective_user

    track(user.id, user.username, user.first_name, d)
    save(d)

    status = "✅ Active" if has_access(user.id, d) else "🔒 No Access"

    await update.message.reply_text(
        f"{LOGO}\n👋 *{user.first_name}*\n🔐 {status}",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=kb_main(user.id, d)
    )

# ================= CALLBACK =================
async def callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    d = load()
    uid = q.from_user.id

    if q.data == "home":
        await q.edit_message_text(LOGO, parse_mode=ParseMode.MARKDOWN, reply_markup=kb_main(uid, d))

    elif q.data == "commands":
        await q.edit_message_text(
            "📋 COMMANDS\n\n/start\n/redeem <key>\n/createkeys",
            reply_markup=kb_main(uid, d)
        )

    elif q.data == "redeem_info":
        await q.edit_message_text("Use:\n/redeem ZEIJIE-PREMIUM-XXXX", reply_markup=kb_main(uid, d))

    elif q.data == "admin":
        if not is_admin(uid, d): return
        await q.edit_message_text("⚡ ADMIN PANEL", reply_markup=kb_admin())

    elif q.data == "adm_create":
        await q.edit_message_text(
            "Use:\n/createkeys <devices> <duration>\nExample:\n/createkeys 1 10d / 1h / 30m",
            reply_markup=kb_admin()
        )

    elif q.data == "status":
        rd = d["redeemed"].get(str(uid))
        if not rd:
            await q.edit_message_text("🔒 No active key")
            return

        exp = rd.get("expires")
        txt = "♾️ Lifetime" if not exp else datetime.fromisoformat(exp).strftime("%Y-%m-%d %H:%M")

        await q.edit_message_text(
            f"🔑 {rd['key']}\n📅 {txt}",
            reply_markup=kb_main(uid, d)
        )

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
                InlineKeyboardButton(
                    f"{Path(f).stem.upper()} ({count:,})",
                    callback_data=f"send_{i}"
                )
            ])

        rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
        await q.edit_message_text("📂 DATABASE", reply_markup=InlineKeyboardMarkup(rows))

    elif q.data.startswith("send_"):
        idx = int(q.data.split("_")[1])
        files = get_files()

        fname = files[idx]
        path = os.path.join(DB_FOLDER, fname)

        msg = await q.message.reply_text("🔄 Processing...")

        chunk, remaining = get_chunk_and_update(path)

        if not chunk:
            await msg.edit_text("❌ Not enough lines")
            return

        bio = io.BytesIO("".join(chunk).encode())
        bio.name = f"ZEIJIE-PREMIUM-{Path(fname).stem.upper()}.txt"

        await q.message.reply_document(bio)

        done = await q.message.reply_text(
            premium_text(Path(fname).stem, len(chunk), remaining),
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
    duration = ctx.args[1]

    key = "ZEIJIE-PREMIUM-" + str(random.randint(10000000, 99999999)) + "-" + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))

    exp = parse_duration(duration)

    d["keys"][key] = {
        "devices": devices,
        "duration": duration,
        "expire": exp.isoformat() if exp else None,
        "used_by": []
    }

    save(d)

    exp_text = "♾️ Lifetime" if not exp else exp.strftime("%Y-%m-%d (%H:%M)")

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
        await update.message.reply_text("Usage: /redeem <key>")
        return

    key = ctx.args[0]

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

    exp = k.get("expire")

    if exp and datetime.fromisoformat(exp) < datetime.now():
        await update.message.reply_text("❌ Key expired")
        return

    k["used_by"].append(uid)
    d["redeemed"][uid] = {"key": key, "expires": exp}

    save(d)

    await update.message.reply_text("✅ Activated!")

# ================= MAIN =================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("createkeys", createkeys))
    app.add_handler(CommandHandler("redeem", redeem))
    app.add_handler(CallbackQueryHandler(callback))

    print("🔥 ZEIJIE BOT RUNNING")
    app.run_polling()

if __name__ == "__main__":
    main()
