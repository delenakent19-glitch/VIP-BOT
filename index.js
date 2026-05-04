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
  return db;
}

async function saveDB(db) {
  await fs.ensureDir(path.dirname(DB_FILE));
  await fs.writeFile(DB_FILE, JSON.stringify(db, null, 2));
}

// ─── BOT ─────────────────────────────────────────────────────────────────────
const WEBHOOK_HOST = process.env.RAILWAY_PUBLIC_DOMAIN;
const bot = WEBHOOK_HOST
  ? new TelegramBot(BOT_TOKEN, { webHook: { port: PORT } })
  : new TelegramBot(BOT_TOKEN, { polling: true });

if (WEBHOOK_HOST) {
  const webhookUrl = `https://${WEBHOOK_HOST}/bot${BOT_TOKEN}`;
  bot.setWebHook(webhookUrl)
    .then(() => console.log("Webhook set OK"))
    .catch(e  => console.error("Webhook error:", e.message));
}

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
      `<b>Hello, ${h(name)}!</b>\n` +
      `Welcome to <b>Zeijie Order Bot</b>\n\n` +
      `Your trusted store for premium game keys.\n\n` +
      `<b>What we offer:</b>\n` +
      `- Instant key delivery after approval\n` +
      `- GCash payment accepted\n` +
      `- Fast, secure &amp; reliable\n\n` +
      `Tap <b>Buy Key</b> to browse available keys.`,
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
      `<b>How It Works</b>\n\n` +
      `<b>Step 1 - Browse</b>\n` +
      `Tap Buy Key and pick your product.\n\n` +
      `<b>Step 2 - Pay</b>\n` +
      `Send payment via GCash to the number shown.\n\n` +
      `<b>Step 3 - Screenshot</b>\n` +
      `Send your payment screenshot in this chat.\n\n` +
      `<b>Step 4 - Wait</b>\n` +
      `Admin reviews within 5 minutes on average.\n\n` +
      `<b>Step 5 - Receive</b>\n` +
      `Your key will be delivered here automatically!\n\n` +
      `Need help? Contact the admin directly.`,
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
        `<b>No Products Available</b>\n\nWe are currently restocking.\nPlease check back soon!`,
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
    for (const [cat, items] of Object.entries(grouped)) {
      inline_keyboard.push([{ text: `--- ${cat} ---`, callback_data: "noop" }]);
      for (const p of items) {
        inline_keyboard.push([{
          text: `${p.emoji || "🔑"} ${p.name} — P${p.price}`,
          callback_data: `buy_${p.id}`
        }]);
      }
    }

    await bot.sendMessage(chatId, "<b>Choose a product:</b>", {
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
        `<b>No Orders Yet</b>\n\nYou have not placed any orders.\nTap Buy Key to browse products!`,
        HTML
      );
    }

    let reply = `<b>My Orders (last 5)</b>\n\n`;
    for (const o of myOrders) {
      const icon = o.status === "approved" ? "APPROVED" : o.status === "rejected" ? "REJECTED" : "PENDING";
      reply += `<b>${h(o.productName)}</b> — P${o.amount}\n`;
      reply += `  ID: <code>${h(o.id)}</code>\n`;
      reply += `  Status: ${icon}\n`;
      reply += `  Date: ${h(phTime(o.createdAt))}\n`;
      if (o.key) reply += `  Key: <code>${h(o.key)}</code>\n`;
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
          `<b>Screenshot Required</b>\n\nPlease send your GCash payment screenshot as a photo to complete your order.`,
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
          `<b>Out of Stock</b>\n\n<b>${h(product.name)}</b> is currently unavailable.\nPlease try another product or check back later.`,
          HTML
        );
      }

      userState[chatId] = { step: "awaiting_screenshot", selectedProduct: product };
      await bot.editMessageReplyMarkup({ inline_keyboard: [] }, { chat_id: chatId, message_id: msgId }).catch(() => {});

      const gcashNum  = h(process.env.GCASH_NUMBER || "09XX-XXX-XXXX");
      const gcashName = h(process.env.GCASH_NAME   || "Admin");

      await bot.sendMessage(chatId,
        `<b>Order Summary</b>\n\n` +
        `Product: <b>${h(product.name)}</b>\n` +
        `Price: <b>P${product.price}</b>\n` +
        `Stock: ${keysLeft} key${keysLeft !== 1 ? "s" : ""} available\n\n` +
        `<b>Payment Instructions</b>\n\n` +
        `Send <b>P${product.price}</b> via GCash to:\n` +
        `Number: <code>${gcashNum}</code>\n` +
        `Name: <b>${gcashName}</b>\n\n` +
        `Now send your <b>payment screenshot</b> here.\n` +
        `Your key will be delivered after verification.`,
        HTML
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

// ─── HANDLE PAYMENT ───────────────────────────────────────────────────────────
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

  // Confirm to buyer
  await bot.sendMessage(chatId,
    `<b>Payment Received!</b>\n\n` +
    `Your order has been submitted.\n\n` +
    `Order ID: <code>${h(orderId)}</code>\n` +
    `Submitted: ${h(phTime(order.createdAt))}\n` +
    `Status: <b>Under Review</b>\n\n` +
    `You will receive your key once approved.\n` +
    `Average wait time: under 5 minutes.`,
    HTML
  );

  // Notify admin
  const adminMsg =
    `<b>NEW ORDER</b>\n\n` +
    `Buyer: ${h(order.buyerUser)}\n` +
    `User ID: <code>${chatId}</code>\n` +
    `Product: <b>${h(product.name)}</b>\n` +
    `Amount: <b>P${product.price}</b>\n` +
    `Order ID: <code>${h(orderId)}</code>\n` +
    `Time: ${h(phTime(order.createdAt))}`;

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

  await bot.sendMessage(order.buyerId,
    `<b>Order Approved!</b>\n\n` +
    `Your key for <b>${h(order.productName)}</b> is ready!\n\n` +
    `<b>Your Key:</b>\n<code>${h(key)}</code>\n\n` +
    `Approved: ${h(phTime(order.approvedAt))}\n\n` +
    `Tap the key above to copy it.\nThank you for your purchase!`,
    HTML
  );

  await bot.sendMessage(adminChatId,
    `Key delivered to ${h(order.buyerUser)}\n<code>${h(key)}</code>`,
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
    `<b>Order Declined</b>\n\n` +
    `Your payment could not be verified.\n\n` +
    `Order ID: <code>${h(orderId)}</code>\n` +
    `Reviewed: ${h(phTime(order.rejectedAt))}\n\n` +
    `If you believe this is an error, contact support with your payment screenshot.`,
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
    res.json({ ok: true, username: info.username, name: info.first_name, id: info.id });
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

// ─── SERVER START ─────────────────────────────────────────────────────────────
if (WEBHOOK_HOST) {
  const ADMIN_PORT = Number(PORT) + 1;
  app.listen(ADMIN_PORT, () => {
    console.log(`Admin panel: port ${ADMIN_PORT}`);
    console.log(`Webhook bot active`);
    // Silent keep-alive ping every 5 min
    const url = `https://${WEBHOOK_HOST}/health`;
    setInterval(() => {
      require("https").get(url, () => {}).on("error", () => {});
    }, 5 * 60 * 1000);
  });
} else {
  app.listen(PORT, () => {
    console.log(`Server: port ${PORT} (polling mode)`);
  });
}
