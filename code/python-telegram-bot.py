import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
from google.cloud import bigquery
import bcrypt
import asyncio

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Telegram bot token
TOKEN = '7496052535:AAEKyaYYC0xgYKUtFoVJunliT7OVszW2jnw'

# MQTT broker details
MQTT_BROKER_HOST = '35.192.204.119'
MQTT_BROKER_PORT = 1883

# BigQuery configuration
PROJECT_ID = 'trans-market-419700'
DATASET_ID = 'smart_home_security_system'
TABLE_ID = 'users'

# Initialize BigQuery client
bigquery_client = bigquery.Client(project=PROJECT_ID)

# Initialize global variables for MQTT
mqtt_client = mqtt.Client()
status_message = None

# Function to authenticate user and retrieve idHouse
def authenticate_user(username, password):
    query = f"""
    SELECT idHouse, password FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
    WHERE username = '{username}'
    """
    query_job = bigquery_client.query(query)
    results = query_job.result()
    row = next(results, None)
    if row:
        hashed_password = row['password'].encode('utf-8')
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
            return row['idHouse']
    return None

# MQTT on_message callback
def on_message(client, userdata, message):
    global status_message
    status_message = message.payload.decode('utf-8')

# Function to handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Login", callback_data='login')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = update.callback_query.message if update.callback_query else update.message
    await message.reply_text(
        "Welcome to the Smart Home Security Bot! You can use the following commands:\n"
        "/start - Show this message\n"
        "/send_command - Send a command to your house\n"
        "/status - Show the status of your house\n"
        "/logout - Logout from the bot",
        reply_markup=reply_markup
    )

# Function to handle login process
async def login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Please enter your username and password separated by a space, e.g., `username password`")

# Function to handle user input after login
async def handle_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        message_text = update.message.text
        username, password = message_text.split()
        idHouse = authenticate_user(username, password)
        if idHouse:
            context.user_data['idHouse'] = idHouse
            await update.message.reply_text('Login successful!')

            await show_main_menu(update, context)
        else:
            await update.message.reply_text('Authentication failed. Please try again.')
    except ValueError:
        await update.message.reply_text('Invalid format. Please provide username and password.')

# Function to show main menu after login or after any command
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Send Command", callback_data='send_command')],
        [InlineKeyboardButton("Show Status", callback_data='show_status')],
        [InlineKeyboardButton("Logout", callback_data='logout')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = update.callback_query.message if update.callback_query else update.message
    await message.reply_text('Choose an option:', reply_markup=reply_markup)

# Function to handle authentication and send MQTT command
async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [InlineKeyboardButton("Start Alarm", callback_data='start_alarm')],
        [InlineKeyboardButton("Stop Alarm", callback_data='stop_alarm')],
        [InlineKeyboardButton("Back to Menu", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Choose a command:", reply_markup=reply_markup)

async def handle_send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    idHouse = context.user_data.get('idHouse')
    
    if idHouse:
        if query.data == 'start_alarm':
            command = '1'
        elif query.data == 'stop_alarm':
            command = '0'
        else:
            await show_main_menu(update, context)
            return
        
        topic = f"cmd/alarm/{idHouse}"
        publish.single(topic, command, hostname=MQTT_BROKER_HOST, port=MQTT_BROKER_PORT)
        await query.edit_message_text('Command sent successfully!')
        await show_main_menu(update, context)
    else:
        await query.edit_message_text('Please login first.')
        await start(update, context)

# Function to show house status
async def show_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global status_message
    idHouse = context.user_data.get('idHouse')
    if idHouse:
        status_message = None  # Reset the status message before sending a new request
        status_topic = f"data/telegram/{idHouse}"
        request_topic = f"cmd/status/{idHouse}"

        # Set up MQTT client to subscribe to status topic
        mqtt_client.on_message = on_message
        mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, 60)
        mqtt_client.subscribe(status_topic)
        mqtt_client.loop_start()

        await update.callback_query.answer()
        await update.callback_query.edit_message_text(f'Requesting status for house {idHouse}...')

        # Publish a status request
        publish.single(request_topic, 'status', hostname=MQTT_BROKER_HOST, port=MQTT_BROKER_PORT)

        # Wait for the status message
        await asyncio.sleep(5)  # Adjust the sleep time as needed

        if status_message:
            try:
                # Attempt to parse the JSON message
                status_data = json.loads(status_message)
                temperature = status_data.get("temperature", "Unavailable")
                humidity = status_data.get("humidity", "Unavailable")
                alarm = status_data.get("alarm", "Unavailable")
                detection = status_data.get("detection", 0)
                time = status_data.get("time", "Unavailable")
                
                # Check if the temperature and humidity values are 'nan' and replace with a more readable message
                if temperature == "nan":
                    temperature = "Unavailable"
                if humidity == "nan":
                    humidity = "Unavailable"
                
                readable_status = f"""
                Status of the House Malaga:
                - Temperature: {temperature}
                - Humidity: {humidity}
                - Alarm Status: {alarm}
                - Detection: {"Movement detected" if detection else "No movement detected"}
                - Last Updated: {time}
                """
                
                # Display the readable status
                await update.callback_query.edit_message_text(readable_status)
            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON: {e}")
                await update.callback_query.edit_message_text(f"Failed to decode status message for house {idHouse}.")
            status_message = None
        else:
            await update.callback_query.edit_message_text(f'Failed to retrieve status for house {idHouse}. Please try again.')

        mqtt_client.loop_stop()
        await show_main_menu(update, context)
    else:
        await update.message.reply_text('Please login first.')
        await start(update, context)



# Function to handle logout process
async def logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    idHouse = context.user_data.get('idHouse')
    if idHouse:
        context.user_data.clear()
        await update.callback_query.answer()
        await update.callback_query.edit_message_text('You have been logged out successfully.')
        await start(update, context)
    else:
        # Show the choice box again after logout
        await update.message.reply_text('Please login first.')
        await start(update, context)

# Function to handle user's choices after login
async def handle_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'send_command':
        await send_command(update, context)
    elif query.data == 'show_status':
        await show_status(update, context)
    elif query.data == 'logout':
        await logout(update, context)
    elif query.data == 'back_to_menu':
        await show_main_menu(update, context)
    else:
        await handle_send_command(update, context)

def main():
    # Create the Application and pass it your bot's token.
    application = ApplicationBuilder().token(TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(login, pattern='^login$'))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_login))
    application.add_handler(CommandHandler("send_command", handle_send_command))
    application.add_handler(CommandHandler("status", show_status))
    application.add_handler(CommandHandler("logout", logout))
    application.add_handler(CallbackQueryHandler(handle_choice, pattern='^(send_command|show_status|logout|start_alarm|stop_alarm|back_to_menu)$'))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
