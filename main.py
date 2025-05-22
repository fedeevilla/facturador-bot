import os
from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
import subprocess

# Estados de conversación
AMOUNT, IVA_TYPE, CUIT = range(3)

load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Hola! ¿Cuál es el monto de la factura?")
    return AMOUNT


async def amount_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = update.message.text.strip()

    if not amount.isdigit():
        await update.message.reply_text("❌ Ingresá un monto válido (solo números).")
        return AMOUNT

    context.user_data["amount"] = amount

    reply_keyboard = [["1", "3"]]
    await update.message.reply_text(
        "📄 ¿Qué tipo de receptor es?\n1️⃣ Responsable Inscripto\n3️⃣ Consumidor Final",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True),
    )
    return IVA_TYPE


async def iva_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    iva = update.message.text.strip()
    if iva not in ["1", "3"]:
        await update.message.reply_text("❌ Seleccioná 1 o 3.")
        return IVA_TYPE

    context.user_data["iva"] = iva

    if iva == "1":
        await update.message.reply_text("🔢 Ingresá el CUIT del receptor:", reply_markup=ReplyKeyboardRemove())
        return CUIT
    else:
        return await run_factura(update, context)


async def cuit_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    cuit = update.message.text.strip()
    if not cuit.isdigit() or len(cuit) != 11:
        await update.message.reply_text("❌ Ingresá un CUIT válido de 11 dígitos.")
        return CUIT

    context.user_data["cuit"] = cuit
    return await run_factura(update, context)


async def run_factura(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = context.user_data
    args = ["python", "facturar.py", "--amount", data["amount"], "--iva", data["iva"]]

    if data.get("cuit"):
        args += ["--cuit", data["cuit"]]

    await update.message.reply_text("⚙️ Generando factura...", reply_markup=ReplyKeyboardRemove())

    result = subprocess.run(args, capture_output=True, text=True)
    output = result.stdout + "\n" + result.stderr

    await update.message.reply_text(f"✅ Resultado:\n{output}")
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Proceso cancelado.", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, amount_handler)],
            IVA_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, iva_handler)],
            CUIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, cuit_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    print("🤖 Bot iniciado. Esperando mensajes...")
    app.run_polling()


if __name__ == "__main__":
    main()
