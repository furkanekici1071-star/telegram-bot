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
        "button_text": None, "button_url": None,
        "stats": {"accepted": 0, "failed": 0},
        "history": [] # İletişime geçilenler listesi
    }

def save_db(db):
    with open(DB_FILE, "w") as f: json.dump(db, f, indent=4)

db = load_db()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    keyboard = [
        [InlineKeyboardButton("📊 İstatistikler", callback_data="stats")],
        [InlineKeyboardButton(f"✅ Oto-Kabul: {'AÇIK' if db['auto_accept'] else 'KAPALI'}", callback_data="toggle_accept")],
        [InlineKeyboardButton("👋 Hoş Geldin Mesajı Ayarla", callback_data="set_welcome")],
        [InlineKeyboardButton("🔗 Buton Ayarla", callback_data="set_button")]
    ]
    await update.message.reply_text("Admin Paneli:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_join_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    req = update.chat_join_request
    user = req.from_user
    
    # DÜZELTME BURADA: chat_id yerine req.chat.id kullanılır
    chat_id = req.chat.id 
    
    if db["auto_accept"]:
        try:
            await context.bot.approve_chat_join_request(chat_id=chat_id, user_id=user.id)
            
            # Geçmişe ekle
            if user.id not in db["history"]:
                db["history"].append(user.id)
            
            # Mesaj gönder
            kb = [[InlineKeyboardButton(db["button_text"], url=db["button_url"])]] if db["button_text"] else None
            await context.bot.send_message(user.id, db["welcome_msg"].format(name=user.first_name), reply_markup=InlineKeyboardMarkup(kb) if kb else None)
            
            db["stats"]["accepted"] += 1
            save_db(db)
        except Exception as e:
            db["stats"]["failed"] += 1
            save_db(db)
            await context.bot.send_message(ADMIN_ID, f"❌ Hata ({user.full_name}): {str(e)}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "stats":
        await query.message.reply_text(f"📊 İstatistikler\nKabul Edilen: {db['stats']['accepted']}\nHatalı: {db['stats']['failed']}")
    elif query.data == "toggle_accept":
        db["auto_accept"] = not db["auto_accept"]
        save_db(db)
        await query.edit_message_text(f"Oto-Kabul: {'AÇIK' if db['auto_accept'] else 'KAPALI'}")
    elif query.data == "set_welcome":
        await query.message.reply_text("Yeni hoş geldin mesajını yaz:")
        context.user_data["action"] = "set_welcome"

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        # Kullanıcıdan gelen mesajı admine ilet
        await context.bot.forward_message(ADMIN_ID, update.effective_chat.id, update.message.message_id)
        return

    action = context.user_data.get("action")
    if action == "set_welcome":
        db["welcome_msg"] = update.message.text
        save_db(db)
        await update.message.reply_text("✅ Hoş geldin mesajı güncellendi!")
        context.user_data["action"] = None

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(ChatJoinRequestHandler(handle_join_request))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message_handler))
    app.run_polling()
