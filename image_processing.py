import cv2
import numpy as np

# HSV color ranges for Standard Rubik's Cube (Tuned empirically to user camera)
COLOR_RANGES = {
    'red': [([0, 70, 50], [10, 255, 255]), ([160, 70, 50], [180, 255, 255])],
    'orange': [([11, 70, 50], [20, 255, 255])],
    'yellow': [([21, 70, 50], [45, 255, 255])],  # Yellow spans 21 to 45
    'green': [([46, 70, 50], [85, 255, 255])],   # Green spans 46 to 85
    'blue': [([86, 70, 50], [130, 255, 255])],
    'white': [([0, 0, 50], [180, 60, 255])]      # White has very low saturation
}

def get_dominant_color(hsv_roi):
    max_count = 0
    detected_color = 'unknown'

    for color_name, ranges in COLOR_RANGES.items():
        mask = np.zeros(hsv_roi.shape[:2], dtype=np.uint8)
        for (lower, upper) in ranges:
            lower = np.array(lower, dtype=np.uint8)
            upper = np.array(upper, dtype=np.uint8)
            mask |= cv2.inRange(hsv_roi, lower, upper)
        
        count = cv2.countNonZero(mask)
        if count > max_count:
            max_count = count
            detected_color = color_name

    return detected_color

def process_face_image(image_path):
    img = cv2.imread(image_path)
    if img is None:
        raise ValueError(f"Could not read image at {image_path}")

    # Resize to standard size for processing
    img = cv2.resize(img, (300, 300))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    height, width, _ = img.shape
    cell_h = height // 3
    cell_w = width // 3
    
    face_colors = []
    
    # Grid goes top-to-bottom, left-to-right rows
    for i in range(3):
        for j in range(3):
            # Extract central part of the cell to avoid borders/black lines
            y1 = i * cell_h + int(cell_h * 0.25)
            y2 = (i + 1) * cell_h - int(cell_h * 0.25)
            x1 = j * cell_w + int(cell_w * 0.25)
            x2 = (j + 1) * cell_w - int(cell_w * 0.25)
            
            roi = hsv[y1:y2, x1:x2]
            color = get_dominant_color(roi)
            face_colors.append(color)

            # Draw rectangle on original image for debugging
            cv2.rectangle(img, (x1, y1), (x2, y2), (255, 255, 255), 2)
            cv2.putText(img, color, (x1, y1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
            
    # Save the debug image to the uploads folder
    debug_path = image_path.replace('.jpg', '_debug.jpg').replace('.png', '_debug.png')
    if not debug_path.endswith('_debug.jpg') and not debug_path.endswith('_debug.png'):
         debug_path += "_debug.jpg"
    cv2.imwrite(debug_path, img)

    return face_colors

def build_cube_string(faces_colors):
    """
    faces_colors is a dict: {'U': [...], 'R': [...], 'F': [...], 'D': [...], 'L': [...], 'B': [...]}
    Each holds 9 color strings.
    We need to return a list of colors in the order L, U, F, D, R, B
    """
    cube_string = []
    # The order for pycuber is L, U, F, D, R, B
    for face_name in ['L', 'U', 'F', 'D', 'R', 'B']:
        for color in faces_colors[face_name]:
            if color == 'unknown':
                raise ValueError(f"Detected invalid color '{color}'. Make sure the cube photos are well-lit and centers are distinct.")
            cube_string.append(color)
            
    return cube_string
