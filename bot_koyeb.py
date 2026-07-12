import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, LinkPreviewOptions
from telegram.ext import ApplicationBuilder, CommandHandler, ChatJoinRequestHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler

import os

TOKEN = os.environ['BOT_TOKEN']
ADMIN_ID = 8527221373

# Veritabanı
db = sqlite3.connect("bot_data.db", check_same_thread=False)
cursor = db.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY)")
cursor.execute("CREATE TABLE IF NOT EXISTS config (key TEXT PRIMARY KEY, value TEXT)")
defaults = [('msg', 'Merhaba {name}, hoş geldin!'), ('btn_txt', 'Web Sitem'), ('btn_url', 'https://google.com')]
for k, v in defaults: cursor.execute("INSERT OR IGNORE INTO config VALUES (?, ?)", (k, v))
db.commit()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id == ADMIN_ID:
        kb = [[InlineKeyboardButton("Mesajı Düzenle", callback_data="edit_msg")],
              [InlineKeyboardButton("Buton Düzenle", callback_data="edit_btn")]]
        await update.message.reply_text("Admin Panel:", reply_markup=InlineKeyboardMarkup(kb))
    else:
        cursor.execute("INSERT OR IGNORE INTO users VALUES (?)", (update.effective_user.id,))
        db.commit()
        await update.message.reply_text("Hoş geldin! Bir isteğin olursa buraya yaz.")

async def cb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query.data == "edit_msg":
        await query.message.reply_text("Yeni hoş geldin mesajını yaz:")
        context.user_data['state'] = 'set_msg'
    elif query.data == "edit_btn":
        await query.message.reply_text("Format: Buton Yazısı | Link\nÖrnek: İletişim | https://t.me/kullanici")
        context.user_data['state'] = 'set_btn'
    await query.answer()

async def msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get('state')
    if update.effective_user.id == ADMIN_ID:
        if state == 'set_msg':
            cursor.execute("UPDATE config SET value = ? WHERE key = 'msg'", (update.message.text,))
            db.commit()
            await update.message.reply_text("Mesaj güncellendi!")
        elif state == 'set_btn':
            txt, url = update.message.text.split('|')
            cursor.execute("UPDATE config SET value = ? WHERE key = 'btn_txt'", (txt.strip(),))
            cursor.execute("UPDATE config SET value = ? WHERE key = 'btn_url'", (url.strip(),))
            db.commit()
            await update.message.reply_text("Buton güncellendi!")
        context.user_data['state'] = None
    else:
        await context.bot.forward_message(ADMIN_ID, update.effective_user.id, update.message.message_id)

async def join_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.chat_join_request.from_user
    cfg = {r[0]: r[1] for r in cursor.execute("SELECT * FROM config").fetchall()}
    msg = cfg['msg'].replace("{name}", user.first_name)
    kb = [[InlineKeyboardButton(cfg['btn_txt'], url=cfg['btn_url'])]]
    
    try:
        await context.bot.send_message(user.id, msg, reply_markup=InlineKeyboardMarkup(kb))
        await context.bot.approve_chat_join_request(update.chat_join_request.chat.id, user.id)
    except: pass

app = ApplicationBuilder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(cb_handler))
app.add_handler(ChatJoinRequestHandler(join_handler))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, msg_handler))
app.run_polling()
