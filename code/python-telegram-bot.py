import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import paho.mqtt.publish as publish
from google.cloud import bigquery
import bcrypt

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Telegram bot token
TOKEN = '7010775283:AAGbVYbbTgFK64DtZ3tcVQsSahKdJukUqGg'

# MQTT broker details
MQTT_BROKER_HOST = '35.192.204.119'
MQTT_BROKER_PORT = 1883

# BigQuery configuration
PROJECT_ID = 'trans-market-419700'
DATASET_ID = 'smart_home_security_system'
TABLE_ID = 'users'

# Initialize BigQuery client
bigquery_client = bigquery.Client(project=PROJECT_ID)

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

# Function to handle /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome! Please enter your username and password.')

# Function to handle authentication and send MQTT command
async def send_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        username = context.args[0]
        password = context.args[1]
        idHouse = authenticate_user(username, password)
        print(idHouse)
        if idHouse:
            topic = f"cmd/{idHouse}"
            command = context.args[2]  # Assuming the command is passed as third argument
            publish.single(topic, command, hostname=MQTT_BROKER_HOST, port=MQTT_BROKER_PORT)
            await update.message.reply_text('Command sent successfully!')
        else:
            await update.message.reply_text('Authentication failed. Please try again.')
    except IndexError:
        await update.message.reply_text('Invalid command. Please provide username, password, and command.')

def main():
    # Create the Application and pass it your bot's token.
    application = ApplicationBuilder().token(TOKEN).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("send_command", send_command))

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()
