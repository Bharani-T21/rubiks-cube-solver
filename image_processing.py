import cv2
import numpy as np

# Robust HSV color centers (OpenCV: H:0-180, S:0-255, V:0-255)
# These are hand-tuned for standard cube colors in average lighting.
# Red has two peaks (0 and 180). We'll handle it via circular distance.
DEFAULT_COLOR_CENTERS = {
    'red': [0, 200, 150],
    'orange': [10, 210, 200],
    'yellow': [25, 180, 200],
    'green': [65, 180, 150],
    'blue': [115, 200, 150],
    'white': [0, 30, 210]
}

def preprocess_image(img):
    """
    Apply Gaussian blur, brightness normalization (CLAHE), and white balance.
    """
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    
    # White Balance (Gray World)
    result = blurred.astype(np.float32)
    avg_b, avg_g, avg_r = np.mean(result[:, :, 0]), np.mean(result[:, :, 1]), np.mean(result[:, :, 2])
    avg_gray = (avg_b + avg_g + avg_r) / 3
    result[:, :, 0] *= (avg_gray / (avg_b + 1e-6))
    result[:, :, 1] *= (avg_gray / (avg_g + 1e-6))
    result[:, :, 2] *= (avg_gray / (avg_r + 1e-6))
    result = np.clip(result, 0, 255).astype(np.uint8)

    # CLAHE
    lab = cv2.cvtColor(result, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    cl = clahe.apply(l)
    limg = cv2.merge((cl, a, b))
    final = cv2.cvtColor(limg, cv2.COLOR_LAB2BGR)
    
    return final

def get_color_and_confidence(hsv_pixel):
    """
    Matches an HSV pixel to the closest static color center and returns
    the color name and a confidence score (0-1).
    """
    h, s, v = hsv_pixel
    min_dist = float('inf')
    best_color = 'white'
    
    # Calculate all distances first to find min and max for confidence
    distances = {}
    for color, center in DEFAULT_COLOR_CENTERS.items():
        ch, cs, cv = center
        dh = min(abs(h - ch), 180 - abs(h - ch))
        ds = s - cs
        dv = v - cv
        
        if color == 'white':
            dist = np.sqrt((dh * 0.2)**2 + (ds * 2.0)**2 + (dv * 1.0)**2)
        elif color == 'red' or color == 'orange':
            # Slightly lower hue weight to be less sensitive but keep separation
            dist = np.sqrt((dh * 2.5)**2 + (ds * 1.0)**2 + (dv * 0.5)**2)
        else:
            dist = np.sqrt((dh * 2.0)**2 + (ds * 1.0)**2 + (dv * 0.5)**2)
        
        distances[color] = dist
        if dist < min_dist:
            min_dist = dist
            best_color = color
            
    # Relaxed confidence: 100-120 is a more realistic range for "good enough" matching
    confidence = max(0, min(1, 1 - (min_dist / 100)))
    
    return best_color, confidence

def process_frame(img):
    """
    Processes a raw frame (numpy array) and returns 9 detected colors with confidence.
    Used for real-time preview.
    """
    if img is None:
        return []

    img = cv2.resize(img, (300, 300))
    proc_img = preprocess_image(img)
    hsv = cv2.cvtColor(proc_img, cv2.COLOR_BGR2HSV)
    
    preview_data = []
    
    for i in range(3):
        for j in range(3):
            y1, y2 = i*100 + 20, (i+1)*100 - 20
            x1, x2 = j*100 + 20, (j+1)*100 - 20
            roi = hsv[y1:y2, x1:x2]
            
            mask = roi[:, :, 2] <= 245
            if np.any(mask):
                avg_hsv = cv2.mean(roi, mask=mask.astype(np.uint8))[:3]
            else:
                avg_hsv = cv2.mean(roi)[:3]
                
            color, conf = get_color_and_confidence(avg_hsv)
            preview_data.append({"color": color, "confidence": conf})
            
    return preview_data

def process_face_image(image_path):
    """
    Processes a single face image and returns a list of 9 color names.
    Includes reflection masking.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image at {image_path}")

    img = cv2.resize(img, (300, 300))
    proc_img = preprocess_image(img)
    hsv = cv2.cvtColor(proc_img, cv2.COLOR_BGR2HSV)
    
    face_colors = []
    
    for i in range(3):
        for j in range(3):
            y1, y2 = i*100 + 20, (i+1)*100 - 20
            x1, x2 = j*100 + 20, (j+1)*100 - 20
            roi = hsv[y1:y2, x1:x2]
            
            mask = roi[:, :, 2] <= 245
            if np.any(mask):
                avg_hsv = cv2.mean(roi, mask=mask.astype(np.uint8))[:3]
            else:
                avg_hsv = cv2.mean(roi)[:3]
                
            color, _ = get_color_and_confidence(avg_hsv)
            face_colors.append(color)
            
    return face_colors

def build_cube_string(faces_colors):
    """
    Order for solver: L, U, F, D, R, B
    """
    order = ['left', 'up', 'front', 'down', 'right', 'back']
    cube_string = []
    for face_key in order:
        if face_key not in faces_colors:
             raise ValueError(f"Missing face data for {face_key}")
        for color in faces_colors[face_key]:
            cube_string.append(color)
    return cube_string
