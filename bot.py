import logging
import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ChatJoinRequestHandler

TOKEN = "8704091873:AAHCSkOxT8CyEcBzBO0t6cav4Z_H7uNuOAA"
ADMIN_ID = 8527221373 
DB_FILE = "db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f: return json.load(f)
    return {
        "auto_accept": True,
        "welcome_msg": "Hoş geldin {name}!",
        "welcome_btn_text": None, "welcome_btn_url": None,
        "stats": {"accepted": 0, "failed": 0},
        "history": [] # Kanal istek atanların ID listesi
    }

def save_db(db):
    with open(DB_FILE, "w") as f: json.dump(db, f, indent=4)

db = load_db()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    keyboard = [
        [InlineKeyboardButton("📊 İstatistikler", callback_data="stats")],
        [InlineKeyboardButton(f"✅ Oto-Kabul: {'AÇIK' if db['auto_accept'] else 'KAPALI'}", callback_data="toggle_accept")],
        [InlineKeyboardButton("👋 Hoş Geldin Ayarla", callback_data="set_welcome")],
        [InlineKeyboardButton("🔗 Hoş Geldin Buton", callback_data="set_welcome_btn")],
        [InlineKeyboardButton("📢 Duyuru Gönder", callback_data="broadcast_step1")]
    ]
    await update.message.reply_text("Admin Paneli:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    user = req.from_user
    if user.id not in db["history"]:
        db["history"].append(user.id)
        save_db(db)
    
    if db["auto_accept"]:
        try:
            await context.bot.approve_chat_join_request(chat_id=req.chat.id, user_id=user.id)
            kb = [[InlineKeyboardButton(db["welcome_btn_text"], url=db["welcome_btn_url"])]] if db["welcome_btn_text"] else None
            await context.bot.send_message(user.id, db["welcome_msg"].format(name=user.first_name), reply_markup=InlineKeyboardMarkup(kb) if kb else None)
            db["stats"]["accepted"] += 1
        except Exception as e:
            db["stats"]["failed"] += 1
            await context.bot.send_message(ADMIN_ID, f"❌ Hata ({user.full_name}): {str(e)}")
        save_db(db)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "stats":
        await query.message.reply_text(f"📊 İstatistikler\nKabul: {db['stats']['accepted']}\nHatalı: {db['stats']['failed']}\nToplam Kayıtlı: {len(db['history'])}")
    elif query.data == "toggle_accept":
        db["auto_accept"] = not db["auto_accept"]
        save_db(db)
        await query.edit_message_text(f"Oto-Kabul: {'AÇIK' if db['auto_accept'] else 'KAPALI'}")
    elif query.data == "set_welcome":
        await query.message.reply_text("Hoş geldin mesajını yaz (Örn: 'Hoş geldin {name}'):")
        context.user_data["action"] = "set_welcome"
    elif query.data == "set_welcome_btn":
        await query.message.reply_text("Buton Metni|URL formatında gönder (Örn: 'Kanalımıza Git|https://t.me/kanalın'):")
        context.user_data["action"] = "set_welcome_btn"
    elif query.data == "broadcast_step1":
        await query.message.reply_text("Duyuru mesajını ve butonunu şu formatta gönder:\n\nMesaj Metni|Buton Yazısı|Buton URL\n(Buton istemiyorsan sadece Mesaj Metni yaz)")
        context.user_data["action"] = "broadcast_exec"

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await context.bot.forward_message(ADMIN_ID, update.effective_chat.id, update.message.message_id)
        return

    action = context.user_data.get("action")
    if action == "set_welcome":
        db["welcome_msg"] = update.message.text
        save_db(db)
        await update.message.reply_text("✅ Hoş geldin mesajı güncellendi!")
    elif action == "set_welcome_btn":
        parts = update.message.text.split('|')
        db["welcome_btn_text"], db["welcome_btn_url"] = parts[0], parts[1]
        save_db(db)
        await update.message.reply_text("✅ Hoş geldin butonu güncellendi!")
    elif action == "broadcast_exec":
        parts = update.message.text.split('|')
        msg = parts[0]
        kb = [[InlineKeyboardButton(parts[1], url=parts[2])]] if len(parts) > 2 else None
        
        for user_id in db["history"]:
            try:
                await context.bot.send_message(user_id, msg, reply_markup=InlineKeyboardMarkup(kb) if kb else None)
            except: pass
        await update.message.reply_text("📢 Duyuru tüm kullanıcılara gönderildi.")
    
    context.user_data["action"] = None

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    app.run_polling()
