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
    
    for color, center in DEFAULT_COLOR_CENTERS.items():
        ch, cs, cv = center
        dh = min(abs(h - ch), 180 - abs(h - ch))
        ds = s - cs
        dv = v - cv
        
        if color == 'white':
            dist = np.sqrt((dh * 0.2)**2 + (ds * 2.0)**2 + (dv * 1.0)**2)
        elif color == 'red' or color == 'orange':
            dist = np.sqrt((dh * 2.5)**2 + (ds * 1.0)**2 + (dv * 0.5)**2)
        else:
            dist = np.sqrt((dh * 2.0)**2 + (ds * 1.0)**2 + (dv * 0.5)**2)
        
        if dist < min_dist:
            min_dist = dist
            best_color = color
            
    # Significantly more relaxed confidence for "Self-Correcting" logic
    # 150 allows for much more variation while still providing a scale.
    confidence = max(0, min(1, 1 - (min_dist / 150)))
    
    return best_color, confidence

def process_frame(img, expected_center=None):
    """
    Processes a raw frame with center-based HSV normalization.
    """
    if img is None:
        return []

    img = cv2.resize(img, (300, 300))
    proc_img = preprocess_image(img)
    hsv = cv2.cvtColor(proc_img, cv2.COLOR_BGR2HSV)
    
    # 1. Extract raw averages for all 9 stickers
    raw_hsv_list = []
    for i in range(3):
        for j in range(3):
            y1, y2 = i*100 + 20, (i+1)*100 - 20
            x1, x2 = j*100 + 20, (j+1)*100 - 20
            roi = hsv[y1:y2, x1:x2]
            
            # Use a slightly more aggressive reflection mask (v > 220)
            mask = roi[:, :, 2] <= 220
            if np.any(mask):
                avg = cv2.mean(roi, mask=mask.astype(np.uint8))[:3]
            else:
                avg = cv2.mean(roi)[:3]
            raw_hsv_list.append(list(avg))

    # 2. Calculate Shift if expected_center is provided
    shift = [0, 0, 0]
    if expected_center and expected_center.lower() in DEFAULT_COLOR_CENTERS:
        center_hsv = raw_hsv_list[4] # Middle sticker
        target_hsv = DEFAULT_COLOR_CENTERS[expected_center.lower()]
        
        # Calculate circular hue shift
        h_diff = target_hsv[0] - center_hsv[0]
        if h_diff > 90: h_diff -= 180
        if h_diff < -90: h_diff += 180
        
        shift = [
            h_diff,
            target_hsv[1] - center_hsv[1],
            target_hsv[2] - center_hsv[2]
        ]

    # 3. Apply shift and classify
    preview_data = []
    for raw_val in raw_hsv_list:
        # Apply normalization shift
        norm_h = (raw_val[0] + shift[0]) % 180
        norm_s = np.clip(raw_val[1] + shift[1], 0, 255)
        norm_v = np.clip(raw_val[2] + shift[2], 0, 255)
        
        color, conf = get_color_and_confidence([norm_h, norm_s, norm_v])
        preview_data.append({"color": color, "confidence": conf})
            
    return preview_data

def process_face_image(image_path):
    """
    Uses the center sticker of the captured image to normalize the whole face.
    """
    img = cv2.imread(image_path)
    if img is None: return ["white"] * 9

    # For the final capture, we use the center sticker (index 4) as the anchor
    # since we don't necessarily know the expected color here (unless we pass it).
    # However, for consistency, let's detect the center color first.
    
    img = cv2.resize(img, (300, 300))
    proc_img = preprocess_image(img)
    hsv = cv2.cvtColor(proc_img, cv2.COLOR_BGR2HSV)
    
    # Extract middle sticker to find its "likely" color for anchoring
    mid_roi = hsv[120:180, 120:180]
    mid_avg = cv2.mean(mid_roi)[:3]
    mid_color, _ = get_color_and_confidence(mid_avg)
    
    # Re-process the whole face with that anchor
    results = process_frame(img, expected_center=mid_color)
    return [r['color'] for r in results]

def build_cube_string(faces_colors):
    order = ['left', 'up', 'front', 'down', 'right', 'back']
    cube_string = []
    for face_key in order:
        if face_key not in faces_colors:
             raise ValueError(f"Missing face data for {face_key}")
        for color in faces_colors[face_key]:
            # Map full names to URFDLB if needed, but solver.py handles string
            # We'll just provide the color name as is
            cube_string.append(color)
    return cube_string
