from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

TOKEN = ""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Olá! 🤖\n"
        "Comandos disponíveis:\n"
        "/ping - testa o bot\n"
        "/status - mostra o status"
    )

async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong! 🟢")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot funcionando normalmente 🟢")

app = Application.builder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("ping", ping))
app.add_handler(CommandHandler("status", status))

print("Bot iniciado!")
app.run_polling()
