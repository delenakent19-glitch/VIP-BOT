/**
 * ╔══════════════════════════════════════════════════════╗
 * ║        TELEGRAM KEY SELLER BOT  –  bot.js           ║
 * ║  Full order + auto-delivery system                   ║
 * ╚══════════════════════════════════════════════════════╝
 *
 * SETUP:
 *   1. npm install node-telegram-bot-api express fs-extra dotenv
 *   2. Copy .env.example → .env and fill values
 *   3. node bot.js
 *
 * HOW IT WORKS:
 *   Buyer → /buy → picks product → sends payment screenshot
 *   Admin → sees order in admin panel or Telegram → clicks Approve
 *   Bot → automatically DMs the key to the buyer
 */

require("dotenv").config();
const TelegramBot = require("node-telegram-bot-api");
const express = require("express");
const fs = require("fs-extra");
const path = require("path");
const cors = require("cors");

// ─── Config ──────────────────────────────────────────────────────────────────
const BOT_TOKEN   = process.env.BOT_TOKEN;       // Your bot token from @BotFather
const ADMIN_ID    = process.env.ADMIN_ID;         // Your Telegram user ID (number)
const CHANNEL_ID  = process.env.CHANNEL_ID || ""; // Optional broadcast channel (e.g. -100xxx)
const PORT        = process.env.PORT || 3000;
const DB_FILE     = "./data/db.json";

if (!BOT_TOKEN || !ADMIN_ID) {
  console.error("❌  Missing BOT_TOKEN or ADMIN_ID in .env");
  process.exit(1);
}

// ─── Database (JSON file – swap for real DB later) ────────────────────────────
async function loadDB() {
  await fs.ensureFile(DB_FILE);
  const raw = await fs.readFile(DB_FILE, "utf8").catch(() => "{}");
  try { return JSON.parse(raw); } catch { return {}; }
}

async function saveDB(db) {
  await fs.ensureDir(path.dirname(DB_FILE));
  await fs.writeFile(DB_FILE, JSON.stringify(db, null, 2));
}

async function getDB() {
  const db = await loadDB();
  if (!db.products) db.products = {};
  if (!db.orders)   db.orders   = {};
  if (!db.keys)     db.keys     = {}; // { productId: ["KEY1","KEY2",...] }
  return db;
}

// ─── Bot ─────────────────────────────────────────────────────────────────────
const bot = new TelegramBot(BOT_TOKEN, { polling: true });

// User state machine: tracks where each user is in the purchase flow
const userState = {}; // { chatId: { step, selectedProduct, orderId } }

// ─── /start ──────────────────────────────────────────────────────────────────
bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  const name = msg.from.first_name || "there";

  await bot.sendMessage(chatId,
    `👋 Hello *${name}*\\!\n\nWelcome to our *Key Shop* 🔑\n\nUse the menu below to browse and buy keys\\.`,
    {
      parse_mode: "MarkdownV2",
      reply_markup: {
        keyboard: [
          [{ text: "🛒 Buy Key" }, { text: "📦 My Orders" }],
          [{ text: "ℹ️ Help" }]
        ],
        resize_keyboard: true
      }
    }
  );
});

// ─── /products or "Buy Key" ───────────────────────────────────────────────────
async function showProducts(chatId) {
  const db = await getDB();
  const products = Object.values(db.products).filter(p => p.active);

  if (products.length === 0) {
    return bot.sendMessage(chatId, "😔 No products available right now\\. Check back soon\\!", { parse_mode: "MarkdownV2" });
  }

  const buttons = products.map(p => ([{
    text: `${p.emoji || "🔑"} ${p.name} — ₱${p.price}`,
    callback_data: `buy_${p.id}`
  }]));

  await bot.sendMessage(chatId, "🛍️ *Choose a product:*", {
    parse_mode: "MarkdownV2",
    reply_markup: { inline_keyboard: buttons }
  });
}

bot.onText(/\/products/, (msg) => showProducts(msg.chat.id));

// /help command
bot.onText(/\/help/, (msg) => sendHelp(msg.chat.id));

async function sendHelp(chatId) {
  try {
    await bot.sendMessage(chatId,
      "🆘 *Help*\n\n" +
      "1\\. Press *🛒 Buy Key* to see products\n" +
      "2\\. Select a product and follow instructions\n" +
      "3\\. Send your GCash payment screenshot\n" +
      "4\\. Wait for admin approval \\(usually fast\\!\\)\n" +
      "5\\. Your key will be sent automatically 🔑\n\n" +
      "Questions? Contact the admin\\.",
      { parse_mode: "MarkdownV2" }
    );
  } catch (err) {
    console.error("Help error:", err.message);
  }
}

bot.on("message", async (msg) => {
  const chatId = msg.chat.id;
  const text = msg.text || "";

  // Ignore all commands — handled by onText above
  if (text.startsWith("/")) return;

  // Ignore forwarded messages and channels
  if (msg.forward_from || msg.forward_from_chat) return;

  try {
    if (text === "🛒 Buy Key") return await showProducts(chatId);

    if (text === "📦 My Orders") {
      const db = await getDB();
      const myOrders = Object.values(db.orders)
        .filter(o => String(o.buyerId) === String(chatId))
        .slice(-5)
        .reverse();

      if (myOrders.length === 0) {
        return bot.sendMessage(chatId, "You have no orders yet\\. Use *🛒 Buy Key* to get started\\!", { parse_mode: "MarkdownV2" });
      }

      let reply = "📦 *Your recent orders:*\n\n";
      for (const o of myOrders) {
        const icon = o.status === "approved" ? "✅" : o.status === "rejected" ? "❌" : "⏳";
        reply += `${icon} *${escMd(o.productName)}* — ₱${o.amount}\n`;
        reply += `   ID: \`${escMd(o.id)}\` · ${escMd(o.status.toUpperCase())}\n`;
        if (o.key) reply += `   🔑 Key: \`${escMd(o.key)}\`\n`;
        reply += "\n";
      }
      return bot.sendMessage(chatId, reply, { parse_mode: "MarkdownV2" });
    }

    if (text === "ℹ️ Help") return await sendHelp(chatId);

    // Handle payment screenshot upload
    const state = userState[chatId];
    if (state && state.step === "awaiting_screenshot") {
      if (msg.photo || msg.document) {
        return await handlePaymentReceived(msg, state);
      } else {
        return bot.sendMessage(chatId, "📸 Please send your *payment screenshot* as a photo\\.", { parse_mode: "MarkdownV2" });
      }
    }

  } catch (err) {
    console.error("Message handler error:", err.message);
  }
});

// ─── Product selected (inline button) ────────────────────────────────────────
bot.on("callback_query", async (query) => {
  const chatId  = query.message.chat.id;
  const data    = query.data;
  const msgId   = query.message.message_id;

  await bot.answerCallbackQuery(query.id);

  // ── Buy product ──
  if (data.startsWith("buy_")) {
    const productId = data.replace("buy_", "");
    const db = await getDB();
    const product = db.products[productId];

    if (!product) return bot.sendMessage(chatId, "Product not found.");

    const keysLeft = (db.keys[productId] || []).length;
    if (keysLeft === 0) {
      return bot.sendMessage(chatId, `😔 *${escMd(product.name)}* is out of stock\\! Please try again later\\.`, { parse_mode: "MarkdownV2" });
    }

    userState[chatId] = { step: "awaiting_screenshot", selectedProduct: product };

    await bot.editMessageReplyMarkup({ inline_keyboard: [] }, { chat_id: chatId, message_id: msgId }).catch(() => {});

    await bot.sendMessage(chatId,
      `✅ Great choice\\!\n\n` +
      `🔑 *${escMd(product.name)}*\n` +
      `💰 Price: *₱${product.price}*\n` +
      `📦 Stock: ${keysLeft} available\n\n` +
      `*Payment Instructions:*\n` +
      `Send *₱${product.price}* via GCash to:\n` +
      `📱 \`${escMd(process.env.GCASH_NUMBER || "09XX-XXX-XXXX")}\`\n` +
      `👤 ${escMd(process.env.GCASH_NAME || "Your Name")}\n\n` +
      `📸 After paying, send your *screenshot here*\\.`,
      { parse_mode: "MarkdownV2" }
    );
    return;
  }

  // ── Admin: Approve order ──
  if (data.startsWith("approve_")) {
    if (String(chatId) !== String(ADMIN_ID)) return;
    const orderId = data.replace("approve_", "");
    await processApproval(orderId, chatId, msgId);
    return;
  }

  // ── Admin: Reject order ──
  if (data.startsWith("reject_")) {
    if (String(chatId) !== String(ADMIN_ID)) return;
    const orderId = data.replace("reject_", "");
    await processRejection(orderId, chatId, msgId);
    return;
  }
});

// ─── Payment screenshot received ─────────────────────────────────────────────
async function handlePaymentReceived(msg, state) {
  const chatId  = msg.chat.id;
  const product = state.selectedProduct;
  const db      = await getDB();

  // Create order
  const orderId = `ORD-${Date.now()}`;
  const order = {
    id:          orderId,
    buyerId:     chatId,
    buyerName:   msg.from.first_name || "",
    buyerUser:   msg.from.username ? `@${msg.from.username}` : String(chatId),
    productId:   product.id,
    productName: product.name,
    amount:      product.price,
    status:      "pending",
    screenshotFileId: msg.photo ? msg.photo[msg.photo.length - 1].file_id : (msg.document?.file_id || null),
    createdAt:   new Date().toISOString(),
  };

  db.orders[orderId] = order;
  await saveDB(db);

  // Confirm to buyer
  await bot.sendMessage(chatId,
    `✅ *Payment received\\!*\n\n` +
    `Your order \`${orderId}\` is under review\\.\n` +
    `You'll receive your key shortly once approved 🔑`,
    { parse_mode: "MarkdownV2" }
  );

  // Notify admin
  const adminMsg =
    `💰 *NEW ORDER REQUEST*\n\n` +
    `👤 User: ${escMd(order.buyerUser)}\n` +
    `🆔 User ID: \`${chatId}\`\n` +
    `📦 Product: 🔑 *${escMd(product.name)}*\n` +
    `💵 AMOUNT: ₱${product.price}\n` +
    `🕐 Time: ${new Date().toLocaleString()}\n` +
    `📋 Order ID: \`${orderId}\``;

  const adminKeyboard = {
    inline_keyboard: [[
      { text: "✅ APPROVE", callback_data: `approve_${orderId}` },
      { text: "❌ REJECT",  callback_data: `reject_${orderId}`  }
    ]]
  };

  // Send screenshot + buttons to admin
  if (order.screenshotFileId) {
    await bot.sendPhoto(ADMIN_ID, order.screenshotFileId, {
      caption: adminMsg,
      parse_mode: "MarkdownV2",
      reply_markup: adminKeyboard
    });
  } else {
    await bot.sendMessage(ADMIN_ID, adminMsg, {
      parse_mode: "MarkdownV2",
      reply_markup: adminKeyboard
    });
  }

  // Broadcast to channel if set
  if (CHANNEL_ID) {
    await bot.sendMessage(CHANNEL_ID, adminMsg, { parse_mode: "MarkdownV2" }).catch(() => {});
  }

  delete userState[chatId];
}

// ─── Approve ─────────────────────────────────────────────────────────────────
async function processApproval(orderId, adminChatId, msgId) {
  const db = await getDB();
  const order = db.orders[orderId];
  if (!order) return bot.sendMessage(adminChatId, "Order not found.");
  if (order.status !== "pending") return bot.sendMessage(adminChatId, "Order already processed.");

  // Pop a key
  const keys = db.keys[order.productId] || [];
  if (keys.length === 0) {
    await bot.sendMessage(adminChatId, `⚠️ No keys left for *${order.productName}*\\! Please add more keys in the admin panel\\.`, { parse_mode: "MarkdownV2" });
    return;
  }

  const key = keys.shift();
  db.keys[order.productId] = keys;
  order.status  = "approved";
  order.key     = key;
  order.approvedAt = new Date().toISOString();
  await saveDB(db);

  // Edit admin message
  await bot.editMessageCaption
    ? bot.editMessageCaption(`✅ APPROVED — Key delivered\n\nOrder: ${orderId}`, { chat_id: adminChatId, message_id: msgId }).catch(() => {})
    : null;

  await bot.editMessageReplyMarkup({ inline_keyboard: [[{ text: "✅ APPROVED", callback_data: "noop" }]] },
    { chat_id: adminChatId, message_id: msgId }).catch(() => {});

  // DM the key to buyer
  await bot.sendMessage(order.buyerId,
    `🎉 *Your order has been approved\\!*\n\n` +
    `Here is your key for *${escMd(order.productName)}*:\n\n` +
    `\`${escMd(key)}\`\n\n` +
    `Copy it by tapping the code above\\. Thank you for your purchase\\! 🙏`,
    { parse_mode: "MarkdownV2" }
  );

  await bot.sendMessage(adminChatId, `✅ Key delivered to ${order.buyerUser}: \`${key}\``, { parse_mode: "MarkdownV2" });
}

// ─── Reject ───────────────────────────────────────────────────────────────────
async function processRejection(orderId, adminChatId, msgId) {
  const db = await getDB();
  const order = db.orders[orderId];
  if (!order) return bot.sendMessage(adminChatId, "Order not found.");
  if (order.status !== "pending") return bot.sendMessage(adminChatId, "Order already processed.");

  order.status = "rejected";
  order.rejectedAt = new Date().toISOString();
  await saveDB(db);

  await bot.editMessageReplyMarkup({ inline_keyboard: [[{ text: "❌ REJECTED", callback_data: "noop" }]] },
    { chat_id: adminChatId, message_id: msgId }).catch(() => {});

  await bot.sendMessage(order.buyerId,
    `❌ *Your order was rejected\\.*\n\n` +
    `Order ID: \`${orderId}\`\n\n` +
    `If you believe this is a mistake, please contact support\\.`,
    { parse_mode: "MarkdownV2" }
  );

  await bot.sendMessage(adminChatId, `❌ Order ${orderId} rejected.`);
}

// ─── REST API for Admin Panel ─────────────────────────────────────────────────
const app = express();

// CORS — must be FIRST before anything else
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, DELETE, PUT, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Origin, X-Requested-With, Content-Type, Accept, Authorization");
  res.setHeader("Access-Control-Max-Age", "86400");
  if (req.method === "OPTIONS") {
    res.status(200).end();
    return;
  }
  next();
});

app.use(express.json());

// Health check
app.get("/", (req, res) => res.json({ status: "ok", bot: "running", uptime: process.uptime() }));
app.get("/health", (req, res) => res.json({ status: "ok", bot: "running", uptime: process.uptime() }));

// Bot info — admin panel uses this to confirm bot is live
app.get("/api/botinfo", async (req, res) => {
  try {
    const info = await bot.getMe();
    res.json({ ok: true, username: info.username, name: info.first_name, id: info.id });
  } catch (err) {
    res.status(500).json({ ok: false, error: err.message });
  }
});

// Self-ping every 4 minutes to prevent Render free tier sleep
const SELF_URL = process.env.RENDER_EXTERNAL_URL || "https://telehostingerg-dypv.onrender.com";
setInterval(async () => {
  try {
    const http = require("https");
    http.get(SELF_URL + "/health", (r) => {
      console.log("✅ Keep-alive ping:", r.statusCode);
    }).on("error", (e) => {
      console.log("⚠️ Keep-alive ping failed:", e.message);
    });
  } catch (e) {
    console.log("⚠️ Keep-alive error:", e.message);
  }
}, 4 * 60 * 1000);

// GET /api/orders
app.get("/api/orders", async (req, res) => {
  try {
    const db = await getDB();
    res.json(Object.values(db.orders).reverse());
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/orders/:id/approve
app.post("/api/orders/:id/approve", async (req, res) => {
  try {
    await processApproval(req.params.id, ADMIN_ID, null);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/orders/:id/reject
app.post("/api/orders/:id/reject", async (req, res) => {
  try {
    await processRejection(req.params.id, ADMIN_ID, null);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// GET /api/products
app.get("/api/products", async (req, res) => {
  try {
    const db = await getDB();
    res.json(Object.values(db.products));
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/products
app.post("/api/products", async (req, res) => {
  try {
    const db = await getDB();
    const { id, name, price, emoji, description } = req.body;
    if (!name || !price) return res.status(400).json({ error: "name and price required" });
    const pid = id || `PROD-${Date.now()}`;
    db.products[pid] = { id: pid, name, price: Number(price), emoji: emoji || "🔑", description: description || "", active: true };
    await saveDB(db);
    res.json(db.products[pid]);
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// DELETE /api/products/:id
app.delete("/api/products/:id", async (req, res) => {
  try {
    const db = await getDB();
    delete db.products[req.params.id];
    delete db.keys[req.params.id];
    await saveDB(db);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// GET /api/keys/:productId
app.get("/api/keys/:productId", async (req, res) => {
  try {
    const db = await getDB();
    res.json({ keys: db.keys[req.params.productId] || [] });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/keys/:productId
app.post("/api/keys/:productId", async (req, res) => {
  try {
    const db = await getDB();
    const pid = req.params.productId;
    const newKeys = (req.body.keys || "").split("\n").map(k => k.trim()).filter(Boolean);
    if (!newKeys.length) return res.status(400).json({ error: "no keys provided" });
    db.keys[pid] = [...(db.keys[pid] || []), ...newKeys];
    await saveDB(db);
    res.json({ count: db.keys[pid].length });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// DELETE /api/keys/:productId
app.delete("/api/keys/:productId", async (req, res) => {
  try {
    const db = await getDB();
    db.keys[req.params.productId] = [];
    await saveDB(db);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// POST /api/broadcast
app.post("/api/broadcast", async (req, res) => {
  try {
    const db = await getDB();
    const { message } = req.body;
    if (!message) return res.status(400).json({ error: "message required" });
    const uniqueBuyers = [...new Set(Object.values(db.orders).map(o => o.buyerId))];
    let sent = 0, failed = 0;
    for (const id of uniqueBuyers) {
      try { await bot.sendMessage(id, message); sent++; }
      catch { failed++; }
    }
    res.json({ sent, failed });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.listen(PORT, () => console.log(`\n🚀 Admin API running at http://localhost:${PORT}\n`));

// ─── Helpers ─────────────────────────────────────────────────────────────────
function escMd(text) {
  return String(text).replace(/[_*[\]()~`>#+\-=|{}.!\\]/g, "\\$&");
}

bot.on("polling_error", (err) => console.error("Polling error:", err.message));
console.log("🤖 Bot is running...");
