import cv2
import os
import math

video_path = input()
output_dir = "frames1"
num_images = 50

os.makedirs(output_dir, exist_ok=True)

cap = cv2.VideoCapture(video_path)

total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
print("Total frames:", total_frames)

step = max(1, total_frames // num_images)
print("Saving every", step, "frames")

frame_id = 0
saved = 0

while True:
    ret, frame = cap.read()
    if not ret:
        break

    if frame_id % step == 0 and saved < num_images:
        cv2.imwrite(f"{output_dir}/frame_{saved:02d}.jpg", frame)
        saved += 1

    frame_id += 1

cap.release()
print(f"Saved {saved} frames")
