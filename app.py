import os
import base64
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from image_processing import process_face_image, build_cube_string
from solver import solve_cube

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

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
    calibration_data = None
    if request.is_json:
        data = request.get_json()
        calibration_data = data.get('calibration')
        for face_key, face_notation in FACE_MAPPING.items():
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
                    
                colors = process_face_image(filepath, calibration_data)
                faces_colors[face_notation] = colors
            except Exception as e:
                return jsonify({"success": False, "error": f"Error processing {face_key} face: {str(e)}"}), 500
                
    else:
        if not request.files:
            return jsonify({"success": False, "error": "No images uploaded."}), 400
            
        # Optional calibration from form-data if needed (though usually JSON from scanner)
        cal_str = request.form.get('calibration')
        import json
        calibration_data = json.loads(cal_str) if cal_str else None

        # Process each uploaded image
        for face_key, face_notation in FACE_MAPPING.items():
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
                    colors = process_face_image(filepath, calibration_data)
                    faces_colors[face_notation] = colors
                except Exception as e:
                    return jsonify({"success": False, "error": f"Error processing {face_key} face: {str(e)}"}), 500
            else:
                return jsonify({"success": False, "error": f"Invalid file type for {face_key}."}), 400
                
    try:
        cube_string = build_cube_string(faces_colors)
        result = solve_cube(cube_string)
        # Also return the detected colors so frontend can display them
        result['faces_colors'] = faces_colors
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    # Use SSL only locally (when PORT is not set by cloud provider)
    # This allows camera access on local network while staying compatible with Render
    if 'PORT' in os.environ:
        app.run(host='0.0.0.0', port=port)
    else:
        app.run(host='0.0.0.0', port=port, debug=True, ssl_context='adhoc')
