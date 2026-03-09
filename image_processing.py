import cv2
import numpy as np

# Default HSV color centers (approximate)
# These will be used if no calibration data is provided
DEFAULT_COLOR_CENTERS = {
    'red': [0, 200, 150],
    'orange': [15, 200, 200],
    'yellow': [30, 200, 200],
    'green': [60, 200, 150],
    'blue': [110, 200, 150],
    'white': [0, 20, 200]
}

def preprocess_image(img):
    """
    Apply Gaussian blur, brightness normalization (CLAHE), and white balance.
    """
    # 1. Gaussian Blur to reduce noise
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    
    # 2. White Balance (Gray World Assumption)
    result = blurred.astype(np.float32)
    avg_b = np.mean(result[:, :, 0])
    avg_g = np.mean(result[:, :, 1])
    avg_r = np.mean(result[:, :, 2])
    avg_gray = (avg_b + avg_g + avg_r) / 3
    
    result[:, :, 0] *= (avg_gray / (avg_b + 1e-6))
    result[:, :, 1] *= (avg_gray / (avg_g + 1e-6))
    result[:, :, 2] *= (avg_gray / (avg_r + 1e-6))
    result = np.clip(result, 0, 255).astype(np.uint8)

    # 3. Brightness Normalization (CLAHE on L channel in LAB space)
    lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    
    return final

def get_color_name(hsv_pixel, calibration_data=None):
    """
    Determines color by finding the closest center in HSV space.
    Uses Euclidean distance in a modified HSV space (cylindrical or weighted).
    """
    centers = calibration_data if calibration_data else DEFAULT_COLOR_CENTERS
    
    h, s, v = hsv_pixel
    
    min_dist = float('inf')
    detected_color = 'white'
    
    for color, center in centers.items():
        ch, cs, cv = center
        
        # Calculate distance. Hue is circular (0-180 in OpenCV)
        dh = min(abs(h - ch), 180 - abs(h - ch))
        ds = s - cs
        dv = v - cv
        
        # Weighting: Hue is most important for chromatic colors, 
        # Saturation/Value for white.
        if color == 'white':
            dist = np.sqrt((ds * 0.5)**2 + (dv * 0.5)**2)
        else:
            # For chromatic colors, low saturation often misidentifies as the wrong color
            # so we give extra weight to hue if saturation is decent.
            dist = np.sqrt((dh * 2.0)**2 + (ds * 0.5)**2 + (dv * 0.5)**2)
            
        if dist < min_dist:
            min_dist = dist
            detected_color = color
            
    return detected_color

def process_face_image(image_path, calibration_data=None):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image at {image_path}")

    # Resize to standard size
    img = cv2.resize(img, (300, 300))
    
    # 1. Preprocess
    proc_img = preprocess_image(img)
    
    # 2. Convert to HSV
    hsv = cv2.cvtColor(proc_img, cv2.COLOR_BGR2HSV)
    
    height, width, _ = img.shape
    cell_h = height // 3
    cell_w = width // 3
    
    face_colors = []
    
    # Grid goes top-to-bottom, left-to-right rows
    for i in range(3):
        for j in range(3):
            # Extract central part of the cell (region-based averaging)
            # Use 40% of the cell to avoid borders entirely
            y1 = i * cell_h + int(cell_h * 0.3)
            y2 = (i + 1) * cell_h - int(cell_h * 0.3)
            x1 = j * cell_w + int(cell_w * 0.3)
            x2 = (j + 1) * cell_w - int(cell_w * 0.3)
            
            roi = hsv[y1:y2, x1:x2]
            # Calculate mean HSV across the ROI
            avg_hsv = cv2.mean(roi)[:3]
            
            color = get_color_name(avg_hsv, calibration_data)
            face_colors.append(color)

            # Draw rectangle on original image for debugging
            cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(img, color[0].upper(), (x1, y1 + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            
    # Save the debug image
    debug_path = image_path.replace('.jpg', '_debug.jpg').replace('.png', '_debug.png')
    if not debug_path.endswith('_debug.jpg') and not debug_path.endswith('_debug.png'):
         debug_path += "_debug.jpg"
    cv2.imwrite(debug_path, img)

    return face_colors

def build_cube_string(faces_colors):
    """
    faces_colors is a dict: {'up': [...], 'right': [...], 'front': [...], 'down': [...], 'left': [...], 'back': [...]}
    Order for solver: L, U, F, D, R, B
    """
    # Map from lowercase frontend keys to solver order
    mapping = {'left': 'left', 'up': 'up', 'front': 'front', 'down': 'down', 'right': 'right', 'back': 'back'}
    order = ['left', 'up', 'front', 'down', 'right', 'back']
    
    cube_string = []
    for face_key in order:
        if face_key not in faces_colors:
             raise ValueError(f"Missing face data for {face_key}")
        for color in faces_colors[face_key]:
            if color == 'unknown':
                raise ValueError(f"Detected invalid color. Ensure good lighting and central placement.")
            cube_string.append(color)
            
    return cube_string
