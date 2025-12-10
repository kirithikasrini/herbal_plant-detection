from flask import Flask, request, render_template, send_file, redirect, url_for, jsonify
import os
from werkzeug.utils import secure_filename
from db import Database

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
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            with open(filepath, 'wb') as f:
                f.write(file_data)
                
            # Use centralized logic from db.py
            plant_data, error = Database.find_best_match(file_data)
            
            if error:
                 if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                     return jsonify({'error': error}), 404
                 return render_template('result.html', 
                                       image_path=os.path.join('uploads', filename).replace('\\', '/'),
                                       error_message=error)

            # Success
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({
                    'success': True,
                    'plant_name': plant_data['name'],
                    'scientific_name': plant_data['scientific_name'],
                    'common_names': plant_data['common_names'],
                    'medicinal_properties': plant_data['medicinal_properties'],
                    'growing_conditions': plant_data['growing_conditions'],
                    'harvesting_guidelines': plant_data['harvesting_guidelines'],
                    'precautions': plant_data['precautions'],
                    'image_url': url_for('static', filename=f'uploads/{filename}')
                })
            else:
                 return render_template('result.html',
                                       image_path=os.path.join('uploads', filename).replace('\\', '/'),
                                        plant_name=plant_data['name'],
                                       scientific_name=plant_data['scientific_name'],
                                       common_names=plant_data['common_names'],
                                       medicinal_properties=plant_data['medicinal_properties'],
                                       growing_conditions=plant_data['growing_conditions'],
                                       harvesting_guidelines=plant_data['harvesting_guidelines'],
                                       precautions=plant_data['precautions'])

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


if __name__ == '__main__':
    app.run(debug=True, port=5000, host='0.0.0.0')