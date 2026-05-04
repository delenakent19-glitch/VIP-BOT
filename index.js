/**
 * KEY SELLER BOT — Railway Deployment
 * Upload: index.js + package.json to GitHub → connect to Railway
 * Variables: BOT_TOKEN, ADMIN_ID, QR_FILE_ID
 */

require("dotenv").config();
const TelegramBot = require("node-telegram-bot-api");
const express     = require("express");
const fs          = require("fs-extra");
const path        = require("path");

const BOT_TOKEN  = process.env.BOT_TOKEN;
const ADMIN_ID   = process.env.ADMIN_ID;
const CHANNEL_ID = process.env.CHANNEL_ID || "";
const PORT       = process.env.PORT || 8080;
const DB_FILE    = "./data/db.json";

if (!BOT_TOKEN || !ADMIN_ID) {
  console.error("Missing BOT_TOKEN or ADMIN_ID in environment variables");
  process.exit(1);
}

// ─── DATABASE ────────────────────────────────────────────────────────────────
async function getDB() {
  await fs.ensureFile(DB_FILE);
  const raw = await fs.readFile(DB_FILE, "utf8").catch(() => "{}");
  let db;
  try { db = JSON.parse(raw); } catch { db = {}; }
  if (!db.products) db.products = {};
  if (!db.orders)   db.orders   = {};
  if (!db.keys)     db.keys     = {};
  if (!db.settings) db.settings = {};
  return db;
}

async function saveDB(db) {
  await fs.ensureDir(path.dirname(DB_FILE));
  await fs.writeFile(DB_FILE, JSON.stringify(db, null, 2));
}

// ─── BOT ─────────────────────────────────────────────────────────────────────
// On Railway: use webhook via Express (single port for both admin + webhook).
// Locally: use polling.
const WEBHOOK_HOST = process.env.RAILWAY_PUBLIC_DOMAIN;
const bot = new TelegramBot(BOT_TOKEN, { polling: !WEBHOOK_HOST });

const userState = {};

// Use HTML parse mode everywhere — no escaping nightmares like MarkdownV2
const HTML = { parse_mode: "HTML" };

// Escape &, <, > in dynamic user data to prevent HTML injection / parse errors
function h(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ─── PHILIPPINE TIME (GMT+8) ──────────────────────────────────────────────────
function phTime(isoString) {
  const date = isoString ? new Date(isoString) : new Date();
  return date.toLocaleString("en-PH", {
    timeZone: "Asia/Manila",
    year:     "numeric",
    month:    "short",
    day:      "2-digit",
    hour:     "2-digit",
    minute:   "2-digit",
    second:   "2-digit",
    hour12:   true
  });
}

// ─── /start ──────────────────────────────────────────────────────────────────
bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  const name   = msg.from.first_name || "there";
  try {
    await bot.sendMessage(chatId,
      `<b>╔══════════════════════╗</b>\n` +
      `<b>   🛒 ZEIJIE ORDER BOT 🛒   </b>\n` +
      `<b>╚══════════════════════╝</b>\n\n` +
      `👋 Hey, <b>${h(name)}!</b> Welcome!\n\n` +
      `<b>━━━━━ WHAT WE OFFER ━━━━━</b>\n` +
      `  ⚡  Instant delivery\n` +
      `  📦  Container or Modded APK\n` +
      `  🔒  Fast, secure and reliable\n\n` +
      `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n` +
      `👇 Tap <b>Buy Key</b> to browse products!`,
      {
        parse_mode: "HTML",
        reply_markup: {
          keyboard: [
            [{ text: "Buy Key" }, { text: "My Orders" }],
            [{ text: "Help" }]
          ],
          resize_keyboard: true,
          one_time_keyboard: false
        }
      }
    );
  } catch (e) { console.error("start error:", e.message); }
});

// ─── HELP ────────────────────────────────────────────────────────────────────
bot.onText(/\/help/, (msg) => sendHelp(msg.chat.id));

async function sendHelp(chatId) {
  try {
    await bot.sendMessage(chatId,
      `<b>╔══════════════════════╗</b>\n` +
      `<b>    📖 HOW IT WORKS 📖    </b>\n` +
      `<b>╚══════════════════════╝</b>\n\n` +
      `<b>1️⃣ BROWSE</b>\n` +
      `     Tap Buy Key and pick a product.\n\n` +
      `<b>2️⃣ CHOOSE TYPE</b>\n` +
      `     Select Container or Modded APK.\n\n` +
      `<b>3️⃣ PAY</b>\n` +
      `     Scan the QR code and send payment. 💳\n\n` +
      `<b>4️⃣ SCREENSHOT</b>\n` +
      `     Send your payment proof here. 📸\n\n` +
      `<b>5️⃣ WAIT</b>\n` +
      `     Admin reviews in ~5 minutes. ⏳\n\n` +
      `<b>6️⃣ RECEIVE</b>\n` +
      `     Your key/APK delivered here instantly! 🔑\n\n` +
      `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n` +
      `❓ Questions? Contact the admin directly.`,
      HTML
    );
  } catch (e) { console.error("help error:", e.message); }
}

// ─── SHOW PRODUCTS ────────────────────────────────────────────────────────────
async function showProducts(chatId) {
  try {
    const db = await getDB();
    const products = Object.values(db.products).filter(p => p.active);
    if (products.length === 0) {
      return bot.sendMessage(chatId,
        `<b>╔══════════════════════╗</b>\n` +
        `<b>    😔 OUT OF STOCK 😔    </b>\n` +
        `<b>╚══════════════════════╝</b>\n\n` +
        `We are currently restocking.\nPlease check back soon! 🔄`,
        HTML
      );
    }

    const grouped = {};
    for (const p of products) {
      const cat = p.category || "Other";
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(p);
    }

    const inline_keyboard = [];
    let messageText =
      `<b>╔══════════════════════╗</b>\n` +
      `<b>     🛍️ SHOP / STORE 🛍️    </b>\n` +
      `<b>╚══════════════════════╝</b>\n\n`;

    for (const [cat, items] of Object.entries(grouped)) {
      messageText += `<b>📂 ${cat}</b>\n`;
      for (const p of items) {
        messageText += `  • ${p.emoji || "🔑"} <b>${h(p.name)}</b> — P${p.price}\n`;
        inline_keyboard.push([{
          text: `${p.emoji || "🔑"} ${p.name} — P${p.price}`,
          callback_data: `buy_${p.id}`
        }]);
      }
      messageText += "\n";
    }

    messageText += `👇 Tap a product to order:`;

    await bot.sendMessage(chatId, messageText, {
      parse_mode: "HTML",
      reply_markup: { inline_keyboard }
    });
  } catch (e) { console.error("showProducts error:", e.message); }
}

// ─── MY ORDERS ────────────────────────────────────────────────────────────────
async function handleMyOrders(chatId) {
  try {
    const db = await getDB();
    const myOrders = Object.values(db.orders)
      .filter(o => String(o.buyerId) === String(chatId))
      .slice(-5).reverse();

    if (!myOrders.length) {
      return bot.sendMessage(chatId,
        `<b>╔══════════════════════╗</b>\n` +
        `<b>    📭 NO ORDERS YET 📭    </b>\n` +
        `<b>╚══════════════════════╝</b>\n\n` +
        `You have not placed any orders yet.\n🛒 Tap <b>Buy Key</b> to get started!`,
        HTML
      );
    }

    let reply = `<b>╔══════════════════════╗</b>\n` +
                `<b>  📦 MY ORDERS (LAST 5) 📦  </b>\n` +
                `<b>╚══════════════════════╝</b>\n\n`;
    for (const o of myOrders) {
      const icon = o.status === "approved" ? "✅ APPROVED" : o.status === "rejected" ? "❌ REJECTED" : "⏳ PENDING";
      reply += `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n`;
      reply += `  🎮 Product : <b>${h(o.productName)}</b>\n`;
      reply += `  💰 Amount  : P${o.amount}\n`;
      reply += `  🆔 Order ID: <code>${h(o.id)}</code>\n`;
      reply += `  📌 Status  : <b>${icon}</b>\n`;
      reply += `  📅 Date    : ${h(phTime(o.createdAt))}\n`;
      if (o.key) reply += `  🔑 Key     : <code>${h(o.key)}</code>\n`;
      reply += "\n";
    }
    return bot.sendMessage(chatId, reply, HTML);
  } catch (e) { console.error("myOrders error:", e.message); }
}

// ─── MESSAGE HANDLER ─────────────────────────────────────────────────────────
bot.on("message", async (msg) => {
  const chatId = msg.chat.id;
  const text   = (msg.text || "").trim();
  if (msg.forward_from || msg.forward_from_chat) return;

  // Slash command aliases
  if (text === "/myorders") return handleMyOrders(chatId);
  if (text === "/help")     return sendHelp(chatId);
  if (text === "/shop")     return showProducts(chatId);
  if (text.startsWith("/")) return;

  try {
    const t = text.toLowerCase();

    if (t.includes("buy") || t.includes("shop")) {
      return await showProducts(chatId);
    }
    if (t.includes("help") || t.includes("how")) {
      return await sendHelp(chatId);
    }
    if (t.includes("order")) {
      return await handleMyOrders(chatId);
    }

    // Awaiting payment screenshot
    const state = userState[chatId];
    if (state && state.step === "awaiting_screenshot") {
      if (msg.photo || msg.document) {
        return await handlePayment(msg, state);
      } else {
        return bot.sendMessage(chatId,
          `<b>Screenshot Required</b>\n\n` +
          `Please send your GCash payment screenshot\nas a photo to complete your order.`,
          HTML
        );
      }
    }
  } catch (e) { console.error("message error:", e.message); }
});

// ─── CALLBACK QUERY ───────────────────────────────────────────────────────────
bot.on("callback_query", async (query) => {
  const chatId = query.message.chat.id;
  const msgId  = query.message.message_id;
  const data   = query.data;
  await bot.answerCallbackQuery(query.id).catch(() => {});

  try {
    if (data === "noop") return;

    if (data.startsWith("buy_")) {
      const pid     = data.replace("buy_", "");
      const db      = await getDB();
      const product = db.products[pid];
      if (!product) return bot.sendMessage(chatId, "Product not found.");

      const keysLeft = (db.keys[pid] || []).length;
      if (keysLeft === 0) {
        return bot.sendMessage(chatId,
          `<b>╔══════════════════════╗</b>\n` +
          `<b>    😔 OUT OF STOCK 😔    </b>\n` +
          `<b>╚══════════════════════╝</b>\n\n` +
          `<b>${h(product.name)}</b> is currently unavailable.\n🔄 Please try another product or check back later.`,
          HTML
        );
      }

      await bot.editMessageReplyMarkup({ inline_keyboard: [] }, { chat_id: chatId, message_id: msgId }).catch(() => {});

      // Ask user to choose: Container or Modded APK
      await bot.sendMessage(chatId,
        `<b>╔══════════════════════╗</b>\n` +
        `<b>   📂 SELECT CATEGORY   </b>\n` +
        `<b>╚══════════════════════╝</b>\n\n` +
        `  🎮 Product : <b>${h(product.name)}</b>\n` +
        `  💰 Price   : <b>P${product.price}</b>\n\n` +
        `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n` +
        `Please choose how you want to receive your product:`,
        {
          parse_mode: "HTML",
          reply_markup: {
            inline_keyboard: [[
              { text: "📦 Container",   callback_data: `cat_container_${pid}` },
              { text: "🤖 Modded APK",  callback_data: `cat_modapk_${pid}`    }
            ]]
          }
        }
      );
    }

    if (data.startsWith("cat_")) {
      // cat_container_PRODID  or  cat_modapk_PRODID
      const parts    = data.split("_");
      const category = parts[1];           // "container" or "modapk"
      const pid      = parts.slice(2).join("_");
      const db       = await getDB();
      const product  = db.products[pid];
      if (!product) return bot.sendMessage(chatId, "Product not found.");

      const keysLeft = (db.keys[pid] || []).length;
      if (keysLeft === 0) {
        return bot.sendMessage(chatId,
          `<b>Out of stock.</b> Please try another product.`, HTML
        );
      }

      userState[chatId] = { step: "awaiting_screenshot", selectedProduct: product, selectedCategory: category };
      await bot.editMessageReplyMarkup({ inline_keyboard: [] }, { chat_id: chatId, message_id: msgId }).catch(() => {});

      const dbSettings = await getDB().catch(()=>({settings:{}}));
      const qrFileId   = dbSettings.settings?.qrFileId || process.env.QR_FILE_ID || null;
      const catLabel  = category === "modapk" ? "🤖 Modded APK" : "📦 Container";

      const summaryText =
        `<b>╔══════════════════════╗</b>\n` +
        `<b>   🧾 ORDER SUMMARY 🧾   </b>\n` +
        `<b>╚══════════════════════╝</b>\n\n` +
        `  🎮 Product  : <b>${h(product.name)}</b>\n` +
        `  📂 Category : <b>${catLabel}</b>\n` +
        `  💰 Price    : <b>P${product.price}</b>\n` +
        `  📦 Stock    : ${keysLeft} key${keysLeft !== 1 ? "s" : ""} left\n\n` +
        `<b>━━━ 💳 PAYMENT QR CODE 💳 ━━━</b>\n\n` +
        `Scan the QR code below and send <b>P${product.price}</b>.\n\n` +
        `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n` +
        `📸 After paying, send your <b>payment screenshot</b> here.\n` +
        `🔑 Your key will be delivered after verification.`;

      if (qrFileId) {
        await bot.sendPhoto(chatId, qrFileId, { caption: summaryText, parse_mode: "HTML" });
      } else {
        await bot.sendMessage(chatId, summaryText, HTML);
      }
    }

    if (data.startsWith("approve_")) {
      if (String(chatId) !== String(ADMIN_ID)) return;
      await processApproval(data.replace("approve_", ""), chatId, msgId);
    }

    if (data.startsWith("reject_")) {
      if (String(chatId) !== String(ADMIN_ID)) return;
      await processRejection(data.replace("reject_", ""), chatId, msgId);
    }
  } catch (e) { console.error("callback error:", e.message); }
});

// ─── HANDLE PAYMENT ───────────────────────────────────────────────────────────
async function handlePayment(msg, state) {
  const chatId   = msg.chat.id;
  const product  = state.selectedProduct;
  const category = state.selectedCategory || "container";
  const db       = await getDB();
  const orderId  = `ORD-${Date.now()}`;

  const order = {
    id:          orderId,
    buyerId:     chatId,
    buyerName:   msg.from.first_name || "",
    buyerUser:   msg.from.username ? `@${msg.from.username}` : String(chatId),
    productId:   product.id,
    productName: product.name,
    amount:      product.price,
    category:    category,
    status:      "pending",
    screenshotFileId: msg.photo
      ? msg.photo[msg.photo.length - 1].file_id
      : (msg.document?.file_id || null),
    createdAt: new Date().toISOString(),
  };

  db.orders[orderId] = order;
  await saveDB(db);

  // Confirm to buyer
  await bot.sendMessage(chatId,
    `<b>╔══════════════════════╗</b>\n` +
    `<b>  ✅ PAYMENT RECEIVED! ✅  </b>\n` +
    `<b>╚══════════════════════╝</b>\n\n` +
    `🎉 Your order has been submitted!\n\n` +
    `  🆔 Order ID  : <code>${h(orderId)}</code>\n` +
    `  📅 Submitted : ${h(phTime(order.createdAt))}\n` +
    `  📌 Status    : <b>⏳ Under Review</b>\n\n` +
    `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n` +
    `🔑 You will receive your key once approved.\n` +
    `⚡ Average wait: under 5 minutes.`,
    HTML
  );

  const catLabel = category === "modapk" ? "🤖 Modded APK" : "📦 Container";
  const adminMsg =
    `<b>╔══════════════════════╗</b>\n` +
    `<b>   🔔 NEW ORDER! 🔔   </b>\n` +
    `<b>╚══════════════════════╝</b>\n\n` +
    `  👤 Buyer    : ${h(order.buyerUser)}\n` +
    `  🆔 User ID  : <code>${chatId}</code>\n` +
    `  🎮 Product  : <b>${h(product.name)}</b>\n` +
    `  📂 Category : <b>${catLabel}</b>\n` +
    `  💰 Amount   : <b>P${product.price}</b>\n` +
    `  📋 Order ID : <code>${h(orderId)}</code>\n` +
    `  📅 Time     : ${h(phTime(order.createdAt))}\n\n` +
    `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>`;

  const keyboard = {
    inline_keyboard: [[
      { text: "APPROVE", callback_data: `approve_${orderId}` },
      { text: "REJECT",  callback_data: `reject_${orderId}`  }
    ]]
  };

  if (order.screenshotFileId) {
    await bot.sendPhoto(ADMIN_ID, order.screenshotFileId, {
      caption: adminMsg, parse_mode: "HTML", reply_markup: keyboard
    });
  } else {
    await bot.sendMessage(ADMIN_ID, adminMsg, { parse_mode: "HTML", reply_markup: keyboard });
  }

  if (CHANNEL_ID) {
    await bot.sendMessage(CHANNEL_ID, adminMsg, { parse_mode: "HTML" }).catch(() => {});
  }

  delete userState[chatId];
}

// ─── APPROVE ──────────────────────────────────────────────────────────────────
async function processApproval(orderId, adminChatId, msgId) {
  const db    = await getDB();
  const order = db.orders[orderId];
  if (!order)                     return bot.sendMessage(adminChatId, "Order not found.");
  if (order.status !== "pending") return bot.sendMessage(adminChatId, "Already processed.");

  const keys = db.keys[order.productId] || [];
  if (keys.length === 0) {
    return bot.sendMessage(adminChatId,
      `No keys left for <b>${h(order.productName)}</b>. Add more keys in the admin panel.`,
      HTML
    );
  }

  const key = keys.shift();
  db.keys[order.productId] = keys;
  order.status     = "approved";
  order.key        = key;
  order.approvedAt = new Date().toISOString();
  await saveDB(db);

  if (msgId) {
    await bot.editMessageReplyMarkup(
      { inline_keyboard: [[{ text: "APPROVED", callback_data: "done" }]] },
      { chat_id: adminChatId, message_id: msgId }
    ).catch(() => {});
  }

  const product = db.products[order.productId];
  const apkDownloadLink   = product?.apkDownloadLink   || null;
  const containerFileId   = product?.containerFileId   || null;
  const containerFileName = product?.containerFileName || "container";
  const isModApk = order.category === "modapk";

  // Send delivery message to buyer
  if (isModApk && apkDownloadLink) {
    // Modded APK: send download link + key
    await bot.sendMessage(order.buyerId,
      `<b>╔══════════════════════╗</b>\n` +
      `<b>  🎉 ORDER APPROVED! 🎉  </b>\n` +
      `<b>╚══════════════════════╝</b>\n\n` +
      `Your order for <b>${h(order.productName)}</b> is ready!\n\n` +
      `<b>━━━ 🤖 MODDED APK LINK 🤖 ━━━</b>\n` +
      `${apkDownloadLink}\n` +
      `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n` +
      `<b>🔑 Your Key:</b>\n` +
      `<code>${h(key)}</code>\n\n` +
      `  ✅ Approved: ${h(phTime(order.approvedAt))}\n\n` +
      `👆 Tap the key above to copy it.\n💙 Thank you for your purchase!`,
      HTML
    );
  } else {
    // Container: send key message first
    await bot.sendMessage(order.buyerId,
      `<b>╔══════════════════════╗</b>\n` +
      `<b>  🎉 ORDER APPROVED! 🎉  </b>\n` +
      `<b>╚══════════════════════╝</b>\n\n` +
      `Your order for <b>${h(order.productName)}</b> is ready!\n\n` +
      `<b>━━━━━ 🔑 YOUR KEY 🔑 ━━━━━</b>\n` +
      `<code>${h(key)}</code>\n` +
      `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n\n` +
      (containerFileId ? `📦 Container file is attached below.\n` : ``) +
      `  ✅ Approved: ${h(phTime(order.approvedAt))}\n\n` +
      `👆 Tap the key above to copy it.\n💙 Thank you for your purchase!`,
      HTML
    );
    // Auto-send container file if attached
    if (containerFileId) {
      await bot.sendDocument(order.buyerId, containerFileId, {
        caption:
          `<b>📦 Container — ${h(order.productName)}</b>\n` +
          `Use this file with your key.`,
        parse_mode: "HTML"
      });
    }
  }

  await bot.sendMessage(adminChatId,
    `✅ Delivered to ${h(order.buyerUser)}\n🔑 Key: <code>${h(key)}</code>` +
    (isModApk && apkDownloadLink ? `\n🤖 APK link sent` : ``) +
    (!isModApk && containerFileId ? `\n📦 Container file sent` : ``),
    HTML
  );
}

// ─── REJECT ───────────────────────────────────────────────────────────────────
async function processRejection(orderId, adminChatId, msgId) {
  const db    = await getDB();
  const order = db.orders[orderId];
  if (!order)                     return bot.sendMessage(adminChatId, "Order not found.");
  if (order.status !== "pending") return bot.sendMessage(adminChatId, "Already processed.");

  order.status     = "rejected";
  order.rejectedAt = new Date().toISOString();
  await saveDB(db);

  if (msgId) {
    await bot.editMessageReplyMarkup(
      { inline_keyboard: [[{ text: "REJECTED", callback_data: "done" }]] },
      { chat_id: adminChatId, message_id: msgId }
    ).catch(() => {});
  }

  await bot.sendMessage(order.buyerId,
    `<b>╔══════════════════════╗</b>\n` +
    `<b>   ❌ ORDER DECLINED ❌   </b>\n` +
    `<b>╚══════════════════════╝</b>\n\n` +
    `😔 Your payment could not be verified.\n\n` +
    `  🆔 Order ID : <code>${h(orderId)}</code>\n` +
    `  📅 Reviewed : ${h(phTime(order.rejectedAt))}\n\n` +
    `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n` +
    `💬 If you believe this is an error,\ncontact support with your payment screenshot.`,
    HTML
  );
}

bot.on("polling_error", (err) => console.error("Polling error:", err.message));

// ─── EXPRESS API ─────────────────────────────────────────────────────────────
const app = express();

app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin",  "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Accept, Authorization, Origin");
  res.setHeader("Access-Control-Max-Age",       "86400");
  if (req.method === "OPTIONS") return res.status(200).end();
  next();
});

app.use(express.json());

app.get("/",       (req, res) => res.sendFile(path.join(__dirname, "index.html")));
app.get("/admin",  (req, res) => res.sendFile(path.join(__dirname, "index.html")));
app.get("/health", (req, res) => res.json({ status: "ok", uptime: process.uptime() }));

app.get("/api/botinfo", async (req, res) => {
  try {
    const info = await bot.getMe();
    res.json({ ok: true, username: info.username, name: info.first_name, id: info.id, adminId: ADMIN_ID });
  } catch (e) { res.status(500).json({ ok: false, error: e.message }); }
});

app.get("/api/orders", async (req, res) => {
  try { const db = await getDB(); res.json(Object.values(db.orders).reverse()); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

app.post("/api/orders/:id/approve", async (req, res) => {
  try { await processApproval(req.params.id, ADMIN_ID, null); res.json({ ok: true }); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

app.post("/api/orders/:id/reject", async (req, res) => {
  try { await processRejection(req.params.id, ADMIN_ID, null); res.json({ ok: true }); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

app.get("/api/products", async (req, res) => {
  try { const db = await getDB(); res.json(Object.values(db.products)); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

app.post("/api/products", async (req, res) => {
  try {
    const db = await getDB();
    const { name, price, emoji, description, category } = req.body;
    if (!name || !price) return res.status(400).json({ error: "name and price required" });
    const pid = `PROD-${Date.now()}`;
    db.products[pid] = {
      id: pid, name, price: Number(price),
      emoji: emoji || "🔑", description: description || "",
      category: category || "Other", active: true
    };
    await saveDB(db);
    res.json(db.products[pid]);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Store container file_id for a product
app.put("/api/products/:id/container", async (req, res) => {
  try {
    const db = await getDB();
    const p = db.products[req.params.id];
    if (!p) return res.status(404).json({ error: "not found" });
    p.containerFileId   = req.body.containerFileId || null;
    p.containerFileName = req.body.containerFileName || null;
    await saveDB(db);
    res.json(p);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Store APK download link for a product (Modded APK category)
app.put("/api/products/:id/apk", async (req, res) => {
  try {
    const db = await getDB();
    const p = db.products[req.params.id];
    if (!p) return res.status(404).json({ error: "not found" });
    p.apkDownloadLink = req.body.apkDownloadLink || null;
    p.apkFileName     = req.body.apkFileName || null;
    await saveDB(db);
    res.json(p);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.put("/api/products/:id/toggle", async (req, res) => {
  try {
    const db = await getDB();
    const p = db.products[req.params.id];
    if (!p) return res.status(404).json({ error: "not found" });
    p.active = req.body.active !== false;
    await saveDB(db);
    res.json(p);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.delete("/api/products/:id", async (req, res) => {
  try {
    const db = await getDB();
    delete db.products[req.params.id];
    delete db.keys[req.params.id];
    await saveDB(db);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.get("/api/keys/:productId", async (req, res) => {
  try { const db = await getDB(); res.json({ keys: db.keys[req.params.productId] || [] }); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

app.post("/api/keys/:productId", async (req, res) => {
  try {
    const db  = await getDB();
    const pid = req.params.productId;
    const newKeys = (req.body.keys || "").split("\n").map(k => k.trim()).filter(Boolean);
    if (!newKeys.length) return res.status(400).json({ error: "no keys provided" });
    db.keys[pid] = [...(db.keys[pid] || []), ...newKeys];
    await saveDB(db);
    res.json({ count: db.keys[pid].length });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.delete("/api/keys/:productId", async (req, res) => {
  try {
    const db = await getDB();
    db.keys[req.params.productId] = [];
    await saveDB(db);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post("/api/broadcast", async (req, res) => {
  try {
    const db = await getDB();
    const { message, parse_mode } = req.body;
    if (!message) return res.status(400).json({ error: "message required" });
    const buyers = [...new Set(Object.values(db.orders).map(o => o.buyerId).filter(Boolean))];
    let sent = 0, failed = 0;
    for (const id of buyers) {
      try {
        await bot.sendMessage(id, message, parse_mode ? { parse_mode } : {});
        sent++;
      } catch { failed++; }
    }
    res.json({ sent, failed });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.put("/api/settings/qr", async (req, res) => {
  try {
    const db = await getDB();
    db.settings.qrFileId = req.body.qrFileId || null;
    await saveDB(db);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.get("/api/settings", async (req, res) => {
  try {
    const db = await getDB();
    res.json(db.settings || {});
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// ─── SERVER START ─────────────────────────────────────────────────────────────
app.listen(PORT, async () => {
  console.log(`Server running on port ${PORT}`);

  if (WEBHOOK_HOST) {
    // Register the webhook endpoint on Express — same port as admin panel
    const webhookPath = `/webhook/${BOT_TOKEN}`;
    app.post(webhookPath, (req, res) => {
      bot.processUpdate(req.body);
      res.sendStatus(200);
    });

    // Tell Telegram where to send updates
    const webhookUrl = `https://${WEBHOOK_HOST}${webhookPath}`;
    try {
      await bot.setWebHook(webhookUrl);
      console.log(`Webhook set: ${webhookUrl}`);
    } catch(e) {
      console.error("Webhook error:", e.message);
    }

    // Silent keep-alive ping every 5 min
    setInterval(() => {
      require("https").get(`https://${WEBHOOK_HOST}/health`, () => {}).on("error", () => {});
    }, 5 * 60 * 1000);

  } else {
    console.log("Polling mode (local dev)");
  }
});
