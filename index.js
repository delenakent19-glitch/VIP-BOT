/**
 * GENERIC ORDER BOT — Railway Deployment
 * Flow: User browses items → picks item → sends payment proof → Admin APPROVE/REJECT
 * DB: Firebase Firestore (free tier, persistent)
 *
 * ENV VARIABLES NEEDED:
 *   BOT_TOKEN           — Telegram bot token
 *   ADMIN_ID            — Your Telegram user ID (number)
 *   FIREBASE_PROJECT_ID — Firebase project ID
 *   FIREBASE_CLIENT_EMAIL — Firebase service account email
 *   FIREBASE_PRIVATE_KEY  — Firebase service account private key (paste full key with \n)
 *   CHANNEL_ID          — (optional) Telegram channel to forward orders
 *   PORT                — (auto on Railway)
 *   RAILWAY_PUBLIC_DOMAIN — (auto on Railway)
 */

require("dotenv").config();
const TelegramBot = require("node-telegram-bot-api");
const express     = require("express");
const path        = require("path");
const fs          = require("fs");
const https       = require("https");
const FormData    = require("form-data");
const multer      = require("multer");
const { initializeApp, cert } = require("firebase-admin/app");
const { getFirestore, FieldValue } = require("firebase-admin/firestore");

// multer: store QR upload in memory (no disk needed)
const upload = multer({ storage: multer.memoryStorage(), limits: { fileSize: 5 * 1024 * 1024 } });

// ─── CONFIG ──────────────────────────────────────────────────────────────────
const BOT_TOKEN  = process.env.BOT_TOKEN;
const ADMIN_ID   = process.env.ADMIN_ID;
const CHANNEL_ID = process.env.CHANNEL_ID || "";
const PORT       = process.env.PORT || 8080;

if (!BOT_TOKEN || !ADMIN_ID) {
  console.error("Missing BOT_TOKEN or ADMIN_ID");
  process.exit(1);
}

// ─── FIREBASE INIT ───────────────────────────────────────────────────────────
let db;
try {
  initializeApp({
    credential: cert({
      projectId:    process.env.FIREBASE_PROJECT_ID,
      clientEmail:  process.env.FIREBASE_CLIENT_EMAIL,
      privateKey:   (process.env.FIREBASE_PRIVATE_KEY || "").replace(/\\n/g, "\n"),
    }),
  });
  db = getFirestore();
  console.log("✅ Firebase connected");
} catch (e) {
  console.error("Firebase init failed:", e.message);
  process.exit(1);
}

// ─── DB HELPERS ──────────────────────────────────────────────────────────────
async function getProducts() {
  const snap = await db.collection("products").get();
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

async function getActiveProducts() {
  const snap = await db.collection("products").where("active", "==", true).get();
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

async function getProduct(id) {
  const doc = await db.collection("products").doc(id).get();
  return doc.exists ? { id: doc.id, ...doc.data() } : null;
}

async function createOrder(data) {
  const ref = await db.collection("orders").add({
    ...data,
    status: "pending",
    createdAt: new Date().toISOString(),
  });
  return ref.id;
}

async function getOrder(id) {
  const doc = await db.collection("orders").doc(id).get();
  return doc.exists ? { id: doc.id, ...doc.data() } : null;
}

async function updateOrder(id, data) {
  await db.collection("orders").doc(id).update(data);
}

async function getOrders(limit = 50) {
  const snap = await db.collection("orders").limit(limit).get();
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

async function getUserOrders(userId) {
  const snap = await db.collection("orders")
    .where("buyerId", "==", String(userId))
    .limit(5)
    .get();
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

async function getSettings() {
  const doc = await db.collection("settings").doc("main").get();
  return doc.exists ? doc.data() : {};
}

async function updateSettings(data) {
  await db.collection("settings").doc("main").set(data, { merge: true });
}

// ─── STOCK HELPERS ───────────────────────────────────────────────────────────
// Each product can have a "stock" subcollection with individual items (key/link/text)
// On approve, we pop one item from stock and deliver it. If stock is empty, deliver deliveryNote instead.

async function getStock(productId) {
  const snap = await db.collection("products").doc(productId)
    .collection("stock")
    .where("used", "==", false)
    .get();
  return snap.docs.map(d => ({ id: d.id, ...d.data() }));
}

async function getStockCount(productId) {
  const snap = await db.collection("products").doc(productId)
    .collection("stock")
    .where("used", "==", false)
    .get();
  return snap.size;
}

async function addStockItems(productId, items) {
  // items = array of strings, may be "KEY|||LINK" pairs or plain strings
  const batch = db.batch();
  for (const item of items) {
    const ref = db.collection("products").doc(productId).collection("stock").doc();
    if (item.includes("|||")) {
      const sep = item.indexOf("|||");
      const key  = item.slice(0, sep).trim();
      const link = item.slice(sep + 3).trim();
      batch.set(ref, { value: item, key, link, used: false, createdAt: new Date().toISOString() });
    } else {
      batch.set(ref, { value: item, used: false, createdAt: new Date().toISOString() });
    }
  }
  await batch.commit();
  return items.length;
}

async function popStockItem(productId) {
  // Get oldest unused item and mark as used atomically
  const snap = await db.collection("products").doc(productId)
    .collection("stock")
    .where("used", "==", false)
    .limit(1)
    .get();
  if (snap.empty) return null;
  const doc = snap.docs[0];
  await doc.ref.update({ used: true, usedAt: new Date().toISOString() });
  return doc.data().value;
}

async function clearStock(productId) {
  const snap = await db.collection("products").doc(productId).collection("stock").get();
  const batch = db.batch();
  snap.docs.forEach(d => batch.delete(d.ref));
  await batch.commit();
  return snap.size;
}

// ─── BOT SETUP ───────────────────────────────────────────────────────────────
const WEBHOOK_HOST = process.env.RAILWAY_PUBLIC_DOMAIN;
const bot = new TelegramBot(BOT_TOKEN, { polling: !WEBHOOK_HOST });
const userState = {};
const HTML = { parse_mode: "HTML" };

function h(text) {
  return String(text || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function phTime(isoString) {
  const date = isoString ? new Date(isoString) : new Date();
  return date.toLocaleString("en-PH", {
    timeZone: "Asia/Manila",
    year: "numeric", month: "short", day: "2-digit",
    hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: true,
  });
}

// ─── /start ──────────────────────────────────────────────────────────────────
bot.onText(/\/start/, async (msg) => {
  const chatId = msg.chat.id;
  const name = msg.from.first_name || "there";
  const settings = await getSettings().catch(() => ({}));
  const shopName = settings.shopName || "ORDER BOT";
  const welcome  = settings.welcomeText || "Browse our products below and place your order!";

  await bot.sendMessage(chatId,
    `<b>🛒 ${h(shopName)}</b>\n\n` +
    `👋 Hey, <b>${h(name)}!</b>\n\n` +
    `${h(welcome)}\n\n` +
    `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n` +
    `👇 Tap <b>🛍️ Shop</b> to browse products!`,
    {
      parse_mode: "HTML",
      reply_markup: {
        keyboard: [
          [{ text: "🛍️ Shop" }, { text: "📦 My Orders" }],
          [{ text: "ℹ️ Help" }]
        ],
        resize_keyboard: true,
        one_time_keyboard: false,
      }
    }
  );
});

// ─── HELP ────────────────────────────────────────────────────────────────────
async function sendHelp(chatId) {
  const settings = await getSettings().catch(() => ({}));
  const helpText = settings.helpText ||
    `<b>1️⃣ BROWSE</b> — Tap 🛍️ Shop and pick an item.\n\n` +
    `<b>2️⃣ PAY</b> — Send payment via GCash. 💳\n\n` +
    `<b>3️⃣ SCREENSHOT</b> — Send your payment proof here. 📸\n\n` +
    `<b>4️⃣ WAIT</b> — Admin reviews in ~5 minutes. ⏳\n\n` +
    `<b>5️⃣ RECEIVE</b> — Your item delivered here! ✅\n\n` +
    `❓ Questions? Contact the admin directly.`;

  await bot.sendMessage(chatId,
    `<b>📖 HOW IT WORKS</b>\n\n${helpText}`, HTML
  );
}

bot.onText(/\/help/, (msg) => sendHelp(msg.chat.id));

// ─── SHOW PRODUCTS ────────────────────────────────────────────────────────────
async function showProducts(chatId) {
  const products = await getActiveProducts();
  if (products.length === 0) {
    return bot.sendMessage(chatId,
      `<b>😔 No items available right now.</b>\n\nPlease check back soon! 🔄`, HTML
    );
  }

  let messageText = `<b>🛍️ SHOP</b>\n\n`;
  const inline_keyboard = [];

  for (const p of products) {
    // Check stock count for stock-type products
    let stockCount = null;
    if (p.stockType === "stock") {
      stockCount = await getStockCount(p.id).catch(() => 0);
    }

    const outOfStock = p.stockType === "stock" && stockCount === 0;
    const priceText = p.price ? ` — ₱${p.price}` : "";
    const stockTag  = outOfStock ? " ❌ OUT OF STOCK" : "";
    const label     = `${p.emoji || "📦"} ${p.name}${priceText}${stockTag}`;

    messageText += `• ${label}\n`;
    if (p.description) messageText += `  <i>${h(p.description)}</i>\n`;
    messageText += "\n";

    if (outOfStock) {
      // Show button but disabled (clicking shows out of stock message)
      inline_keyboard.push([{ text: label, callback_data: `oos_${p.id}` }]);
    } else {
      inline_keyboard.push([{ text: label, callback_data: `buy_${p.id}` }]);
    }
  }

  messageText += `👇 Tap an item to order:`;

  await bot.sendMessage(chatId, messageText, {
    parse_mode: "HTML",
    reply_markup: { inline_keyboard },
  });
}

// ─── MY ORDERS ────────────────────────────────────────────────────────────────
async function handleMyOrders(chatId) {
  const myOrders = await getUserOrders(chatId).catch(() => []);
  if (!myOrders.length) {
    return bot.sendMessage(chatId,
      `<b>📭 No orders yet.</b>\n\nTap <b>🛍️ Shop</b> to get started!`, HTML
    );
  }

  let reply = `<b>📦 MY ORDERS (LAST 5)</b>\n\n`;
  for (const o of myOrders) {
    const icon = o.status === "approved" ? "✅ APPROVED"
      : o.status === "rejected" ? "❌ REJECTED" : "⏳ PENDING";
    reply += `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n`;
    reply += `  📦 Item   : <b>${h(o.productName)}</b>\n`;
    if (o.amount) reply += `  💰 Amount : ₱${o.amount}\n`;
    reply += `  📌 Status : <b>${icon}</b>\n`;
    reply += `  📅 Date   : ${h(phTime(o.createdAt))}\n`;
    if (o.deliveryNote) reply += `  📝 Note   : ${h(o.deliveryNote)}\n`;
    reply += "\n";
  }
  return bot.sendMessage(chatId, reply, HTML);
}

// ─── MESSAGE HANDLER ─────────────────────────────────────────────────────────
bot.on("message", async (msg) => {
  const chatId = msg.chat.id;
  const text   = (msg.text || "").trim();
  if (msg.forward_from || msg.forward_from_chat) return;
  if (text.startsWith("/start")) return;
  if (text === "/help" || text === "ℹ️ Help") return sendHelp(chatId);
  if (text === "/shop" || text === "🛍️ Shop") return showProducts(chatId);
  if (text === "/myorders" || text === "📦 My Orders") return handleMyOrders(chatId);
  if (text.startsWith("/")) return;

  try {
    const state = userState[chatId];
    if (state && state.step === "awaiting_screenshot") {
      if (msg.photo || msg.document) {
        return await handlePayment(msg, state);
      } else {
        return bot.sendMessage(chatId,
          `📸 <b>Please send your payment screenshot as a photo.</b>`, HTML
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
    if (data === "noop" || data === "done") return;

    if (data.startsWith("oos_")) {
      await bot.sendMessage(chatId,
        `<b>❌ OUT OF STOCK</b>\n\nSorry, this item is currently out of stock.\n\nPlease check back later! 🔄`,
        HTML
      );
      return;
    }

    if (data.startsWith("buy_")) {
      const pid     = data.replace("buy_", "");
      const product = await getProduct(pid);
      if (!product) return bot.sendMessage(chatId, "Item not found.");

      await bot.editMessageReplyMarkup(
        { inline_keyboard: [] }, { chat_id: chatId, message_id: msgId }
      ).catch(() => {});

      const settings  = await getSettings().catch(() => ({}));
      const qrFileId  = settings.qrFileId || null;
      const qrCaption = settings.qrCaption || "";

      const priceText = product.price ? `₱${product.price}` : "contact admin";
      const summaryText =
        `<b>🧾 ORDER SUMMARY</b>\n\n` +
        `  📦 Item  : <b>${h(product.name)}</b>\n` +
        (product.price ? `  💰 Price : <b>₱${product.price}</b>\n` : "") +
        (product.description ? `  📝 Info  : ${h(product.description)}\n` : "") +
        `\n<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n` +
        (qrCaption ? `${h(qrCaption)}\n\n` : `💳 Send your payment of <b>${priceText}</b> via GCash.\n\n`) +
        `📸 After paying, <b>send your payment screenshot here</b>.\n` +
        `✅ Admin will verify and deliver your item.`;

      userState[chatId] = { step: "awaiting_screenshot", selectedProduct: product };

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
  const chatId  = msg.chat.id;
  const product = state.selectedProduct;

  const orderId = await createOrder({
    buyerId:     String(chatId),
    buyerName:   msg.from.first_name || "",
    buyerUser:   msg.from.username ? `@${msg.from.username}` : String(chatId),
    productId:   product.id,
    productName: product.name,
    amount:      product.price || null,
    screenshotFileId: msg.photo
      ? msg.photo[msg.photo.length - 1].file_id
      : (msg.document?.file_id || null),
  });

  delete userState[chatId];

  // Confirm to buyer
  await bot.sendMessage(chatId,
    `<b>✅ ORDER SUBMITTED!</b>\n\n` +
    `🎉 Your order has been received.\n\n` +
    `  📦 Item   : <b>${h(product.name)}</b>\n` +
    `  🆔 Order  : <code>${orderId}</code>\n` +
    `  📅 Time   : ${h(phTime())}\n` +
    `  📌 Status : <b>⏳ Under Review</b>\n\n` +
    `🔔 You will be notified once your order is processed.`,
    HTML
  );

  // Notify admin
  const adminMsg =
    `<b>💰 NEW ORDER REQUEST</b>\n\n` +
    `  👤 User     : ${h(msg.from.username ? `@${msg.from.username}` : "None")}\n` +
    `  🆔 User ID  : <code>${chatId}</code>\n` +
    `  📦 Item     : <b>${h(product.name)}</b>\n` +
    (product.price ? `  💵 Amount   : ₱${product.price}\n` : "") +
    `  🔖 Order ID : <code>${orderId}</code>\n` +
    `  📅 Time     : ${h(phTime())}`;

  const keyboard = {
    inline_keyboard: [[
      { text: "✅ APPROVE", callback_data: `approve_${orderId}` },
      { text: "❌ REJECT",  callback_data: `reject_${orderId}`  }
    ]]
  };

  const order = await getOrder(orderId);
  if (order?.screenshotFileId) {
    await bot.sendPhoto(ADMIN_ID, order.screenshotFileId, {
      caption: adminMsg, parse_mode: "HTML", reply_markup: keyboard
    });
  } else {
    await bot.sendMessage(ADMIN_ID, adminMsg, { parse_mode: "HTML", reply_markup: keyboard });
  }

  if (CHANNEL_ID) {
    await bot.sendMessage(CHANNEL_ID, adminMsg, HTML).catch(() => {});
  }
}

// ─── APPROVE ──────────────────────────────────────────────────────────────────
async function processApproval(orderId, adminChatId, msgId) {
  const order = await getOrder(orderId);
  if (!order) return bot.sendMessage(adminChatId, "Order not found.");
  if (order.status !== "pending") return bot.sendMessage(adminChatId, "Already processed.");

  await updateOrder(orderId, {
    status:     "approved",
    approvedAt: new Date().toISOString(),
  });

  if (msgId) {
    await bot.editMessageReplyMarkup(
      { inline_keyboard: [[{ text: "✅ APPROVED", callback_data: "done" }]] },
      { chat_id: adminChatId, message_id: msgId }
    ).catch(() => {});
  }

  // Get product
  const product = await getProduct(order.productId).catch(() => null);

  // Try to pop a stock item (key/link) first
  let deliveredItem = null;
  let deliveredKey  = null;
  let deliveredLink = null;
  if (product) {
    deliveredItem = await popStockItem(order.productId).catch(() => null);
    if (deliveredItem && deliveredItem.includes("|||")) {
      const sep = deliveredItem.indexOf("|||");
      deliveredKey  = deliveredItem.slice(0, sep).trim();
      deliveredLink = deliveredItem.slice(sep + 3).trim();
    }
  }

  // Fallback to deliveryNote if no stock
  const deliveryNote = product?.deliveryNote || null;
  const hasDelivery  = deliveredItem || deliveryNote;

  // Save what was delivered to order record
  if (deliveredItem) {
    await updateOrder(orderId, { deliveredItem });
  }

  // Build delivery block
  let deliveryBlock = "";
  if (deliveredItem) {
    if (deliveredKey && deliveredLink) {
      deliveryBlock =
        `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n` +
        `📦 <b>YOUR ITEM:</b>\n\n` +
        `🔑 <b>Key:</b>\n<code>${h(deliveredKey)}</code>\n\n` +
        `🔗 <b>Link:</b>\n${h(deliveredLink)}\n\n` +
        `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n`;
    } else {
      deliveryBlock =
        `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n` +
        `📦 <b>YOUR ITEM:</b>\n\n` +
        `<code>${h(deliveredItem)}</code>\n\n` +
        `<b>━━━━━━━━━━━━━━━━━━━━━━━━</b>\n`;
    }
  } else if (deliveryNote) {
    deliveryBlock = `<b>━━━ 📝 DELIVERY INFO ━━━</b>\n${h(deliveryNote)}\n\n`;
  }

  await bot.sendMessage(order.buyerId,
    `<b>🎉 ORDER APPROVED!</b>\n\n` +
    `✅ Your order for <b>${h(order.productName)}</b> has been approved!\n\n` +
    deliveryBlock +
    `  📅 Approved : ${h(phTime())}\n\n` +
    `💙 Thank you for your order!`,
    HTML
  );

  // If product has a file attached, send it too
  if (product?.deliveryFileId) {
    await bot.sendDocument(order.buyerId, product.deliveryFileId, {
      caption: `📦 File for: <b>${h(order.productName)}</b>`,
      parse_mode: "HTML",
    }).catch(() => {});
  }

  // Warn admin if stock is now low
  let stockWarn = "";
  if (product) {
    const remaining = await getStockCount(order.productId).catch(() => null);
    if (remaining !== null) {
      stockWarn = `\n📦 Stock remaining: <b>${remaining}</b>`;
      if (remaining === 0) {
        stockWarn += " ⚠️ <b>OUT OF STOCK!</b>";
        // Product stays visible but shows as OUT OF STOCK in shop
        // Admin gets notified to restock
      } else if (remaining <= 3) {
        stockWarn += " ⚠️ Running low! Please restock soon.";
      }
    }
  }

  await bot.sendMessage(adminChatId,
    `✅ Approved & delivered to ${h(order.buyerUser)}` +
    (deliveredKey && deliveredLink
      ? `\n🔑 Key: <code>${h(deliveredKey)}</code>\n🔗 Link: ${h(deliveredLink)}`
      : deliveredItem ? `\n🔑 Sent: <code>${h(deliveredItem)}</code>` : "") +
    stockWarn,
    HTML
  );
}

// ─── REJECT ───────────────────────────────────────────────────────────────────
async function processRejection(orderId, adminChatId, msgId) {
  const order = await getOrder(orderId);
  if (!order) return bot.sendMessage(adminChatId, "Order not found.");
  if (order.status !== "pending") return bot.sendMessage(adminChatId, "Already processed.");

  await updateOrder(orderId, {
    status:     "rejected",
    rejectedAt: new Date().toISOString(),
  });

  if (msgId) {
    await bot.editMessageReplyMarkup(
      { inline_keyboard: [[{ text: "❌ REJECTED", callback_data: "done" }]] },
      { chat_id: adminChatId, message_id: msgId }
    ).catch(() => {});
  }

  await bot.sendMessage(order.buyerId,
    `<b>❌ ORDER DECLINED</b>\n\n` +
    `😔 Your payment could not be verified.\n\n` +
    `  📦 Item     : <b>${h(order.productName)}</b>\n` +
    `  📅 Reviewed : ${h(phTime())}\n\n` +
    `💬 If you think this is an error, contact the admin with your payment screenshot.`,
    HTML
  );
}

bot.on("polling_error", (err) => console.error("Polling error:", err.message));

// ─── EXPRESS API ─────────────────────────────────────────────────────────────
const app = express();

app.use((req, res, next) => {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization");
  if (req.method === "OPTIONS") return res.status(200).end();
  next();
});
app.use(express.json());

// ── Token auth middleware for all /api/* routes except /api/botinfo verify ──
// We validate the token by comparing to BOT_TOKEN env var
function requireAuth(req, res, next) {
  const auth = req.headers["authorization"] || "";
  const token = auth.replace("Bearer ", "").trim();
  if (!token || token !== BOT_TOKEN) {
    return res.status(401).json({ ok: false, error: "Unauthorized" });
  }
  next();
}

// Health — no auth needed
app.get("/health", (req, res) => res.json({ status: "ok", uptime: process.uptime() }));

// Bot info — validates token and returns bot details
app.get("/api/botinfo", requireAuth, async (req, res) => {
  try {
    const info = await bot.getMe();
    res.json({ ok: true, username: info.username, name: info.first_name, adminId: ADMIN_ID });
  } catch (e) { res.status(500).json({ ok: false, error: e.message }); }
});

// Orders
app.get("/api/orders", requireAuth, async (req, res) => {
  try { res.json(await getOrders(100)); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

app.post("/api/orders/:id/approve", requireAuth, async (req, res) => {
  try { await processApproval(req.params.id, ADMIN_ID, null); res.json({ ok: true }); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

app.post("/api/orders/:id/reject", requireAuth, async (req, res) => {
  try { await processRejection(req.params.id, ADMIN_ID, null); res.json({ ok: true }); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

// Products
app.get("/api/products", requireAuth, async (req, res) => {
  try { res.json(await getProducts()); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

app.post("/api/products", requireAuth, async (req, res) => {
  try {
    const { name, price, emoji, description, deliveryNote } = req.body;
    if (!name) return res.status(400).json({ error: "name required" });
    const { stockType } = req.body; // 'stock' or 'note'
    const ref = await db.collection("products").add({
      name, price: price ? Number(price) : null,
      emoji: emoji || "📦", description: description || "",
      deliveryNote: deliveryNote || "",
      deliveryFileId: null,
      stockType: stockType || "note",
      active: true,
      createdAt: new Date().toISOString(),
    });
    res.json({ id: ref.id, name });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.put("/api/products/:id", requireAuth, async (req, res) => {
  try {
    const { name, price, emoji, description, deliveryNote, active } = req.body;
    const data = {};
    if (name !== undefined) data.name = name;
    if (price !== undefined) data.price = price ? Number(price) : null;
    if (emoji !== undefined) data.emoji = emoji;
    if (description !== undefined) data.description = description;
    if (deliveryNote !== undefined) data.deliveryNote = deliveryNote;
    if (active !== undefined) data.active = active;
    const { stockType } = req.body;
    if (stockType !== undefined) data.stockType = stockType;
    await db.collection("products").doc(req.params.id).update(data);
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.delete("/api/products/:id", requireAuth, async (req, res) => {
  try {
    await db.collection("products").doc(req.params.id).delete();
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Stock management
app.get("/api/products/:id/stock", requireAuth, async (req, res) => {
  try {
    const items = await getStock(req.params.id);
    const count = items.length;
    res.json({ count, items });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.post("/api/products/:id/stock", requireAuth, async (req, res) => {
  try {
    // Accept newline-separated or array of items
    let { items } = req.body;
    if (typeof items === "string") {
      items = items.split("\n").map(s => s.trim()).filter(Boolean);
    }
    if (!items || !items.length) return res.status(400).json({ error: "No items provided" });
    const added = await addStockItems(req.params.id, items);
    const count = await getStockCount(req.params.id);
    res.json({ ok: true, added, totalStock: count });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

app.delete("/api/products/:id/stock", requireAuth, async (req, res) => {
  try {
    const deleted = await clearStock(req.params.id);
    res.json({ ok: true, deleted });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Upload delivery file for a product (send file to bot first, use file_id)
app.put("/api/products/:id/deliveryfile", requireAuth, async (req, res) => {
  try {
    const { deliveryFileId } = req.body;
    await db.collection("products").doc(req.params.id).update({ deliveryFileId: deliveryFileId || null });
    res.json({ ok: true });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// Settings (QR code, shop name, welcome text, help text, payment info)
app.get("/api/settings", requireAuth, async (req, res) => {
  try { res.json(await getSettings()); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

app.put("/api/settings", requireAuth, async (req, res) => {
  try { await updateSettings(req.body); res.json({ ok: true }); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

// QR upload — admin uploads image file → send to Telegram → save file_id
app.post("/api/settings/qr/upload", requireAuth, upload.single("qr"), async (req, res) => {
  try {
    if (!req.file) return res.status(400).json({ error: "No file uploaded" });

    const FormData = require("form-data");
    const form = new FormData();
    form.append("chat_id", ADMIN_ID);
    form.append("photo", req.file.buffer, {
      filename: req.file.originalname || "qr.jpg",
      contentType: req.file.mimetype,
    });
    form.append("caption", "✅ QR code uploaded via admin panel");

    const tgRes = await new Promise((resolve, reject) => {
      const options = {
        hostname: "api.telegram.org",
        path: "/bot" + BOT_TOKEN + "/sendPhoto",
        method: "POST",
        headers: form.getHeaders(),
      };
      const request = require("https").request(options, (r) => {
        let data = "";
        r.on("data", chunk => data += chunk);
        r.on("end", () => { try { resolve(JSON.parse(data)); } catch { reject(new Error("Bad Telegram response")); } });
      });
      request.on("error", reject);
      form.pipe(request);
    });

    if (!tgRes.ok) throw new Error(tgRes.description || "Telegram upload failed");
    const fileId = tgRes.result.photo[tgRes.result.photo.length - 1].file_id;
    await updateSettings({ qrFileId: fileId });
    res.json({ ok: true, fileId });
  } catch (e) {
    console.error("QR upload error:", e.message);
    res.status(500).json({ error: e.message });
  }
});

// QR remove
app.delete("/api/settings/qr", requireAuth, async (req, res) => {
  try { await updateSettings({ qrFileId: null }); res.json({ ok: true }); }
  catch (e) { res.status(500).json({ error: e.message }); }
});

// Broadcast
app.post("/api/broadcast", requireAuth, async (req, res) => {
  try {
    const { message } = req.body;
    if (!message) return res.status(400).json({ error: "message required" });
    const orders = await getOrders(500);
    const buyers = [...new Set(orders.map(o => o.buyerId).filter(Boolean))];
    let sent = 0, failed = 0;
    for (const id of buyers) {
      try { await bot.sendMessage(id, message); sent++; } catch { failed++; }
    }
    res.json({ sent, failed });
  } catch (e) { res.status(500).json({ error: e.message }); }
});

// ─── HTML (must be after all API routes) ─────────────────────────────────────
app.get("/admin", (req, res) => res.sendFile(path.join(__dirname, "index.html")));
app.get("/",      (req, res) => res.sendFile(path.join(__dirname, "index.html")));
// Unknown API routes → JSON 404 instead of HTML
app.use("/api", (req, res) => res.status(404).json({ ok: false, error: "Not found" }));

// ─── SERVER START ─────────────────────────────────────────────────────────────
app.listen(PORT, async () => {
  console.log(`Server running on port ${PORT}`);

  if (WEBHOOK_HOST) {
    const webhookPath = `/webhook/${BOT_TOKEN}`;
    app.post(webhookPath, (req, res) => {
      bot.processUpdate(req.body);
      res.sendStatus(200);
    });
    const webhookUrl = `https://${WEBHOOK_HOST}${webhookPath}`;
    try {
      await bot.setWebHook(webhookUrl);
      console.log(`Webhook set: ${webhookUrl}`);
    } catch (e) { console.error("Webhook error:", e.message); }

    setInterval(() => {
      require("https").get(`https://${WEBHOOK_HOST}/health`, () => {}).on("error", () => {});
    }, 5 * 60 * 1000);
  } else {
    console.log("Polling mode (local)");
  }
});
