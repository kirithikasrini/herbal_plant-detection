from flask import Flask, request, render_template, send_file, redirect, url_for, jsonify
import os
from werkzeug.utils import secure_filename
from db import Database
from translator_service import get_plant_translations

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if request.method == 'GET':
        return render_template('index.html') # Redirect back to home effectively
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        try:
            # Read file data
            file_data = file.read()
            
            # Save the uploaded file for display
            import uuid
            ext = secure_filename(file.filename).rsplit('.', 1)[1].lower() if '.' in file.filename else 'jpg'
            filename = f"{uuid.uuid4().hex}.{ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'wb') as f:
                f.write(file_data)
                
                f.write(file_data)
                
            # Use centralized logic from db.py
            # CHECK SOURCE: If webcam, use lenient threshold (100) to force a match.
            # If upload, use strict threshold (20) for accuracy.
            source = request.form.get('source')
            threshold = 100 if source == 'webcam' else 20
            
            plant_data, error = Database.find_best_match(file_data, threshold=threshold)
            
            if error:
                 if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                     return jsonify({'error': error}), 404
                 return render_template('result.html', 
                                       image_path=os.path.join('uploads', filename).replace('\\', '/'),
                                       error_message=error,
                                       plant_name=None,
                                       medicinal_properties=None,
                                       scientific_name=None,
                                       growing_conditions=None,
                                       harvesting_guidelines=None,
                                       precautions=None,
                                       common_names=None,
                                       translations=None)

            # Success
            if 'id' in plant_data:
                Database.log_scan(plant_data['id'])
            
            # Prepare Display Name
            display_name = plant_data['name']
            
            # Logic to avoid displaying filename as plant name
            is_filename = '.' in display_name and (display_name.lower().endswith(('.jpg', '.png', '.jpeg', '.gif')))
            
            if is_filename:
                if plant_data['common_names'] and len(plant_data['common_names']) > 0:
                     display_name = plant_data['common_names'][0]
                elif plant_data['scientific_name']:
                     display_name = plant_data['scientific_name']
                else:
                    display_name = "Unidentified Plant"

            # Get Translations (using the clean name if possible, or scientific)
            name_to_translate = display_name
            if name_to_translate == "Unidentified Plant" and plant_data['scientific_name']:
                name_to_translate = plant_data['scientific_name']
            
            translations = get_plant_translations(name_to_translate)

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'plant_name': display_name,
                    'scientific_name': plant_data['scientific_name'],
                    'common_names': plant_data['common_names'],
                    'medicinal_properties': plant_data['medicinal_properties'],
                    'growing_conditions': plant_data['growing_conditions'],
                    'harvesting_guidelines': plant_data['harvesting_guidelines'],
                    'precautions': plant_data['precautions'],
                    'image_url': url_for('static', filename=f'uploads/{filename}'),
                    'translations': translations
                })
            else:
                 return render_template('result.html',
                                       image_path=os.path.join('uploads', filename).replace('\\', '/'),
                                        plant_name=display_name,
                                       scientific_name=plant_data['scientific_name'],
                                       common_names=plant_data['common_names'],
                                       medicinal_properties=plant_data['medicinal_properties'],
                                       growing_conditions=plant_data['growing_conditions'],
                                       harvesting_guidelines=plant_data['harvesting_guidelines'],
                                       precautions=plant_data['precautions'],
                                       translations=translations)

        except Exception as e:
            error_msg = f"Error processing image: {str(e)}"
            print(error_msg)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': str(e)}), 500
            return error_msg, 500
    
    error_msg = 'Invalid file type. Please upload a PNG, JPG, or JPEG image.'
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({'error': error_msg}), 400
    return error_msg, 400

@app.route('/doctor', methods=['GET', 'POST'])
def doctor():
    if request.method == 'POST':
        # Specific Plant Mode (from Result Page)
        plant_name = request.form.get('plant_name')
        medicinal_properties = request.form.get('medicinal_properties')
        mode = 'specific'
        all_plants = [] # Not needed in specific mode
    else:
        # General Mode (from Navbar)
        plant_name = None
        medicinal_properties = None
        mode = 'general'
        # Fetch all medicinal plants for the expert system
        all_plants = Database.get_medicinal_plants()

    return render_template('doctor.html', 
                           plant_name=plant_name, 
                           medicinal_properties=medicinal_properties,
                           mode=mode,
                           all_plants=all_plants)

@app.route('/garden')
def garden():
    stats = Database.get_garden_stats()
    recent_scans = Database.get_recent_scans()
    return render_template('garden.html', stats=stats, recent_scans=recent_scans)





if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')