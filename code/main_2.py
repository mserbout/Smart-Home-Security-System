#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""This example showcases how PTBs "arbitrary callback data" feature can be used.

For detailed info on arbitrary callback data, see the wiki page at
https://github.com/python-telegram-bot/python-telegram-bot/wiki/Arbitrary-callback_data

Note:
To use arbitrary callback data, you must install PTB via
`pip install "python-telegram-bot[callback-data]"`
"""
import logging
from typing import List, Tuple, cast
from io import BytesIO
from telegram import InputFile

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    InvalidCallbackData,
    PicklePersistence,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays info on how to use the bot."""
    await update.message.reply_text(
        "Use /start to test this bot. Use /clear to clear the stored data so that you can see "
        "what happens, if the button data is not available. "
    )


async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Clears the callback data cache"""
    context.bot.callback_data_cache.clear_callback_data()
    context.bot.callback_data_cache.clear_callback_queries()
    await update.effective_message.reply_text("All clear!")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Sends a message with 5 inline buttons attached."""
    string_list: List[str] = ["menu", "prenotazione"]
    await update.message.reply_text("Ciao! Sono il bot ristorante di prova.\nScegli uno dei seguenti comandi:", reply_markup=build_keyboard(string_list))


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    # Estrai il chat_id dal contesto dell'utente
    chat_id = context.user_data.get('chat_id')

    if chat_id:
        # Invia un messaggio al chat_id
        await context.bot.send_message(chat_id, "Ecco il menu del giorno!")

        # Ora invia anche un file
        with open('BotTelegramRisto\menu-spagnolo-prova.pdf', 'rb') as file:
            file_content = file.read()

        file_stream = BytesIO(file_content)
        file_stream.name = 'menu_del_giorno.pdf'  # Sostituisci con il nome del tuo file
        await context.bot.send_document(chat_id, document=InputFile(file_stream))
    else:
        print("Chat ID non disponibile nell'handler del menu.")



def build_keyboard(items: List[str]) -> InlineKeyboardMarkup:
    """Builds an inline keyboard with a row of buttons."""
    keyboard = [[InlineKeyboardButton(item, callback_data=item)] for item in items]
    return InlineKeyboardMarkup(keyboard)


async def list_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query
    await query.answer()
    # Get the data from the callback_data.
    # If you're using a type checker like MyPy, you'll have to use typing.cast
    # to make the checker get the expected type of the callback_data

    print(query.data)
    message_comand = query.data

    context.user_data['selected_command'] = message_comand
    context.user_data['chat_id'] = query.message.chat_id

    # Ora puoi utilizzare il nuovo comando come desiderato
    print(f"Nuovo comando selezionato: {message_comand}")

    # Ad esempio, puoi avviare l'handler associato al comando 'menu'
    if message_comand == 'menu':
        await menu(update, context)


async def handle_invalid_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Informs the user that the button is no longer available."""
    await update.callback_query.answer()
    await update.effective_message.edit_text(
        "Sorry, I could not process this button click 😕 Please send /start to get a new keyboard."
    )


def main() -> None:
    """Run the bot."""
    # We use persistence to demonstrate how buttons can still work after the bot was restarted
    persistence = PicklePersistence(filepath="arbitrarycallbackdatabot")
    # Create the Application and pass it your bot's token.
    application = (
        Application.builder()
        .token("7010775283:AAGbVYbbTgFK64DtZ3tcVQsSahKdJukUqGg")
        .persistence(persistence)
        .arbitrary_callback_data(True)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(
        CallbackQueryHandler(handle_invalid_button, pattern=InvalidCallbackData)
    )
    application.add_handler(CallbackQueryHandler(list_button))

    # Run the bot until the user presses Ctrl-C
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()