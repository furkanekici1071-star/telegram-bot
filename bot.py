import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ChatJoinRequestHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

TOKEN = '8704091873:AAHCSkOxT8CyEcBzBO0t6cav4Z_H7uNuOAA'
ADMIN_ID = 8527221373

# --- VERİTABANI VE AYARLAR ---
db = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
cursor.execute("CREATE TABLE IF NOT EXISTS stats (key TEXT PRIMARY KEY, count INTEGER)")

# Ayarları başlat (Varsayılanlar)
defaults = [('msg', 'Merhaba {name}, hoş geldin!'), ('footer', 'Hile/Cihaz bilginizi yazın, admin dönecektir.'),
            ('btn_txt', 'Siteye Git'), ('btn_url', 'https://google.com'), ('auto_approve', 'True')]
for k, v in defaults: cursor.execute("INSERT OR IGNORE INTO config VALUES (?, ?)", (k, v))
for k in ['total_req', 'success', 'failed']: cursor.execute("INSERT OR IGNORE INTO stats VALUES (?, 0)", (k,))
db.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        kb = [
            [InlineKeyboardButton("Mesajı Düzenle", callback_data="edit_msg"), InlineKeyboardButton("Buton Düzenle", callback_data="edit_btn")],
            [InlineKeyboardButton("Duyuru Gönder", callback_data="broadcast"), InlineKeyboardButton("İstatistikler", callback_data="stats")],
            [InlineKeyboardButton("Otomatik Kabul: AÇ/KAPAT", callback_data="toggle_approve")]
        ]
        await update.message.reply_text("Admin Paneli:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        await update.message.reply_text("Furkan'ın özel botuna hoş geldin!")

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    if data == "edit_msg":
        await query.message.reply_text("Yeni hoş geldin mesajını yaz:")
        context.user_data['state'] = 'set_msg'
    elif data == "edit_btn":
        await query.message.reply_text("Format: Yazı | Link\nÖrnek: Site | https://google.com")
        context.user_data['state'] = 'set_btn'
    elif data == "stats":
        s = {r[0]: r[1] for r in cursor.execute("SELECT * FROM stats").fetchall()}
        await query.message.reply_text(f"📊 İstatistikler:\nToplam İstek: {s['total_req']}\nBaşarılı: {s['success']}\nBaşarısız: {s['failed']}")
    elif data == "broadcast":
        await query.message.reply_text("Duyuru metnini gönder:")
        context.user_data['state'] = 'broadcasting'
    elif data == "toggle_approve":
        current = cursor.execute("SELECT value FROM config WHERE key='auto_approve'").fetchone()[0]
        new_val = 'False' if current == 'True' else 'True'
        cursor.execute("UPDATE config SET value = ? WHERE key = 'auto_approve'", (new_val,))
        db.commit()
        await query.message.reply_text(f"Otomatik onay: {new_val}")
    await query.answer()

async def join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    chat = update.chat_join_request.chat
    cursor.execute("UPDATE stats SET count = count + 1 WHERE key = 'total_req'")
    
    is_new = cursor.execute("SELECT id FROM users WHERE id = ?", (user.id,)).fetchone() is None
    cfg = {r[0]: r[1] for r in cursor.execute("SELECT * FROM config").fetchall()}
    
    msg = cfg['msg'].replace("{name}", user.first_name) if is_new else "Tekrar hoş geldin dostum, seni görmek güzel!"
    full_msg = f"{msg}\n\n{cfg['footer']}"
    
    try:
        await context.bot.send_message(user.id, full_msg, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(cfg['btn_txt'], url=cfg['btn_url'])]]))
        cursor.execute("UPDATE stats SET count = count + 1 WHERE key = 'success'")
        if is_new: cursor.execute("INSERT INTO users VALUES (?)", (user.id,))
    except:
        cursor.execute("UPDATE stats SET count = count + 1 WHERE key = 'failed'")
    
    if cfg['auto_approve'] == 'True':
        await context.bot.approve_chat_join_request(chat.id, user.id)
    db.commit()

async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    if update.effective_user.id == ADMIN_ID:
        if state == 'set_msg':
            cursor.execute("UPDATE config SET value = ? WHERE key = 'msg'", (update.message.text,))
            await update.message.reply_text("Mesaj güncellendi!")
        elif state == 'set_btn':
            txt, url = update.message.text.split('|')
            cursor.execute("UPDATE config SET value = ? WHERE key = 'btn_txt'", (txt.strip(),))
            cursor.execute("UPDATE config SET value = ? WHERE key = 'btn_url'", (url.strip(),))
            await update.message.reply_text("Buton güncellendi!")
        elif state == 'broadcasting':
            for u in cursor.execute("SELECT id FROM users").fetchall():
                try: await context.bot.send_message(u[0], update.message.text)
                except: pass
            await update.message.reply_text("Duyuru gönderildi!")
        db.commit()
        context.user_data['state'] = None
    elif update.effective_user.id != ADMIN_ID:
        await context.bot.forward_message(ADMIN_ID, update.effective_user.id, update.message.message_id)

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(ChatJoinRequestHandler(join_handler))
app.add_handler(CallbackQueryHandler(cb_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))
app.run_polling()
