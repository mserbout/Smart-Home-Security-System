from flask import Flask, flash, redirect, render_template, request, url_for
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

app = Flask(__name__)

# Initialize BigQuery client
bigquery_client = bigquery.Client()
app.secret_key = 'your_secret_key'  # Needed for flash messages

# BigQuery project ID and dataset ID
project_id = 'trans-market-419700'  # Replace with your Google Cloud project ID
dataset_id = 'smart_home_security_system'

# Function to create a new house (table) in BigQuery
def create_house_table(house_name):
    schema = [
        bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("temperature", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("humidity", "FLOAT", mode="REQUIRED"),
        bigquery.SchemaField("motionDetection", "BOOLEAN", mode="REQUIRED"),
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
    print("table id : "+table_id)
    try:
        table = bigquery_client.get_table(table_id)  # Make an API request to check if table exists
        return True
    except NotFound:
        return False


# Function to delete a house (table) in BigQuery
def delete_house_table(house_name):
    table_id = f"{project_id}.{dataset_id}.{house_name}"
    bigquery_client.delete_table(table_id, not_found_ok=True)  # Make an API request

# Function to fetch measurements from BigQuery for a specific house
def fetch_measurements(house_name, limit=None):
    query = f"SELECT * FROM `{project_id}.{dataset_id}.{house_name}`"
    if limit is not None:
        query += " LIMIT " + str(limit)
    query_job = bigquery_client.query(query)
    results = query_job.result()
    measurements = [dict(row) for row in results]
    return measurements


@app.route('/')
def home():
    selected_house_url = request.args.get('house_name')  # Get the selected house URL from the URL query parameter
    
    # Extract the house name from the URL
    selected_house = selected_house_url.split('=')[-1] if selected_house_url else None
    
    # Fetch measurements for the selected house if a house is selected
    measurements = []
    if selected_house:
        try:
            if house_table_exists(selected_house):
                measurements = fetch_measurements(selected_house, limit=100)
            else:
                flash(f'House {selected_house} does not exist.', 'error')
        except Exception as e:
            flash(f'An error occurred: {str(e)}', 'error')
    
    # Fetch list of houses
    tables = bigquery_client.list_tables(dataset_id)
    houses = [table.table_id.split('.')[-1] for table in tables]  # Get only the table names

    return render_template('home.html', measurements=measurements, houses=houses)
    




# @app.route('/houses')
# def list_houses():
    # tables = bigquery_client.list_tables(dataset_id)
    # houses = [table.table_id.split('.')[-1] for table in tables]  # Get only the table names
    # print(houses)
    # print(tables)
    
    # return render_template('home.html', houses=houses)





@app.route('/add_house', methods=['POST'])
def add_house():
    house_name = request.form['house_name']
    if house_name:
        if house_table_exists(house_name):
            flash(f'House {house_name} already exists. Please choose another name.', 'error')
        else:
            create_house_table(house_name)
            flash(f'House {house_name} created successfully.', 'success')
    return redirect(url_for('home'))  # Redirect back to the home route


@app.route('/delete_house/<house_name>', methods=['POST'])
def delete_house(house_name):
    delete_house_table(house_name)
    flash(f'House {house_name} deleted successfully.', 'success')
    return redirect(url_for('home'))  # Redirect back to the home route


@app.route('/display_house/<house_name>')
def display_house(house_name):
    if house_table_exists(house_name):
        measurements = fetch_measurements(house_name, limit=100)
        return render_template('house_data.html', house_name=house_name, measurements=measurements)
    else:
        return "No data available for this house."

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == '__main__':
    app.run(debug=True)
