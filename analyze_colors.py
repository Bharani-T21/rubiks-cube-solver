import cv2
import numpy as np
import os
import glob

upload_dir = 'uploads'
images = glob.glob(os.path.join(upload_dir, '*_camera.jpg'))

print("Analyzing recent camera captures...")

for img_path in images:
    img = cv2.imread(img_path)
    if img is None: continue
    
    img = cv2.resize(img, (300, 300))
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    height, width, _ = img.shape
    cell_h = height // 3
    cell_w = width // 3
    
    print(f"\n--- {os.path.basename(img_path)} ---")
    
    for i in range(3):
        for j in range(3):
            y1 = i * cell_h + int(cell_h * 0.25)
            y2 = (i + 1) * cell_h - int(cell_h * 0.25)
            x1 = j * cell_w + int(cell_w * 0.25)
            x2 = (j + 1) * cell_w - int(cell_w * 0.25)
            
            roi = hsv[y1:y2, x1:x2]
            
            # Get median or mean H, S, V for this cell
            mean_h = np.median(roi[:,:,0])
            mean_s = np.median(roi[:,:,1])
            mean_v = np.median(roi[:,:,2])
            
            print(f"Cell ({i},{j}): H={mean_h:.1f}, S={mean_s:.1f}, V={mean_v:.1f}")
