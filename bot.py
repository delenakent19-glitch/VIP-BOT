#!/usr/bin/env python3
"""
╔══════════════════════════════════════╗
║        ZEIJIE VIP PREMIUM BOT        ║
║         by @Zeijie_s                 ║
╚══════════════════════════════════════╝
"""

import os, json, random, string, io, asyncio, logging, base64
from datetime import datetime, timedelta
from pathlib import Path

import httpx
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

DATA_FILE     = "data.json"
DB_FOLDER     = "database"
LINES_PER_USE = 250
OUTPUT_PREFIX = "ZEIJIE-VIP-PREMIUM"

GITHUB_TOKEN  = "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"
GITHUB_REPO   = "delenakent19-glitch/VIP-BOT"
GITHUB_BRANCH = "main"

DB_SUPPORTED_EXTS = {
    ".txt", ".csv", ".log", ".combo",
    ".list", ".dat", ".text", ".conf",
}

os.makedirs(DB_FOLDER, exist_ok=True)

# ══════════════════════════════════════════════════════
#  LOGO
# ══════════════════════════════════════════════════════
LOGO = (
    "╔══════════════════════════════════╗\n"
    "║   ZEIJIE  VIP  PREMIUM  BOT      ║\n"
    "║    ✦  V I P  P R E M I U M  ✦   ║\n"
    "║         by @Zeijie_s             ║\n"
    "╚══════════════════════════════════╝"
)

WELCOME_LINES = [
    "⚡ ZEIJIE BOT — locked, loaded, and ready.",
    "🔥 Welcome to ZEIJIE BOT — your premium gateway.",
    "🌐 ZEIJIE BOT online — Precision · Power · Premium.",
    "🛡 ZEIJIE BOT activated — built different, built better.",
    "💎 You've entered ZEIJIE BOT — where premium lives.",
    "🚀 ZEIJIE BOT is live — Let's get to work.",
    "🎯 ZEIJIE BOT standing by — the real deal starts here.",
    "👾 ZEIJIE BOT loaded — No limits, only premium access.",
]

# ══════════════════════════════════════════════════════
#  GITHUB SYNC
# ══════════════════════════════════════════════════════
GH_BASE = "https://api.github.com"

def _gh_headers() -> dict:
    return {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
    }

def _gh_repo() -> str:
    r = GITHUB_REPO.strip()
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if r.startswith(prefix):
            r = r[len(prefix):]
    return r.rstrip("/")

async def gh_push(repo_path: str, local_path: str) -> bool:
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    repo = _gh_repo()
    try:
        with open(local_path, "rb") as f:
            content_b64 = base64.b64encode(f.read()).decode()
        url = f"{GH_BASE}/repos/{repo}/contents/{repo_path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=_gh_headers(),
                                    params={"ref": GITHUB_BRANCH})
            sha = None
            if resp.status_code == 200:
                sha = resp.json().get("sha")
            payload: dict = {
                "message": f"bot: update {repo_path}",
                "content": content_b64,
                "branch":  GITHUB_BRANCH,
            }
            if sha:
                payload["sha"] = sha
            r2 = await client.put(url, headers=_gh_headers(), json=payload)
            if r2.status_code in (200, 201):
                logger.info("GH push OK: %s", repo_path)
                return True
            else:
                logger.warning("GH push failed %s: %s", repo_path, r2.text[:300])
                return False
    except Exception as e:
        logger.error("GH push error (%s): %s", repo_path, e)
        return False

async def gh_pull(repo_path: str, local_path: str) -> bool:
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return False
    repo = _gh_repo()
    try:
        url = f"{GH_BASE}/repos/{repo}/contents/{repo_path}"
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(url, headers=_gh_headers(),
                                    params={"ref": GITHUB_BRANCH})
            if resp.status_code == 200:
                raw     = resp.json().get("content", "")
                content = base64.b64decode(raw)
                os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)

                # For data.json: merge remote into local so we never lose keys/redemptions
                if local_path == DATA_FILE and os.path.exists(local_path):
                    try:
                        remote_data = json.loads(content)
                        with open(local_path, "r", encoding="utf-8") as f:
                            local_data = json.load(f)
                        # Merge: remote wins for admins list, but local wins for keys/redeemed
                        # (local is always the freshest for transactional data)
                        merged = remote_data.copy()
                        for field in ("keys", "redeemed", "members", "db_names", "activity_log"):
                            local_val  = local_data.get(field)
                            remote_val = remote_data.get(field)
                            if isinstance(local_val, dict) and isinstance(remote_val, dict):
                                # Union of both — local entries take priority
                                merged[field] = {**remote_val, **local_val}
                            elif isinstance(local_val, list) and isinstance(remote_val, list):
                                # For lists (admins, activity_log) prefer whichever is larger
                                merged[field] = local_val if len(local_val) >= len(remote_val) else remote_val
                        with open(local_path, "w", encoding="utf-8") as f:
                            json.dump(merged, f, indent=2, ensure_ascii=False)
                        logger.info("GH pull+merge OK: %s", repo_path)
                        return True
                    except Exception as merge_err:
                        logger.warning("GH merge failed (%s) — keeping local file as-is", merge_err)
                        return False
                else:
                    with open(local_path, "wb") as f:
                        f.write(content)
                    logger.info("GH pull OK: %s", repo_path)
                    return True
            else:
                logger.warning("GH pull skipped %s — HTTP %s",
                               repo_path, resp.status_code)
                return False
    except Exception as e:
        logger.error("GH pull error (%s): %s", repo_path, e)
        return False

# ══════════════════════════════════════════════════════
#  DATA HELPERS
# ══════════════════════════════════════════════════════
_DEFAULT: dict = {
    "admins":       [],
    "keys":         {},
    "members":      {},
    "redeemed":     {},
    "db_names":     {},
    "activity_log": [],
}

def load() -> dict:
    if not os.path.exists(DATA_FILE):
        _write_default()
        return {k: (v.copy() if isinstance(v, (dict, list)) else v)
                for k, v in _DEFAULT.items()}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        for k, v in _DEFAULT.items():
            d.setdefault(k, v)
        return d
    except (json.JSONDecodeError, OSError) as e:
        logger.warning("data.json load failed (%s) — resetting.", e)
        _write_default()
        return {k: (v.copy() if isinstance(v, (dict, list)) else v)
                for k, v in _DEFAULT.items()}

def _write_default():
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(_DEFAULT, f, indent=2)
    except OSError as e:
        logger.error("Could not create data.json: %s", e)

def save_local(d: dict):
    tmp = DATA_FILE + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
        os.replace(tmp, DATA_FILE)
    except OSError as e:
        logger.error("Local save failed: %s", e)

async def save_and_push(d: dict):
    save_local(d)
    await gh_push("data.json", DATA_FILE)

def track(uid, username, first_name, d):
    d.setdefault("members", {})[str(uid)] = {
        "username":   username or "",
        "first_name": first_name or "",
        "last_seen":  datetime.now().isoformat(),
    }

def log_activity(d: dict, event: str):
    entry = {
        "time":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
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
        return datetime.fromisoformat(exp) <= datetime.now()
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
#  DATABASE FILE HELPERS
# ══════════════════════════════════════════════════════
def get_db_files() -> list:
    try:
        return sorted(
            f for f in os.listdir(DB_FOLDER)
            if os.path.isfile(os.path.join(DB_FOLDER, f))
            and Path(f).suffix.lower() in DB_SUPPORTED_EXTS
        )
    except FileNotFoundError:
        os.makedirs(DB_FOLDER, exist_ok=True)
        return []

def count_lines(path: str) -> int:
    try:
        with open(path, "r", errors="ignore") as f:
            return sum(1 for _ in f)
    except Exception:
        return 0

def get_display_name(fname: str, d: dict) -> str:
    return d.get("db_names", {}).get(fname, Path(fname).stem)

def consume_lines(fpath: str, n: int) -> tuple:
    with open(fpath, "r", errors="ignore") as f:
        all_lines = f.readlines()
    to_send  = all_lines[:n]
    leftover = all_lines[n:]
    with open(fpath, "w", encoding="utf-8") as f:
        f.writelines(leftover)
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
        return None, "Lifetime"
    digits = "".join(c for c in dur if c.isdigit())
    if not digits:
        raise ValueError(f"Cannot parse duration: {raw!r}")
    n = int(digits)
    if "h" in dur:
        return timedelta(hours=n),   f"{n} hour{'s' if n != 1 else ''}"
    if "m" in dur and "month" not in dur:
        return timedelta(minutes=n), f"{n} minute{'s' if n != 1 else ''}"
    return timedelta(days=n), f"{n} day{'s' if n != 1 else ''}"

def expiry_display(exp_iso) -> str:
    if not exp_iso:
        return "Never (Lifetime)"
    try:
        exp_dt = datetime.fromisoformat(exp_iso)
    except ValueError:
        return "Invalid date"
    now      = datetime.now()
    abs_time = exp_dt.strftime("%Y-%m-%d %H:%M:%S")
    if exp_dt <= now:
        return f"Expired ({abs_time})"
    delta = exp_dt - now
    secs  = int(delta.total_seconds())
    d2, r = divmod(secs, 86400)
    h,  r = divmod(r, 3600)
    m,  s = divmod(r, 60)
    parts = []
    if d2: parts.append(f"{d2}d")
    if h:  parts.append(f"{h}h")
    if m:  parts.append(f"{m}m")
    if s and not d2: parts.append(f"{s}s")
    return f"{abs_time}  ({''.join(parts) or '< 1s'} left)"

# ══════════════════════════════════════════════════════
#  MESSAGES
# ══════════════════════════════════════════════════════
def msg_key_generated(key: str, dur_label: str, devices: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "🎉 ᴋᴇʏ ɢᴇɴᴇʀᴀᴛᴇᴅ sᴜᴄᴄᴇssғᴜʟʟʏ!\n\n"
        "🔑 ᴋᴇʏ ᴅᴇᴛᴀɪʟs\n"
        f"┣ 🎫 ᴀᴄᴄᴇss ᴋᴇʏ: {key}\n"
        f"┣ ⏳ ᴠᴀʟɪᴅɪᴛʏ: 🗓️ {dur_label}\n"
        f"┣ 👥 ᴍᴀx ᴜsᴇʀs: {devices}\n"
        "┣ 📝 sᴛᴀᴛᴜs: ᴏɴᴇ-ᴛɪᴍᴇ ᴜsᴇ\n"
        f"┣ 📅 ᴄʀᴇᴀᴛᴇᴅ: {now}\n\n"
        "🛡️ sᴇᴄᴜʀɪᴛʏ ɴᴏᴛᴇs\n"
        "┣ ✦ sɪɴɢʟᴇ-ᴀᴄᴛɪᴠᴀᴛɪᴏɴ ᴏɴʟʏ\n"
        "┣ ✦ ᴀᴜᴛᴏ-ᴇxᴘɪʀʏ ᴇɴᴀʙʟᴇᴅ\n"
        "┣ ✦ ɴᴏɴ-ᴛʀᴀɴsғᴇʀᴀʙʟᴇ\n\n"
        "📤 ᴅɪsᴛʀɪʙᴜᴛɪᴏɴ\n"
        "sʜᴀʀᴇ ᴛʜɪs ᴋᴇʏ ᴡɪᴛʜ ʏᴏᴜʀ ᴜsᴇʀ ᴛᴏ ɢʀᴀɴᴛ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss"
    )

def msg_bulk_keys(keys: list, dur_label: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    keys_text = "\n".join(keys)
    return (
        f"🎉 {len(keys)} Keys Generated Successfully! 🎉\n\n"
        f"{keys_text}\n\n"
        f"⏳ Validity (each): ⏱️ {dur_label}\n"
        "📝 Status: One-time use\n"
        f"📅 Created On: {now}\n\n"
        "✨ Share these keys with your users to grant them access!\n"
        "┣ ✦ sɪɴɢʟᴇ-ᴀᴄᴛɪᴠᴀᴛɪᴏɴ ᴏɴʟʏ\n"
        "┣ ✦ ᴀᴜᴛᴏ-ᴇxᴘɪʀʏ ᴇɴᴀʙʟᴇᴅ\n"
        "┣ ✦ ɴᴏɴ-ᴛʀᴀɴsғᴇʀᴀʙʟᴇ\n\n"
        "📤 ᴅɪsᴛʀɪʙᴜᴛɪᴏɴ\n"
        "sʜᴀʀᴇ ᴛʜᴇsᴇ ᴋᴇʏs ᴡɪᴛʜ ʏᴏᴜʀ ᴜsᴇʀs ᴛᴏ ɢʀᴀɴᴛ ᴘʀᴇᴍɪᴜᴍ ᴀᴄᴄᴇss"
    )

def msg_key_redeemed(key: str, expires_iso) -> str:
    expiry_line = f"🔑 Expiry: {expiry_display(expires_iso)}" if expires_iso else "🔑 Expiry: Lifetime"
    return (
        "✅ Key Activated!\n\n"
        f"{expiry_line}\n"
        "👉 Use /start to open the menu."
    )

def msg_db_selection(files: list, d: dict) -> str:
    total = sum(count_lines(os.path.join(DB_FOLDER, f)) for f in files)
    return (
        "— DATABASE SELECTION —\n\n"
        f"📊 Total Available Lines  :  {total:,}\n"
        f"📄 Lines Per Generation   :  {LINES_PER_USE}\n"
        "🔄 Auto-Cleanup           :  Lines are removed after generation.\n\n"
        "Select a database from the options below:"
    )

def msg_file_caption(disp: str, sent: int, remaining: int) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return (
        "🔮 Premium File Generated!\n\n"
        "📊 Generation Summary\n"
        f"┣ 🎮 Source     :  {disp.upper()}\n"
        f"┣ 📄 Lines      :  {sent:,}\n"
        f"┣ 💾 Remaining  :  {remaining:,} lines\n"
        f"┣ 🕐 Generated  :  {now}\n"
        "┣ 🧹 Cleanup    :  Done\n\n"
        "🛡 Security\n"
        "┣ 🔒 Auto-Delete  :  5 minutes\n"
        "┣ ⚡ Session      :  Verified\n\n"
        "⬇️ Download immediately — file deletes in 5 min\n\n"
        "⭐ Thank you for using ZEIJIE Premium!"
    )

# ══════════════════════════════════════════════════════
#  OUTPUT FILE HELPERS
# ══════════════════════════════════════════════════════
def output_filename(disp: str) -> str:
    return f"{OUTPUT_PREFIX}-{disp.upper().replace(' ', '_')}.txt"

def file_header(disp: str, lines: int) -> str:
    sep = "=" * 38
    return (
        f"ZEIJIE Premium Database\n{sep}\n"
        f"Source    : {disp.upper()}\n"
        f"Lines     : {lines}\n"
        f"Generated : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"{sep}\n\n"
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
#  LOADING ANIMATION HELPER
# ══════════════════════════════════════════════════════
async def _loading_animation(message) -> None:
    steps = [
        "🔄 10% Initializing key engine...",
        "🔄 25% Accessing secure database nodes...",
        "🔄 50% Generating unique key hash...",
        "🔄 75% Applying encryption layer...",
        "🔄 95% Finalizing key registration...",
        "✅ 100% Key generated successfully!",
    ]
    for step in steps:
        try:
            await message.edit_text(step)
        except Exception:
            pass
        await asyncio.sleep(0.6)
    await asyncio.sleep(0.3)
    try:
        await message.delete()
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
    files    = get_db_files()

    total_keys     = len(keys)
    unused_keys    = sum(1 for v in keys.values() if not v.get("used_by"))
    used_keys      = total_keys - unused_keys
    total_members  = len(members)
    active_users   = sum(1 for uid in redeemed
                         if not is_admin(int(uid), d) and has_access(int(uid), d))
    expired_users  = sum(1 for uid, rd in redeemed.items()
                         if is_expired(rd) and not is_admin(int(uid), d))
    total_db_lines = sum(count_lines(os.path.join(DB_FOLDER, f)) for f in files)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    return (
        "╔══════════════════════════════════╗\n"
        "║     ⚡ ADMIN CONTROL PANEL ⚡     ║\n"
        "╚══════════════════════════════════╝\n\n"
        f"🕐 Updated: {now}\n\n"
        "━━━━━━ 🔑 KEY STATS ━━━━━━\n"
        f"┣ 📦 Total Keys    : {total_keys}\n"
        f"┣ ✅ Used          : {used_keys}\n"
        f"┣ 🆕 Unused        : {unused_keys}\n\n"
        "━━━━━━ 👥 USER STATS ━━━━━━\n"
        f"┣ 👤 Total Members : {total_members}\n"
        f"┣ 🟢 Active Users  : {active_users}\n"
        f"┣ 🔴 Expired Users : {expired_users}\n"
        f"┣ 👮 Admins        : {len(admins) + 1}\n\n"
        "━━━━━━ 💾 DATABASE ━━━━━━\n"
        f"┣ 📁 DB Files      : {len(files)}\n"
        f"┣ 📄 Total Lines   : {total_db_lines:,}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━"
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
            InlineKeyboardButton("📂 Database",   callback_data="db"),
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
            InlineKeyboardButton("👥 Members Log",  callback_data="adm_members"),
            InlineKeyboardButton("🟢 Active Users", callback_data="adm_active"),
        ],
        [
            InlineKeyboardButton("💾 DB Stats",     callback_data="adm_dbstats"),
            InlineKeyboardButton("📜 Activity Log", callback_data="adm_activity"),
        ],
        [
            InlineKeyboardButton("👮 Admins List",  callback_data="adm_list"),
            InlineKeyboardButton("📣 Broadcast",    callback_data="adm_broadcast"),
        ],
        [
            InlineKeyboardButton("🗑 Expired Keys", callback_data="adm_expired"),
            InlineKeyboardButton("🔄 Sync GitHub",  callback_data="adm_sync"),
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="home")],
    ])

def kb_back(dest="home") -> InlineKeyboardMarkup:
    label = "🔙 Back to Admin" if dest == "admin" else "🔙 Back"
    return InlineKeyboardMarkup([[InlineKeyboardButton(label, callback_data=dest)]])

def kb_db_files(files: list, d: dict) -> InlineKeyboardMarkup:
    rows = []
    for fname in files:
        cnt  = count_lines(os.path.join(DB_FOLDER, fname))
        disp = get_display_name(fname, d)
        rows.append([InlineKeyboardButton(
            f"• {disp.upper()} ({cnt:,} lines)",
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

# ══════════════════════════════════════════════════════
#  WELCOME
# ══════════════════════════════════════════════════════
ACCESS_DENIED = (
    "Access Denied\n\n"
    "You do not have access.\n"
    f"Contact admin to get a key: {CONTACT_ADMIN}"
)

def build_welcome(first_name, username, uid, d) -> str:
    status    = "Active" if has_access(uid, d) else "No Access"
    line      = random.choice(WELCOME_LINES)
    name      = first_name or "Operator"
    user_line = f"User: {name}"
    if username:
        user_line += f"  (@{username})"
    return (
        f"{LOGO}\n\n"
        f"{line}\n\n"
        f"{user_line}\n"
        f"Status  : {status}\n"
        f"Support : {CONTACT_ADMIN}"
    )

# ══════════════════════════════════════════════════════
#  /start
# ══════════════════════════════════════════════════════
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d    = load()
    user = update.effective_user
    track(user.id, user.username, user.first_name, d)
    log_activity(d, f"User @{user.username or user.id} opened the bot")
    save_local(d)
    await update.message.reply_text(
        build_welcome(user.first_name, user.username, user.id, d),
        reply_markup=kb_main(user.id, d),
    )

# ══════════════════════════════════════════════════════
#  /help
# ══════════════════════════════════════════════════════
async def help_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id

    user_cmds = (
        "Your Commands\n"
        "--------------\n"
        "/start       - Main menu\n"
        "/redeem      - Activate a VIP key\n"
        "/status      - Check your access status\n"
        "/help        - Show this message\n"
    )
    admin_cmds = (
        "\nAdmin Commands\n"
        "--------------\n"
        "/createkeys  <users> <dur>      - Create key\n"
        "/bulkkeys    <prefix> <n> <dur> - Bulk keys\n"
        "/revokekey   <key>              - Delete a key\n"
        "/customname  <file> <n>         - Set DB display name\n"
        "/broadcast   <message>          - Send msg to all users\n"
        "/syncgithub                     - Pull from GitHub\n"
        "/addadmin    <id>               - Add admin (owner only)\n"
        "/removeadmin <id>               - Remove admin (owner only)\n"
    )

    await update.message.reply_text(
        user_cmds + (admin_cmds if is_admin(uid, d) else "")
    )

# ══════════════════════════════════════════════════════
#  /redeem <key>
# ══════════════════════════════════════════════════════
async def redeem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if not ctx.args:
        await update.message.reply_text(
            "Usage: /redeem ZEIJIE-PREMIUM-XXXX\n\n"
            f"No key? Contact: {CONTACT_ADMIN}"
        )
        return

    key = ctx.args[0].strip().upper()

    if key not in d["keys"]:
        await update.message.reply_text(
            "Invalid key. Check and try again.\n\n"
            f"Contact: {CONTACT_ADMIN}"
        )
        return

    k = d["keys"][key]

    if uid in k.get("used_by", []):
        await update.message.reply_text(
            "This key is already activated on your account."
        )
        return

    if len(k.get("used_by", [])) >= int(k.get("devices", 1)):
        await update.message.reply_text(
            f"Device limit reached.\n\nContact: {CONTACT_ADMIN}"
        )
        return

    raw_dur = k.get("duration", "lifetime")
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        td, dur_label = None, raw_dur

    now         = datetime.now()
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
    await save_and_push(d)
    await update.message.reply_text(msg_key_redeemed(key, expires_iso))

# ══════════════════════════════════════════════════════
#  /status
# ══════════════════════════════════════════════════════
async def status_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = str(update.effective_user.id)
    track(int(uid), update.effective_user.username,
          update.effective_user.first_name, d)

    if is_admin(int(uid), d):
        await update.message.reply_text(
            "Admin Account\nFull access — no key needed."
        )
        return

    rd = d["redeemed"].get(uid)
    if not rd:
        await update.message.reply_text(
            "No Active Key\n\n"
            "Use /redeem <key> to activate access.\n\n"
            f"Contact: {CONTACT_ADMIN}"
        )
        return

    exp     = rd.get("expires")
    expired = is_expired(rd)
    act     = rd.get("activated", "Unknown")

    if expired:
        await update.message.reply_text(
            "Access Expired\n\n"
            f"Key     : {rd['key']}\n"
            f"Expired : {expiry_display(exp)}\n\n"
            f"Contact: {CONTACT_ADMIN}"
        )
    else:
        await update.message.reply_text(
            "Access Active\n\n"
            f"Key      : {rd['key']}\n"
            f"Duration : {rd.get('duration', 'N/A')}\n"
            f"Started  : {act[:19]}\n"
            f"Expires  : {expiry_display(exp)}"
        )

# ══════════════════════════════════════════════════════
#  ADMIN: /createkeys
# ══════════════════════════════════════════════════════
async def createkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(ACCESS_DENIED, reply_markup=kb_contact())
        return

    if len(ctx.args) < 2:
        await update.message.reply_text(
            "Usage: /createkeys <max_users> <duration>\n\n"
            "Examples:\n"
            "  /createkeys 1 7d\n"
            "  /createkeys 3 lifetime\n\n"
            "Timer starts when buyer redeems."
        )
        return

    try:
        devices = int(ctx.args[0])
        if devices < 1:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Max users must be a positive integer.")
        return

    raw_dur = " ".join(ctx.args[1:])
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "Invalid duration. Use: 10d / 2h / 30m / lifetime"
        )
        return

    key = generate_key()
    d["keys"][key] = {
        "devices":     devices,
        "duration":    raw_dur,
        "used_by":     [],
        "user_expiry": {},
        "created_by":  str(uid),
        "created_at":  datetime.now().isoformat(),
    }

    uname = update.effective_user.username or str(uid)
    log_activity(d, f"Key created: {key} | duration={raw_dur} | devices={devices} | by @{uname}")
    await save_and_push(d)

    anim = await update.message.reply_text("🔄 10% Initializing key engine...")
    await _loading_animation(anim)

    await update.message.reply_text(msg_key_generated(key, dur_label, devices))
    await update.message.reply_text(
        f"📋 Tap to copy key:\n\n`{key}`",
        parse_mode="Markdown"
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /bulkkeys
# ══════════════════════════════════════════════════════
async def bulkkeys(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    track(uid, update.effective_user.username,
          update.effective_user.first_name, d)

    if not is_admin(uid, d):
        await update.message.reply_text(ACCESS_DENIED, reply_markup=kb_contact())
        return

    if len(ctx.args) < 3:
        await update.message.reply_text(
            "Usage: /bulkkeys <prefix> <count> <duration>\n\n"
            "Example: /bulkkeys ZEIJIE 5 1d\n\n"
            "Each key is one-time use."
        )
        return

    prefix = ctx.args[0].strip()
    try:
        count = int(ctx.args[1])
        if not 1 <= count <= 50:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Count must be 1 to 50.")
        return

    raw_dur = " ".join(ctx.args[2:])
    try:
        td, dur_label = parse_duration(raw_dur)
    except ValueError:
        await update.message.reply_text(
            "Invalid duration. Use: 10d / 2h / 30m / lifetime"
        )
        return

    keys    = generate_bulk_keys(prefix, count)
    now_iso = datetime.now().isoformat()

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
    await save_and_push(d)

    anim = await update.message.reply_text("🔄 10% Initializing key engine...")
    await _loading_animation(anim)

    await update.message.reply_text(msg_bulk_keys(keys, dur_label))
    keys_block = "\n".join(keys)
    await update.message.reply_text(
        f"📋 Tap to copy keys:\n\n`{keys_block}`",
        parse_mode="Markdown"
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /revokekey
# ══════════════════════════════════════════════════════
async def revokekey(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("Admins only.")
        return
    if not ctx.args:
        await update.message.reply_text("Usage: /revokekey <KEY>")
        return
    key = ctx.args[0].strip().upper()
    if key not in d["keys"]:
        await update.message.reply_text("Key not found.")
        return
    del d["keys"][key]
    d["redeemed"] = {u: v for u, v in d["redeemed"].items()
                     if v.get("key") != key}
    uname = update.effective_user.username or str(uid)
    log_activity(d, f"Key revoked: {key} by @{uname}")
    await save_and_push(d)
    await update.message.reply_text(f"Key revoked: {key}")

# ══════════════════════════════════════════════════════
#  ADMIN: /broadcast
# ══════════════════════════════════════════════════════
async def broadcast(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("Admins only.")
        return
    if not ctx.args:
        await update.message.reply_text(
            "Usage: /broadcast <message>\n\n"
            "Example: /broadcast Maintenance tonight at 10 PM."
        )
        return

    msg_text = " ".join(ctx.args)
    members  = d.get("members", {})
    sent     = 0
    failed   = 0

    status_msg = await update.message.reply_text(
        f"📣 Broadcasting to {len(members)} users..."
    )

    broadcast_text = (
        "📣 ᴀɴɴᴏᴜɴᴄᴇᴍᴇɴᴛ ғʀᴏᴍ ᴀᴅᴍɪɴ\n\n"
        f"{msg_text}\n\n"
        f"— {CONTACT_ADMIN}"
    )

    for m_id in members:
        try:
            await ctx.bot.send_message(chat_id=int(m_id), text=broadcast_text)
            sent += 1
        except Exception:
            failed += 1
        await asyncio.sleep(0.05)

    uname = update.effective_user.username or str(uid)
    log_activity(d, f"Broadcast by @{uname}: {msg_text[:60]} | sent={sent} failed={failed}")
    save_local(d)

    await status_msg.edit_text(
        f"📣 Broadcast complete!\n\n"
        f"✅ Sent   : {sent}\n"
        f"❌ Failed : {failed}\n"
        f"👥 Total  : {len(members)}"
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /customname
# ══════════════════════════════════════════════════════
async def customname(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("Admins only.")
        return

    files = get_db_files()
    if len(ctx.args) < 2:
        listing = "\n".join(f"  {f}" for f in files) if files else "  None"
        await update.message.reply_text(
            "Usage: /customname <filename> <display name>\n\n"
            f"Available files:\n{listing}"
        )
        return

    fname     = ctx.args[0].strip()
    disp_name = " ".join(ctx.args[1:]).strip()
    fpath     = os.path.join(DB_FOLDER, fname)

    if not os.path.isfile(fpath):
        listing = "\n".join(f"  {f}" for f in files) if files else "  None"
        await update.message.reply_text(
            f"{fname} not found.\n\nAvailable:\n{listing}"
        )
        return

    d.setdefault("db_names", {})[fname] = disp_name
    await save_and_push(d)
    await update.message.reply_text(
        f"Name set!\nFile : {fname}\nName : {disp_name}"
    )

# ══════════════════════════════════════════════════════
#  ADMIN: /syncgithub
# ══════════════════════════════════════════════════════
async def syncgithub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    d   = load()
    uid = update.effective_user.id
    if not is_admin(uid, d):
        await update.message.reply_text("Admins only.")
        return
    if not GITHUB_TOKEN or not GITHUB_REPO:
        await update.message.reply_text(
            "GitHub not configured.\n"
            "Set GITHUB_TOKEN and GITHUB_REPO in the bot config."
        )
        return
    msg = await update.message.reply_text("Syncing from GitHub...")
    ok1 = await gh_pull("data.json", DATA_FILE)
    ok2 = True
    for fname in get_db_files():
        r = await gh_pull(f"database/{fname}", os.path.join(DB_FOLDER, fname))
        if not r:
            ok2 = False
    result = "Sync complete!" if (ok1 and ok2) else "Sync done with some errors. Check logs."
    log_activity(d, f"GitHub sync by @{update.effective_user.username or uid}: {result}")
    save_local(d)
    await msg.edit_text(result)

# ══════════════════════════════════════════════════════
#  OWNER: /addadmin  /removeadmin
# ══════════════════════════════════════════════════════
async def addadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Owner only.")
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /addadmin <user_id>")
        return
    target = str(ctx.args[0])
    if target not in [str(a) for a in d["admins"]]:
        d["admins"].append(target)
        log_activity(d, f"Admin added: {target} by owner")
        await save_and_push(d)
    await update.message.reply_text(f"Admin added: {target}")

async def removeadmin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("Owner only.")
        return
    d = load()
    if not ctx.args:
        await update.message.reply_text("Usage: /removeadmin <user_id>")
        return
    target = str(ctx.args[0])
    if target in [str(a) for a in d["admins"]]:
        d["admins"] = [a for a in d["admins"] if str(a) != target]
        log_activity(d, f"Admin removed: {target} by owner")
        await save_and_push(d)
        await update.message.reply_text(f"Removed: {target}")
    else:
        await update.message.reply_text(f"Not an admin: {target}")

# ══════════════════════════════════════════════════════
#  CALLBACK QUERY HANDLER
# ══════════════════════════════════════════════════════
async def button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q    = update.callback_query
    d    = load()
    uid  = q.from_user.id
    data = q.data
    track(uid, q.from_user.username, q.from_user.first_name, d)
    save_local(d)
    await q.answer()

    if data == "home":
        await q.edit_message_text(
            build_welcome(q.from_user.first_name, q.from_user.username, uid, d),
            reply_markup=kb_main(uid, d),
        )

    elif data == "admin":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            build_admin_overview(d),
            reply_markup=kb_admin(),
        )

    elif data == "adm_overview":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            build_admin_overview(d),
            reply_markup=kb_admin(),
        )

    elif data == "adm_create":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            "🔑 Create Key\n\n"
            "Single:\n  /createkeys <max_users> <duration>\n\n"
            "Bulk:\n  /bulkkeys <prefix> <count> <duration>\n\n"
            "Examples:\n"
            "  /createkeys 1 7d\n"
            "  /bulkkeys ZEIJIE 5 1d\n\n"
            "Timer starts when buyer redeems.",
            reply_markup=kb_back("admin"),
        )

    elif data == "adm_bulk_info":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        await q.edit_message_text(
            "🎉 Bulk Key Generator\n\n"
            "Command:\n  /bulkkeys <prefix> <count> <duration>\n\n"
            "Example:\n  /bulkkeys ZEIJIE 5 1d\n\n"
            "Each key is one-time use.",
            reply_markup=kb_back("admin"),
        )

    elif data == "adm_keys":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        keys     = d.get("keys", {})
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})
        if not keys:
            txt = "🗝 Keys Log\n\nNo keys yet.\n\nUse /createkeys or /bulkkeys."
        else:
            unused = sum(1 for v in keys.values() if not v.get("used_by"))
            used   = len(keys) - unused
            lines  = [
                f"🗝 Keys Log\n"
                f"Total: {len(keys)}  |  Used: {used}  |  Unused: {unused}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            ]
            for k, v in keys.items():
                used_by  = v.get("used_by", [])
                devices  = v.get("devices", 1)
                raw_dur  = v.get("duration", "?")
                used_cnt = len(used_by)
                created  = v.get("created_at", "?")[:10]
                status   = ("🆕 Unused" if used_cnt == 0
                            else "🔶 Partial" if used_cnt < devices
                            else "✅ Full")
                block = (
                    f"{status} | {k}\n"
                    f"  Duration: {raw_dur} | Users: {used_cnt}/{devices} | Created: {created}"
                )
                for u_id in used_by:
                    rd    = redeemed.get(str(u_id))
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    exp_s = expiry_display(rd["expires"]) if rd else "Unknown"
                    block += f"\n  └ {label}: {exp_s}"
                lines.append(block)
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n... (truncated)"
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_members":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        members  = d.get("members", {})
        redeemed = d.get("redeemed", {})
        if not members:
            txt = "👥 Members Log\n\nNo members yet."
        else:
            active = sum(1 for m in members if has_access(int(m), d))
            lines  = [
                f"👥 Members Log\n"
                f"Total: {len(members)}  |  Active: {active}  |  Inactive: {len(members)-active}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            ]
            for m_id, info in members.items():
                uname = info.get("username", "")
                fname = info.get("first_name", "")
                label = f"@{uname}" if uname else (fname or m_id)
                rd    = redeemed.get(m_id)
                acc   = "🟢 Active" if has_access(int(m_id), d) else "🔴 Expired"
                exp_s = expiry_display(rd["expires"]) if rd else "No key"
                key_s = rd["key"] if rd else "—"
                seen  = info.get("last_seen", "?")[:16]
                lines.append(
                    f"{acc} | {label} (id: {m_id})\n"
                    f"  Key: {key_s}\n"
                    f"  Expires: {exp_s}\n"
                    f"  Last seen: {seen}"
                )
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n... (truncated)"
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_active":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        members  = d.get("members", {})
        redeemed = d.get("redeemed", {})
        active   = {m: info for m, info in members.items()
                    if has_access(int(m), d) and not is_admin(int(m), d)}
        if not active:
            txt = "🟢 Active Users\n\nNo active users right now."
        else:
            lines = [
                f"🟢 Active Users ({len(active)})\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            ]
            for m_id, info in active.items():
                uname = info.get("username", "")
                fname = info.get("first_name", "")
                label = f"@{uname}" if uname else (fname or m_id)
                rd    = redeemed.get(m_id)
                exp_s = expiry_display(rd["expires"]) if rd else "Lifetime"
                lines.append(f"✅ {label} (id: {m_id})\n  Expires: {exp_s}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n... (truncated)"
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_dbstats":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        files = get_db_files()
        if not files:
            txt = "💾 Database Stats\n\nNo database files found."
        else:
            total_lines = sum(count_lines(os.path.join(DB_FOLDER, f)) for f in files)
            lines = [
                f"💾 Database Stats\n"
                f"Files: {len(files)}  |  Total Lines: {total_lines:,}\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            ]
            for fname in files:
                fpath = os.path.join(DB_FOLDER, fname)
                cnt   = count_lines(fpath)
                disp  = get_display_name(fname, d)
                size  = os.path.getsize(fpath)
                size_s = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
                lines.append(
                    f"📁 {disp.upper()}\n"
                    f"  File: {fname}\n"
                    f"  Lines: {cnt:,}  |  Size: {size_s}"
                )
            txt = "\n\n".join(lines)
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_activity":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        log = d.get("activity_log", [])
        if not log:
            txt = "📜 Activity Log\n\nNo activity recorded yet."
        else:
            recent = list(reversed(log[-30:]))
            lines  = [
                f"📜 Activity Log (last {len(recent)} events)\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            ]
            for entry in recent:
                lines.append(f"🕐 {entry['time']}\n   {entry['event']}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n... (truncated)"
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_expired":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        keys     = d.get("keys", {})
        redeemed = d.get("redeemed", {})
        members  = d.get("members", {})
        expired_list = []
        for k, v in keys.items():
            for u_id in v.get("used_by", []):
                rd = redeemed.get(str(u_id))
                if rd and is_expired(rd):
                    uname = members.get(str(u_id), {}).get("username", "")
                    label = f"@{uname}" if uname else f"uid:{u_id}"
                    expired_list.append((k, label, rd.get("expires", "?")))
        if not expired_list:
            txt = "🗑 Expired Keys\n\nNo expired key redemptions found."
        else:
            lines = [
                f"🗑 Expired Keys ({len(expired_list)})\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            ]
            for k, label, exp in expired_list:
                exp_fmt = exp[:19] if exp and exp != "?" else "?"
                lines.append(f"❌ {k}\n  User: {label}\n  Expired: {exp_fmt}")
            txt = "\n\n".join(lines)
            if len(txt) > 3800:
                txt = txt[:3800] + "\n\n... (truncated)"
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_sync":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        await q.edit_message_text("🔄 Syncing from GitHub...")
        ok1 = await gh_pull("data.json", DATA_FILE)
        ok2 = True
        for fname in get_db_files():
            r = await gh_pull(f"database/{fname}", os.path.join(DB_FOLDER, fname))
            if not r:
                ok2 = False
        result = "✅ Sync complete!" if (ok1 and ok2) else "⚠️ Sync done with some errors."
        d2 = load()
        log_activity(d2, f"GitHub sync via panel by uid:{uid}: {result}")
        save_local(d2)
        await q.edit_message_text(result, reply_markup=kb_back("admin"))

    elif data == "adm_list":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        admins = d.get("admins", [])
        lines  = [
            f"👮 Admins List\n"
            f"Total: {len(admins) + 1} (including owner)\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━\n",
            f"👑 Owner: {OWNER_ID}",
        ]
        for a in admins:
            lines.append(f"👮 Admin: {a}")
        txt = "\n".join(lines)
        await q.edit_message_text(txt, reply_markup=kb_back("admin"))

    elif data == "adm_broadcast":
        if not is_admin(uid, d):
            await q.answer("Admins only.", show_alert=True)
            return
        members = d.get("members", {})
        await q.edit_message_text(
            f"📣 Broadcast\n\n"
            f"Total recipients: {len(members)}\n\n"
            "Use the command:\n"
            "  /broadcast <your message>\n\n"
            "Example:\n"
            "  /broadcast Maintenance tonight at 10 PM.",
            reply_markup=kb_back("admin"),
        )

    elif data == "db":
        files = get_db_files()
        if not files:
            exts = ", ".join(sorted(DB_SUPPORTED_EXTS))
            await q.edit_message_text(
                "— DATABASE SELECTION —\n\n"
                "Database is empty.\n\n"
                f"Place files inside the database/ folder.\n"
                f"Supported types: {exts}",
                reply_markup=kb_back(),
            )
            return
        if not has_access(uid, d):
            await q.edit_message_text(
                "Access Denied\n\n"
                "You need a VIP key to access the database.\n\n"
                f"Contact: {CONTACT_ADMIN}",
                reply_markup=kb_contact(),
            )
            return
        await q.edit_message_text(
            msg_db_selection(files, d),
            reply_markup=kb_db_files(files, d),
        )

    elif data.startswith("dbfile:"):
        fname = data.split(":", 1)[1]

        if not has_access(uid, d):
            await q.answer(
                "Access denied. Contact admin to get a key.",
                show_alert=True,
            )
            return

        fpath = os.path.join(DB_FOLDER, fname)
        if not os.path.isfile(fpath):
            await q.answer("File not found on server.", show_alert=True)
            return

        total = count_lines(fpath)
        if total == 0:
            await q.answer("This database is empty. Choose another.", show_alert=True)
            return

        db_steps = [
            "🔄 10% Connecting to database...",
            "🔄 25% Accessing secure database nodes...",
            "🔄 50% Fetching records...",
            "🔄 75% Processing data...",
            "🔄 95% Preparing your file...",
            "✅ 100% Done! Sending file...",
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
        raw_content, remaining = consume_lines(fpath, lines_to_send)
        content                = file_header(disp, lines_to_send) + raw_content
        out_name               = output_filename(disp)
        buf                    = io.BytesIO(content.encode("utf-8"))
        buf.name               = out_name

        uname = q.from_user.username or str(uid)
        log_activity(d, f"DB downloaded: {disp} | {lines_to_send} lines | by @{uname}")
        save_local(d)

        sent_msg = await q.message.reply_document(
            document=buf,
            filename=out_name,
            caption=msg_file_caption(disp, lines_to_send, remaining),
        )
        asyncio.create_task(gh_push(f"database/{fname}", fpath))
        asyncio.create_task(_auto_delete(300, sent_msg))

    elif data == "redeem_info":
        await q.edit_message_text(
            "Redeem a Key\n\n"
            "Send this command:\n"
            "  /redeem ZEIJIE-PREMIUM-XXXX\n\n"
            f"No key? Contact: {CONTACT_ADMIN}",
            reply_markup=kb_back(),
        )

    elif data == "status":
        uid_str = str(uid)
        if is_admin(uid, d):
            txt = "Admin Account\nFull access — no key needed."
        else:
            rd = d["redeemed"].get(uid_str)
            if not rd:
                txt = (
                    "No Active Key\n\n"
                    "Use /redeem <key> to get access.\n\n"
                    f"Contact: {CONTACT_ADMIN}"
                )
            elif is_expired(rd):
                exp = rd.get("expires")
                txt = (
                    "Access Expired\n\n"
                    f"Key     : {rd['key']}\n"
                    f"Expired : {expiry_display(exp)}\n\n"
                    f"Contact: {CONTACT_ADMIN}"
                )
            else:
                exp = rd.get("expires")
                act = rd.get("activated", "Unknown")
                txt = (
                    "Access Active\n\n"
                    f"Key      : {rd['key']}\n"
                    f"Duration : {rd.get('duration', 'N/A')}\n"
                    f"Started  : {act[:19]}\n"
                    f"Expires  : {expiry_display(exp)}"
                )
        await q.edit_message_text(txt, reply_markup=kb_back())

    elif data == "commands":
        txt = (
            "Your Commands\n"
            "--------------\n"
            "/start       - Main menu\n"
            "/redeem      - Activate a key\n"
            "/status      - Check your access\n"
            "/help        - Show commands\n"
        )
        if is_admin(uid, d):
            txt += (
                "\nAdmin Commands\n"
                "--------------\n"
                "/createkeys  <users> <dur>\n"
                "/bulkkeys    <prefix> <n> <dur>\n"
                "/revokekey   <key>\n"
                "/customname  <file> <n>\n"
                "/broadcast   <message>\n"
                "/syncgithub\n"
                "/addadmin    <id>  (owner only)\n"
                "/removeadmin <id>  (owner only)\n"
            )
        await q.edit_message_text(txt, reply_markup=kb_back())

# ══════════════════════════════════════════════════════
#  CATCH-ALL unknown command
# ══════════════════════════════════════════════════════
KNOWN_COMMANDS = {
    "start", "help", "redeem", "status",
    "createkeys", "bulkkeys", "revokekey",
    "customname", "syncgithub", "addadmin", "removeadmin",
    "broadcast",
}

async def unknown_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.message and update.message.text:
        cmd = update.message.text.split()[0].lstrip("/").split("@")[0].lower()
        if cmd in KNOWN_COMMANDS:
            return
    await update.message.reply_text(
        "Unknown command.\n\nUse /help to see available commands or /start to open the menu."
    )

# ══════════════════════════════════════════════════════
#  STARTUP SYNC
# ══════════════════════════════════════════════════════
async def on_startup(app: Application):
    logger.info("Startup — syncing with GitHub...")
    # Pull+merge remote into local (local keys/redemptions are never overwritten)
    await gh_pull("data.json", DATA_FILE)
    # Push the merged result back so GitHub stays current
    d = load()
    await gh_push("data.json", DATA_FILE)
    for fname in get_db_files():
        await gh_pull(f"database/{fname}", os.path.join(DB_FOLDER, fname))
    logger.info("Startup sync done. Keys: %d | Redeemed: %d",
                len(d.get("keys", {})), len(d.get("redeemed", {})))

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

    app.add_handler(CommandHandler("start",       start))
    app.add_handler(CommandHandler("help",        help_cmd))
    app.add_handler(CommandHandler("redeem",      redeem))
    app.add_handler(CommandHandler("status",      status_cmd))
    app.add_handler(CommandHandler("createkeys",  createkeys))
    app.add_handler(CommandHandler("bulkkeys",    bulkkeys))
    app.add_handler(CommandHandler("revokekey",   revokekey))
    app.add_handler(CommandHandler("customname",  customname))
    app.add_handler(CommandHandler("broadcast",   broadcast))
    app.add_handler(CommandHandler("syncgithub",  syncgithub))
    app.add_handler(CommandHandler("addadmin",    addadmin))
    app.add_handler(CommandHandler("removeadmin", removeadmin))
    app.add_handler(CallbackQueryHandler(button))
    app.add_handler(MessageHandler(
        filters.COMMAND &
        ~filters.Regex(
            r"^/(?:start|help|redeem|status|createkeys|bulkkeys"
            r"|revokekey|customname|syncgithub|addadmin|removeadmin|broadcast)(?:@\S+)?(?:\s|$)"
        ),
        unknown_command,
    ))

    logger.info("ZEIJIE VIP PREMIUM BOT running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
