import cv2
import numpy as np

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

def extract_facelet_hsv(image_path):
    """
    Extracts 9 average HSV values from a face image.
    Applies reflection reduction by ignoring pixels with V > 240.
    """
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image at {image_path}")

    img = cv2.resize(img, (300, 300))
    proc_img = preprocess_image(img)
    hsv = cv2.cvtColor(proc_img, cv2.COLOR_BGR2HSV)
    
    height, width, _ = img.shape
    cell_h = height // 3
    cell_w = width // 3
    
    face_hsv_values = []
    
    for i in range(3):
        for j in range(3):
            # Extract central part of the cell (60% of area for reliability)
            y1 = i * cell_h + int(cell_h * 0.2)
            y2 = (i + 1) * cell_h - int(cell_h * 0.2)
            x1 = j * cell_w + int(cell_w * 0.2)
            x2 = (j + 1) * cell_w - int(cell_w * 0.2)
            
            roi = hsv[y1:y2, x1:x2]
            
            # Reflection Reduction: Create mask for non-reflective pixels (V <= 240)
            v_channel = roi[:, :, 2]
            mask = v_channel <= 245 # Slightly more relaxed
            
            if np.any(mask):
                avg_hsv = cv2.mean(roi, mask=mask.astype(np.uint8))[:3]
            else:
                avg_hsv = cv2.mean(roi)[:3]
                
            face_hsv_values.append(avg_hsv)
            
    return face_hsv_values

def classify_colors_anchored(all_54_hsv, anchor_indices):
    """
    Classifies 54 facelets by comparing them to 6 ground-truth anchors (centers).
    """
    # 1. Extract the 6 anchors based on center indices
    # anchor_indices maps color_name -> index in all_54_hsv
    anchors = {color: all_54_hsv[idx] for color, idx in anchor_indices.items()}
    
    detected_colors = []
    
    for hsv in all_54_hsv:
        h, s, v = hsv
        min_dist = float('inf')
        best_color = 'white'
        
        for color, anchor in anchors.items():
            ah, asat, av = anchor
            
            # Cylindrical distance in HSV
            # Hue is circular (0-180)
            dh = min(abs(h - ah), 180 - abs(h - ah))
            ds = s - asat
            dv = v - av
            
            # Calculate weighted Euclidean distance
            # For White, Hue is less stable, so we weight S/V more
            if color == 'white':
                dist = np.sqrt((dh * 0.5)**2 + (ds * 2.0)**2 + (dv * 1.0)**2)
            else:
                dist = np.sqrt((dh * 2.5)**2 + (ds * 1.0)**2 + (dv * 0.5)**2)
                
            if dist < min_dist:
                min_dist = dist
                best_color = color
                
        detected_colors.append(best_color)
        
    return detected_colors

def build_cube_string(faces_colors):
    """
    faces_colors is a dict: {'up': [...], 'right': [...], 'front': [...], 'down': [...], 'left': [...], 'back': [...]}
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
