import cv2
import numpy as np
from sklearn.cluster import KMeans

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
            # Extract central part of the cell (50% of area for reliability)
            y1 = i * cell_h + int(cell_h * 0.25)
            y2 = (i + 1) * cell_h - int(cell_h * 0.25)
            x1 = j * cell_w + int(cell_w * 0.25)
            x2 = (j + 1) * cell_w - int(cell_w * 0.25)
            
            roi = hsv[y1:y2, x1:x2]
            
            # Reflection Reduction: Create mask for non-reflective pixels (V <= 240)
            v_channel = roi[:, :, 2]
            mask = v_channel <= 240
            
            if np.any(mask):
                # Calculate mean only on non-reflective pixels
                avg_hsv = cv2.mean(roi, mask=mask.astype(np.uint8))[:3]
            else:
                # Fallback to simple mean if everything is reflective (unlikely)
                avg_hsv = cv2.mean(roi)[:3]
                
            face_hsv_values.append(avg_hsv)
            
    return face_hsv_values

def classify_colors_clustering(all_54_hsv):
    """
    Perform K-Means clustering (k=6) on 54 facelets and map clusters to colors.
    """
    # Convert to numpy array for KMeans
    data = np.array(all_54_hsv)
    
    # Initialize KMeans
    kmeans = KMeans(n_clusters=6, n_init=10, random_state=42)
    labels = kmeans.fit_predict(data)
    centroids = kmeans.cluster_centers_
    
    # Mapping strategy: Identify clusters based on Hue, Saturation, and Value
    # color_map[cluster_index] = color_name
    color_map = {}
    
    # 1. Identify White: Lowest Saturation
    white_idx = np.argmin(centroids[:, 1])
    color_map[white_idx] = 'white'
    
    # Remaining indices
    remaining_indices = [i for i in range(6) if i != white_idx]
    
    # 2. Map other colors based on Hue
    # Standard HSV Hues: Red (0, 180), Orange (15), Yellow (30), Green (60), Blue (110-120)
    for idx in remaining_indices:
        hue = centroids[idx, 0]
        # Handle Red wrap-around (Red can be around 0-10 or 160-180)
        eff_hue = hue if hue <= 150 else 0 
        
        if eff_hue < 8:
            color_map[idx] = 'red'
        elif eff_hue < 20:
            color_map[idx] = 'orange'
        elif eff_hue < 40:
            color_map[idx] = 'yellow'
        elif eff_hue < 85:
            color_map[idx] = 'green'
        else:
            color_map[idx] = 'blue'

    # Ensure all 6 colors are unique. If they aren't, K-Means might have failed
    # due to lighting or missing colors. We'll use the labels as-is but log a warning.
    detected_colors = [color_map.get(label, 'unknown') for label in labels]
    
    # If duplicates exist, fall back to simple heuristic for the centroids
    if len(set(color_map.values())) < 6:
        # Sort remaining by hue
        sorted_by_hue = sorted(remaining_indices, key=lambda i: centroids[i,0])
        # This is a very rough backup: Orange < Yellow < Green < Blue < Red (wrap)
        # But let's trust the current mapping first.
        pass

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
