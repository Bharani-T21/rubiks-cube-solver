print("--- DEBUG: Starting Import Trace ---")
import os
print("--- DEBUG: os imported ---")
import base64
import numpy as np
print("--- DEBUG: numpy imported ---")
import cv2
print("--- DEBUG: cv2 imported ---")
from flask import Flask, render_template, request, jsonify
print("--- DEBUG: flask imported ---")
from werkzeug.utils import secure_filename
from image_processing import process_face_image, build_cube_string
print("--- DEBUG: image_processing imported ---")
from solver import solve_cube
print("--- DEBUG: solver imported ---")

app = Flask(__name__)
print("--- DEBUG: Flask app initialized ---")
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
print("--- DEBUG: Uploads folder checked ---")

# Map UI names to solver order names
FACE_MAPPING = {
    'up': 'up',
    'right': 'right',
    'front': 'front',
    'down': 'down',
    'left': 'left',
    'back': 'back'
}

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/solve', methods=['POST'])
def solve():
    faces_colors = {}
    
    if request.is_json:
        data = request.get_json()
        for face_key in FACE_MAPPING.keys():
            if face_key not in data:
                return jsonify({"success": False, "error": f"Missing {face_key} image."}), 400
                
            img_b64 = data[face_key]
            if ',' in img_b64:
                img_b64 = img_b64.split(',')[1]
                
            try:
                img_bytes = base64.b64decode(img_b64)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{face_key}_camera.jpg")
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                    
                colors = process_face_image(filepath)
                faces_colors[face_key] = colors
            except Exception as e:
                return jsonify({"success": False, "error": f"Error processing {face_key} face: {str(e)}"}), 500
                
    else:
        if not request.files:
            return jsonify({"success": False, "error": "No images uploaded."}), 400
            
        for face_key in FACE_MAPPING.keys():
            if face_key not in request.files:
                return jsonify({"success": False, "error": f"Missing {face_key} image."}), 400
            
            file = request.files[face_key]
            if file.filename == '':
                return jsonify({"success": False, "error": f"No selected file for {face_key}."}), 400
                
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{face_key}_{filename}")
                file.save(filepath)
                
                try:
                    colors = process_face_image(filepath)
                    faces_colors[face_key] = colors
                except Exception as e:
                    return jsonify({"success": False, "error": f"Error processing {face_key} face: {str(e)}"}), 500
            else:
                return jsonify({"success": False, "error": f"Invalid file type for {face_key}."}), 400
                
    return process_and_solve(faces_colors)

@app.route('/analyze', methods=['POST'])
def analyze():
    faces_colors = {}
    
    if request.is_json:
        data = request.get_json()
        for face_key in FACE_MAPPING.keys():
            if face_key not in data:
                return jsonify({"success": False, "error": f"Missing {face_key} image."}), 400
                
            img_b64 = data[face_key]
            if ',' in img_b64:
                img_b64 = img_b64.split(',')[1]
                
            try:
                img_bytes = base64.b64decode(img_b64)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"{face_key}_analyze_camera.jpg")
                with open(filepath, "wb") as f:
                    f.write(img_bytes)
                    
                colors = process_face_image(filepath)
                faces_colors[face_key] = colors
            except Exception as e:
                return jsonify({"success": False, "error": f"Error processing {face_key} face: {str(e)}"}), 500
                
    else:
        if not request.files:
            return jsonify({"success": False, "error": "No images uploaded."}), 400
            
        for face_key in FACE_MAPPING.keys():
            if face_key not in request.files:
                return jsonify({"success": False, "error": f"Missing {face_key} image."}), 400
            
            file = request.files[face_key]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], f"analyze_{face_key}_{filename}")
                file.save(filepath)
                
                try:
                    colors = process_face_image(filepath)
                    faces_colors[face_key] = colors
                except Exception as e:
                    return jsonify({"success": False, "error": f"Error processing {face_key} face: {str(e)}"}), 500
            else:
                return jsonify({"success": False, "error": f"Invalid file for {face_key}."}), 400

    return jsonify({"success": True, "faces_colors": faces_colors})

def process_and_solve(faces_colors):
    try:
        cube_string = build_cube_string(faces_colors)
        result = solve_cube(cube_string)
        result['faces_colors'] = faces_colors
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/solve_final', methods=['POST'])
def solve_final():
    data = request.get_json()
    if not data or 'faces_colors' not in data:
        return jsonify({"success": False, "error": "No color data provided"}), 400
    
    return process_and_solve(data['faces_colors'])

@app.route('/preview_colors', methods=['POST'])
def preview_colors():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({"success": False, "error": "No image provided"}), 400
    
    img_b64 = data['image']
    if ',' in img_b64:
        img_b64 = img_b64.split(',')[1]
        
    try:
        img_bytes = base64.b64decode(img_b64)
        nparr = np.frombuffer(img_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        expected_center = data.get('expected_center')
        from image_processing import process_frame
        result = process_frame(img, expected_center=expected_center)
        return jsonify({"success": True, "preview_data": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    if 'PORT' in os.environ:
        app.run(host='0.0.0.0', port=port)
    else:
        app.run(host='0.0.0.0', port=port, debug=True, ssl_context='adhoc')
