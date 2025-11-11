import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

# CONFIG
BOT_TOKEN = os.environ['BOT_TOKEN']
SHEET_ID = os.environ['SHEET_ID']
GOOGLE_CREDS = json.loads(os.environ['GOOGLE_CREDENTIALS'])

# Google Sheets
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDS, scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1

pending = {}

def normalizar_dni(dni):
    if not dni:
        return None
    dni = str(dni).replace(' ', '').upper()
    return dni if all(c.isalnum() or c == '-' for c in dni) else None

def buscar_dni(dni):
    try:
        records = sheet.get_all_records()
        for idx, row in enumerate(records, start=2):
            if normalizar_dni(row.get('DNI', '')) == dni:
                return {
                    'fila': idx,
                    'nombre': row.get('Nombre', ''),
                    'entregado': str(row.get('Entregado', '')).upper() == 'TRUE'
                }
        return None
    except:
        return None

def marcar_entregado(dni):
    try:
        resultado = buscar_dni(dni)
        if not resultado:
            return False
        fecha = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        sheet.update_cell(resultado['fila'], 3, 'TRUE')
        sheet.update_cell(resultado['fila'], 4, fecha)
        return True
    except:
        return False

async def start(update: Update, context):
    await update.message.reply_text('Envíame un DNI (ej. 12345678Z).')

async def handle_message(update: Update, context):
    chat_id = update.message.chat_id
    text = update.message.text.strip()
    
    if chat_id in pending:
        if text.lower() in ['si', 'sí']:
            dni = pending[chat_id]
            ok = marcar_entregado(dni)
            del pending[chat_id]
            await update.message.reply_text(f"✅ {dni}" if ok else f"❌ Error")
            return
        elif text.lower() == 'no':
            del pending[chat_id]
            await update.message.reply_text('Sin cambios.')
            return
    
    dni = normalizar_dni(text)
    if not dni:
        await update.message.reply_text('DNI no válido.')
        return
    
    resultado = buscar_dni(dni)
    if not resultado:
        await update.message.reply_text(f'❌ {dni} no encontrado.')
        return
    
    if resultado['entregado']:
        await update.message.reply_text(f"✅ {resultado['nombre']} – Ya entregado.")
    else:
        pending[chat_id] = dni
        keyboard = [[
            InlineKeyboardButton("✅ Sí", callback_data=f"ok|{dni}"),
            InlineKeyboardButton("❌ No", callback_data=f"no|{dni}")
        ]]
        await update.message.reply_text(
            f"📋 {resultado['nombre']}\n\n¿Marcar?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def handle_callback(update: Update, context):
    query = update.callback_query
    await query.answer()
    action, dni = query.data.split('|')
    
    if action == 'ok':
        ok = marcar_entregado(dni)
        await query.edit_message_text(f"✅ {dni}" if ok else f"❌ Error")
    else:
        await query.edit_message_text(f"{dni}: sin cambios")

# Bot
app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler('start', start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
app.add_handler(CallbackQueryHandler(handle_callback))

print("Bot iniciado!")
app.run_polling()
```

**`requirements.txt`:**
```
python-telegram-bot==20.7
gspread==5.12.0
oauth2client==4.1.3
