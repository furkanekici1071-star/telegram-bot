import sqlite3, asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ChatJoinRequestHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

# Bilgilerin yerleştirildi
TOKEN = '8704091873:AAHCSkOxT8CyEcBzBO0t6cav4Z_H7uNuOAA'
ADMIN_ID = 8527221373

# Veritabanı
db = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS hourly_stats (hour TEXT PRIMARY KEY, count INTEGER)")
db.commit()

async def join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # İstatistik
    hour = datetime.now().strftime("%Y-%m-%d %H:00")
    cursor.execute("INSERT OR IGNORE INTO hourly_stats VALUES (?, 0)", (hour,))
    cursor.execute("UPDATE hourly_stats SET count = count + 1 WHERE hour = ?", (hour,))
    db.commit()

    # 2 Dakika bekleme (Telegram sınırlarını aşmamak için)
    await asyncio.sleep(120)

    user = update.chat_join_request.from_user
    chat = update.chat_join_request.chat
    
    cfg = {r[0]: r[1] for r in cursor.execute("SELECT * FROM config").fetchall()}
    msg = cfg.get('msg', 'Merhaba {name}, hoş geldin!').replace("{name}", user.first_name)
    
    try:
        await context.bot.send_message(user.id, msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(cfg.get('btn_txt', 'Siteye Git'), url=cfg.get('btn_url', 'https://google.com'))]]))
        await context.bot.approve_chat_join_request(chat.id, user.id)
    except Exception as e:
        await context.bot.send_message(ADMIN_ID, f"❌ {user.first_name} kişisine mesaj atılamadı!\nSebep: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        kb = [[InlineKeyboardButton("📊 Saatlik Rapor", callback_data="stats")]]
        await update.message.reply_text("👑 **Admin Paneli Aktif**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')
    else:
        await update.message.reply_text("Hoş geldin!")

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "stats":
        rows = cursor.execute("SELECT * FROM hourly_stats ORDER BY hour DESC LIMIT 5").fetchall()
        text = "🕒 **Son 5 Saatin Raporu:**\n" + "\n".join([f"{r[0]} -> {r[1]} kişi" for r in rows])
        await query.message.reply_text(text)
    await query.answer()

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatJoinRequestHandler(join_handler))
    app.add_handler(CallbackQueryHandler(cb_handler))
    print("Bot başarıyla başlatıldı, istekleri bekliyor...")
    app.run_polling()
