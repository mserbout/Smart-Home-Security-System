import datetime
from flask import Flask, flash, redirect, render_template, request, session, url_for, jsonify
from google.cloud import bigquery
from google.cloud.exceptions import NotFound
import uuid
import bcrypt

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Initialize BigQuery client
bigquery_client = bigquery.Client()

# BigQuery project ID and dataset ID
project_id = 'trans-market-419700'  # Replace with your Google Cloud project ID
dataset_id = 'smart_home_security_system'

# Function to create a new house (table) in BigQuery
def create_house_table(house_name):
    schema = [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("temperature", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("humidity", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("alarm_status", "BOOLEAN", mode="REQUIRED"),
        bigquery.SchemaField("number_detection", "INTEGER", mode="REQUIRED"),
        bigquery.SchemaField("longitude", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("latitude", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("time", "TIMESTAMP")
    ]
    
    table_id = f"{project_id}.{dataset_id}.{house_name}"
    table = bigquery.Table(table_id, schema=schema)
    table = bigquery_client.create_table(table)  # Make an API request
    return table

# Function to check if a house (table) exists in BigQuery
def house_table_exists(house_name):
    table_id = f"{project_id}.{dataset_id}.{house_name}"
    try:
        bigquery_client.get_table(table_id)  # Make an API request to check if table exists
        return True
    except NotFound:
        return False

# Function to delete a house (table) in BigQuery
def delete_house_table(house_name):
    table_id = f"{project_id}.{dataset_id}.{house_name}"
    bigquery_client.delete_table(table_id, not_found_ok=True)  # Make an API request

# Function to fetch measurements from BigQuery for a specific house
def fetch_measurements(house_name, limit=15):
    query = f"""
        SELECT id, temperature, humidity, alarm_status, number_detection, longitude, latitude, time
        FROM `{project_id}.{dataset_id}.{house_name}`
        ORDER BY time DESC
        LIMIT {limit}
    """
    query_job = bigquery_client.query(query)
    results = query_job.result()
    measurements = [dict(row) for row in results]
    measurements.reverse()  # Reverse to get the oldest data first
    return measurements

# Function to convert measurements with datetime objects to strings
def convert_measurements(measurements):
    for measurement in measurements:
        if 'time' in measurement and isinstance(measurement['time'], datetime.datetime):
            measurement['time'] = measurement['time'].isoformat()
    return measurements

# Function to add a new user
def add_user(username, password, idHouse, is_admin=False):
    query = f"""
        INSERT INTO `{project_id}.{dataset_id}.users` (id, username, password, idHouse, is_admin)
        VALUES ('{uuid.uuid4()}', '{username}', '{password}', '{idHouse}', {is_admin})
    """
    query_job = bigquery_client.query(query)
    query_job.result()

# Function to delete a user
def delete_user(user_id):
    query = f"DELETE FROM `{project_id}.{dataset_id}.users` WHERE id = '{user_id}'"
    query_job = bigquery_client.query(query)
    query_job.result()

# Function to fetch users from the BigQuery table
def fetch_users():
    query = f"SELECT * FROM `{project_id}.{dataset_id}.users`"
    query_job = bigquery_client.query(query)
    results = query_job.result()
    users = [dict(row) for row in results]
    return users

@app.route('/')
def home():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    is_admin = session.get('is_admin')
    idHouse = session.get('idHouse')
    
    selected_house = request.args.get('house_name') if is_admin else idHouse
    
    measurements = []
    if selected_house:
        try:
            if house_table_exists(selected_house):
                measurements = fetch_measurements(selected_house, limit=15)
            else:
                flash(f'House {selected_house} does not exist.', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
    
    tables = bigquery_client.list_tables(dataset_id)
    houses = [table.table_id.split('.')[-1] for table in tables]

    return render_template('home.html', measurements=measurements, houses=houses, is_admin=is_admin, selected_house=selected_house, idHouse=idHouse)

@app.route('/manage_users')
def manage_users():
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    users = fetch_users()
    return render_template('users.html', users=users)

@app.route('/add_user_route', methods=['POST'])
def add_user_route():
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    username = request.form['username']
    password = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    idHouse = request.form['idHouse']
    is_admin = request.form.get('is_admin') == 'on'

    add_user(username, password, idHouse, is_admin)
    flash('User added successfully', 'success')
    return redirect(url_for('manage_users'))

@app.route('/delete_user/<user_id>', methods=['POST'])
def delete_user_route(user_id):
    if not session.get('is_admin'):
        return redirect(url_for('home'))

    delete_user(user_id)
    flash('User deleted successfully', 'success')
    return redirect(url_for('manage_users'))

@app.route('/add_house', methods=['POST'])
def add_house():
    house_name = request.form['house_name']
    if house_name:
        if house_table_exists(house_name):
            flash(f'House {house_name} already exists. Please choose another name.', 'error')
        else:
            create_house_table(house_name)
            flash(f'House {house_name} created successfully.', 'success')
    return redirect(url_for('home'))

@app.route('/delete_house/<house_name>', methods=['POST'])
def delete_house(house_name):
    try:
        delete_house_table(house_name)
        flash(f'House {house_name} deleted successfully.', 'success')
        return 'OK', 200
    except Exception as e:
        flash(f'An error occurred: {str(e)}', 'error')
        return 'Failed', 500

@app.route('/display_house/<house_name>')
def display_house(house_name):
    if house_table_exists(house_name):
        measurements = fetch_measurements(house_name, limit=100)
        tables = bigquery_client.list_tables(dataset_id)
        houses = [table.table_id.split('.')[-1] for table in tables]
        return render_template('home.html', measurements=measurements, houses=houses, selected_house=house_name, is_admin=session.get('is_admin'))
    else:
        return redirect(url_for('home'))

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = fetch_user_by_username(username)
        if user and bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = user['is_admin']
            session['idHouse'] = user['idHouse']
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login.html')

def fetch_user_by_username(username):
    query = f"SELECT * FROM `{project_id}.{dataset_id}.users` WHERE username = '{username}'"
    query_job = bigquery_client.query(query)
    results = query_job.result()
    users = [dict(row) for row in results]
    return users[0] if users else None

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/measurements/<house_name>')
def get_measurements(house_name):
    try:
        if house_table_exists(house_name):
            measurements = fetch_measurements(house_name, limit=15)
            measurements = convert_measurements(measurements)
            return jsonify(measurements)
        else:
            return jsonify({"error": "House does not exist"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def fetch_latest_measurement(house_name):
    query = f"""
        SELECT number_detection, alarm_status
        FROM `{project_id}.{dataset_id}.{house_name}`
        ORDER BY time DESC
        LIMIT 1
    """
    query_job = bigquery_client.query(query)
    result = query_job.result()
    latest_measurement = None
    for row in result:
        latest_measurement = dict(row)
        break
    return latest_measurement

@app.route('/latest_measurements/<house_name>')
def get_latest_measurements(house_name):
    try:
        if house_table_exists(house_name):
            latest_measurement = fetch_latest_measurement(house_name)
            return jsonify(latest_measurement)
        else:
            return jsonify({"error": "House does not exist"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/historical_data', methods=['GET'])
def historical_data():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    is_admin = session.get('is_admin')
    idHouse = session.get('idHouse')
    
    # If the user is an admin, they can select any house. If not, they can only see their house.
    selected_house = request.args.get('house_name') if is_admin else idHouse
    time_range = request.args.get('time_range', 'hourly')

    measurements = []
    if selected_house:
        try:
            if house_table_exists(selected_house):
                measurements = fetch_measurements_by_time_range(selected_house, time_range)
            else:
                flash(f'House {selected_house} does not exist.', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
    
    # Admin sees all houses, user sees only their house
    tables = bigquery_client.list_tables(dataset_id)
    houses = [table.table_id.split('.')[-1] for table in tables] if is_admin else [idHouse]

    return render_template('historical_data.html', measurements=measurements, houses=houses, is_admin=is_admin, selected_house=selected_house, time_range=time_range)

def fetch_measurements_by_time_range(house_name, time_range):
    time_filter = {
        'hourly': 'TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)',
        'daily': 'TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 DAY)',
        'weekly': 'TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 WEEK)'
    }.get(time_range, 'TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 1 HOUR)')

    query = f"""
        SELECT id, temperature, humidity, alarm_status, number_detection, longitude, latitude, time
        FROM `{project_id}.{dataset_id}.{house_name}`
        WHERE time > {time_filter}
        ORDER BY time DESC
    """
    query_job = bigquery_client.query(query)
    results = query_job.result()
    measurements = [dict(row) for row in results]
    return measurements

@app.route('/historical_measurements/<house_name>')
def get_historical_measurements(house_name):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    try:
        measurements = fetch_measurements(house_name)
        return jsonify(measurements)
    except Exception as e:
        return jsonify({'error': str(e)})

# Rest of your code...


if __name__ == '__main__':
    app.run(debug=True)
