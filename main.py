#!/usr/bin/env python3
"""
╔══════════════════════════════════════╗
║        ZEIJIE VIP PREMIUM BOT        ║
║         by @Zeijie_s                 ║
╚══════════════════════════════════════╝
"""

import os, json, random, string, io, asyncio, logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from supabase import create_client, Client

# Philippine Time (UTC+8)
PHT = timezone(timedelta(hours=8))

def now_pht() -> datetime:
    """Return current datetime in Philippine Time (UTC+8)."""
    return datetime.now(PHT)

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
BOT_TOKEN     = "8797773644:AAEqK3MGZOu2mQRAJKJZjnW7XRmThbbDiZA"
OWNER_ID      = 8420104044
CONTACT_ADMIN = "@Zeijie_s"

# ── Supabase config ──────────────────────────────────
SUPABASE_URL    = "https://ynzrpqiyootxnknapztp.supabase.co"
SUPABASE_KEY    = "sb_secret_jcVS20jWZLdP0dIJD2OVww_dFGcBub-"
# Table names (create these in Supabase — see setup instructions)
TBL_META        = "bot_meta"       # stores keys/members/admins/logs as JSON
TBL_DB_META     = "bot_db_meta"    # stores db name + display label
TBL_DB_LINES    = "bot_db_lines"   # stores actual lines per database
# ─────────────────────────────────────────────────────

LINES_PER_USE = 250
OUTPUT_PREFIX = "ZEIJIE-VIP-PREMIUM"

DB_SUPPORTED_EXTS = {
    ".txt", ".csv", ".log", ".combo",
    ".list", ".dat", ".text", ".conf",
}

# Telegram hard limit is 20 MB for bots downloading files.
# We raise the local processing limit so any valid Telegram file works.
MAX_FILE_SIZE_MB = 19  # Telegram Bot API hard limit is 20 MB — keep this at 19

# ══════════════════════════════════════════════════════
#  MAINTENANCE MODE
# ══════════════════════════════════════════════════════
MAINTENANCE = False

MAINTENANCE_MSG = (
    "╔══════════════════════════════════╗\n"
    "║       🔧  MAINTENANCE  🔧        ║\n"
    "╚══════════════════════════════════╝\n\n"
    "⚙️ ᴛʜᴇ ʙᴏᴛ ɪs ᴄᴜʀʀᴇɴᴛʟʏ ᴜɴᴅᴇʀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ.\n"
    "⏳ ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ ʟᴀᴛᴇʀ.\n\n"
    f"📞 ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}"
)

async def maintenance_check(update: Update) -> bool:
    global MAINTENANCE
    if not MAINTENANCE:
        return False
    uid = update.effective_user.id if update.effective_user else None
    if uid and int(uid) == OWNER_ID:
        return False
    if update.message:
        await update.message.reply_text(MAINTENANCE_MSG)
    elif update.callback_query:
        await update.callback_query.answer(
            "🔧 Bot is under maintenance. Please try again later.",
            show_alert=True
        )
    return True

# ══════════════════════════════════════════════════════
#  LOGO
# ══════════════════════════════════════════════════════
LOGO = (
    "╔══════════════════════════════════╗\n"
    "║   ᴢᴇɪᴊɪᴇ  ᴠɪᴘ  ᴘʀᴇᴍɪᴜᴍ  ʙᴏᴛ   ║\n"
    "║    ✦  ᴠ ɪ ᴘ  ᴘ ʀ ᴇ ᴍ ɪ ᴜ ᴍ  ✦  ║\n"
    "║         ʙʏ @ᴢᴇɪᴊɪᴇ_s            ║\n"
    "╚══════════════════════════════════╝"
)

WELCOME_LINES = [
    "⚡ ᴢᴇɪᴊɪᴇ ʙᴏᴛ — ʟᴏᴄᴋᴇᴅ, ʟᴏᴀᴅᴇᴅ, ᴀɴᴅ ʀᴇᴀᴅʏ.",
    "🔥 ᴡᴇʟᴄᴏᴍᴇ ᴛᴏ ᴢᴇɪᴊɪᴇ ʙᴏᴛ — ʏᴏᴜʀ ᴘʀᴇᴍɪᴜᴍ ɢᴀᴛᴇᴡᴀʏ.",
    "🌐 ᴢᴇɪᴊɪᴇ ʙᴏᴛ ᴏɴʟɪɴᴇ — ᴘʀᴇᴄɪsɪᴏɴ · ᴘᴏᴡᴇʀ · ᴘʀᴇᴍɪᴜᴍ.",
    "🛡 ᴢᴇɪᴊɪᴇ ʙᴏᴛ ᴀᴄᴛɪᴠᴀᴛᴇᴅ — ʙᴜɪʟᴛ ᴅɪꜰꜰᴇʀᴇɴᴛ, ʙᴜɪʟᴛ ʙᴇᴛᴛᴇʀ.",
    "💎 ʏᴏᴜ'ᴠᴇ ᴇɴᴛᴇʀᴇᴅ ᴢᴇɪᴊɪᴇ ʙᴏᴛ — ᴡʜᴇʀᴇ ᴘʀᴇᴍɪᴜᴍ ʟɪᴠᴇs.",
    "🚀 ᴢᴇɪᴊɪᴇ ʙᴏᴛ ɪs ʟɪᴠᴇ — ʟᴇᴛ's ɢᴇᴛ ᴛᴏ ᴡᴏʀᴋ.",
    "🎯 ᴢᴇɪᴊɪᴇ ʙᴏᴛ sᴛᴀɴᴅɪɴɢ ʙʏ — ᴛʜᴇ ʀᴇᴀʟ ᴅᴇᴀʟ sᴛᴀʀᴛs ʜᴇʀᴇ.",
    "👾 ᴢᴇɪᴊɪᴇ ʙᴏᴛ ʟᴏᴀᴅᴇᴅ — ɴᴏ ʟɪᴍɪᴛs, ᴏɴʟʏ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss.",
]

# ══════════════════════════════════════════════════════
#  SUPABASE CLIENT
# ══════════════════════════════════════════════════════
_sb: Client | None = None

def _get_sb() -> Client:
    global _sb
    if _sb is None:
        _sb = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("✅ Supabase client created.")
    return _sb

# ══════════════════════════════════════════════════════
#  DATA HELPERS
# ══════════════════════════════════════════════════════
_DEFAULT: dict = {
    "admins":       [],
    "keys":         {},
    "members":      {},
    "redeemed":     {},
    "databases":    {},
    "activity_log": [],
}

_cache: dict | None = None

# ─── META (keys / members / admins / logs) ───────────────────────────────────
# Stored as a single JSON row in bot_meta with id=1

def _meta_load() -> dict:
    """Load metadata from Supabase bot_meta table."""
    sb  = _get_sb()
    res = sb.table(TBL_META).select("data").eq("id", 1).execute()
    if res.data:
        return res.data[0]["data"] or {}
    return {}

def _meta_save(meta: dict):
    """Upsert metadata into bot_meta table."""
    sb = _get_sb()
    sb.table(TBL_META).upsert({"id": 1, "data": meta}).execute()

# ─── DATABASE LINES ──────────────────────────────────────────────────────────
# bot_db_meta  : id (fname), display (text)
# bot_db_lines : id (auto), fname (text), chunk_index (int), lines (jsonb)

def _db_lines_save(fname: str, lines: list):
    """Save all lines for a database, replacing old chunks."""
    sb        = _get_sb()
    chunk_size = 20000
    # Strip null bytes that PostgreSQL JSONB cannot store
    lines = [l.replace("\x00", "") if isinstance(l, str) else l for l in lines]
    # Delete existing chunks for this fname
    sb.table(TBL_DB_LINES).delete().eq("fname", fname).execute()
    # Insert new chunks
    chunks = []
    for i in range(0, max(len(lines), 1), chunk_size):
        chunks.append({
            "fname":       fname,
            "chunk_index": i // chunk_size,
            "lines":       lines[i:i + chunk_size],
        })
    if chunks:
        sb.table(TBL_DB_LINES).insert(chunks).execute()
    logger.info("✅ Saved %d lines for %s (%d chunks)", len(lines), fname, len(chunks))

def _db_lines_load(fname: str) -> list:
    """Load all lines for a database, reassembling chunks in order."""
    sb  = _get_sb()
    res = (sb.table(TBL_DB_LINES)
             .select("chunk_index, lines")
             .eq("fname", fname)
             .order("chunk_index")
             .execute())
    lines = []
    for row in res.data:
        lines.extend(row["lines"] or [])
    return lines

def _db_meta_save(fname: str, display: str):
    sb = _get_sb()
    sb.table(TBL_DB_META).upsert({"fname": fname, "display": display}).execute()

def _db_meta_delete(fname: str):
    sb = _get_sb()
    sb.table(TBL_DB_META).delete().eq("fname", fname).execute()
    sb.table(TBL_DB_LINES).delete().eq("fname", fname).execute()

def _db_meta_list() -> list:
    sb  = _get_sb()
    res = sb.table(TBL_DB_META).select("fname, display").execute()
    return res.data or []

# ─── load / save ─────────────────────────────────────────────────────────────

def load(force: bool = False) -> dict:
    global _cache
    if _cache is not None and not force:
        return _cache
    try:
        meta = _meta_load()
        d    = {}
        for k, v in _DEFAULT.items():
            if k == "databases":
                continue
            val = meta.get(k)
            d[k] = val if val is not None else (v.copy() if isinstance(v, (dict, list)) else v)

        # Load databases
        d["databases"] = {}
        for row in _db_meta_list():
            fname   = row["fname"]
            display = row["display"] or ""
            lines   = _db_lines_load(fname)
            d["databases"][fname] = {"display": display, "lines": lines}

        _cache = d
        logger.info("✅ Loaded from Supabase — DBs: %d  lines: %d",
                    len(d["databases"]),
                    sum(len(v["lines"]) for v in d["databases"].values()))
    except Exception as e:
        logger.error("❌ Supabase load failed: %s", e)
        _cache = {k: (v.copy() if isinstance(v, (dict, list)) else v)
                  for k, v in _DEFAULT.items()}
    return _cache

def save(d: dict) -> str:
    """Save to Supabase. Returns error string or empty string on success."""
    global _cache
    _cache = d
    try:
        meta = {k: v for k, v in d.items() if k != "databases"}
        _meta_save(meta)
    except Exception as e:
        logger.error("❌ meta save failed: %s", e)
        return f"meta save failed: {e}"
    for fname, info in (d.get("databases") or {}).items():
        try:
            _db_lines_save(fname, info.get("lines", []))
            _db_meta_save(fname, info.get("display", ""))
        except Exception as e:
            logger.error("❌ db save failed for %s: %s", fname, e)
            return f"db save failed for {fname}: {e}"
    return ""

def save_db_lines(fname: str, lines: list):
    """Fast path — only rewrite one db's lines after consume."""
    try:
        _db_lines_save(fname, lines)
    except Exception as e:
        logger.error("❌ save_db_lines failed: %s", e)

save_local = save

# ══════════════════════════════════════════════════════
#  CONVERSATION STATE  (button-driven input flows)
# ══════════════════════════════════════════════════════
# _state[uid] = {"step": "...", ...extra data...}
_state: dict = {}

def track(uid, username, first_name, d):
    d.setdefault("members", {})[str(uid)] = {
        "username":   username or "",
        "first_name": first_name or "",
        "last_seen":  now_pht().isoformat(),
    }

def log_activity(d: dict, event: str):
    entry = {
        "time":  now_pht().strftime("%Y-%m-%d %H:%M:%S"),
        "event": event,
    }
    d.setdefault("activity_log", []).append(entry)
    d["activity_log"] = d["activity_log"][-200:]

# ══════════════════════════════════════════════════════
#  PERMISSION HELPERS
# ══════════════════════════════════════════════════════
def is_owner(uid) -> bool:
    return int(uid) == OWNER_ID

def is_admin(uid, d: dict) -> bool:
    return is_owner(uid) or str(uid) in [str(x) for x in d.get("admins", [])]

def is_expired(rd: dict) -> bool:
    exp = rd.get("expires")
    if not exp:
        return False
    try:
        exp_dt = datetime.fromisoformat(exp)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=PHT)
        return exp_dt <= now_pht()
    except ValueError:
        return False

def has_access(uid, d: dict) -> bool:
    if is_admin(uid, d):
        return True
    rd = d.get("redeemed", {}).get(str(uid))
    if not rd:
        return False
    return not is_expired(rd)

# ══════════════════════════════════════════════════════
#  DATABASE HELPERS
# ══════════════════════════════════════════════════════
def get_db_files(d: dict) -> list:
    return sorted(
        fname for fname, info in d.get("databases", {}).items()
        if info.get("lines")
    )

def count_db_lines(fname: str, d: dict) -> int:
    return len(d.get("databases", {}).get(fname, {}).get("lines", []))

def get_display_name(fname: str, d: dict) -> str:
    db = d.get("databases", {}).get(fname, {})
    return db.get("display") or Path(fname).stem

def consume_db_lines(fname: str, n: int, d: dict) -> tuple:
    lines    = d["databases"][fname]["lines"]
    to_send  = lines[:n]
    leftover = lines[n:]
    d["databases"][fname]["lines"] = leftover
    save_db_lines(fname, leftover)
    return "".join(to_send), len(leftover)

# ══════════════════════════════════════════════════════
#  KEY HELPERS
# ══════════════════════════════════════════════════════
def generate_key() -> str:
    return "ZEIJIE-PREMIUM-" + "".join(random.choices(string.digits, k=4))

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
        return None, "ʟɪꜰᴇᴛɪᴍᴇ"
    digits = "".join(c for c in dur if c.isdigit())
    if not digits:
        raise ValueError(f"Cannot parse duration: {raw!r}")
    n = int(digits)
    if "h" in dur:
        return timedelta(hours=n),   f"{n} ʜᴏᴜʀ{'s' if n != 1 else ''}"
    if "m" in dur and "month" not in dur:
        return timedelta(minutes=n), f"{n} ᴍɪɴᴜᴛᴇ{'s' if n != 1 else ''}"
    return timedelta(days=n), f"{n} ᴅᴀʏ{'s' if n != 1 else ''}"

def expiry_display(exp_iso) -> str:
    if not exp_iso:
        return "♾️ ɴᴇᴠᴇʀ (ʟɪꜰᴇᴛɪᴍᴇ)"
    try:
        exp_dt = datetime.fromisoformat(exp_iso)
        if exp_dt.tzinfo is None:
            exp_dt = exp_dt.replace(tzinfo=PHT)
    except ValueError:
        return "ɪɴᴠᴀʟɪᴅ ᴅᴀᴛᴇ"
    now      = now_pht()
    abs_time = exp_dt.strftime("%Y-%m-%d %H:%M:%S")
    if exp_dt <= now:
        return f"❌ ᴇxᴘɪʀᴇᴅ ({abs_time})"
    delta = exp_dt - now
    secs  = int(delta.total_seconds())
    d2, r = divmod(secs, 86400)
    h,  r = divmod(r, 3600)
    m,  s = divmod(r, 60)
    parts = []
    if d2: parts.append(f"{d2}ᴅ")
    if h:  parts.append(f"{h}ʜ")
    if m:  parts.append(f"{m}ᴍ")
    if s and not d2: parts.append(f"{s}s")
    return f"✅ {abs_time}  ({''.join(parts) or '< 1s'} ʟᴇꜰᴛ)"

# ══════════════════════════════════════════════════════
#  BEAUTIFUL MESSAGES
# ══════════════════════════════════════════════════════
def msg_key_generated(key: str, dur_label: str, devices: int) -> str:
    now = now_pht().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "🎉 ᴋᴇʏ ɢᴇɴᴇʀᴀᴛᴇᴅ sᴜᴄᴄᴇssꜰᴜʟʟʏ! 🎉\n\n"
        "🔑 ᴋᴇʏ ᴅᴇᴛᴀɪʟs\n"
        "┣ 🎫 ᴀᴄᴄᴇss ᴋᴇʏ: " + key + "\n"
        f"┣ ⏳ ᴠᴀʟɪᴅɪᴛʏ: {dur_label}\n"
        f"┣ 👥 ᴍᴀx ᴜsᴇʀs: {devices}\n"
        "┣ 📝 sᴛᴀᴛᴜs: ᴏɴᴇ-ᴛɪᴍᴇ ᴜsᴇ\n"
        f"┗ 📅 ᴄʀᴇᴀᴛᴇᴅ: {now}\n\n"
        "🛡️ sᴇᴄᴜʀɪᴛʏ ɴᴏᴛᴇs\n"
        "┣ ✦ sɪɴɢʟᴇ-ᴀᴄᴛɪᴠᴀᴛɪᴏɴ ᴏɴʟʏ\n"
        "┣ ✦ ᴀᴜᴛᴏ-ᴇxᴘɪʀʏ ᴇɴᴀʙʟᴇᴅ\n"
        "┗ ✦ ɴᴏɴ-ᴛʀᴀɴsꜰᴇʀᴀʙʟᴇ\n\n"
        "📤 ᴅɪsᴛʀɪʙᴜᴛɪᴏɴ\n"
        "sʜᴀʀᴇ ᴛʜɪs ᴋᴇʏ ᴡɪᴛʜ ʏᴏᴜʀ ᴜsᴇʀ ᴛᴏ ɢʀᴀɴᴛ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss!"
    )

def msg_bulk_keys(keys: list, dur_label: str) -> str:
    now = now_pht().strftime("%Y-%m-%d %H:%M:%S")
    keys_text = "\n".join(f"  ᴢᴇɪᴊɪᴇ-ᴘʀᴇᴍɪᴜᴍ-{k.split('-')[-1]}" if "-" in k else f"  {k}" for k in keys)
    # Use actual keys for copy block, styled display here
    styled_keys = "\n".join(f"  {k}" for k in keys)
    return (
        f"🎉 {len(keys)} ᴋᴇʏs ɢᴇɴᴇʀᴀᴛᴇᴅ sᴜᴄᴄᴇssꜰᴜʟʟʏ! 🎉\n\n"
        f"{styled_keys}\n\n"
        f"⏳ ᴠᴀʟɪᴅɪᴛʏ (ᴇᴀᴄʜ): ⏱️ {dur_label}\n"
        "📝 sᴛᴀᴛᴜs: ᴏɴᴇ-ᴛɪᴍᴇ ᴜsᴇ\n"
        f"📅 ᴄʀᴇᴀᴛᴇᴅ ᴏɴ: {now}\n\n"
        "✨ sʜᴀʀᴇ ᴛʜᴇsᴇ ᴋᴇʏs ᴡɪᴛʜ ʏᴏᴜʀ ᴜsᴇʀs ᴛᴏ ɢʀᴀɴᴛ ᴛʜᴇᴍ ᴀᴄᴄᴇss!\n"
        "┣ ✦ sɪɴɢʟᴇ-ᴀᴄᴛɪᴠᴀᴛɪᴏɴ ᴏɴʟʏ\n"
        "┣ ✦ ᴀᴜᴛᴏ-ᴇxᴘɪʀʏ ᴇɴᴀʙʟᴇᴅ\n"
        "┗ ✦ ɴᴏɴ-ᴛʀᴀɴsꜰᴇʀᴀʙʟᴇ"
    )

def msg_key_redeemed(key: str, expires_iso) -> str:
    expiry_line = expiry_display(expires_iso)
    return (
        "╔══════════════════════════════════╗\n"
        "║   ✅  ᴋᴇʏ ᴀᴄᴛɪᴠᴀᴛᴇᴅ!  ✅        ║\n"
        "╚══════════════════════════════════╝\n\n"
        f"🔑 ᴋᴇʏ: {key}\n"
        f"⏳ ᴇxᴘɪʀʏ: {expiry_line}\n\n"
        "💎 ʏᴏᴜ ɴᴏᴡ ʜᴀᴠᴇ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss!\n"
        "🚀 ᴜsᴇ /start ᴛᴏ ᴏᴘᴇɴ ᴛʜᴇ ᴍᴇɴᴜ."
    )

def msg_db_selection(files: list, d: dict) -> str:
    total = sum(count_db_lines(f, d) for f in files)
    return (
        "╔══════════════════════════════════╗\n"
        "║     💾  ᴅᴀᴛᴀʙᴀsᴇ  ᴍᴇɴᴜ  💾      ║\n"
        "╚══════════════════════════════════╝\n\n"
        f"┣ 📊 ᴛᴏᴛᴀʟ ᴀᴠᴀɪʟᴀʙʟᴇ: {total:,} ʟɪɴᴇs\n"
        f"┣ 📦 ᴘᴇʀ ɢᴇɴᴇʀᴀᴛɪᴏɴ: {LINES_PER_USE} ʟɪɴᴇs\n"
        "┗ 🧹 ᴀᴜᴛᴏ-ᴄʟᴇᴀɴᴜᴘ: ʟɪɴᴇs ʀᴇᴍᴏᴠᴇᴅ ᴀꜰᴛᴇʀ ɢᴇɴᴇʀᴀᴛɪᴏɴ\n\n"
        "👇 sᴇʟᴇᴄᴛ ᴀ ᴅᴀᴛᴀʙᴀsᴇ ʙᴇʟᴏᴡ:"
    )

def msg_file_caption(disp: str, sent: int, remaining: int) -> str:
    now = now_pht().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "🔮 ✨ ᴘʀᴇᴍɪᴜᴍ ꜰɪʟᴇ ɢᴇɴᴇʀᴀᴛᴇᴅ sᴜᴄᴄᴇssꜰᴜʟʟʏ! ✨ 🔮\n\n"
        "📊 ɢᴇɴᴇʀᴀᴛɪᴏɴ sᴜᴍᴍᴀʀʏ\n"
        f"┣ 🎮 sᴏᴜʀᴄᴇ: {disp.upper()}\n"
        f"┣ 📜 ʟɪɴᴇs ɢᴇɴᴇʀᴀᴛᴇᴅ: {sent:,}\n"
        f"┣ 🕐 ɢᴇɴᴇʀᴀᴛᴇᴅ ᴏɴ: {now}\n"
        f"┣ 💾 ᴅᴀᴛᴀʙᴀsᴇ sᴛᴀᴛᴜs: {remaining:,} ʟɪɴᴇs ᴀᴠᴀɪʟᴀʙʟᴇ\n"
        "┗ 🧹 ᴄʟᴇᴀɴᴜᴘ sᴛᴀᴛᴜs: ✅ ᴄᴏᴍᴘʟᴇᴛᴇᴅ\n\n"
        "🛡️ sᴇᴄᴜʀɪᴛʏ & ᴘʀɪᴠᴀᴄʏ\n"
        "┣ 🔒 ᴀᴜᴛᴏ-ᴇxᴘɪʀʏ: 5 ᴍɪɴᴜᴛᴇs\n"
        "┣ 🗑️ ᴀᴜᴛᴏ-ᴅᴇʟᴇᴛɪᴏɴ: ᴇɴᴀʙʟᴇᴅ\n"
        "┣ 🛡️ ᴅᴀᴛᴀ ᴘʀᴏᴛᴇᴄᴛɪᴏɴ: ᴀᴄᴛɪᴠᴇ\n"
        "┗ ⚡ sᴇᴄᴜʀᴇ sᴇssɪᴏɴ: ᴠᴇʀɪꜰɪᴇᴅ\n\n"
        "🚀 ɴᴇxᴛ sᴛᴇᴘs\n"
        "┣ ⬇️ ᴅᴏᴡɴʟᴏᴀᴅ ɪᴍᴍᴇᴅɪᴀᴛᴇʟʏ\n"
        "┣ ⏳ ꜰɪʟᴇ ᴇxᴘɪʀᴇs ɪɴ 5:00\n"
        "┗ 📚 ᴍᴀɴᴀɢᴇ ʏᴏᴜʀ ᴅᴀᴛᴀ sᴇᴄᴜʀᴇʟʏ\n\n"
        "⭐ ᴛʜᴀɴᴋ ʏᴏᴜ ꜰᴏʀ ᴄʜᴏᴏsɪɴɢ ᴘʀᴇᴍɪᴜᴍ sᴇʀᴠɪᴄᴇ!"
    )

def msg_db_uploaded(fname: str, disp: str, line_count: int, size_kb: float) -> str:
    now = now_pht().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "╔══════════════════════════════════╗\n"
        "║  ✅  ᴅᴀᴛᴀʙᴀsᴇ ᴜᴘʟᴏᴀᴅᴇᴅ!  ✅     ║\n"
        "╚══════════════════════════════════╝\n\n"
        "📂 ᴜᴘʟᴏᴀᴅ ᴅᴇᴛᴀɪʟs\n"
        f"┣ 🗂️ ꜰɪʟᴇ: {fname}\n"
        f"┣ 🏷️ ɴᴀᴍᴇ: {disp}\n"
        f"┣ 📜 ʟɪɴᴇs: {line_count:,}\n"
        f"┣ 💾 sɪᴢᴇ: {size_kb:.1f} KB\n"
        f"┗ 📅 ᴜᴘʟᴏᴀᴅᴇᴅ: {now}\n\n"
        "✨ ᴅᴀᴛᴀʙᴀsᴇ ɪs ɴᴏᴡ ᴀᴠᴀɪʟᴀʙʟᴇ ɪɴ ᴛʜᴇ ᴍᴇɴᴜ!"
    )

def msg_access_denied() -> str:
    return (
        "╔══════════════════════════════════╗\n"
        "║     🚫  ᴀᴄᴄᴇss  ᴅᴇɴɪᴇᴅ  🚫      ║\n"
        "╚══════════════════════════════════╝\n\n"
        "❌ ʏᴏᴜ ᴅᴏ ɴᴏᴛ ʜᴀᴠᴇ ᴀᴄᴄᴇss.\n"
        f"📞 ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ ᴛᴏ ɢᴇᴛ ᴀ ᴋᴇʏ: {CONTACT_ADMIN}"
    )

def msg_broadcast_text(msg_text: str) -> str:
    return (
        "📣 ᴀɴɴᴏᴜɴᴄᴇᴍᴇɴᴛ ꜰʀᴏᴍ ᴀᴅᴍɪɴ\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"{msg_text}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"— {CONTACT_ADMIN}"
    )

ACCESS_DENIED = msg_access_denied()

# ══════════════════════════════════════════════════════
#  OUTPUT FILE HELPERS
# ══════════════════════════════════════════════════════
def output_filename(disp: str) -> str:
    return f"{OUTPUT_PREFIX}-{disp.upper().replace(' ', '_')}.txt"

def file_header(disp: str, lines: int) -> str:
    sep = "═" * 38
    return (
        f"╔{sep}╗\n"
        f"  ZEIJIE VIP PREMIUM — {disp.upper()}\n"
        f"╚{sep}╝\n"
        f"  Lines     : {lines}\n"
        f"  Generated : {now_pht().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{'═' * 40}\n\n"
    )

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
#  ADMIN OVERVIEW BUILDER
# ══════════════════════════════════════════════════════
def build_admin_overview(d: dict) -> str:
    keys     = d.get("keys", {})
    members  = d.get("members", {})
    redeemed = d.get("redeemed", {})
    admins   = d.get("admins", [])
    files    = get_db_files(d)

    total_keys     = len(keys)
    unused_keys    = sum(1 for v in keys.values() if not v.get("used_by"))
    used_keys      = total_keys - unused_keys
    total_members  = len(members)
    active_users   = sum(1 for uid in redeemed
                         if not is_admin(int(uid), d) and has_access(int(uid), d))
    expired_users  = sum(1 for uid, rd in redeemed.items()
                         if is_expired(rd) and not is_admin(int(uid), d))
    total_db_lines = sum(count_db_lines(f, d) for f in files)
    now = now_pht().strftime("%Y-%m-%d %H:%M:%S")
    maintenance_status = "🔧 ON" if MAINTENANCE else "✅ OFF"

    return (
        "╔══════════════════════════════════╗\n"
        "║    ⚡  ᴀᴅᴍɪɴ ᴄᴏɴᴛʀᴏʟ ᴘᴀɴᴇʟ  ⚡   ║\n"
        "╚══════════════════════════════════╝\n\n"
        f"🕐 ᴜᴘᴅᴀᴛᴇᴅ: {now}\n"
        f"⚙️ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ: {maintenance_status}\n\n"
        "🔑 ᴋᴇʏ sᴛᴀᴛs\n"
        f"┣ 🗂️ ᴛᴏᴛᴀʟ ᴋᴇʏs:   {total_keys}\n"
        f"┣ ✅ ᴜsᴇᴅ:          {used_keys}\n"
        f"┗ 🔓 ᴜɴᴜsᴇᴅ:        {unused_keys}\n\n"
        "👥 ᴜsᴇʀ sᴛᴀᴛs\n"
        f"┣ 🌐 ᴛᴏᴛᴀʟ ᴍᴇᴍʙᴇʀs: {total_members}\n"
        f"┣ 🟢 ᴀᴄᴛɪᴠᴇ:        {active_users}\n"
        f"┣ 🔴 ᴇxᴘɪʀᴇᴅ:       {expired_users}\n"
        f"┗ 👮 ᴀᴅᴍɪɴs:        {len(admins) + 1}\n\n"
        "💾 ᴅᴀᴛᴀʙᴀsᴇ\n"
        f"┣ 📂 ᴅʙ ꜰɪʟᴇs:      {len(files)}\n"
        f"┗ 📜 ᴛᴏᴛᴀʟ ʟɪɴᴇs:   {total_db_lines:,}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    )

# ══════════════════════════════════════════════════════
#  KEYBOARDS
# ══════════════════════════════════════════════════════
def kb_main(uid, d) -> InlineKeyboardMarkup:
    rows = []
    if is_admin(uid, d):
        rows.append([InlineKeyboardButton("⚡ Admin Panel", callback_data="admin")])
    rows += [
        [
            InlineKeyboardButton("💾 Database",   callback_data="db"),
            InlineKeyboardButton("🔑 Redeem Key", callback_data="redeem_info"),
        ],
        [
            InlineKeyboardButton("👤 My Status",  callback_data="status"),
            InlineKeyboardButton("📋 Commands",   callback_data="commands"),
        ],
        [InlineKeyboardButton("📞 Contact Admin",
                              url=f"https://t.me/{CONTACT_ADMIN.lstrip('@')}")],
    ]
    return InlineKeyboardMarkup(rows)

def kb_admin() -> InlineKeyboardMarkup:
    maintenance_label = "✅ Maintenance: ON" if MAINTENANCE else "🔧 Maintenance: OFF"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Overview",     callback_data="adm_overview"),
            InlineKeyboardButton("🔑 Create Key",   callback_data="adm_create"),
        ],
        [
            InlineKeyboardButton("🎉 Bulk Keys",    callback_data="adm_bulk_info"),
            InlineKeyboardButton("🗝 Keys Log",     callback_data="adm_keys"),
        ],
        [
            InlineKeyboardButton("🗑️ Revoke Key",   callback_data="adm_revokekey"),
            InlineKeyboardButton("🟢 Active Users", callback_data="adm_active"),
        ],
        [
            InlineKeyboardButton("👥 Members Log",  callback_data="adm_members"),
            InlineKeyboardButton("📜 Activity Log", callback_data="adm_activity"),
        ],
        [
            InlineKeyboardButton("💾 DB Stats",     callback_data="adm_dbstats"),
            InlineKeyboardButton("📂 Add Database", callback_data="adddb_menu"),
        ],
        [
            InlineKeyboardButton("🔄 Reload DB",    callback_data="adm_reload_db"),
        ],
        [
            InlineKeyboardButton("🗑️ Delete DB",    callback_data="deletedb_menu"),
            InlineKeyboardButton("🏷️ Rename DB",    callback_data="adm_customname"),
        ],
        [
            InlineKeyboardButton("🗂️ Remove DB",    callback_data="adm_removedb_btn"),
            InlineKeyboardButton("📣 Broadcast",    callback_data="adm_broadcast"),
        ],
        [
            InlineKeyboardButton("👮 Admins List",  callback_data="adm_list"),
            InlineKeyboardButton("➕ Add Admin",    callback_data="adm_addadmin"),
        ],
        [
            InlineKeyboardButton("➖ Remove Admin", callback_data="adm_removeadmin"),
            InlineKeyboardButton(maintenance_label, callback_data="adm_toggle_maintenance"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "🔙 Back to Admin" if dest == "admin" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

def kb_db_files(files: list, d: dict) -> InlineKeyboardMarkup:
    rows = []
    for fname in files:
        cnt  = count_db_lines(fname, d)
        disp = get_display_name(fname, d)
        rows.append([InlineKeyboardButton(
            f"💾 {disp.upper()}  •  {cnt:,} ʟɪɴᴇs",
            callback_data=f"dbfile:{fname}"
        )])
    rows.append([InlineKeyboardButton("🔙 Back", callback_data="home")])
    return InlineKeyboardMarkup(rows)

def kb_contact() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📞 Contact Admin",
                              url=f"https://t.me/{CONTACT_ADMIN.lstrip('@')}")],
        [InlineKeyboardButton("🔙 Back", callback_data="home")],
    ])

def kb_deletedb(d: dict) -> InlineKeyboardMarkup:
    dbs  = d.get("databases", {})
    rows = []
    for fname, info in dbs.items():
        cnt  = len(info.get("lines", []))
        disp = info.get("display", Path(fname).stem)
        rows.append([InlineKeyboardButton(
            f"🗑 {disp.upper()}  •  {cnt:,} ʟɪɴᴇs",
            callback_data=f"deletedb_file:{fname}"
        )])
    if dbs:
        rows.append([InlineKeyboardButton(
            "⚠️ ᴅᴇʟᴇᴛᴇ ᴀʟʟ ᴅᴀᴛᴀʙᴀsᴇs",
            callback_data="deletedb_all"
        )])
    rows.append([InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")])
    return InlineKeyboardMarkup(rows)

# ══════════════════════════════════════════════════════
#  WELCOME
# ══════════════════════════════════════════════════════
def build_welcome(first_name, username, uid, d) -> str:
    if has_access(uid, d):
        status = "✅ ᴀᴄᴛɪᴠᴇ"
    elif is_admin(uid, d):
        status = "👮 ᴀᴅᴍɪɴ"
    else:
        status = "❌ ɴᴏ ᴀᴄᴄᴇss"
    line = random.choice(WELCOME_LINES)
    name = first_name or "Operator"
    user_line = f"👤 {name}"
    if username:
        user_line += f"  (@{username})"
    return (
        f"{LOGO}\n\n"
        f"{line}\n\n"
        f"{user_line}\n"
        f"📊 sᴛᴀᴛᴜs  : {status}\n"
        f"📞 sᴜᴘᴘᴏʀᴛ : {CONTACT_ADMIN}"
    )

# ══════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    d    = load(force=True)
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    log_activity(d, f"User @{user.username or user.id} opened the bot")
    save(d)
    await update.message.reply_text(
        build_welcome(user.first_name, user.username, user.id, d),
        reply_markup=kb_main(user.id, d),
    )

# ══════════════════════════════════════════════════════
#  /help
# ══════════════════════════════════════════════════════
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    d   = load()
    uid = update.effective_user.id

    user_cmds = (
        "╔══════════════════════════════════╗\n"
        "║     📋  ᴄᴏᴍᴍᴀɴᴅs  ʟɪsᴛ  📋     ║\n"
        "╚══════════════════════════════════╝\n\n"
        "👤 ᴜsᴇʀ ᴄᴏᴍᴍᴀɴᴅs\n"
        "┣ /start       — ᴍᴀɪɴ ᴍᴇɴᴜ\n"
        "┣ /redeem      — ᴀᴄᴛɪᴠᴀᴛᴇ ᴀ ᴠɪᴘ ᴋᴇʏ\n"
        "┣ /status      — ᴄʜᴇᴄᴋ ᴀᴄᴄᴇss sᴛᴀᴛᴜs\n"
        "┗ /help        — sʜᴏᴡ ᴛʜɪs ᴍᴇssᴀɢᴇ\n"
    )
    admin_cmds = (
        "\n👮 ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs\n"
        "┣ /createkeys  <ᴜsᴇʀs> <ᴅᴜʀ>       — ᴄʀᴇᴀᴛᴇ ᴋᴇʏ\n"
        "┣ /bulkkeys    <ᴘʀᴇꜰɪx> <ɴ> <ᴅᴜʀ>  — ʙᴜʟᴋ ᴋᴇʏs\n"
        "┣ /revokekey   <ᴋᴇʏ>               — ᴅᴇʟᴇᴛᴇ ᴀ ᴋᴇʏ\n"
        "┣ /adddb       [ɴᴀᴍᴇ]              — ᴜᴘʟᴏᴀᴅ ᴅʙ ꜰɪʟᴇ\n"
        "┣ /removedb    <ꜰɪʟᴇɴᴀᴍᴇ>          — ʀᴇᴍᴏᴠᴇ ᴀ ᴅʙ\n"
        "┣ /listdb                           — ʟɪsᴛ ᴀʟʟ ᴅʙs\n"
        "┣ /customname  <ꜰɪʟᴇ> <ɴᴀᴍᴇ>       — sᴇᴛ ᴅɪsᴘʟᴀʏ ɴᴀᴍᴇ\n"
        "┣ /broadcast   <ᴍᴇssᴀɢᴇ>           — sᴇɴᴅ ᴛᴏ ᴀʟʟ ᴜsᴇʀs\n"
        "┣ /maintenance                      — ᴛᴏɢɢʟᴇ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ\n"
        "┣ /addadmin    <ɪᴅ>                — ᴀᴅᴅ ᴀᴅᴍɪɴ (ᴏᴡɴᴇʀ)\n"
        "┗ /removeadmin <ɪᴅ>                — ʀᴇᴍᴏᴠᴇ ᴀᴅᴍɪɴ (ᴏᴡɴᴇʀ)\n"
    )

    await update.message.reply_text(
        user_cmds + (admin_cmds if is_admin(uid, d) else "")
    )

# ══════════════════════════════════════════════════════
#  /redeem <key>
# ══════════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if not ctx.args:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║     🔑  ʀᴇᴅᴇᴇᴍ  ᴀ  ᴋᴇʏ  🔑      ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📌 ᴜsᴀɢᴇ:\n"
            "   /redeem ZEIJIE-PREMIUM-XXXX\n\n"
            f"💬 ɴᴏ ᴋᴇʏ? ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}"
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text(
            "❌ ɪɴᴠᴀʟɪᴅ ᴋᴇʏ.\n\n"
            "ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ.\n\n"
            f"📞 ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}"
        )
        return

    k = d["keys"][key]

    if uid in k.get("used_by", []):
        await update.message.reply_text(
            "⚠️ ᴛʜɪs ᴋᴇʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ᴏɴ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ."
        )
        return

    if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
        await update.message.reply_text(
            "🚫 ᴅᴇᴠɪᴄᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ.\n\n"
            f"📞 ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}"
        )
        return

    raw_dur = k.get("duration", "lifetime")
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        td, dur_label = None, raw_dur

    now         = now_pht()
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

    uname = update.effective_user.username or uid
    log_activity(d, f"Key redeemed: {key} by @{uname} | expires: {expires_iso or 'Lifetime'}")
    save(d)
    await update.message.reply_text(msg_key_redeemed(key, expires_iso))

# ══════════════════════════════════════════════════════
#  /status
# ══════════════════════════════════════════════════════
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║    👮  ᴀᴅᴍɪɴ  ᴀᴄᴄᴏᴜɴᴛ  👮      ║\n"
            "╚══════════════════════════════════╝\n\n"
            "✅ ꜰᴜʟʟ ᴀᴄᴄᴇss — ɴᴏ ᴋᴇʏ ɴᴇᴇᴅᴇᴅ."
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║    ❌  ɴᴏ  ᴀᴄᴛɪᴠᴇ  ᴋᴇʏ  ❌      ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📌 ᴜsᴇ /redeem <ᴋᴇʏ> ᴛᴏ ᴀᴄᴛɪᴠᴀᴛᴇ ᴀᴄᴄᴇss.\n\n"
            f"📞 ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}"
        )
        return

    exp     = rd.get("expires")
    expired = is_expired(rd)
    act     = rd.get("activated", "Unknown")

    if expired:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║    🔴  ᴀᴄᴄᴇss  ᴇxᴘɪʀᴇᴅ  🔴      ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"┣ 🔑 ᴋᴇʏ: {rd['key']}\n"
            f"┗ ⏳ ᴇxᴘɪʀᴇᴅ: {expiry_display(exp)}\n\n"
            f"📞 ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}"
        )
    else:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║    🟢  ᴀᴄᴄᴇss  ᴀᴄᴛɪᴠᴇ  🟢       ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"┣ 🔑 ᴋᴇʏ:      {rd['key']}\n"
            f"┣ ⏱️ ᴅᴜʀᴀᴛɪᴏɴ: {rd.get('duration', 'N/A')}\n"
            f"┣ 📅 sᴛᴀʀᴛᴇᴅ:  {act[:19]}\n"
            f"┗ ⏳ ᴇxᴘɪʀᴇs:  {expiry_display(exp)}"
        )

# ══════════════════════════════════════════════════════
#  ADMIN: /createkeys
# ══════════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(ACCESS_DENIED, reply_markup=kb_contact())
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║     🔑  ᴄʀᴇᴀᴛᴇ  ᴋᴇʏ  🔑         ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📌 ᴜsᴀɢᴇ:\n"
            "   /createkeys <ᴍᴀx_ᴜsᴇʀs> <ᴅᴜʀᴀᴛɪᴏɴ>\n\n"
            "📋 ᴇxᴀᴍᴘʟᴇs:\n"
            "┣ /createkeys 1 7d\n"
            "┣ /createkeys 3 lifetime\n"
            "┗ /createkeys 1 2h\n\n"
            "⏱️ ᴛɪᴍᴇʀ sᴛᴀʀᴛs ᴡʜᴇɴ ʙᴜʏᴇʀ ʀᴇᴅᴇᴇᴍs."
        )
        return

    try:
        devices = int(ctx.args[0])
        if devices < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ ᴍᴀx ᴜsᴇʀs ᴍᴜsᴛ ʙᴇ ᴀ ᴘᴏsɪᴛɪᴠᴇ ɪɴᴛᴇɢᴇʀ.")
        return

    raw_dur = " ".join(ctx.args[1:])
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ ɪɴᴠᴀʟɪᴅ ᴅᴜʀᴀᴛɪᴏɴ.\n\nᴜsᴇ: 10d / 2h / 30m / lifetime"
        )
        return

    key = generate_key()
    d["keys"][key] = {
        "devices":     devices,
        "duration":    raw_dur,
        "used_by":     [],
        "user_expiry": {},
        "created_by":  str(uid),
        "created_at":  now_pht().isoformat(),
    }

    uname = update.effective_user.username or str(uid)
    log_activity(d, f"Key created: {key} | duration={raw_dur} | devices={devices} | by @{uname}")
    save(d)

    await update.message.reply_text(msg_key_generated(key, dur_label, devices))
    await update.message.reply_text(f"📋 ᴛᴀᴘ ᴛᴏ ᴄᴏᴘʏ:\n\n`{key}`", parse_mode="Markdown")

# ══════════════════════════════════════════════════════
#  ADMIN: /bulkkeys
# ══════════════════════════════════════════════════════
async def bulkkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(ACCESS_DENIED, reply_markup=kb_contact())
        return

    if len(ctx.args) < 3:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║    🎉  ʙᴜʟᴋ  ᴋᴇʏ  ɢᴇɴ  🎉       ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📌 ᴜsᴀɢᴇ:\n"
            "   /bulkkeys <ᴘʀᴇꜰɪx> <ᴄᴏᴜɴᴛ> <ᴅᴜʀᴀᴛɪᴏɴ>\n\n"
            "📋 ᴇxᴀᴍᴘʟᴇ:\n"
            "   /bulkkeys ZEIJIE 5 1d\n\n"
            "⚠️ ᴇᴀᴄʜ ᴋᴇʏ ɪs ᴏɴᴇ-ᴛɪᴍᴇ ᴜsᴇ.\n"
            "📊 ᴍᴀx 50 ᴋᴇʏs ᴘᴇʀ ᴄᴏᴍᴍᴀɴᴅ."
        )
        return

    prefix = ctx.args[0].strip()
    try:
        count = int(ctx.args[1])
        if not 1 <= count <= 50:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ ᴄᴏᴜɴᴛ ᴍᴜsᴛ ʙᴇ 1 ᴛᴏ 50.")
        return

    raw_dur = " ".join(ctx.args[2:])
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "❌ ɪɴᴠᴀʟɪᴅ ᴅᴜʀᴀᴛɪᴏɴ.\n\nᴜsᴇ: 10d / 2h / 30m / lifetime"
        )
        return

    keys    = generate_bulk_keys(prefix, count)
    now_iso = now_pht().isoformat()

    for k in keys:
        d["keys"][k] = {
            "devices":     1,
            "duration":    raw_dur,
            "used_by":     [],
            "user_expiry": {},
            "created_by":  str(uid),
            "created_at":  now_iso,
        }

    uname = update.effective_user.username or str(uid)
    log_activity(d, f"Bulk keys: {count} keys | prefix={prefix} | duration={raw_dur} | by @{uname}")
    save(d)

    await update.message.reply_text(msg_bulk_keys(keys, dur_label))
    keys_block = "\n".join(keys)
    await update.message.reply_text(f"📋 ᴛᴀᴘ ᴛᴏ ᴄᴏᴘʏ:\n\n`{keys_block}`", parse_mode="Markdown")

# ══════════════════════════════════════════════════════
#  ADMIN: /revokekey
# ══════════════════════════════════════════════════════
async def revokekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.")
        return
    if not ctx.args:
        await update.message.reply_text(
            "📌 ᴜsᴀɢᴇ: /revokekey <KEY>"
        )
        return
    key = ctx.args[0].strip().upper()
    if key not in d["keys"]:
        await update.message.reply_text("❌ ᴋᴇʏ ɴᴏᴛ ꜰᴏᴜɴᴅ.")
        return
    del d["keys"][key]
    d["redeemed"] = {u: v for u, v in d["redeemed"].items()
                     if v.get("key") != key}
    uname = update.effective_user.username or str(uid)
    log_activity(d, f"Key revoked: {key} by @{uname}")
    save(d)
    await update.message.reply_text(
        f"✅ ᴋᴇʏ ʀᴇᴠᴏᴋᴇᴅ!\n\n🔑 {key}"
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /adddb  — upload a database file (ANY SIZE up to Telegram's 20 MB limit)
#  Usage: reply to a file with /adddb [optional_name]
#    OR:  /adddb [name]  then send file next message
# ══════════════════════════════════════════════════════
_pending_db_upload: dict = {}
_saving_db: set = set()  # uids currently saving to Supabase

async def adddb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.")
        return

    msg = update.message

    # Case 1: command is a reply to a document
    if msg.reply_to_message and msg.reply_to_message.document:
        doc       = msg.reply_to_message.document
        fname     = doc.file_name or "database.txt"
        disp_name = " ".join(ctx.args).strip() if ctx.args else Path(fname).stem
        await _process_db_upload(update, ctx, doc, fname, disp_name, d)
        return

    # Case 2: command itself has a document attached
    if msg.document:
        doc       = msg.document
        fname     = doc.file_name or "database.txt"
        disp_name = " ".join(ctx.args).strip() if ctx.args else Path(fname).stem
        await _process_db_upload(update, ctx, doc, fname, disp_name, d)
        return

    # Case 3: no file yet — prompt admin to send it
    disp_name = " ".join(ctx.args).strip() if ctx.args else ""
    _pending_db_upload[uid] = disp_name or None
    await msg.reply_text(
        "╔══════════════════════════════════╗\n"
        "║   📂  ᴜᴘʟᴏᴀᴅ  ᴅᴀᴛᴀʙᴀsᴇ  📂     ║\n"
        "╚══════════════════════════════════╝\n\n"
        "📤 sᴇɴᴅ ᴍᴇ ᴛʜᴇ ᴅᴀᴛᴀʙᴀsᴇ ꜰɪʟᴇ ɴᴏᴡ.\n\n"
        "📋 sᴜᴘᴘᴏʀᴛᴇᴅ: .txt / .csv / .log / .combo / .list / .dat\n"
        f"💾 ᴍᴀx sɪᴢᴇ: {MAX_FILE_SIZE_MB} MB (ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ʟɪᴍɪᴛ)\n\n"
        + (f"🏷️ ᴅɪsᴘʟᴀʏ ɴᴀᴍᴇ: {disp_name}" if disp_name else
           "🏷️ ɪ'ʟʟ ᴜsᴇ ᴛʜᴇ ꜰɪʟᴇɴᴀᴍᴇ ᴀs ᴅɪsᴘʟᴀʏ ɴᴀᴍᴇ.")
    )

async def _process_db_upload(update, ctx, doc, fname, disp_name, d):
    uid = update.effective_user.id
    ext = Path(fname).suffix.lower()

    if ext not in DB_SUPPORTED_EXTS:
        await update.message.reply_text(
            f"❌ ᴜɴsᴜᴘᴘᴏʀᴛᴇᴅ ꜰɪʟᴇ ᴛʏᴘᴇ: {ext}\n\n"
            f"✅ sᴜᴘᴘᴏʀᴛᴇᴅ: {', '.join(sorted(DB_SUPPORTED_EXTS))}"
        )
        _pending_db_upload.pop(uid, None)
        return

    # Check file size (Telegram reports file_size in bytes)
    file_size_bytes = getattr(doc, "file_size", 0) or 0
    max_bytes = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size_bytes > max_bytes:
        await update.message.reply_text(
            f"❌ ꜰɪʟᴇ ᴛᴏᴏ ʟᴀʀɢᴇ!\n\n"
            f"┣ ꜰɪʟᴇ sɪᴢᴇ: {file_size_bytes / 1024 / 1024:.1f} MB\n"
            f"┗ ᴍᴀx ᴀʟʟᴏᴡᴇᴅ: {MAX_FILE_SIZE_MB} MB\n\n"
            "⚠️ ᴛᴇʟᴇɢʀᴀᴍ ʙᴏᴛ ʟɪᴍɪᴛ ɪs 20 MB."
        )
        _pending_db_upload.pop(uid, None)
        return

    size_kb  = file_size_bytes / 1024
    size_mb  = size_kb / 1024

    def _bar(pct: int) -> str:
        filled = pct // 10
        empty  = 10 - filled
        return "█" * filled + "░" * empty

    def _progress(pct: int, label: str, extra: str = "") -> str:
        return (
            "╔══════════════════════════════════╗\n"
            "║     📤  ᴜᴘʟᴏᴀᴅɪɴɢ  ᴅᴀᴛᴀʙᴀsᴇ  📤  ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"📁 ꜰɪʟᴇ: {fname}\n"
            f"💾 sɪᴢᴇ: {size_mb:.1f} MB\n\n"
            f"[{_bar(pct)}] {pct}%\n"
            f"📌 {label}"
            + (f"\n\n{extra}" if extra else "")
        )

    status = await update.message.reply_text(_progress(0, "ᴄᴏɴɴᴇᴄᴛɪɴɢ ᴛᴏ ᴛᴇʟᴇɢʀᴀᴍ..."))

    try:
        await status.edit_text(_progress(10, "ꜰᴇᴛᴄʜɪɴɢ ꜰɪʟᴇ ɪɴꜰᴏ..."))
        file_obj = await ctx.bot.get_file(doc.file_id)

        await status.edit_text(_progress(25, "ᴅᴏᴡɴʟᴏᴀᴅɪɴɢ ᴅᴀᴛᴀ ꜰʀᴏᴍ ᴛᴇʟᴇɢʀᴀᴍ..."))
        raw_bytes = await file_obj.download_as_bytearray()

        await status.edit_text(_progress(50, "ᴘʀᴏᴄᴇssɪɴɢ & ᴄʟᴇᴀɴɪɴɢ ʟɪɴᴇs..."))
        text  = raw_bytes.decode("utf-8", errors="ignore")
        text  = text.replace("\x00", "")
        lines = text.splitlines(keepends=True)
        lines = [l for l in lines if l.strip()]

        if not lines:
            await status.edit_text(
                "╔══════════════════════════════════╗\n"
                "║        ❌  ᴜᴘʟᴏᴀᴅ  ꜰᴀɪʟᴇᴅ  ❌     ║\n"
                "╚══════════════════════════════════╝\n\n"
                "⚠️ ꜰɪʟᴇ ɪs ᴇᴍᴘᴛʏ ᴏʀ ʜᴀs ɴᴏ ᴠᴀʟɪᴅ ʟɪɴᴇs.\n"
                "📤 ᴘʟᴇᴀsᴇ ᴜᴘʟᴏᴀᴅ ᴀ ᴠᴀʟɪᴅ ꜰɪʟᴇ."
            )
            _pending_db_upload.pop(uid, None)
            return

        await status.edit_text(_progress(70, f"ᴘʀᴇᴘᴀʀɪɴɢ {len(lines):,} ʟɪɴᴇs ꜰᴏʀ sᴀᴠᴇ..."))

        d.setdefault("databases", {})[fname] = {
            "lines":   lines,
            "display": disp_name or Path(fname).stem,
        }
        uname = update.effective_user.username or str(uid)
        log_activity(d, f"DB uploaded: {fname} | {len(lines)} lines | by @{uname}")

        # ── Run heavy Supabase save in background thread ──────────────
        _saving_db.add(uid)
        loop       = asyncio.get_event_loop()
        start_time = asyncio.get_event_loop().time()

        def _fast_save():
            try:
                meta = {k: v for k, v in d.items() if k != "databases"}
                _meta_save(meta)
                _db_lines_save(fname, lines)
                _db_meta_save(fname, disp_name or Path(fname).stem)
                return ""
            except Exception as e:
                return str(e)

        # Live updating progress bar during save (every 4s)
        async def _live_progress():
            pcts   = [75, 80, 85, 88, 91, 94, 97]
            labels = [
                "ᴄᴏɴɴᴇᴄᴛɪɴɢ ᴛᴏ sᴜᴘᴀʙᴀsᴇ...",
                "sᴀᴠɪɴɢ ᴄʜᴜɴᴋs ᴛᴏ ᴅᴀᴛᴀʙᴀsᴇ...",
                "ᴡʀɪᴛɪɴɢ ʀᴇᴄᴏʀᴅs...",
                "ꜰɪɴᴀʟɪᴢɪɴɢ ᴄʜᴜɴᴋs...",
                "ᴀʟᴍᴏsᴛ ᴅᴏɴᴇ...",
                "ᴠᴇʀɪꜰʏɪɴɢ ᴅᴀᴛᴀ...",
                "ᴄᴏᴍᴘʟᴇᴛɪɴɢ sᴀᴠᴇ...",
            ]
            i = 0
            while uid in _saving_db:
                elapsed = int(asyncio.get_event_loop().time() - start_time)
                pct     = pcts[min(i, len(pcts) - 1)]
                lbl     = labels[min(i, len(labels) - 1)]
                try:
                    await status.edit_text(
                        _progress(pct, lbl,
                                  f"📊 {len(lines):,} ʟɪɴᴇs  |  ⏱️ {elapsed}s ᴇʟᴀᴘsᴇᴅ\n"
                                  "🔒 ᴅᴏ ɴᴏᴛ ᴄʟᴏsᴇ — sᴀᴠɪɴɢ ɪɴ ᴘʀᴏɢʀᴇss...")
                    )
                except Exception:
                    pass
                i += 1
                await asyncio.sleep(4)

        progress_task = asyncio.create_task(_live_progress())
        err           = await loop.run_in_executor(None, _fast_save)
        _saving_db.discard(uid)
        progress_task.cancel()

        if err:
            await status.edit_text(
                "╔══════════════════════════════════╗\n"
                "║     ❌  sᴜᴘᴀʙᴀsᴇ  ꜰᴀɪʟᴇᴅ  ❌    ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"⚠️ ᴇʀʀᴏʀ: {err}\n\n"
                "📩 ᴘʟᴇᴀsᴇ sᴇɴᴅ ᴛʜɪs ᴇʀʀᴏʀ ᴛᴏ ᴅᴇᴠ."
            )
            _pending_db_upload.pop(uid, None)
            return

        # ── SUCCESS ───────────────────────────────────────────────────
        elapsed_total = int(asyncio.get_event_loop().time() - start_time)
        global _cache
        _cache = None
        _pending_db_upload.pop(uid, None)

        await status.edit_text(
            "╔══════════════════════════════════╗\n"
            "║   ✅  ᴜᴘʟᴏᴀᴅ  ᴄᴏᴍᴘʟᴇᴛᴇ!  ✅    ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"[{'█' * 10}] 100% ✅\n\n"
            f"📁 ꜰɪʟᴇ:   {fname}\n"
            f"🏷️ ɴᴀᴍᴇ:   {disp_name or Path(fname).stem}\n"
            f"📜 ʟɪɴᴇs:  {len(lines):,}\n"
            f"💾 sɪᴢᴇ:   {size_mb:.1f} MB\n"
            f"⏱️ ᴛɪᴍᴇ:   {elapsed_total}s\n\n"
            "✨ ᴅᴀᴛᴀʙᴀsᴇ ɪs ɴᴏᴡ ʟɪᴠᴇ ɪɴ ᴛʜᴇ ᴍᴇɴᴜ!"
        )

    except Exception as e:
        _saving_db.discard(uid)
        logger.error("DB upload error: %s", e)
        try:
            await status.edit_text(
                "╔══════════════════════════════════╗\n"
                "║     ❌  ᴜᴘʟᴏᴀᴅ  ꜰᴀɪʟᴇᴅ  ❌      ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"⚠️ ᴇʀʀᴏʀ: {e}\n\n"
                "🔄 ᴘʟᴇᴀsᴇ ᴛʀʏ ᴀɢᴀɪɴ."
            )
        except Exception:
            pass
        _pending_db_upload.pop(uid, None)

# ══════════════════════════════════════════════════════
#  ADMIN: /removedb
# ══════════════════════════════════════════════════════
async def removedb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.")
        return

    dbs = d.get("databases", {})
    if not ctx.args:
        listing = "\n".join(f"┣ {f}" for f in dbs) if dbs else "  ɴᴏɴᴇ"
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║    🗑️  ʀᴇᴍᴏᴠᴇ  ᴅᴀᴛᴀʙᴀsᴇ  🗑️    ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📌 ᴜsᴀɢᴇ: /removedb <ꜰɪʟᴇɴᴀᴍᴇ>\n\n"
            f"📂 ᴀᴠᴀɪʟᴀʙʟᴇ ᴅᴀᴛᴀʙᴀsᴇs:\n{listing}"
        )
        return

    fname = ctx.args[0].strip()
    if fname not in dbs:
        await update.message.reply_text(f"❌ ᴅᴀᴛᴀʙᴀsᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ: {fname}")
        return

    del dbs[fname]
    uname = update.effective_user.username or str(uid)
    log_activity(d, f"DB removed: {fname} by @{uname}")
    try:
        _db_meta_delete(fname)
    except Exception as e:
        logger.error("Supabase removedb failed: %s", e)
    save(d)
    await update.message.reply_text(
        f"✅ ᴅᴀᴛᴀʙᴀsᴇ ʀᴇᴍᴏᴠᴇᴅ!\n\n🗂️ {fname}"
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /listdb
# ══════════════════════════════════════════════════════
async def listdb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.")
        return

    dbs = d.get("databases", {})
    if not dbs:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║     💾  ᴅᴀᴛᴀʙᴀsᴇ  ʟɪsᴛ  💾      ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📭 ɴᴏ ᴅᴀᴛᴀʙᴀsᴇs ᴜᴘʟᴏᴀᴅᴇᴅ ʏᴇᴛ.\n\n"
            "📤 ᴜsᴇ /adddb ᴛᴏ ᴜᴘʟᴏᴀᴅ ᴏɴᴇ."
        )
        return

    total_lines = sum(len(v.get("lines", [])) for v in dbs.values())
    lines = [
        "╔══════════════════════════════════╗\n"
        "║     💾  ᴅᴀᴛᴀʙᴀsᴇ  ʟɪsᴛ  💾      ║\n"
        "╚══════════════════════════════════╝\n"
    ]
    for fname, info in dbs.items():
        cnt  = len(info.get("lines", []))
        disp = info.get("display", Path(fname).stem)
        lines.append(f"┣ 📂 {disp}\n  ꜰɪʟᴇ: {fname}\n  ʟɪɴᴇs: {cnt:,}")
    lines.append(f"\n📊 ᴛᴏᴛᴀʟ: {total_lines:,} ʟɪɴᴇs ᴀᴄʀᴏss {len(dbs)} ᴅʙ(s)")
    await update.message.reply_text("\n".join(lines))

# ══════════════════════════════════════════════════════
#  MESSAGE HANDLER — state-based input + file uploads
# ══════════════════════════════════════════════════════
async def handle_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return

    uid = update.effective_user.id
    msg = update.message

    # ── File upload (adddb pending) ──────────────────
    if msg.document:
        if uid in _pending_db_upload and uid not in _saving_db:
            d         = load()
            doc       = msg.document
            fname     = doc.file_name or "database.txt"
            disp_name = _pending_db_upload[uid] or Path(fname).stem
            await _process_db_upload(update, ctx, doc, fname, disp_name, d)
        elif uid in _saving_db:
            await msg.reply_text("⏳ ᴘʟᴇᴀsᴇ ᴡᴀɪᴛ... sᴛɪʟʟ sᴀᴠɪɴɢ ᴛᴏ sᴜᴘᴀʙᴀsᴇ.")
        return

    # ── Text input for conversation states ───────────
    if not msg.text:
        return

    text = msg.text.strip()
    step = _state.get(uid, {}).get("step")

    if not step:
        return  # no active state; unknown_command handler covers commands

    d = load()
    cancel_kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 Back to Admin", callback_data="admin")]
    ])

    # ── REDEEM via button ────────────────────────────
    if step == "redeem_key":
        _state.pop(uid, None)
        key = text.upper()
        if key not in d["keys"]:
            await msg.reply_text(
                "❌ ɪɴᴠᴀʟɪᴅ ᴋᴇʏ. ᴘʟᴇᴀsᴇ ᴄʜᴇᴄᴋ ᴀɴᴅ ᴛʀʏ ᴀɢᴀɪɴ.\n\n"
                f"📞 ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}"
            )
            return
        uid_str = str(uid)
        k = d["keys"][key]
        if uid_str in k.get("used_by", []):
            await msg.reply_text("⚠️ ᴛʜɪs ᴋᴇʏ ɪs ᴀʟʀᴇᴀᴅʏ ᴀᴄᴛɪᴠᴀᴛᴇᴅ ᴏɴ ʏᴏᴜʀ ᴀᴄᴄᴏᴜɴᴛ.")
            return
        if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
            await msg.reply_text(f"🚫 ᴅᴇᴠɪᴄᴇ ʟɪᴍɪᴛ ʀᴇᴀᴄʜᴇᴅ.\n\n📞 ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}")
            return
        raw_dur = k.get("duration", "lifetime")
        try:
            td, dur_label = parse_duration(raw_dur)
        except ValueError:
            td, dur_label = None, raw_dur
        now        = now_pht()
        expires_dt = (now + td) if td else None
        expires_iso = expires_dt.isoformat() if expires_dt else None
        k.setdefault("used_by", []).append(uid_str)
        k.setdefault("user_expiry", {})[uid_str] = expires_iso
        d["redeemed"][uid_str] = {
            "key": key, "duration": raw_dur,
            "expires": expires_iso, "activated": now.isoformat(),
        }
        uname = update.effective_user.username or uid_str
        log_activity(d, f"Key redeemed (btn): {key} by @{uname}")
        save(d)
        await msg.reply_text(msg_key_redeemed(key, expires_iso))
        return

    # ── Only admins past this point ──────────────────
    if not is_admin(uid, d):
        _state.pop(uid, None)
        return

    # ── CREATE KEY: step 1 — devices ────────────────
    if step == "createkey_devices":
        try:
            devices = int(text)
            if devices < 1:
                raise ValueError
        except ValueError:
            await msg.reply_text("❌ ᴇɴᴛᴇʀ ᴀ ᴠᴀʟɪᴅ ɴᴜᴍʙᴇʀ (ᴇ.ɢ. 1)", reply_markup=cancel_kb)
            return
        _state[uid] = {"step": "createkey_duration", "devices": devices}
        await msg.reply_text(
            f"✅ ᴜsᴇʀs: {devices}\n\n"
            "⏱️ sᴛᴇᴘ 2/2 — ᴇɴᴛᴇʀ ᴅᴜʀᴀᴛɪᴏɴ:\n\n"
            "┣ 1d / 7d / 30d\n"
            "┣ 2h / 30m\n"
            "┗ lifetime",
            reply_markup=cancel_kb,
        )

    # ── CREATE KEY: step 2 — duration ───────────────
    elif step == "createkey_duration":
        devices = _state[uid].get("devices", 1)
        try:
            td, dur_label = parse_duration(text)
        except ValueError:
            await msg.reply_text(
                "❌ ɪɴᴠᴀʟɪᴅ ᴅᴜʀᴀᴛɪᴏɴ.\n\nᴜsᴇ: 1d / 7d / 30d / 2h / 30m / lifetime",
                reply_markup=cancel_kb,
            )
            return
        _state.pop(uid, None)
        key = generate_key()
        d["keys"][key] = {
            "devices":     devices,
            "duration":    text.strip().lower(),
            "used_by":     [],
            "user_expiry": {},
            "created_by":  str(uid),
            "created_at":  now_pht().isoformat(),
        }
        uname = update.effective_user.username or str(uid)
        log_activity(d, f"Key created (btn): {key} | duration={text} | devices={devices} | by @{uname}")
        save(d)
        await msg.reply_text(msg_key_generated(key, dur_label, devices))
        await msg.reply_text(
            f"📋 ᴛᴀᴘ ᴛᴏ ᴄᴏᴘʏ:\n\n`{key}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔑 ᴄʀᴇᴀᴛᴇ ᴀɴᴏᴛʜᴇʀ", callback_data="adm_create")],
                [InlineKeyboardButton("🔙 Admin Panel",     callback_data="admin")],
            ]),
        )

    # ── BULK KEYS: step 1 — prefix ───────────────────
    elif step == "bulkkeys_prefix":
        if not text.replace("-", "").replace("_", "").isalnum():
            await msg.reply_text("❌ ᴘʀᴇꜰɪx ᴍᴜsᴛ ʙᴇ ʟᴇᴛᴛᴇʀs/ɴᴜᴍʙᴇʀs ᴏɴʟʏ.", reply_markup=cancel_kb)
            return
        _state[uid] = {"step": "bulkkeys_count", "prefix": text.strip().upper()}
        await msg.reply_text(
            f"✅ ᴘʀᴇꜰɪx: {text.strip().upper()}\n\n"
            "🔢 sᴛᴇᴘ 2/3 — ʜᴏᴡ ᴍᴀɴʏ ᴋᴇʏs? (1–50)",
            reply_markup=cancel_kb,
        )

    # ── BULK KEYS: step 2 — count ────────────────────
    elif step == "bulkkeys_count":
        try:
            count = int(text)
            if not 1 <= count <= 50:
                raise ValueError
        except ValueError:
            await msg.reply_text("❌ ᴇɴᴛᴇʀ ᴀ ɴᴜᴍʙᴇʀ ʙᴇᴛᴡᴇᴇɴ 1 ᴀɴᴅ 50.", reply_markup=cancel_kb)
            return
        _state[uid]["step"]  = "bulkkeys_duration"
        _state[uid]["count"] = count
        await msg.reply_text(
            f"✅ ᴄᴏᴜɴᴛ: {count}\n\n"
            "⏱️ sᴛᴇᴘ 3/3 — ᴇɴᴛᴇʀ ᴅᴜʀᴀᴛɪᴏɴ:\n\n"
            "┣ 1d / 7d / 30d\n"
            "┣ 2h / 30m\n"
            "┗ lifetime",
            reply_markup=cancel_kb,
        )

    # ── BULK KEYS: step 3 — duration ─────────────────
    elif step == "bulkkeys_duration":
        try:
            td, dur_label = parse_duration(text)
        except ValueError:
            await msg.reply_text(
                "❌ ɪɴᴠᴀʟɪᴅ ᴅᴜʀᴀᴛɪᴏɴ.\n\nᴜsᴇ: 1d / 7d / 30d / 2h / 30m / lifetime",
                reply_markup=cancel_kb,
            )
            return
        prefix   = _state[uid].get("prefix", "ZEIJIE")
        count    = _state[uid].get("count", 1)
        raw_dur  = text.strip().lower()
        _state.pop(uid, None)
        keys     = generate_bulk_keys(prefix, count)
        now_iso  = now_pht().isoformat()
        for k in keys:
            d["keys"][k] = {
                "devices":     1,
                "duration":    raw_dur,
                "used_by":     [],
                "user_expiry": {},
                "created_by":  str(uid),
                "created_at":  now_iso,
            }
        uname = update.effective_user.username or str(uid)
        log_activity(d, f"Bulk keys (btn): {count} | prefix={prefix} | dur={raw_dur} | by @{uname}")
        save(d)
        await msg.reply_text(msg_bulk_keys(keys, dur_label))
        keys_block = "\n".join(keys)
        await msg.reply_text(
            f"📋 ᴛᴀᴘ ᴛᴏ ᴄᴏᴘʏ:\n\n`{keys_block}`",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎉 ɢᴇɴᴇʀᴀᴛᴇ ᴍᴏʀᴇ", callback_data="adm_bulk_info")],
                [InlineKeyboardButton("🔙 Admin Panel",     callback_data="admin")],
            ]),
        )

    # ── REVOKE KEY ───────────────────────────────────
    elif step == "revokekey_input":
        _state.pop(uid, None)
        key = text.strip().upper()
        if key not in d["keys"]:
            await msg.reply_text("❌ ᴋᴇʏ ɴᴏᴛ ꜰᴏᴜɴᴅ.", reply_markup=cancel_kb)
            return
        del d["keys"][key]
        d["redeemed"] = {u: v for u, v in d["redeemed"].items() if v.get("key") != key}
        uname = update.effective_user.username or str(uid)
        log_activity(d, f"Key revoked (btn): {key} by @{uname}")
        save(d)
        await msg.reply_text(
            f"✅ ᴋᴇʏ ʀᴇᴠᴏᴋᴇᴅ!\n\n🔑 {key}",
            reply_markup=cancel_kb,
        )

    # ── BROADCAST ────────────────────────────────────
    elif step == "broadcast_msg":
        _state.pop(uid, None)
        members    = d.get("members", {})
        msg_text   = text
        sent       = 0
        failed     = 0
        status_msg = await msg.reply_text(f"📣 ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ᴛᴏ {len(members):,} ᴜsᴇʀs...")
        for m_id in members:
            try:
                await ctx.bot.send_message(chat_id=int(m_id), text=msg_broadcast_text(msg_text))
                sent += 1
            except Exception:
                failed += 1
            await asyncio.sleep(0.05)
        uname = update.effective_user.username or str(uid)
        log_activity(d, f"Broadcast (btn) by @{uname}: {msg_text[:60]} | sent={sent} failed={failed}")
        save(d)
        await status_msg.edit_text(
            "╔══════════════════════════════════╗\n"
            "║  ✅  ʙʀᴏᴀᴅᴄᴀsᴛ  ᴄᴏᴍᴘʟᴇᴛᴇ!  ✅   ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"┣ ✅ sᴇɴᴛ:   {sent:,}\n"
            f"┣ ❌ ꜰᴀɪʟᴇᴅ: {failed:,}\n"
            f"┗ 📊 ᴛᴏᴛᴀʟ:  {len(members):,}",
            reply_markup=cancel_kb,
        )

    # ── ADD ADMIN ────────────────────────────────────
    elif step == "addadmin_input":
        if not is_owner(uid):
            _state.pop(uid, None)
            return
        _state.pop(uid, None)
        target = text.strip()
        if target not in [str(a) for a in d["admins"]]:
            d["admins"].append(target)
            log_activity(d, f"Admin added (btn): {target} by owner")
            save(d)
        await msg.reply_text(
            f"✅ ᴀᴅᴍɪɴ ᴀᴅᴅᴇᴅ!\n\n👮 ID: {target}",
            reply_markup=cancel_kb,
        )

    # ── REMOVE ADMIN ─────────────────────────────────
    elif step == "removeadmin_input":
        if not is_owner(uid):
            _state.pop(uid, None)
            return
        _state.pop(uid, None)
        target = text.strip()
        if target in [str(a) for a in d["admins"]]:
            d["admins"] = [a for a in d["admins"] if str(a) != target]
            log_activity(d, f"Admin removed (btn): {target} by owner")
            save(d)
            await msg.reply_text(f"✅ ᴀᴅᴍɪɴ ʀᴇᴍᴏᴠᴇᴅ!\n\n👤 ID: {target}", reply_markup=cancel_kb)
        else:
            await msg.reply_text(f"❌ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ: {target}", reply_markup=cancel_kb)

    # ── CUSTOM DB NAME: step 1 — filename ────────────
    elif step == "customname_file":
        dbs = d.get("databases", {})
        if text not in dbs:
            listing = "\n".join(f"┣ {f}" for f in dbs) if dbs else "  ɴᴏɴᴇ"
            await msg.reply_text(
                f"❌ ꜰɪʟᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ: {text}\n\n📂 ᴀᴠᴀɪʟᴀʙʟᴇ:\n{listing}",
                reply_markup=cancel_kb,
            )
            return
        _state[uid] = {"step": "customname_newname", "fname": text}
        await msg.reply_text(
            f"✅ ꜰɪʟᴇ: {text}\n\n📩 sᴛᴇᴘ 2/2 — ᴛʏᴘᴇ ᴛʜᴇ ɴᴇᴡ ᴅɪsᴘʟᴀʏ ɴᴀᴍᴇ:",
            reply_markup=cancel_kb,
        )

    # ── CUSTOM DB NAME: step 2 — new name ────────────
    elif step == "customname_newname":
        fname     = _state[uid].get("fname")
        disp_name = text.strip()
        _state.pop(uid, None)
        if fname and fname in d.get("databases", {}):
            d["databases"][fname]["display"] = disp_name
            save(d)
            await msg.reply_text(
                "✅ ᴅɪsᴘʟᴀʏ ɴᴀᴍᴇ ᴜᴘᴅᴀᴛᴇᴅ!\n\n"
                f"┣ 🗂️ ꜰɪʟᴇ: {fname}\n"
                f"┗ 🏷️ ɴᴀᴍᴇ: {disp_name}",
                reply_markup=cancel_kb,
            )
        else:
            await msg.reply_text("❌ ꜰɪʟᴇ ɴᴏ ʟᴏɴɢᴇʀ ꜰᴏᴜɴᴅ.", reply_markup=cancel_kb)

    # ── REMOVE DB ────────────────────────────────────
    elif step == "removedb_input":
        _state.pop(uid, None)
        fname = text.strip()
        dbs   = d.get("databases", {})
        if fname not in dbs:
            await msg.reply_text(f"❌ ᴅᴀᴛᴀʙᴀsᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ: {fname}", reply_markup=cancel_kb)
            return
        del dbs[fname]
        uname = update.effective_user.username or str(uid)
        log_activity(d, f"DB removed (btn): {fname} by @{uname}")
        save(d)
        await msg.reply_text(
            f"✅ ᴅᴀᴛᴀʙᴀsᴇ ʀᴇᴍᴏᴠᴇᴅ!\n\n🗂️ {fname}",
            reply_markup=cancel_kb,
        )

# ══════════════════════════════════════════════════════
#  ADMIN: /broadcast
# ══════════════════════════════════════════════════════
async def broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.")
        return
    if not ctx.args:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║     📣  ʙʀᴏᴀᴅᴄᴀsᴛ  📣           ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📌 ᴜsᴀɢᴇ: /broadcast <ᴍᴇssᴀɢᴇ>\n\n"
            "📋 ᴇxᴀᴍᴘʟᴇ:\n"
            "   /broadcast ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴛᴏɴɪɢʜᴛ ᴀᴛ 10 ᴘᴍ."
        )
        return

    msg_text = " ".join(ctx.args)
    members  = d.get("members", {})
    sent     = 0
    failed   = 0

    status_msg = await update.message.reply_text(
        f"📣 ʙʀᴏᴀᴅᴄᴀsᴛɪɴɢ ᴛᴏ {len(members):,} ᴜsᴇʀs..."
    )

    for m_id in members:
        try:
            await ctx.bot.send_message(chat_id=int(m_id), text=msg_broadcast_text(msg_text))
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    uname = update.effective_user.username or str(uid)
    log_activity(d, f"Broadcast by @{uname}: {msg_text[:60]} | sent={sent} failed={failed}")
    save(d)

    await status_msg.edit_text(
        "╔══════════════════════════════════╗\n"
        "║  ✅  ʙʀᴏᴀᴅᴄᴀsᴛ  ᴄᴏᴍᴘʟᴇᴛᴇ!  ✅   ║\n"
        "╚══════════════════════════════════╝\n\n"
        f"┣ ✅ sᴇɴᴛ:   {sent:,}\n"
        f"┣ ❌ ꜰᴀɪʟᴇᴅ: {failed:,}\n"
        f"┗ 📊 ᴛᴏᴛᴀʟ:  {len(members):,}"
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /customname
# ══════════════════════════════════════════════════════
async def customname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.")
        return

    dbs = d.get("databases", {})
    if len(ctx.args) < 2:
        listing = "\n".join(f"┣ {f}" for f in dbs) if dbs else "  ɴᴏɴᴇ"
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║    🏷️  ᴄᴜsᴛᴏᴍ  ᴅʙ  ɴᴀᴍᴇ  🏷️    ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📌 ᴜsᴀɢᴇ: /customname <ꜰɪʟᴇ> <ɴᴀᴍᴇ>\n\n"
            f"📂 ᴀᴠᴀɪʟᴀʙʟᴇ:\n{listing}"
        )
        return

    fname     = ctx.args[0].strip()
    disp_name = " ".join(ctx.args[1:]).strip()

    if fname not in dbs:
        listing = "\n".join(f"┣ {f}" for f in dbs) if dbs else "  ɴᴏɴᴇ"
        await update.message.reply_text(
            f"❌ {fname} ɴᴏᴛ ꜰᴏᴜɴᴅ.\n\n📂 ᴀᴠᴀɪʟᴀʙʟᴇ:\n{listing}"
        )
        return

    dbs[fname]["display"] = disp_name
    save(d)
    await update.message.reply_text(
        "✅ ᴅɪsᴘʟᴀʏ ɴᴀᴍᴇ ᴜᴘᴅᴀᴛᴇᴅ!\n\n"
        f"┣ 🗂️ ꜰɪʟᴇ: {fname}\n"
        f"┗ 🏷️ ɴᴀᴍᴇ: {disp_name}"
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /maintenance
# ══════════════════════════════════════════════════════
async def maintenance_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global MAINTENANCE
    uid = update.effective_user.id
    d   = load()
    if not is_admin(uid, d):
        await update.message.reply_text("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.")
        return
    MAINTENANCE = not MAINTENANCE
    if MAINTENANCE:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║       🔧  MAINTENANCE  ON  🔧    ║\n"
            "╚══════════════════════════════════╝\n\n"
            "⚠️ ᴜsᴇʀs ᴡɪʟʟ sᴇᴇ ᴀ ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴇssᴀɢᴇ."
        )
    else:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║      ✅  MAINTENANCE  OFF  ✅    ║\n"
            "╚══════════════════════════════════╝\n\n"
            "✨ ᴜsᴇʀs ᴄᴀɴ ᴜsᴇ ᴛʜᴇ ʙᴏᴛ ɴᴏʀᴍᴀʟʟʏ."
        )

# ══════════════════════════════════════════════════════
#  OWNER: /addadmin  /removeadmin
# ══════════════════════════════════════════════════════
async def addadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("👑 ᴏᴡɴᴇʀ ᴏɴʟʏ.")
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("📌 ᴜsᴀɢᴇ: /addadmin <ᴜsᴇʀ_ɪᴅ>")
        return
    target = str(ctx.args[0])
    if target not in [str(a) for a in d["admins"]]:
        d["admins"].append(target)
        log_activity(d, f"Admin added: {target} by owner")
        save(d)
    await update.message.reply_text(
        f"✅ ᴀᴅᴍɪɴ ᴀᴅᴅᴇᴅ!\n\n👮 ID: {target}"
    )

async def removeadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("👑 ᴏᴡɴᴇʀ ᴏɴʟʏ.")
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("📌 ᴜsᴀɢᴇ: /removeadmin <ᴜsᴇʀ_ɪᴅ>")
        return
    target = str(ctx.args[0])
    if target in [str(a) for a in d["admins"]]:
        d["admins"] = [a for a in d["admins"] if str(a) != target]
        log_activity(d, f"Admin removed: {target} by owner")
        save(d)
        await update.message.reply_text(f"✅ ᴀᴅᴍɪɴ ʀᴇᴍᴏᴠᴇᴅ!\n\n👤 ID: {target}")
    else:
        await update.message.reply_text(f"❌ ɴᴏᴛ ᴀɴ ᴀᴅᴍɪɴ: {target}")

# ══════════════════════════════════════════════════════
#  ADMIN: /deletedb  — opens button UI
# ══════════════════════════════════════════════════════
async def deletedb(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    uid = update.effective_user.id
    d   = load()
    if not is_admin(uid, d):
        await update.message.reply_text("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.")
        return
    dbs = d.get("databases", {})
    if not dbs:
        await update.message.reply_text(
            "╔══════════════════════════════════╗\n"
            "║       🗑  DELETE  DATABASE  🗑   ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📭 ɴᴏ ᴅᴀᴛᴀʙᴀsᴇs ꜰᴏᴜɴᴅ.\n\n"
            "📤 ᴜsᴇ /adddb ᴛᴏ ᴜᴘʟᴏᴀᴅ ᴏɴᴇ."
        )
        return
    total = sum(len(v.get("lines", [])) for v in dbs.values())
    await update.message.reply_text(
        "╔══════════════════════════════════╗\n"
        "║       🗑  DELETE  DATABASE  🗑   ║\n"
        "╚══════════════════════════════════╝\n\n"
        f"📂 ᴅᴀᴛᴀʙᴀsᴇs: {len(dbs)}\n"
        f"📊 ᴛᴏᴛᴀʟ ʟɪɴᴇs: {total:,}\n\n"
        "👇 sᴇʟᴇᴄᴛ ᴀ ᴅᴀᴛᴀʙᴀsᴇ ᴛᴏ ᴅᴇʟᴇᴛᴇ:",
        reply_markup=kb_deletedb(d),
    )

# ══════════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════════
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global MAINTENANCE
    q    = update.callback_query
    d    = load()
    uid  = q.from_user.id
    data = q.data
    # Update member last_seen in memory only (no disk write on every tap)
    track(uid, q.from_user.username, q.from_user.first_name, d)
    await q.answer()

    # Clear any pending conversation state on navigation
    _state.pop(uid, None)

    if MAINTENANCE and not is_owner(uid):
        await q.edit_message_text(MAINTENANCE_MSG)
        return

    if data == "home":
        await q.edit_message_text(
            build_welcome(q.from_user.first_name, q.from_user.username, uid, d),
            reply_markup=kb_main(uid, d),
        )

    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        await q.edit_message_text(build_admin_overview(d), reply_markup=kb_admin())

    elif data == "adm_overview":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        await q.edit_message_text(build_admin_overview(d), reply_markup=kb_admin())

    elif data == "adm_toggle_maintenance":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        MAINTENANCE = not MAINTENANCE
        state = "ON 🔧" if MAINTENANCE else "OFF ✅"
        await q.answer(f"ᴍᴀɪɴᴛᴇɴᴀɴᴄᴇ ᴍᴏᴅᴇ {state}", show_alert=True)
        await q.edit_message_text(build_admin_overview(d), reply_markup=kb_admin())

    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        _state[uid] = {"step": "createkey_devices"}
        await q.edit_message_text(
            "╔══════════════════════════════════╗\n"
            "║     🔑  ᴄʀᴇᴀᴛᴇ  ᴀ  ᴋᴇʏ  🔑      ║\n"
            "╚══════════════════════════════════╝\n\n"
            "👥 sᴛᴇᴘ 1/2 — ʜᴏᴡ ᴍᴀɴʏ ᴜsᴇʀs ᴄᴀɴ ᴜsᴇ ᴛʜɪs ᴋᴇʏ?\n\n"
            "📩 ᴛʏᴘᴇ ᴀ ɴᴜᴍʙᴇʀ (ᴇ.ɢ. 1, 2, 3...)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="admin")],
            ]),
        )

    elif data == "adm_bulk_info":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        _state[uid] = {"step": "bulkkeys_prefix"}
        await q.edit_message_text(
            "╔══════════════════════════════════╗\n"
            "║    🎉  ʙᴜʟᴋ  ᴋᴇʏ  ɢᴇɴ  🎉       ║\n"
            "╚══════════════════════════════════╝\n\n"
            "🏷️ sᴛᴇᴘ 1/3 — ᴇɴᴛᴇʀ ᴋᴇʏ ᴘʀᴇꜰɪx:\n\n"
            "📩 ᴇ.ɢ. ZEIJIE, VIP, PREMIUM",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="admin")],
            ]),
        )

    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        keys = d.get("keys", {})
        if not keys:
            txt = "📭 ɴᴏ ᴋᴇʏs ɢᴇɴᴇʀᴀᴛᴇᴅ ʏᴇᴛ."
        else:
            lines = [
                "╔══════════════════════════════════╗\n"
                "║      🗝️  ᴋᴇʏs  ʟᴏɢ  🗝️          ║\n"
                "╚══════════════════════════════════╝\n"
            ]
            for k, v in list(keys.items())[-20:]:
                used    = len(v.get("used_by", []))
                devices = v.get("devices", 1)
                dur     = v.get("duration", "?")
                lines.append(f"┣ 🔑 {k}\n  👥 {used}/{devices} ᴜsᴇᴅ | ⏱️ {dur}")
            txt = "\n\n".join(lines)
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_members":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        members = d.get("members", {})
        if not members:
            txt = "📭 ɴᴏ ᴍᴇᴍʙᴇʀs ʏᴇᴛ."
        else:
            lines = [
                "╔══════════════════════════════════╗\n"
                "║     👥  ᴍᴇᴍʙᴇʀs  ʟᴏɢ  👥        ║\n"
                "╚══════════════════════════════════╝\n"
            ]
            for m_id, info in list(members.items())[-20:]:
                uname = info.get("username") or info.get("first_name") or m_id
                lines.append(f"┣ 👤 @{uname} ({m_id})")
            txt = "\n".join(lines)
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_active":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})
        active   = [(uid2, rd) for uid2, rd in redeemed.items()
                    if has_access(int(uid2), d) and not is_admin(int(uid2), d)]
        if not active:
            txt = "📭 ɴᴏ ᴀᴄᴛɪᴠᴇ ᴜsᴇʀs."
        else:
            lines = [
                "╔══════════════════════════════════╗\n"
                f"║  🟢  ᴀᴄᴛɪᴠᴇ ᴜsᴇʀs ({len(active)})  🟢    ║\n"
                "╚══════════════════════════════════╝\n"
            ]
            for uid2, rd in active:
                info  = members.get(uid2, {})
                uname = info.get("username") or info.get("first_name") or uid2
                exp   = expiry_display(rd.get("expires"))
                lines.append(f"┣ 👤 @{uname}\n  ⏳ {exp}")
            txt = "\n\n".join(lines)
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_dbstats":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        dbs = d.get("databases", {})
        if not dbs:
            txt = (
                "╔══════════════════════════════════╗\n"
                "║     💾  ᴅᴀᴛᴀʙᴀsᴇ  sᴛᴀᴛs  💾     ║\n"
                "╚══════════════════════════════════╝\n\n"
                "📭 ɴᴏ ᴅᴀᴛᴀʙᴀsᴇs ᴜᴘʟᴏᴀᴅᴇᴅ.\n\n"
                "📤 ᴜsᴇ /adddb ᴛᴏ ᴜᴘʟᴏᴀᴅ ᴀ ᴅᴀᴛᴀʙᴀsᴇ ꜰɪʟᴇ."
            )
        else:
            total = sum(len(v.get("lines", [])) for v in dbs.values())
            lines = [
                "╔══════════════════════════════════╗\n"
                "║     💾  ᴅᴀᴛᴀʙᴀsᴇ  sᴛᴀᴛs  💾     ║\n"
                "╚══════════════════════════════════╝\n"
            ]
            for fname, info in dbs.items():
                cnt  = len(info.get("lines", []))
                disp = info.get("display", Path(fname).stem)
                lines.append(f"┣ 📂 {disp}\n  ꜰɪʟᴇ: {fname}\n  ʟɪɴᴇs: {cnt:,}")
            lines.append(f"\n📊 ᴛᴏᴛᴀʟ: {total:,} ʟɪɴᴇs")
            txt = "\n\n".join(lines)
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_activity":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        log = d.get("activity_log", [])
        if not log:
            txt = "📭 ɴᴏ ᴀᴄᴛɪᴠɪᴛʏ ʏᴇᴛ."
        else:
            lines = [
                "╔══════════════════════════════════╗\n"
                "║     📜  ᴀᴄᴛɪᴠɪᴛʏ  ʟᴏɢ  📜       ║\n"
                "╚══════════════════════════════════╝\n"
            ]
            for e in log[-15:]:
                lines.append(f"┣ 🕐 [{e['time']}]\n  {e['event']}")
            txt = "\n\n".join(lines)
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        admins = d.get("admins", [])
        lines  = [
            "╔══════════════════════════════════╗\n"
            "║     👮  ᴀᴅᴍɪɴs  ʟɪsᴛ  👮        ║\n"
            "╚══════════════════════════════════╝\n",
            f"┣ 👑 {OWNER_ID} (ᴏᴡɴᴇʀ)"
        ] + [f"┣ 👮 {a}" for a in admins]
        await q.edit_message_text("\n".join(lines), reply_markup=kb_back("admin"))

    elif data == "adm_expired":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})
        expired  = [(uid2, rd) for uid2, rd in redeemed.items()
                    if is_expired(rd) and not is_admin(int(uid2), d)]
        if not expired:
            txt = "📭 ɴᴏ ᴇxᴘɪʀᴇᴅ ᴜsᴇʀs."
        else:
            lines = [
                "╔══════════════════════════════════╗\n"
                f"║  🔴  ᴇxᴘɪʀᴇᴅ ᴜsᴇʀs ({len(expired)})  🔴   ║\n"
                "╚══════════════════════════════════╝\n"
            ]
            for uid2, rd in expired:
                info  = members.get(uid2, {})
                uname = info.get("username") or info.get("first_name") or uid2
                exp   = expiry_display(rd.get("expires"))
                lines.append(f"┣ 👤 @{uname}\n  ⏳ {exp}")
            txt = "\n\n".join(lines)
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_broadcast":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        members = d.get("members", {})
        _state[uid] = {"step": "broadcast_msg"}
        await q.edit_message_text(
            "╔══════════════════════════════════╗\n"
            "║       📣  ʙʀᴏᴀᴅᴄᴀsᴛ  📣         ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"👥 ʀᴇᴄɪᴘɪᴇɴᴛs: {len(members):,}\n\n"
            "📩 ᴛʏᴘᴇ ʏᴏᴜʀ ᴍᴇssᴀɢᴇ ɴᴏᴡ:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="admin")],
            ]),
        )

    elif data == "adddb_menu":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        await q.edit_message_text(
            "╔══════════════════════════════════╗\n"
            "║   📂  ᴜᴘʟᴏᴀᴅ  ᴅᴀᴛᴀʙᴀsᴇ  📂     ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📤 sᴇɴᴅ ᴍᴇ ᴛʜᴇ ᴅᴀᴛᴀʙᴀsᴇ ꜰɪʟᴇ ɴᴏᴡ.\n\n"
            "📋 sᴜᴘᴘᴏʀᴛᴇᴅ: .txt / .csv / .log / .combo / .list / .dat\n"
            f"💾 ᴍᴀx sɪᴢᴇ: {MAX_FILE_SIZE_MB} MB\n\n"
            "💡 ᴏʀ ᴜsᴇ ᴛʜᴇ ᴄᴏᴍᴍᴀɴᴅ:\n"
            "   /adddb [ᴏᴘᴛɪᴏɴᴀʟ_ɴᴀᴍᴇ]\n"
            "   ᴛʜᴇɴ sᴇɴᴅ ᴛʜᴇ ꜰɪʟᴇ.",
            reply_markup=kb_back("admin"),
        )
        # Set pending upload so the next file sent is captured
        _pending_db_upload[uid] = None

    elif data == "adm_reload_db":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        # Show animated reloading steps
        steps = [
            "🔄 10%  ᴄᴏɴɴᴇᴄᴛɪɴɢ ᴛᴏ sᴜᴘᴀʙᴀsᴇ...",
            "🔄 30%  ꜰᴇᴛᴄʜɪɴɢ ᴅᴀᴛᴀʙᴀsᴇ ʟɪsᴛ...",
            "🔄 60%  ʟᴏᴀᴅɪɴɢ ʟɪɴᴇs...",
            "🔄 90%  ʀᴇʙᴜɪʟᴅɪɴɢ ᴄᴀᴄʜᴇ...",
        ]
        reload_msg = await q.message.reply_text(steps[0])
        for step in steps[1:]:
            await asyncio.sleep(0.6)
            try:
                await reload_msg.edit_text(step)
            except Exception:
                pass
        try:
            fresh = load(force=True)
            db_count   = len(fresh.get("databases", {}))
            line_count = sum(len(v.get("lines", [])) for v in fresh.get("databases", {}).values())
            uname = q.from_user.username or str(uid)
            log_activity(fresh, f"DB reloaded from Supabase by @{uname}")
            try:
                _meta_save({k: v for k, v in fresh.items() if k != "databases"})
            except Exception:
                pass
            # Build DB list summary
            dbs = fresh.get("databases", {})
            db_lines_txt = ""
            for fname, info in dbs.items():
                disp = info.get("display") or Path(fname).stem
                cnt  = len(info.get("lines", []))
                db_lines_txt += f"┣ 📂 {disp.upper()}  •  {cnt:,} ʟɪɴᴇs\n"
            if not db_lines_txt:
                db_lines_txt = "┗ 📭 ɴᴏ ᴅᴀᴛᴀʙᴀsᴇs ꜰᴏᴜɴᴅ.\n"
            await reload_msg.edit_text(
                "╔══════════════════════════════════╗\n"
                "║   ✅  ʀᴇʟᴏᴀᴅ  sᴜᴄᴄᴇss!  ✅     ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"📂 ᴅʙ ꜰɪʟᴇs: {db_count}\n"
                f"📜 ᴛᴏᴛᴀʟ ʟɪɴᴇs: {line_count:,}\n\n"
                f"{db_lines_txt}\n"
                "✅ ᴄᴀᴄʜᴇ ʀᴇꜰʀᴇsʜᴇᴅ ꜰʀᴏᴍ sᴜᴘᴀʙᴀsᴇ!",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("💾 ᴠɪᴇᴡ ᴅᴀᴛᴀʙᴀsᴇ", callback_data="db")],
                    [InlineKeyboardButton("🔙 ʙᴀᴄᴋ ᴛᴏ ᴀᴅᴍɪɴ", callback_data="admin")],
                ]),
            )
        except Exception as e:
            await reload_msg.edit_text(
                "╔══════════════════════════════════╗\n"
                "║   ❌  ʀᴇʟᴏᴀᴅ  ꜰᴀɪʟᴇᴅ!  ❌      ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"⚠️ ᴇʀʀᴏʀ: {e}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔙 ʙᴀᴄᴋ ᴛᴏ ᴀᴅᴍɪɴ", callback_data="admin")],
                ]),
            )

    elif data == "adm_revokekey":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        _state[uid] = {"step": "revokekey_input"}
        await q.edit_message_text(
            "╔══════════════════════════════════╗\n"
            "║     🗑️  ʀᴇᴠᴏᴋᴇ  ᴀ  ᴋᴇʏ  🗑️     ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📩 ᴛʏᴘᴇ ᴛʜᴇ ᴋᴇʏ ᴛᴏ ʀᴇᴠᴏᴋᴇ:\n\n"
            "ᴇ.ɢ. ZEIJIE-PREMIUM-1234",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="admin")],
            ]),
        )

    elif data == "adm_addadmin":
        if not is_owner(uid):
            await q.answer("👑 ᴏᴡɴᴇʀ ᴏɴʟʏ.", show_alert=True)
            return
        _state[uid] = {"step": "addadmin_input"}
        await q.edit_message_text(
            "╔══════════════════════════════════╗\n"
            "║      👮  ᴀᴅᴅ  ᴀᴅᴍɪɴ  👮         ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📩 ᴛʏᴘᴇ ᴛʜᴇ ᴜsᴇʀ ɪᴅ ᴛᴏ ᴀᴅᴅ ᴀs ᴀᴅᴍɪɴ:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="admin")],
            ]),
        )

    elif data == "adm_removeadmin":
        if not is_owner(uid):
            await q.answer("👑 ᴏᴡɴᴇʀ ᴏɴʟʏ.", show_alert=True)
            return
        admins = d.get("admins", [])
        if not admins:
            await q.answer("📭 ɴᴏ ᴀᴅᴍɪɴs ᴛᴏ ʀᴇᴍᴏᴠᴇ.", show_alert=True)
            return
        _state[uid] = {"step": "removeadmin_input"}
        admin_list = "\n".join(f"┣ 👮 {a}" for a in admins)
        await q.edit_message_text(
            "╔══════════════════════════════════╗\n"
            "║    👮  ʀᴇᴍᴏᴠᴇ  ᴀᴅᴍɪɴ  👮       ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"ᴄᴜʀʀᴇɴᴛ ᴀᴅᴍɪɴs:\n{admin_list}\n\n"
            "📩 ᴛʏᴘᴇ ᴛʜᴇ ᴜsᴇʀ ɪᴅ ᴛᴏ ʀᴇᴍᴏᴠᴇ:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="admin")],
            ]),
        )

    elif data == "adm_customname":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        dbs = d.get("databases", {})
        if not dbs:
            await q.answer("📭 ɴᴏ ᴅᴀᴛᴀʙᴀsᴇs ꜰᴏᴜɴᴅ.", show_alert=True)
            return
        listing = "\n".join(f"┣ {f}" for f in dbs)
        _state[uid] = {"step": "customname_file"}
        await q.edit_message_text(
            "╔══════════════════════════════════╗\n"
            "║    🏷️  ᴄᴜsᴛᴏᴍ  ᴅʙ  ɴᴀᴍᴇ  🏷️    ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"📂 ᴀᴠᴀɪʟᴀʙʟᴇ:\n{listing}\n\n"
            "📩 sᴛᴇᴘ 1/2 — ᴛʏᴘᴇ ᴛʜᴇ ꜰɪʟᴇɴᴀᴍᴇ ᴇxᴀᴄᴛʟʏ:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="admin")],
            ]),
        )

    elif data == "adm_removedb_btn":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        dbs = d.get("databases", {})
        if not dbs:
            await q.answer("📭 ɴᴏ ᴅᴀᴛᴀʙᴀsᴇs ꜰᴏᴜɴᴅ.", show_alert=True)
            return
        listing = "\n".join(f"┣ {f}" for f in dbs)
        _state[uid] = {"step": "removedb_input"}
        await q.edit_message_text(
            "╔══════════════════════════════════╗\n"
            "║    🗑️  ʀᴇᴍᴏᴠᴇ  ᴅᴀᴛᴀʙᴀsᴇ  🗑️    ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"📂 ᴀᴠᴀɪʟᴀʙʟᴇ:\n{listing}\n\n"
            "📩 ᴛʏᴘᴇ ᴛʜᴇ ꜰɪʟᴇɴᴀᴍᴇ ᴛᴏ ʀᴇᴍᴏᴠᴇ:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="admin")],
            ]),
        )

    elif data == "deletedb_menu":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        dbs = d.get("databases", {})
        if not dbs:
            await q.edit_message_text(
                "╔══════════════════════════════════╗\n"
                "║       🗑  DELETE  DATABASE  🗑   ║\n"
                "╚══════════════════════════════════╝\n\n"
                "📭 ɴᴏ ᴅᴀᴛᴀʙᴀsᴇs ꜰᴏᴜɴᴅ.\n\n"
                "📤 ᴜsᴇ /adddb ᴛᴏ ᴜᴘʟᴏᴀᴅ ᴏɴᴇ.",
                reply_markup=kb_back("admin"),
            )
            return
        total = sum(len(v.get("lines", [])) for v in dbs.values())
        await q.edit_message_text(
            "╔══════════════════════════════════╗\n"
            "║       🗑  DELETE  DATABASE  🗑   ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"📂 ᴅᴀᴛᴀʙᴀsᴇs: {len(dbs)}\n"
            f"📊 ᴛᴏᴛᴀʟ ʟɪɴᴇs: {total:,}\n\n"
            "👇 sᴇʟᴇᴄᴛ ᴀ ᴅᴀᴛᴀʙᴀsᴇ ᴛᴏ ᴅᴇʟᴇᴛᴇ:",
            reply_markup=kb_deletedb(d),
        )

    elif data.startswith("deletedb_file:"):
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        fname = data.split(":", 1)[1]
        dbs   = d.get("databases", {})
        if fname not in dbs:
            await q.answer("❌ ᴅᴀᴛᴀʙᴀsᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ.", show_alert=True)
            return
        lines_count = len(dbs[fname].get("lines", []))
        disp        = dbs[fname].get("display", Path(fname).stem)
        uname       = q.from_user.username or str(uid)
        del d["databases"][fname]
        log_activity(d, f"deletedb {fname} ({lines_count:,} lines) by @{uname}")
        save(d)
        remaining_dbs = d.get("databases", {})
        if remaining_dbs:
            remaining_total = sum(len(v.get("lines", [])) for v in remaining_dbs.values())
            await q.edit_message_text(
                "╔══════════════════════════════════╗\n"
                "║       🗑  DELETE  DATABASE  🗑   ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"✅ ᴅᴇʟᴇᴛᴇᴅ: {disp.upper()}  ({lines_count:,} ʟɪɴᴇs)\n\n"
                f"📂 ʀᴇᴍᴀɪɴɪɴɢ: {len(remaining_dbs)}\n"
                f"📊 ʟɪɴᴇs ʟᴇꜰᴛ: {remaining_total:,}\n\n"
                "👇 sᴇʟᴇᴄᴛ ᴀɴᴏᴛʜᴇʀ ᴛᴏ ᴅᴇʟᴇᴛᴇ:",
                reply_markup=kb_deletedb(d),
            )
        else:
            await q.edit_message_text(
                "╔══════════════════════════════════╗\n"
                "║     ✅  DB  DELETED  ✅          ║\n"
                "╚══════════════════════════════════╝\n\n"
                f"🗑 ᴅᴇʟᴇᴛᴇᴅ: {disp.upper()}\n"
                f"📊 ʟɪɴᴇs: {lines_count:,} ʀᴇᴍᴏᴠᴇᴅ\n\n"
                "📭 ɴᴏ ᴍᴏʀᴇ ᴅᴀᴛᴀʙᴀsᴇs.\n"
                "🚀 ʙᴏᴛ sʜᴏᴜʟᴅ ʀᴜɴ ꜰᴀsᴛᴇʀ ɴᴏᴡ!",
                reply_markup=kb_back("admin"),
            )

    elif data == "deletedb_all":
        if not is_admin(uid, d):
            await q.answer("👮 ᴀᴅᴍɪɴs ᴏɴʟʏ.", show_alert=True)
            return
        dbs   = d.get("databases", {})
        count = len(dbs)
        total = sum(len(v.get("lines", [])) for v in dbs.values())
        uname = q.from_user.username or str(uid)
        d["databases"] = {}
        log_activity(d, f"deletedb ALL — {count} DBs, {total:,} lines removed by @{uname}")
        save(d)
        await q.edit_message_text(
            "╔══════════════════════════════════╗\n"
            "║     ✅  ALL  DBs  DELETED  ✅    ║\n"
            "╚══════════════════════════════════╝\n\n"
            f"🗑 ᴅᴇʟᴇᴛᴇᴅ: {count} ᴅᴀᴛᴀʙᴀsᴇ(s)\n"
            f"📊 ʀᴇᴍᴏᴠᴇᴅ: {total:,} ʟɪɴᴇs\n\n"
            "🚀 ʙᴏᴛ sʜᴏᴜʟᴅ ʀᴜɴ ꜰᴀsᴛᴇʀ ɴᴏᴡ!",
            reply_markup=kb_back("admin"),
        )

    elif data == "db":
        d = load(force=True)
        files = get_db_files(d)
        if not files:
            try:
                await q.edit_message_text(
                    "╔══════════════════════════════════╗\n"
                    "║     💾  ᴅᴀᴛᴀʙᴀsᴇ  ᴍᴇɴᴜ  💾      ║\n"
                    "╚══════════════════════════════════╝\n\n"
                    "📭 ᴅᴀᴛᴀʙᴀsᴇ ɪs ᴇᴍᴘᴛʏ.\n\n"
                    "👮 ᴀᴅᴍɪɴ: ᴜsᴇ /adddb ᴛᴏ ᴜᴘʟᴏᴀᴅ ᴀ ᴅᴀᴛᴀʙᴀsᴇ ꜰɪʟᴇ.",
                    reply_markup=kb_back(),
                )
            except Exception:
                await q.message.reply_text(
                    "╔══════════════════════════════════╗\n"
                    "║     💾  ᴅᴀᴛᴀʙᴀsᴇ  ᴍᴇɴᴜ  💾      ║\n"
                    "╚══════════════════════════════════╝\n\n"
                    "📭 ᴅᴀᴛᴀʙᴀsᴇ ɪs ᴇᴍᴘᴛʏ.\n\n"
                    "👮 ᴀᴅᴍɪɴ: ᴜsᴇ /adddb ᴛᴏ ᴜᴘʟᴏᴀᴅ ᴀ ᴅᴀᴛᴀʙᴀsᴇ ꜰɪʟᴇ.",
                    reply_markup=kb_back(),
                )
            return
        if not has_access(uid, d):
            try:
                await q.edit_message_text(
                    "╔══════════════════════════════════╗\n"
                    "║     🚫  ᴀᴄᴄᴇss  ᴅᴇɴɪᴇᴅ  🚫      ║\n"
                    "╚══════════════════════════════════╝\n\n"
                    "🔑 ʏᴏᴜ ɴᴇᴇᴅ ᴀ ᴠɪᴘ ᴋᴇʏ ᴛᴏ ᴀᴄᴄᴇss ᴛʜᴇ ᴅᴀᴛᴀʙᴀsᴇ.\n\n"
                    f"📞 ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}",
                    reply_markup=kb_contact(),
                )
            except Exception:
                await q.message.reply_text(
                    "╔══════════════════════════════════╗\n"
                    "║     🚫  ᴀᴄᴄᴇss  ᴅᴇɴɪᴇᴅ  🚫      ║\n"
                    "╚══════════════════════════════════╝\n\n"
                    "🔑 ʏᴏᴜ ɴᴇᴇᴅ ᴀ ᴠɪᴘ ᴋᴇʏ ᴛᴏ ᴀᴄᴄᴇss ᴛʜᴇ ᴅᴀᴛᴀʙᴀsᴇ.\n\n"
                    f"📞 ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}",
                    reply_markup=kb_contact(),
                )
            return
        try:
            await q.edit_message_text(
                msg_db_selection(files, d),
                reply_markup=kb_db_files(files, d),
            )
        except Exception:
            await q.message.reply_text(
                msg_db_selection(files, d),
                reply_markup=kb_db_files(files, d),
            )

    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

        if not has_access(uid, d):
            await q.answer("🚫 ᴀᴄᴄᴇss ᴅᴇɴɪᴇᴅ. ᴄᴏɴᴛᴀᴄᴛ ᴀᴅᴍɪɴ.", show_alert=True)
            return

        if fname not in d.get("databases", {}):
            await q.answer("❌ ᴅᴀᴛᴀʙᴀsᴇ ɴᴏᴛ ꜰᴏᴜɴᴅ.", show_alert=True)
            return

        total = count_db_lines(fname, d)
        if total == 0:
            await q.answer("📭 ᴛʜɪs ᴅᴀᴛᴀʙᴀsᴇ ɪs ᴇᴍᴘᴛʏ. ᴄʜᴏᴏsᴇ ᴀɴᴏᴛʜᴇʀ.", show_alert=True)
            return

        db_steps = [
            "🔄 10%  ᴄᴏɴɴᴇᴄᴛɪɴɢ ᴛᴏ ᴅᴀᴛᴀʙᴀsᴇ...",
            "🔄 25%  ᴀᴄᴄᴇssɪɴɢ sᴇᴄᴜʀᴇ ɴᴏᴅᴇs...",
            "🔄 50%  ꜰᴇᴛᴄʜɪɴɢ ʀᴇᴄᴏʀᴅs...",
            "🔄 75%  ᴘʀᴏᴄᴇssɪɴɢ ᴅᴀᴛᴀ...",
            "🔄 95%  ᴘʀᴇᴘᴀʀɪɴɢ ʏᴏᴜʀ ꜰɪʟᴇ...",
            "✅ 100% ᴅᴏɴᴇ! sᴇɴᴅɪɴɢ ꜰɪʟᴇ...",
        ]
        anim = await q.message.reply_text(db_steps[0])
        for step in db_steps[1:]:
            await asyncio.sleep(0.6)
            try:
                await anim.edit_text(step)
            except Exception:
                pass
        await asyncio.sleep(0.3)
        try:
            await anim.delete()
        except Exception:
            pass

        lines_to_send          = min(LINES_PER_USE, total)
        disp                   = get_display_name(fname, d)
        raw_content, remaining = consume_db_lines(fname, lines_to_send, d)
        content                = file_header(disp, lines_to_send) + raw_content
        out_name               = output_filename(disp)
        buf                    = io.BytesIO(content.encode("utf-8"))
        buf.name               = out_name

        uname = q.from_user.username or str(uid)
        log_activity(d, f"DB downloaded: {disp} | {lines_to_send} lines | by @{uname}")
        save(d)

        sent_msg = await q.message.reply_document(
            document=buf,
            filename=out_name,
            caption=msg_file_caption(disp, lines_to_send, remaining),
        )
        asyncio.create_task(_auto_delete(300, sent_msg))

    elif data == "redeem_info":
        _state[uid] = {"step": "redeem_key"}
        await q.edit_message_text(
            "╔══════════════════════════════════╗\n"
            "║     🔑  ʀᴇᴅᴇᴇᴍ  ᴀ  ᴋᴇʏ  🔑      ║\n"
            "╚══════════════════════════════════╝\n\n"
            "📩 ᴛʏᴘᴇ ʏᴏᴜʀ ᴋᴇʏ ɴᴏᴡ:\n\n"
            f"💬 ɴᴏ ᴋᴇʏ ʏᴇᴛ? ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📞 ɢᴇᴛ ᴀ ᴋᴇʏ",
                                      url=f"https://t.me/{CONTACT_ADMIN.lstrip('@')}")],
                [InlineKeyboardButton("❌ ᴄᴀɴᴄᴇʟ", callback_data="home")],
            ]),
        )

    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = (
                "╔══════════════════════════════════╗\n"
                "║    👮  ᴀᴅᴍɪɴ  ᴀᴄᴄᴏᴜɴᴛ  👮      ║\n"
                "╚══════════════════════════════════╝\n\n"
                "✅ ꜰᴜʟʟ ᴀᴄᴄᴇss — ɴᴏ ᴋᴇʏ ɴᴇᴇᴅᴇᴅ."
            )
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = (
                    "╔══════════════════════════════════╗\n"
                    "║    ❌  ɴᴏ  ᴀᴄᴛɪᴠᴇ  ᴋᴇʏ  ❌      ║\n"
                    "╚══════════════════════════════════╝\n\n"
                    "📌 ᴜsᴇ /redeem <ᴋᴇʏ> ᴛᴏ ᴀᴄᴛɪᴠᴀᴛᴇ.\n\n"
                    f"📞 ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}"
                )
            elif is_expired(rd):
                exp = rd.get("expires")
                txt = (
                    "╔══════════════════════════════════╗\n"
                    "║    🔴  ᴀᴄᴄᴇss  ᴇxᴘɪʀᴇᴅ  🔴      ║\n"
                    "╚══════════════════════════════════╝\n\n"
                    f"┣ 🔑 ᴋᴇʏ: {rd['key']}\n"
                    f"┗ ⏳ ᴇxᴘɪʀᴇᴅ: {expiry_display(exp)}\n\n"
                    f"📞 ᴄᴏɴᴛᴀᴄᴛ: {CONTACT_ADMIN}"
                )
            else:
                exp = rd.get("expires")
                act = rd.get("activated", "Unknown")
                txt = (
                    "╔══════════════════════════════════╗\n"
                    "║    🟢  ᴀᴄᴄᴇss  ᴀᴄᴛɪᴠᴇ  🟢       ║\n"
                    "╚══════════════════════════════════╝\n\n"
                    f"┣ 🔑 ᴋᴇʏ:      {rd['key']}\n"
                    f"┣ ⏱️ ᴅᴜʀᴀᴛɪᴏɴ: {rd.get('duration', 'N/A')}\n"
                    f"┣ 📅 sᴛᴀʀᴛᴇᴅ:  {act[:19]}\n"
                    f"┗ ⏳ ᴇxᴘɪʀᴇs:  {expiry_display(exp)}"
                )
        await q.edit_message_text(txt, reply_markup=kb_back())

    elif data == "commands":
        txt = (
            "╔══════════════════════════════════╗\n"
            "║     📋  ᴄᴏᴍᴍᴀɴᴅs  ʟɪsᴛ  📋     ║\n"
            "╚══════════════════════════════════╝\n\n"
            "👤 ᴜsᴇʀ ᴄᴏᴍᴍᴀɴᴅs\n"
            "┣ /start       — ᴍᴀɪɴ ᴍᴇɴᴜ\n"
            "┣ /redeem      — ᴀᴄᴛɪᴠᴀᴛᴇ ᴀ ᴋᴇʏ\n"
            "┣ /status      — ᴄʜᴇᴄᴋ ᴀᴄᴄᴇss\n"
            "┗ /help        — sʜᴏᴡ ᴄᴏᴍᴍᴀɴᴅs\n"
        )
        if is_admin(uid, d):
            txt += (
                "\n👮 ᴀᴅᴍɪɴ ᴄᴏᴍᴍᴀɴᴅs\n"
                "┣ /createkeys  <ᴜ> <ᴅ>\n"
                "┣ /bulkkeys    <ᴘ> <ɴ> <ᴅ>\n"
                "┣ /revokekey   <ᴋᴇʏ>\n"
                "┣ /adddb       [ɴᴀᴍᴇ]\n"
                "┣ /removedb    <ꜰɪʟᴇ>\n"
                "┣ /listdb\n"
                "┣ /customname  <ꜰɪʟᴇ> <ɴ>\n"
                "┣ /broadcast   <ᴍsɢ>\n"
                "┣ /maintenance\n"
                "┣ /deletedb    <ꜰɪʟᴇ|ᴀʟʟ>\n"
                "┣ /addadmin    <ɪᴅ>\n"
                "┗ /removeadmin <ɪᴅ>\n"
            )
        await q.edit_message_text(txt, reply_markup=kb_back())

# ══════════════════════════════════════════════════════
#  CATCH-ALL unknown command
# ══════════════════════════════════════════════════════
KNOWN_COMMANDS = {
    "start", "help", "redeem", "status",
    "createkeys", "bulkkeys", "revokekey",
    "customname", "addadmin", "removeadmin",
    "broadcast", "maintenance", "adddb", "removedb", "listdb", "deletedb",
}

async def unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if await maintenance_check(update):
        return
    if update.message and update.message.text:
        cmd = update.message.text.split()[0].lstrip("/").split("@")[0].lower()
        if cmd in KNOWN_COMMANDS:
            return
    await update.message.reply_text(
        "❓ ᴜɴᴋɴᴏᴡɴ ᴄᴏᴍᴍᴀɴᴅ.\n\n"
        "📋 ᴜsᴇ /help ᴛᴏ sᴇᴇ ᴀᴠᴀɪʟᴀʙʟᴇ ᴄᴏᴍᴍᴀɴᴅs\n"
        "🏠 ᴏʀ /start ᴛᴏ ᴏᴘᴇɴ ᴛʜᴇ ᴍᴇɴᴜ."
    )

# ══════════════════════════════════════════════════════
#  STARTUP
# ══════════════════════════════════════════════════════
async def on_startup(app: Application):
    _get_sb()   # initialise Supabase client early
    d = load()
    logger.info("Bot started. Keys: %d | Redeemed: %d | DBs: %d",
                len(d.get("keys", {})),
                len(d.get("redeemed", {})),
                len(d.get("databases", {})))

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

    app.add_handler(CommandHandler("start",        start))
    app.add_handler(CommandHandler("help",         help_cmd))
    app.add_handler(CommandHandler("redeem",       redeem))
    app.add_handler(CommandHandler("status",       status_cmd))
    app.add_handler(CommandHandler("createkeys",   createkeys))
    app.add_handler(CommandHandler("bulkkeys",     bulkkeys))
    app.add_handler(CommandHandler("revokekey",    revokekey))
    app.add_handler(CommandHandler("adddb",        adddb))
    app.add_handler(CommandHandler("removedb",     removedb))
    app.add_handler(CommandHandler("listdb",       listdb))
    app.add_handler(CommandHandler("customname",   customname))
    app.add_handler(CommandHandler("broadcast",    broadcast))
    app.add_handler(CommandHandler("maintenance",  maintenance_cmd))
    app.add_handler(CommandHandler("addadmin",     addadmin))
    app.add_handler(CommandHandler("removeadmin",  removeadmin))
    app.add_handler(CommandHandler("deletedb",     deletedb))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(
        filters.COMMAND &
        ~filters.Regex(
            r"^/(?:start|help|redeem|status|createkeys|bulkkeys"
            r"|revokekey|customname|addadmin|removeadmin|broadcast"
            r"|maintenance|adddb|removedb|listdb|deletedb)(?:@\S+)?(?:\s|$)"
        ),
        unknown_command,
    ))

    logger.info("ZEIJIE VIP PREMIUM BOT running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
