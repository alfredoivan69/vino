import os
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json
from datetime import datetime

app = Flask(__name__)

# CONFIG
BOT_TOKEN = os.environ['BOT_TOKEN']
SHEET_ID = os.environ['SHEET_ID']
GOOGLE_CREDS = json.loads(os.environ['GOOGLE_CREDENTIALS'])

bot = Bot(token=BOT_TOKEN)

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

def handle_message(message):
    chat_id = message['chat']['id']
    text = message.get('text', '').strip()
    
    if text == '/start':
        bot.send_message(chat_id=chat_id, text='Envíame un DNI (ej. 12345678Z).')
        return
    
    if chat_id in pending:
        if text.lower() in ['si', 'sí']:
            dni = pending[chat_id]
            ok = marcar_entregado(dni)
            del pending[chat_id]
            bot.send_message(chat_id=chat_id, text=f"✅ {dni}" if ok else f"❌ Error")
            return
        elif text.lower() == 'no':
            del pending[chat_id]
            bot.send_message(chat_id=chat_id, text='Sin cambios.')
            return
    
    dni = normalizar_dni(text)
    if not dni:
        bot.send_message(chat_id=chat_id, text='DNI no válido.')
        return
    
    resultado = buscar_dni(dni)
    if not resultado:
        bot.send_message(chat_id=chat_id, text=f'❌ {dni} no encontrado.')
        return
    
    if resultado['entregado']:
        bot.send_message(chat_id=chat_id, text=f"✅ {resultado['nombre']} – Ya entregado.")
    else:
        pending[chat_id] = dni
        keyboard = {
            'inline_keyboard': [[
                {'text': '✅ Sí', 'callback_data': f"ok|{dni}"},
                {'text': '❌ No', 'callback_data': f"no|{dni}"}
            ]]
        }
        bot.send_message(
            chat_id=chat_id,
            text=f"📋 {resultado['nombre']}\n\n¿Marcar?",
            reply_markup=keyboard
        )

def handle_callback(callback_query):
    query_id = callback_query['id']
    chat_id = callback_query['message']['chat']['id']
    message_id = callback_query['message']['message_id']
    data = callback_query['data']
    
    action, dni = data.split('|')
    
    if action == 'ok':
        ok = marcar_entregado(dni)
        bot.answer_callback_query(callback_query_id=query_id, text='✅' if ok else '❌')
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"✅ {dni}" if ok else f"❌ Error"
        )
    else:
        bot.answer_callback_query(callback_query_id=query_id, text='Sin cambios')
        bot.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=f"{dni}: sin cambios"
        )

@app.route('/', methods=['GET'])
def index():
    return 'Bot running!', 200

@app.route('/' + BOT_TOKEN, methods=['POST'])
def webhook():
    try:
        update = request.get_json()
        
        if 'message' in update:
            handle_message(update['message'])
        elif 'callback_query' in update:
            handle_callback(update['callback_query'])
            
    except Exception as e:
        print(f"Error: {e}")
    
    return 'ok', 200

if __name__ == '__main__':
    # Configurar webhook
    webhook_url = os.environ.get('RENDER_EXTERNAL_URL', '')
    if webhook_url:
        bot.set_webhook(url=f"{webhook_url}/{BOT_TOKEN}")
        print(f"Webhook configurado: {webhook_url}/{BOT_TOKEN}")
    
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port)
```

### **Actualiza `requirements.txt`:**
```
Flask==3.0.0
python-telegram-bot==20.7
gspread==5.12.0
oauth2client==4.1.3
gunicorn==21.2.0
```

---

## 🚀 **Configuración en Render:**

### **Tipo de servicio:**
- ✅ **Web Service** (NO Background Worker)

### **Build Command:**
```
pip install -r requirements.txt
```

### **Start Command:**
```
gunicorn bot:app
