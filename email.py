import os
import subprocess
import sys

# Instalar dependencias
def install_dependencies():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "python-telegram-bot==13.11", "requests"])

install_dependencies()

import logging
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

# Configuración básica del bot
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Definición de estados
ASK_EMAIL, ASK_SPOOFED_EMAIL, ASK_SPOOFED_NAME, ASK_MESSAGE, ASK_SUBJECT = range(5)

# Credenciales de SMTP y token de Telegram
TELEGRAM_BOT_TOKEN = '7022795067:AAFo7mQallwh1KySoyeJOFnlnKBxzweCS-w'
AUTHORIZED_USER_ID = 5498464941
SMTP_USERNAME = 'caiilosf@gmail.com'
SMTP_PASSWORD = 'knhrxP1Y5Czj49sg'
SMTP_HOST = 'smtp-relay.brevo.com'
SMTP_PORT = 587

# Almacenamiento en memoria de las claves
keys = {}
user_keys = {}

def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text(
        '¡Hola! Bienvenido al bot. Aquí tienes los comandos disponibles:\n\n'
        '/ayuda - Mostrar esta ayuda\n'
        '/nuevo_mensaje - Enviar un nuevo mensaje\n'
        '/creditos - Verificar tus créditos restantes\n'
        '/canjear <tuclave> - Canjear una clave\n'
        '/cancelar - Cancelar la operación actual'
    )
    return ConversationHandler.END

def ayuda(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Lista de comandos:\n\n'
        '/ayuda - Mostrar esta ayuda\n'
        '/nuevo_mensaje - Enviar un nuevo mensaje\n'
        '/creditos - Verificar tus créditos restantes\n'
        '/canjear <tuclave> - Canjear una clave\n'
        '/cancelar - Cancelar la operación actual'
    )

def creditos(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id in user_keys:
        remaining_credits = user_keys[user_id]
        update.message.reply_text(f'Tienes {remaining_credits} créditos restantes.')
    else:
        update.message.reply_text('No tienes créditos asignados. Usa /canjear <tuclave> para canjear una clave.')

def canjear(update: Update, context: CallbackContext) -> None:
    try:
        key = context.args[0]
        user_id = update.message.from_user.id

        if key in keys and keys[key] > 0:
            user_keys[user_id] = keys.pop(key)
            update.message.reply_text(f'Clave canjeada exitosamente! Tienes {user_keys[user_id]} créditos.')
        else:
            update.message.reply_text('Clave inválida o expirada. Por favor, ingresa una clave válida.')
    except IndexError:
        update.message.reply_text('Por favor, proporciona una clave válida con el comando /canjear <tuclave>.')

def nuevo_mensaje(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if user_id in user_keys and user_keys[user_id] > 0:
        update.message.reply_text('Ingresa el correo del destinatario:')
        return ASK_EMAIL
    else:
        update.message.reply_text('No tienes suficientes créditos. Por favor, canjea una clave usando /canjear <tuclave>.')
        return ConversationHandler.END

def ask_email(update: Update, context: CallbackContext) -> int:
    context.user_data['receiver_email'] = update.message.text
    update.message.reply_text('Ahora ingresa el correo falsificado:')
    return ASK_SPOOFED_EMAIL

def ask_spoofed_email(update: Update, context: CallbackContext) -> int:
    context.user_data['spoofed_email'] = update.message.text
    update.message.reply_text('Ahora ingresa el nombre falsificado:')
    return ASK_SPOOFED_NAME

def ask_spoofed_name(update: Update, context: CallbackContext) -> int:
    context.user_data['spoofed_name'] = update.message.text
    update.message.reply_text('Ahora ingresa el mensaje que deseas enviar:')
    return ASK_MESSAGE

def ask_message(update: Update, context: CallbackContext) -> int:
    context.user_data['message'] = update.message.text
    update.message.reply_text('Finalmente, ingresa el asunto del correo:')
    return ASK_SUBJECT

def ask_subject(update: Update, context: CallbackContext) -> int:
    context.user_data['subject'] = update.message.text

    # Enviar correo
    data = {
        'receiver_email': context.user_data['receiver_email'],
        'spoofed_email': context.user_data['spoofed_email'],
        'spoofed_name': context.user_data['spoofed_name'],
        'message': context.user_data['message'],
        'subject': context.user_data['subject']
    }

    try:
        msg = MIMEMultipart("related")
        msg['From'] = f"{data['spoofed_name']} <{data['spoofed_email']}>"
        msg['To'] = data['receiver_email']
        msg['Subject'] = data['subject']
        msg.attach(MIMEText(data['message'], 'plain'))

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(data['spoofed_email'], data['receiver_email'], msg.as_string())

        user_id = update.message.from_user.id
        user_keys[user_id] -= 1
        update.message.reply_text('Correo enviado exitosamente!')
    except Exception as e:
        update.message.reply_text(f'Hubo un error al enviar el correo: {e}')

    return ConversationHandler.END

def cancelar(update: Update, _: CallbackContext) -> int:
    update.message.reply_text('Operación cancelada.')
    return ConversationHandler.END

def generate_key(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id != AUTHORIZED_USER_ID:
        update.message.reply_text('No estás autorizado para generar claves.')
        return

    try:
        limit = int(context.args[0])
        key = os.urandom(16).hex()
        keys[key] = limit
        update.message.reply_text(f'Nueva clave generada: {key} (Límite: {limit} usos)')
    except (IndexError, ValueError):
        update.message.reply_text('Uso: /generate_key <límite>')

def main():
    updater = Updater(TELEGRAM_BOT_TOKEN)
    dispatcher = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('nuevo_mensaje', nuevo_mensaje)],
        states={
            ASK_EMAIL: [MessageHandler(Filters.text & ~Filters.command, ask_email)],
            ASK_SPOOFED_EMAIL: [MessageHandler(Filters.text & ~Filters.command, ask_spoofed_email)],
            ASK_SPOOFED_NAME: [MessageHandler(Filters.text & ~Filters.command, ask_spoofed_name)],
            ASK_MESSAGE: [MessageHandler(Filters.text & ~Filters.command, ask_message)],
            ASK_SUBJECT: [MessageHandler(Filters.text & ~Filters.command, ask_subject)],
        },
        fallbacks=[CommandHandler('cancelar', cancelar)],
    )

    dispatcher.add_handler(conv_handler)
    dispatcher.add_handler(CommandHandler('generate_key', generate_key))
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('ayuda', ayuda))
    dispatcher.add_handler(CommandHandler('creditos', creditos))
    dispatcher.add_handler(CommandHandler('canjear', canjear))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
