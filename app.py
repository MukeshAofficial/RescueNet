from flask import Flask, render_template, request, jsonify,send_file,  redirect, url_for , send_from_directory
from flask_sqlalchemy import SQLAlchemy
import requests
from gtts import gTTS
import google.generativeai as genai
import os
from io import BytesIO
import io
import PIL.Image
import base64
from werkzeug.utils import secure_filename
import sqlite3



app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///locations.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
db = SQLAlchemy(app)


# Change to a different database URI for water quality
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///locations2.db'  # Updated database name

# Database model for water quality locations
class WaterQualityLocation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # Categories: clean, polluted, disease

    __table_args__ = (db.UniqueConstraint('latitude', 'longitude', name='unique_water_quality_location'),)

# Delete old database if exists
if os.path.exists('locations2.db'):  # Updated to match new database name
    os.remove('locations2.db')  # Updated to match new database name

# Create the database tables
with app.app_context():
    db.create_all()

# Route to serve the main HTML page
@app.route('/map-need')
def water_map():
    return render_template('map-need.html')


# Route to fetch counts
@app.route('/api/counts', methods=['GET'])
def get_counts():
    clean_water_count = WaterQualityLocation.query.filter_by(category='clean').count()
    polluted_water_count = WaterQualityLocation.query.filter_by(category='polluted').count()
    disease_area_count = WaterQualityLocation.query.filter_by(category='disease').count()
    resources_needed_count = Locations.query.count()
    volunteer_count = Volunteer.query.count()

    return jsonify({
        'clean_water': clean_water_count,
        'polluted': polluted_water_count,
        'disease': disease_area_count,
        'resources_needed': resources_needed_count,
        'volunteers': volunteer_count
    })


# Route to fetch flood severity data for the graph
@app.route('/api/flood-severity', methods=['GET'])
def get_flood_severity():
    # Example data - you should replace this with actual queries from your database
    labels = ["Week 1", "Week 2", "Week 3", "Week 4"]
    values = [3, 5, 2, 7]  # Example values representing flood severity over time

    return jsonify({
        'labels': labels,
        'values': values
    })

@app.route('/dashboard-main')
def dash():
    return render_template('main-dashboard.html')

# Route to save a new water quality location
@app.route('/save_water_quality_location', methods=['POST'])
def save_water_quality_location():
    data = request.get_json()
    existing_location = WaterQualityLocation.query.filter_by(
        latitude=data['latitude'], 
        longitude=data['longitude']
    ).first()
    
    if not existing_location:
        new_location = WaterQualityLocation(
            # Removed description as it is no longer being passed
            latitude=data['latitude'],
            longitude=data['longitude'],
            category=data['category']
        )
        db.session.add(new_location)
        db.session.commit()
        return jsonify({'status': 'success'})
    else:
        return jsonify({'status': 'exists'})


genai.configure(api_key="AIzaSyAbmCYsZsjfCPf-uakFksDglYasW4EsehE")
model = genai.GenerativeModel('gemini-1.5-flash')

# Database model for locations
class Locations(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    description = db.Column(db.String(200), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)

    __table_args__ = (db.UniqueConstraint('latitude', 'longitude', name='unique_location'),)

# Delete old database if exists
if os.path.exists('locations.db'):
    os.remove('locations.db')

# Create the database tables
with app.app_context():
    db.create_all()

# Route to serve the main HTML page
@app.route('/map')
def map():          
    return render_template('map.html')

# Route to save a new location
@app.route('/save_location', methods=['POST'])
def save_location():
    data = request.get_json()
    # Check if the location already exists
    existing_location = Locations.query.filter_by(latitude=data['latitude'], longitude=data['longitude']).first()
    
    # Only save if it doesn't exist
    if not existing_location:
        new_location = Locations(description=data['description'], latitude=data['latitude'], longitude=data['longitude'])
        db.session.add(new_location)
        db.session.commit()

    return jsonify({'status': 'success' if not existing_location else 'exists'})

# Route to get all locations
@app.route('/get_locations', methods=['GET'])
def get_locations():
    locations = Locations.query.all()
    return jsonify([{
        'description': location.description,
        'latitude': location.latitude,
        'longitude': location.longitude
    } for location in locations])

def init_db():
    with sqlite3.connect("disaster_volunteers.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_path TEXT,
                description TEXT,
                latitude REAL,
                longitude REAL
            )
        ''')

# Route to serve the homepage
@app.route('/damage')
def damage():
    return render_template('damage-map.html')

# Route to view reports
@app.route('/view-reports')
def view_reports():
    return render_template('view_reports.html')

# Endpoint to fetch all reports data
@app.route('/api/reports', methods=['GET'])
def get_reports():
    with sqlite3.connect("disaster_volunteers.db") as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM reports")
        reports = [
            {
                "id": row["id"],
                "image_path": f"/uploads/{os.path.basename(row['image_path'])}",
                "description": row["description"],
                "latitude": row["latitude"],
                "longitude": row["longitude"]
            }
            for row in cursor.fetchall()
        ]
    return jsonify(reports)

# Serve uploaded images
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Route to handle image upload
@app.route('/upload', methods=['POST'])
def upload():
    if 'image' not in request.files:
        return jsonify({"error": "No image provided"}), 400

    image = request.files['image']
    description = request.form.get('description')
    latitude = request.form.get('latitude')
    longitude = request.form.get('longitude')

    # Save image
    filename = secure_filename(image.filename)
    image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    image.save(image_path)

    # Save data to database
    with sqlite3.connect("disaster_volunteers.db") as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO reports (image_path, description, latitude, longitude)
            VALUES (?, ?, ?, ?)
        ''', (image_path, description, latitude, longitude))
        conn.commit()

    return jsonify({"message": "Data successfully uploaded!"}), 200

API_KEY = "2bfaac82a56640299f7c2353da4a50ec"
BASE_URL = "https://newsapi.org/v2/everything"

# Fetch Myanmar flood-related news articles from News API
def get_news():
    params = {
        'q': 'Myanmar flood',  # Query for flood-related news in Myanmar
        'language': 'en',
        'apiKey': API_KEY,
        'pageSize': 10,        # Number of articles to fetch
    }
    response = requests.get(BASE_URL, params=params)
    if response.status_code == 200:
        return response.json().get("articles", [])
    else:
        return []

@app.route('/api/news')
def news_api():
    articles = get_news()
    return jsonify(articles)

@app.route('/news')
def news():
    return render_template('news.html')



@app.route('/scan')
def scan():
    return render_template('scan.html')


@app.route('/uploads', methods=['GET','POST'])
def uploads():
    if request.method == 'POST':
        # Get the image data from the request
        data = request.json
        image_data = data.get('image')

        # Decode the base64 image data
        image_data = image_data.split(',')[1]
        image_binary = base64.b64decode(image_data)

        # Save the image to a file on your local PC
        img_path = 'captured_image.png'
        with open(img_path, 'wb') as img_file:
            img_file.write(image_binary)

        # Load the image
        img = PIL.Image.open(io.BytesIO(image_binary))

        # Use Generative AI model to generate text from the image
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content([" Analyze the image and provide recommendations for first aid or health tips and Provide safety tips for individuals affected by the flood, including evacuation advice based on the content of the image . ", img], stream=True)
        response.resolve()
        rply=response.text

        with open('static/describe.txt', 'w') as f:
            f.write(rply)

        # Generate speech from the extracted text
        tts = gTTS(text=response.text, lang='en')

        # Save the speech to a file
        audio_path = 'static/output.mp3'
        tts.save(audio_path)
        audio_url = f"/{audio_path}"
        
        return redirect(url_for('result'))

@app.route('/result')
def result():
    audio_url = "output.mp3"
    with open('static/describe.txt', 'r') as f:
        describe = f.read()
    return render_template('result.html',recipe=describe, audio=audio_url)

@app.route('/gpt', methods=['GET', 'POST'])
def gpt():
    response_text = ""
    encoded_string = ""
    
    if request.method == 'POST':
        # Get transcribed text from the form
        transcribed_text = request.form.get('transcribed_text')
        
        # Generate response using the transcribed text
        if transcribed_text:
            # Generate response using Generative AI model
            model = genai.GenerativeModel('gemini-pro')
            rply = model.generate_content("Respond to user queries related to flood disasters, focusing on first aid and safety tips. Provide concise, practical answers tailored to the specific situation, emphasizing immediate actions to take and essential safety precautions answer in very short.Return the text  in normal text and **TItle** i dont wnat this format " + transcribed_text)
            response_text = rply.text
            print(response_text)
            
            # Convert response text to speech
            tts = gTTS(text=response_text, lang='en')
            tts.save('response.mp3')
            
            # Encode the audio file as base64
            with open("response.mp3", "rb") as audio_file:
                encoded_string = base64.b64encode(audio_file.read()).decode('utf-8')
        
        else:
            response_text = "No input provided."
        
        # Return the response to the client
        return render_template('gpt.html', response=response_text, audio=encoded_string)
    
    # If it's a GET request, render the form
    return render_template('gpt.html')



@app.route('/dashboards')
def dashboard():
    return render_template('dashboard.html')


@app.route('/analyze_cameras')
def analyze_cameras():
    # Simulate LLM analysis
    # For demonstration, randomly select a camera with a threat
    import random
    threat_camera = random.choice([5, 5, 5])  # Simulate threat detection
    return jsonify({"threat": True, "cameraNumber": threat_camera})

@app.route('/dashboard')
def dashboard_redirect():
    return render_template('dashboard.html')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/chatbot')
def chatbot():
    return render_template('chatbot.html')

@app.route('/get_response', methods=['POST'])
def get_response():
    data = request.json
    user_message = data['message']
    model = genai.GenerativeModel('gemini-1.5-flash')
    rply = model.generate_content(f"{user_message}  answer in one or 2 lines without any */ symbols")

    return jsonify({'response': rply.text})   

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
    
