import asyncio
from aiohttp import web
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from google.cloud import bigquery
import bcrypt
import paho.mqtt.publish as publish
import paho.mqtt.client as mqtt
import json
import logging
from datetime import datetime
import uuid
from asyncio import Queue

# Inizializza il client di BigQuery
bigquery_client = bigquery.Client()


# Queue to store MQTT messages
mqtt_message_queue = Queue()

# Parametri di configurazione di BigQuery
PROJECT_ID = 'trans-market-419700'
DATASET_ID = 'smart_home_security_system'
TABLE_ID = 'users'

# Configurazione MQTT
MQTT_BROKER_HOST = '35.192.204.119'
MQTT_BROKER_PORT = 1883

# Crea una coda per tracciare lo stato degli utenti
user_states = {}
user_data = {}
pending_requests = {}
mqtt_clients = {}
mqtt_messages = {}
client_to_user = {}
status_message = None

"""
# Coroutine to handle sending MQTT messages
async def send_mqtt_messages():
    while True:
        print(mqtt_message_queue.qsize())
        if mqtt_message_queue.qsize() > 0:
            # Wait for a message to be enqueued
            print("Checking message queue")
            message = await mqtt_message_queue.get()
            print(message)
            # Send the message
            publish.single(message['topic'], message['payload'], hostname=message['hostname'], port=message['port'])
        
            # Notify the queue that the message has been processed
            mqtt_message_queue.task_done()
        else:
            print("Empty queue")
            await asyncio.sleep(1)


# Function to enqueue MQTT messages
async def enqueue_mqtt_message(topic, payload, hostname, port):
    message = {'topic': topic, 'payload': payload, 'hostname': hostname, 'port': port}
    print(message)
    await mqtt_message_queue.put(message)

# Function to request status
async def request_status(idHouse, chat_id):
    request_topic = f"cmd/status/{idHouse}"
    print(request_topic)
    await enqueue_mqtt_message(request_topic, 'status', MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    return chat_id

"""

def add_mqtt_message_for_user(user_id, message):
    mqtt_messages[user_id] = message

def remove_mqtt_message_for_user(user_id, message):
    if user_id in mqtt_messages:
        mqtt_messages.pop(user_id)

# Funzione per creare e avviare un nuovo client MQTT per un utente
def create_mqtt_client_for_user(user_id):
    client = mqtt.Client()
    # Configura i callback e altri parametri del client MQTT, se necessario
    client.on_message = on_message
    client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT)
    # Avvia il loop di rete in background
    client.loop_start()
    mqtt_clients[user_id] = client
    client_to_user[client] = user_id

# Funzione per interrompere e liberare il client MQTT associato a un utente
def stop_mqtt_client_for_user(user_id):
    if user_id in mqtt_clients:
        client = mqtt_clients[user_id]
        client.disconnect()
        client.loop_stop()
        del mqtt_clients[user_id]
        del client_to_user[client]

# Funzione callback MQTT per la ricezione dei messaggi
def on_message(client, userdata, msg):
    global status_message
    user_id = client_to_user.get(client)
    status_message = msg.payload.decode()
    add_mqtt_message_for_user(user_id, status_message)
    print(f"user: {user_id} msg: {status_message}")

# Inizializza il client MQTT
mqtt_client = mqtt.Client()

# Funzione per inviare un messaggio di benvenuto
async def start(bot, chat_id):
    msg = (
        "Welcome to the Smart Home Security Bot.\n"
        "Log in to access information about your home and control it!\n"
        "Use /start to return to login in case of errors."
    )

    # Creazione della tastiera inline
    keyboard = [
        [InlineKeyboardButton("Login", callback_data='login')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # Invio del messaggio con la tastiera inline
    await bot.sendMessage(chat_id=chat_id, text=msg, reply_markup=reply_markup)

# Funzione per gestire il login
async def handle_login(bot, chat_id):
    await bot.sendMessage(chat_id=chat_id, text="Please enter your username and password separated by a space, e.g., `username password`")
    #await user_states.put((chat_id, 'awaiting_credentials'))
    user_states[chat_id] = "awaiting_credentials"
    #print(user_states)

# Funzione per mostrare il menu principale
async def show_main_menu(bot, chat_id):
    keyboard = [
        [InlineKeyboardButton("Send Command", callback_data='send_command')],
        [InlineKeyboardButton("Show Status", callback_data='show_status')],
        [InlineKeyboardButton("Logout", callback_data='logout')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await bot.sendMessage(chat_id=chat_id, text='Choose an option:', reply_markup=reply_markup)

# Funzione per inviare comandi
async def send_command(bot, query):
    keyboard = [
        [InlineKeyboardButton("Start Alarm", callback_data='start_alarm')],
        [InlineKeyboardButton("Stop Alarm", callback_data='stop_alarm')],
        [InlineKeyboardButton("Back to Menu", callback_data='back_to_menu')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text("Choose a command:", reply_markup=reply_markup)

# Funzione per elaborare le credenziali
async def process_credentials(bot, chat_id, text):
    try:
        username, password = text.split(' ', 1)
    except ValueError:
        await bot.sendMessage(chat_id=chat_id, text="Invalid format. Please enter your username and password separated by a space.")
        return

    query = f"""
        SELECT idHouse, password FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}`
        WHERE username = '{username}'
    """
    try:
        query_job = bigquery_client.query(query)
        results = query_job.result()
        row = next(results, None)
        if row:
            hashed_password = row['password'].encode('utf-8')
            if bcrypt.checkpw(password.encode('utf-8'), hashed_password):
                await bot.sendMessage(chat_id=chat_id, text="Login successful! Your house ID is " + row['idHouse'])
                user_data[chat_id] = {'idHouse': row['idHouse']}
                create_mqtt_client_for_user(chat_id)
                await show_main_menu(bot, chat_id)
                #await user_states.put((chat_id, 'logged_in'))  # Change user state to logged_in
                user_states[chat_id] = "logged_in"
                print(user_states)
                return
        await bot.sendMessage(chat_id=chat_id, text="Login failed. Please check your credentials and try again.")
    except Exception as e:
        await bot.sendMessage(chat_id=chat_id, text=f"An error occurred: {str(e)}")
        print("errore nel login")

# Funzione per gestire l'invio dei comandi
async def handle_send_command(bot, query, data):
    chat_id = query.message.chat.id
    idHouse = user_data.get(chat_id, {}).get('idHouse')
    
    if idHouse:
        if data == 'start_alarm':
            command = '1'
        elif data == 'stop_alarm':
            command = '0'
        else:
            await show_main_menu(bot, chat_id)
            return
        
        topic = f"cmd/alarm/{idHouse}"
        publish.single(topic, command, hostname=MQTT_BROKER_HOST, port=MQTT_BROKER_PORT)
        await query.edit_message_text('Command sent successfully!')
        await show_main_menu(bot, chat_id)
    else:
        await query.edit_message_text('Please login first.')
        await start(bot, chat_id)

# Function to handle showing status
async def show_status(bot, query):
    chat_id = query.message.chat.id
    idHouse = user_data.get(chat_id, {}).get('idHouse')
    
    if idHouse:
        status_topic = f"data/telegram/{idHouse}"
        topic = f"cmd/status/{idHouse}"
        print(status_topic)

        if chat_id in mqtt_clients:
            mqtt_clients[chat_id].subscribe(status_topic)
        
        publish.single(topic, "status", hostname=MQTT_BROKER_HOST, port=MQTT_BROKER_PORT)

        await query.answer()
        await query.edit_message_text(f'Requesting status for house {idHouse}...')

        # Aspetta il messaggio di stato o timeout
        start_time = datetime.now()
        timeout = 5  # Regola il timeout secondo necessità
        while (datetime.now() - start_time).total_seconds() < timeout:
            if chat_id in mqtt_messages:
                message = mqtt_messages[chat_id]
                if message is not None:
                    try:
                        # Processa la risposta
                        response = json.loads(message)
                        temperature = response.get("temperature", "Unavailable")
                        humidity = response.get("humidity", "Unavailable")
                        alarm = response.get("alarm", "Unavailable")
                        detection = response.get("detection", 0)
                        time = response.get("time", "Unavailable")
                        
                        # Controlla se i valori di temperatura e umidità sono 'nan' e sostituiscili con un messaggio più leggibile
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
                        
                        # Visualizza lo stato leggibile
                        await bot.sendMessage(chat_id=chat_id, text=readable_status)
                        #await query.edit_message_text(readable_status)
                        await show_main_menu(bot, chat_id)
                        return
                    except json.JSONDecodeError as e:
                        logging.error(f"Failed to decode JSON: {e}")
                        await query.edit_message_text(f"Failed to decode status message for house {idHouse}.")
                    finally:
                        mqtt_messages[chat_id] = None
            await asyncio.sleep(1)  # Controlla il messaggio di stato ogni secondo

        # Richiesta scaduta, informa l'utente
        await query.edit_message_text(f'Failed to retrieve status for house {idHouse}. Please try again.')
    else:
        await query.edit_message_text('Please login first.')
        await start(bot, chat_id)


# Funzione per gestire il logout
async def handle_logout(bot, query):
    chat_id = query.message.chat.id
    stop_mqtt_client_for_user(chat_id)

    if chat_id in user_data:
        user_data.pop(chat_id)
    
    #await user_states.get()
    del user_states[chat_id]
    print(user_states)
    await query.edit_message_text('You have been logged out.')
    await start(bot, chat_id)

# Funzione per gestire le richieste al bot Telegram
async def telegram_bot(request):
    bot = telegram.Bot(token="7496052535:AAEKyaYYC0xgYKUtFoVJunliT7OVszW2jnw")
    if request.method == "POST":
        update = telegram.Update.de_json(await request.json(), bot)

        if update.message:
            chat_id = update.message.chat.id
            text = update.message.text

            if len(user_states) != 0: # Check if the queue is not empty
                state = user_states[chat_id]
                if state == 'awaiting_credentials':
                    await process_credentials(bot, chat_id, text)
                    return web.Response(status=200, text="okay")

            if text == "/start":
                await start(bot, chat_id)

        if update.callback_query:
            query = update.callback_query
            chat_id = query.message.chat.id
            data = query.data

            # Gestione delle callback della tastiera inline
            if data == 'login':
                await handle_login(bot, chat_id)
                await query.answer()
            elif data == 'send_command':
                await send_command(bot, query)
                await query.answer()
            elif data in ['start_alarm', 'stop_alarm']:
                await handle_send_command(bot, query, data)
                await query.answer()
            elif data == 'show_status':
                await show_status(bot, query)
                await query.answer()
            elif data == 'back_to_menu':
                await show_main_menu(bot, chat_id)
                await query.answer()
            elif data == 'logout':
                await handle_logout(bot, query)
                await query.answer()

    return web.Response(status=200, text="okay")
"""
async def main():
    asyncio.create_task(send_mqtt_messages())
    print("send_mqtt_messages coroutine started successfully")
# Run the event loop
"""
# Configura il server web
app = web.Application()
app.router.add_post('/', telegram_bot)

if __name__ == '__main__':
    #asyncio.run(main())
    web.run_app(app, host='0.0.0.0', port=8080)
    
