import cv2
import numpy as np

# Robust HSV color centers (OpenCV: H:0-180, S:0-255, V:0-255)
DEFAULT_COLOR_CENTERS = {
    'red': [175, 200, 150],
    'orange': [12, 220, 200],
    'yellow': [30, 200, 200],
    'green': [70, 200, 150],
    'blue': [110, 200, 150],
    'white': [0, 0, 210]
}

def preprocess_image(img):
    """
    Apply Gaussian blur and smartly boost saturation to make colors pop for HSV thresholding.
    Note: Gray World white balance was removed because it fails drastically when 
    the camera is pointed at a solid color (e.g., staring at a red Rubik's cube face).
    """
    blurred = cv2.GaussianBlur(img, (5, 5), 0)
    
    # Convert to HSV to boost saturation slightly without altering Hue
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV).astype(np.float32)
    
    # Boost saturation by 20% to help differentiate washed out colors
    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * 1.2, 0, 255)
    
    final = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR)
    
    return final

def get_color_and_confidence(hsv_pixel):
    """
    Matches an HSV pixel to the closest static color center and returns
    the color name and a confidence score (0-1).
    """
    h, s, v = hsv_pixel
    
    # Hard override for white - if it has low saturation or is very bright and somewhat desaturated
    if s < 75 and v > 80:
        return 'white', 1.0
        
    min_dist = float('inf')
    best_color = 'white'
    
    for color, center in DEFAULT_COLOR_CENTERS.items():
        if color == 'white': continue # Handled by the explicit check above
        
        ch, cs, cv = center
        dh = min(abs(h - ch), 180 - abs(h - ch))
        ds = s - cs
        dv = v - cv
        
        # Heavy weight on Hue since it represents the actual color tint
        if color == 'orange' or color == 'red':
             # Red and orange are very close in Hue, differentiate carefully
             weigh_h = 4.0
        else:
             weigh_h = 3.0
             
        dist = np.sqrt((dh * weigh_h)**2 + (ds * 1.0)**2 + (dv * 0.5)**2)
        
        if dist < min_dist:
            min_dist = dist
            best_color = color
            
    # Confidence score calculation
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

    # 2. Shift Calculation (Disabled)
    # Shifting colors based on a single center sticker is highly volatile 
    # and usually causes incorrect detections across the whole face if the camera
    # hits a glare. We rely on the improved static thresholding instead.
    
    # 3. Classify colors directly based on raw averages
    preview_data = []
    for raw_val in raw_hsv_list:
        color, conf = get_color_and_confidence(raw_val)
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
