import sqlite3, asyncio, logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ChatJoinRequestHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

TOKEN = '8704091873:AAHCSkOxT8CyEcBzBO0t6cav4Z_H7uNuOAA'
ADMIN_ID = 8527221373

# Loglama ayarı (Hataları görmek için)
logging.basicConfig(level=logging.INFO)

db = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
# Saatlik istatistik tablosu
cursor.execute("CREATE TABLE IF NOT EXISTS hourly_stats (hour TEXT PRIMARY KEY, count INTEGER)")

# Varsayılanlar
defaults = [('msg', 'Merhaba {name}, hoş geldin!'), ('btn_txt', 'Siteye Git'), ('btn_url', 'https://google.com')]
for k, v in defaults: cursor.execute("INSERT OR IGNORE INTO config VALUES (?, ?)", (k, v))
db.commit()

# Kuyruk sistemi (Telegram sınırlarını aşmamak için)
queue = asyncio.Queue()

async def worker():
    """Arka planda çalışan hız sınırlandırıcı."""
    while True:
        request_data = await queue.get()
        # İki işlem arasında 2 dakika bekleme
        await asyncio.sleep(120) 
        try:
            await process_join(request_data)
        except Exception as e:
            print(f"Worker hatası: {e}")
        queue.task_done()

async def process_join(data):
    update, context = data
    user = update.chat_join_request.from_user
    cfg = {r[0]: r[1] for r in cursor.execute("SELECT * FROM config").fetchall()}
    
    try:
        msg = cfg['msg'].replace("{name}", user.first_name)
        await context.bot.send_message(user.id, msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(cfg['btn_txt'], url=cfg['btn_url'])]]))
        await context.bot.approve_chat_join_request(update.chat_join_request.chat.id, user.id)
    except Exception as e:
        await context.bot.send_message(ADMIN_ID, f"❌ Hata! {user.first_name} kişisine mesaj atılamadı.\nSebep: {e}")

async def join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Saatlik istatistik güncelleme
    hour = datetime.now().strftime("%Y-%m-%d %H:00")
    cursor.execute("INSERT OR IGNORE INTO hourly_stats VALUES (?, 0)", (hour,))
    cursor.execute("UPDATE hourly_stats SET count = count + 1 WHERE hour = ?", (hour,))
    db.commit()
    
    # Kuyruğa ekle
    await queue.put((update, context))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        kb = [[InlineKeyboardButton("📝 Mesaj Düzenle", callback_data="edit_msg")],
              [InlineKeyboardButton("📊 Saatlik Rapor", callback_data="hourly_stats")]]
        await update.message.reply_text("👑 **Admin Paneli**", reply_markup=InlineKeyboardMarkup(kb), parse_mode='Markdown')

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "hourly_stats":
        rows = cursor.execute("SELECT * FROM hourly_stats ORDER BY hour DESC LIMIT 5").fetchall()
        text = "🕒 **Son 5 Saatin İstatistikleri:**\n" + "\n".join([f"{r[0]}: {r[1]} kişi" for r in rows])
        await query.message.reply_text(text, parse_mode='Markdown')
    # ... (diğer edit işlemleri) ...
    await query.answer()

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatJoinRequestHandler(join_handler))
    app.add_handler(CallbackQueryHandler(cb_handler))
    
    # Worker'ı başlat
    asyncio.create_task(worker())
    
    app.run_polling()
