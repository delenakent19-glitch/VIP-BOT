/**
 * KEY SELLER BOT — Railway Deployment
 * Upload: index.js + package.json to GitHub → connect to Railway
 * Variables: BOT_TOKEN, ADMIN_ID, GCASH_NUMBER, GCASH_NAME
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
  console.error("❌ Missing BOT_TOKEN or ADMIN_ID in environment variables");
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
  return db;
}

async function saveDB(db) {
  await fs.ensureDir(path.dirname(DB_FILE));
  await fs.writeFile(DB_FILE, JSON.stringify(db, null, 2));
}

// ─── BOT ─────────────────────────────────────────────────────────────────────
const bot = new TelegramBot(BOT_TOKEN, { polling: true });
const userState = {};

function escMd(text) {
  return String(text || "").replace(/[_*[\]()~`>#+\-=|{}.!\\]/g, "\\$&");
}

// /start
bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  const name   = msg.from.first_name || "there";
  try {
    await bot.sendMessage(chatId,
      `🎮 *Hello, ${escMd(name)}!*\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
      `Welcome to *Zeijie Order Bot* —\n` +
      `your trusted store for premium game keys\.\n\n` +
      `✅ Instant key delivery after approval\n` +
      `💳 GCash payment accepted\n` +
      `⚡ Fast, secure & reliable\n\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
      `Tap *Shop Now* to browse available keys\.`,
      {
        parse_mode: "MarkdownV2",
        reply_markup: {
          keyboard: [
            [{ text: "🛒 Shop Now" }, { text: "📦 My Orders" }],
            [{ text: "ℹ️ How It Works" }]
          ],
          resize_keyboard: true
        }
      }
    );
  } catch (e) { console.error("start error:", e.message); }
});

// /help
bot.onText(/\/help/, (msg) => sendHelp(msg.chat.id));

async function sendHelp(chatId) {
  try {
    await bot.sendMessage(chatId,
      `ℹ️ *How It Works*\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
      `*Step 1* — Browse 🛒\n` +
      `Tap *Shop Now* and pick your product\.\n\n` +
      `*Step 2* — Pay 💳\n` +
      `Send payment via *GCash* to the number shown\.\n\n` +
      `*Step 3* — Screenshot 📸\n` +
      `Send your payment screenshot in this chat\.\n\n` +
      `*Step 4* — Wait ⏳\n` +
      `Admin reviews within *5 minutes* on average\.\n\n` +
      `*Step 5* — Receive 🔑\n` +
      `Your key will be delivered here automatically\!\n\n` +
      `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
      `Need help\? Contact the admin directly\.`,
      { parse_mode: "MarkdownV2" }
    );
  } catch (e) { console.error("help error:", e.message); }
}

// Show products grouped by category
async function showProducts(chatId) {
  try {
    const db = await getDB();
    const products = Object.values(db.products).filter(p => p.active);
    if (products.length === 0) {
      return bot.sendMessage(chatId,
        `⚠️ *No Products Available*\n\n` +
        `We are currently restocking\.\n` +
        `Please check back soon\!`,
        { parse_mode: "MarkdownV2" }
      );
    }

    // Group by category
    const grouped = {};
    for (const p of products) {
      const cat = p.category || "Other";
      if (!grouped[cat]) grouped[cat] = [];
      grouped[cat].push(p);
    }

    // Build inline keyboard with category headers
    const inline_keyboard = [];
    for (const [cat, items] of Object.entries(grouped)) {
      inline_keyboard.push([{ text: `┌─ 🎮  ${cat}  ─┐`, callback_data: "noop" }]);
      for (const p of items) {
        inline_keyboard.push([{
          text: `${p.emoji || "🔑"} ${p.name} — ₱${p.price}`,
          callback_data: `buy_${p.id}`
        }]);
      }
    }

    await bot.sendMessage(chatId, "🛍️ *Choose a product:*", {
      parse_mode: "MarkdownV2",
      reply_markup: { inline_keyboard }
    });
  } catch (e) { console.error("showProducts error:", e.message); }
}

// Message handler
bot.on("message", async (msg) => {
  const chatId = msg.chat.id;
  const text   = msg.text || "";
  if (text.startsWith("/")) return;
  if (msg.forward_from || msg.forward_from_chat) return;

  try {
    if (text === "🛒 Shop Now" || text === "🛒 Buy Key")  return await showProducts(chatId);
    if (text === "ℹ️ How It Works" || text === "ℹ️ Help") return await sendHelp(chatId);

    if (text === "📦 My Orders") {
      const db = await getDB();
      const myOrders = Object.values(db.orders)
        .filter(o => String(o.buyerId) === String(chatId))
        .slice(-5).reverse();

      if (!myOrders.length) {
        return bot.sendMessage(chatId,
          `📭 *No Orders Yet*\n\n` +
          `You have not placed any orders\.\n` +
          `Tap *Shop Now* to browse products\!`,
          { parse_mode: "MarkdownV2" }
        );
      }
      let reply = `📦 *My Orders*\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n`;
      for (const o of myOrders) {
        const icon = o.status === "approved" ? "✅" : o.status === "rejected" ? "❌" : "⏳";
        reply += `${icon} *${escMd(o.productName)}* — ₱${o.amount}\n`;
        reply += `   ID: \`${escMd(o.id)}\` · ${escMd(o.status.toUpperCase())}\n`;
        if (o.key) reply += `   🔑 \`${escMd(o.key)}\`\n`;
        reply += "\n";
      }
      return bot.sendMessage(chatId, reply, { parse_mode: "MarkdownV2" });
    }

    // Payment screenshot
    const state = userState[chatId];
    if (state && state.step === "awaiting_screenshot") {
      if (msg.photo || msg.document) {
        return await handlePayment(msg, state);
      } else {
        return bot.sendMessage(chatId,
          `📸 *Screenshot Required*\n\n` +
          `Please send your *GCash payment screenshot*\n` +
          `as a photo to complete your order\.`,
          { parse_mode: "MarkdownV2" }
        );
      }
    }
  } catch (e) { console.error("message error:", e.message); }
});

// Callback query (inline buttons)
bot.on("callback_query", async (query) => {
  const chatId = query.message.chat.id;
  const msgId  = query.message.message_id;
  const data   = query.data;
  await bot.answerCallbackQuery(query.id).catch(() => {});

  try {
    if (data === "noop") return; // category header tap — do nothing

  if (data.startsWith("buy_")) {
      const pid = data.replace("buy_", "");
      const db  = await getDB();
      const product = db.products[pid];
      if (!product) return bot.sendMessage(chatId, "Product not found.");

      const keysLeft = (db.keys[pid] || []).length;
      if (keysLeft === 0) {
        return bot.sendMessage(chatId,
          `🚫 *Out of Stock*\n\n` +
          `*${escMd(product.name)}* is currently unavailable\.\n` +
          `Please try another product or check back later\.`,
          { parse_mode: "MarkdownV2" }
        );
      }

      userState[chatId] = { step: "awaiting_screenshot", selectedProduct: product };
      await bot.editMessageReplyMarkup({ inline_keyboard: [] }, { chat_id: chatId, message_id: msgId }).catch(() => {});

      await bot.sendMessage(chatId,
        `🛒 *Order Summary*\n` +
        `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
        `🎮 *${escMd(product.name)}*\n` +
        `💰 Price: *₱${product.price}*\n` +
        `📦 Stock: ${keysLeft} key${keysLeft !== 1 ? "s" : ""} available\n\n` +
        `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
        `💳 *Payment Instructions*\n\n` +
        `Send *₱${product.price}* via GCash to:\n\n` +
        `📱 Number: \`${escMd(process.env.GCASH_NUMBER || "09XX-XXX-XXXX")}\`\n` +
        `👤 Name: *${escMd(process.env.GCASH_NAME || "Admin")}*\n\n` +
        `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
        `📸 Send your *payment screenshot* here\.\n` +
        `Your key will be delivered after verification\.`,
        { parse_mode: "MarkdownV2" }
      );
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

// Payment received
async function handlePayment(msg, state) {
  const chatId  = msg.chat.id;
  const product = state.selectedProduct;
  const db      = await getDB();
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
    screenshotFileId: msg.photo
      ? msg.photo[msg.photo.length - 1].file_id
      : (msg.document?.file_id || null),
    createdAt: new Date().toISOString(),
  };

  db.orders[orderId] = order;
  await saveDB(db);

  await bot.sendMessage(chatId,
    `✅ *Payment Received\!*\n` +
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
    `Your order has been submitted\.\n\n` +
    `📋 Order ID: \`${escMd(orderId)}\`\n` +
    `⏳ Status: *Under Review*\n\n` +
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
    `You will receive your key once approved\.\n` +
    `Average wait time: *under 5 minutes*\.`,
    { parse_mode: "MarkdownV2" }
  );

  const adminMsg =
    `🔔 *NEW ORDER*\n` +
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
    `👤 Buyer: ${escMd(order.buyerUser)}\n` +
    `🆔 User ID: \`${chatId}\`\n` +
    `🎮 Product: *${escMd(product.name)}*\n` +
    `💰 Amount: *₱${product.price}*\n` +
    `📋 Order ID: \`${escMd(orderId)}\`\n` +
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━`;
    `📋 Order ID: \`${escMd(orderId)}\``;

  const keyboard = {
    inline_keyboard: [[
      { text: "✅ APPROVE", callback_data: `approve_${orderId}` },
      { text: "❌ REJECT",  callback_data: `reject_${orderId}`  }
    ]]
  };

  if (order.screenshotFileId) {
    await bot.sendPhoto(ADMIN_ID, order.screenshotFileId, {
      caption: adminMsg, parse_mode: "MarkdownV2", reply_markup: keyboard
    });
  } else {
    await bot.sendMessage(ADMIN_ID, adminMsg, {
      parse_mode: "MarkdownV2", reply_markup: keyboard
    });
  }

  if (CHANNEL_ID) {
    await bot.sendMessage(CHANNEL_ID, adminMsg, { parse_mode: "MarkdownV2" }).catch(() => {});
  }

  delete userState[chatId];
}

// Approve
async function processApproval(orderId, adminChatId, msgId) {
  const db    = await getDB();
  const order = db.orders[orderId];
  if (!order)                   return bot.sendMessage(adminChatId, "Order not found.");
  if (order.status !== "pending") return bot.sendMessage(adminChatId, "Already processed.");

  const keys = db.keys[order.productId] || [];
  if (keys.length === 0) {
    return bot.sendMessage(adminChatId,
      `⚠️ No keys left for *${escMd(order.productName)}*\\! Add more keys in the admin panel\\.`,
      { parse_mode: "MarkdownV2" }
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
      { inline_keyboard: [[{ text: "✅ APPROVED", callback_data: "done" }]] },
      { chat_id: adminChatId, message_id: msgId }
    ).catch(() => {});
  }

  await bot.sendMessage(order.buyerId,
    `✅ *Order Approved\!*\n` +
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
    `Your key for *${escMd(order.productName)}* is ready\!\n\n` +
    `🔑 *Your Key:*\n` +
    `\`${escMd(key)}\`\n\n` +
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
    `Tap the key above to copy it\.\n` +
    `Thank you for your purchase\! 🙏`,
    { parse_mode: "MarkdownV2" }
  );

  await bot.sendMessage(adminChatId,
    `✅ Key delivered to ${escMd(order.buyerUser)}\n\`${escMd(key)}\``,
    { parse_mode: "MarkdownV2" }
  );
}

// Reject
async function processRejection(orderId, adminChatId, msgId) {
  const db    = await getDB();
  const order = db.orders[orderId];
  if (!order)                   return bot.sendMessage(adminChatId, "Order not found.");
  if (order.status !== "pending") return bot.sendMessage(adminChatId, "Already processed.");

  order.status     = "rejected";
  order.rejectedAt = new Date().toISOString();
  await saveDB(db);

  if (msgId) {
    await bot.editMessageReplyMarkup(
      { inline_keyboard: [[{ text: "❌ REJECTED", callback_data: "done" }]] },
      { chat_id: adminChatId, message_id: msgId }
    ).catch(() => {});
  }

  await bot.sendMessage(order.buyerId,
    `❌ *Order Declined*\n` +
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n` +
    `Your payment could not be verified\.\n\n` +
    `📋 Order ID: \`${escMd(orderId)}\`\n\n` +
    `━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n` +
    `If you believe this is an error,\n` +
    `contact support with your payment screenshot\.`,
    { parse_mode: "MarkdownV2" }
  );
}

bot.on("polling_error", (err) => console.error("Polling error:", err.message));

// ─── EXPRESS API ─────────────────────────────────────────────────────────────
const app = express();

// CORS — must be ABSOLUTE FIRST
app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin",  "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Accept, Authorization, Origin");
  res.setHeader("Access-Control-Max-Age",       "86400");
  if (req.method === "OPTIONS") return res.status(200).end();
  next();
});

app.use(express.json());

// Admin panel — serve index.html at root and /admin
app.get("/",      (req, res) => res.sendFile(path.join(__dirname, "index.html")));
app.get("/admin", (req, res) => res.sendFile(path.join(__dirname, "index.html")));
app.get("/health",(req, res) => res.json({ status: "ok", bot: "running", uptime: process.uptime() }));

// Bot info
app.get("/api/botinfo", async (req, res) => {
  try {
    const info = await bot.getMe();
    res.json({ ok: true, username: info.username, name: info.first_name, id: info.id });
  } catch (e) { res.status(500).json({ ok: false, error: e.message }); }
});

// Orders
app.get("/api/orders", async (req, res) => {
  try {
    const db = await getDB();
    res.json(Object.values(db.orders).reverse());
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post("/api/orders/:id/approve", async (req, res) => {
  try {
    await processApproval(req.params.id, ADMIN_ID, null);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post("/api/orders/:id/reject", async (req, res) => {
  try {
    await processRejection(req.params.id, ADMIN_ID, null);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Products
app.get("/api/products", async (req, res) => {
  try {
    const db = await getDB();
    res.json(Object.values(db.products));
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post("/api/products", async (req, res) => {
  try {
    const db = await getDB();
    const { name, price, emoji, description, category } = req.body;
    if (!name || !price) return res.status(400).json({ error: "name and price required" });
    const pid = `PROD-${Date.now()}`;
    db.products[pid] = { id: pid, name, price: Number(price), emoji: emoji || "🔑", description: description || "", category: category || "Other", active: true };
    await saveDB(db);
    res.json(db.products[pid]);
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

// Keys
app.get("/api/keys/:productId", async (req, res) => {
  try {
    const db = await getDB();
    res.json({ keys: db.keys[req.params.productId] || [] });
  } catch (e) { res.status(500).json({ error: e.message }); }
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

// Broadcast
app.post("/api/broadcast", async (req, res) => {
  try {
    const db = await getDB();
    const { message } = req.body;
    if (!message) return res.status(400).json({ error: "message required" });
    const buyers = [...new Set(Object.values(db.orders).map(o => o.buyerId))];
    let sent = 0, failed = 0;
    for (const id of buyers) {
      try { await bot.sendMessage(id, message); sent++; }
      catch { failed++; }
    }
    res.json({ sent, failed });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.listen(PORT, () => {
  console.log(`🚀 Server running on port ${PORT}`);
  console.log(`🤖 Bot is running — @${BOT_TOKEN.split(":")[0]}`);

  // ── KEEP-ALIVE: ping self every 5 min so Railway never sleeps ──────────────
  const SELF_URL = process.env.RAILWAY_PUBLIC_DOMAIN
    ? `https://${process.env.RAILWAY_PUBLIC_DOMAIN}/health`
    : `http://localhost:${PORT}/health`;

  setInterval(async () => {
    try {
      const http = require("http"), https = require("https");
      const lib = SELF_URL.startsWith("https") ? https : http;
      lib.get(SELF_URL, (r) => console.log(`♻️  Keep-alive ping → ${r.statusCode}`))
         .on("error", (e) => console.warn("Keep-alive error:", e.message));
    } catch(e) { console.warn("Keep-alive error:", e.message); }
  }, 5 * 60 * 1000); // every 5 minutes
});
