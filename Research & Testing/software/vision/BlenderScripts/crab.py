import bpy
import os
import random

# ========= SETTINGS =========
dataset_path =  r"C:\Users\nadah\OneDrive\Desktop\dataset\images"   
output_path = r"C:\Users\nadah\OneDrive\Desktop\dataset\images-filters"
start_index =1400 # Start from image #300
end_index = 1500

# SPEED OPTIMIZATIONS
scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64 
scene.cycles.use_denoising = True 
scene.render.resolution_percentage = 100

# SET OUTPUT FORMAT TO JPEG
scene.render.image_settings.file_format = 'JPEG'
scene.render.image_settings.quality = 90  # JPEG quality (0-100)

# Use GPU if available
try:
    scene.cycles.device = 'GPU'
    print("GPU rendering enabled")
except:
    print("GPU not available, using CPU")

# Get image list and sort for consistent ordering
all_images = [f for f in os.listdir(dataset_path)
              if f.lower().endswith(('.png', '.jpg', '.jpeg','webp'))]
all_images.sort()  # Sort alphabetically to ensure consistent indexing

# Calculate valid range
total_images = len(all_images)
if start_index > total_images:
    print(f"Error: Start index {start_index} exceeds total images ({total_images})")
    # Don't exit, just set to max
    start_index = total_images
    
if end_index > total_images:
    print(f"Warning: End index {end_index} exceeds total images ({total_images})")
    print(f"Setting end index to {total_images}")
    end_index = total_images

num_images = end_index - start_index + 1

# Select the range
selected_images = all_images[start_index-1:end_index]  # -1 because list is 0-indexed

print(f"\n{'='*50}")
print(f" Selected images {start_index} to {end_index}")
print(f" Total: {num_images} images")
print(f" Output: {output_path}")
print(f" Output format: JPG (Quality: {scene.render.image_settings.quality})")
print(f"{'='*50}\n")

# Get objects once (faster than looking up each time)
plane = bpy.data.objects["Plane"]
mat = plane.data.materials[0]
image_node = mat.node_tree.nodes["ImageTexture"]

light = bpy.data.objects["Spot"]
light_nodes = light.data.node_tree.nodes
value_node = light_nodes["ShadowControl"]

min_value = -200
max_value = 200

skipped_count = 0
rendered_count = 0

for i, img_name in enumerate(selected_images):
    img_path = os.path.join(dataset_path, img_name)

    # Load image
    img = bpy.data.images.load(img_path, check_existing=True)
    image_node.image = img

    # Random light value
    value_node.outputs[0].default_value = random.uniform(min_value, max_value)

    # Output filename - keep original name but ensure JPG extension
    base_name = os.path.splitext(img_name)[0]
    extension = '.jpg'  # Force JPG format
    
    filename = f"{base_name}{extension}"
    filepath = os.path.join(output_path, filename)
    
    # CHECK IF FILE ALREADY EXISTS - SKIP IF IT DOES
    if os.path.exists(filepath):
        print(f"!! Skipping !! {filename} - already exists")
        skipped_count += 1
        # Clean up and continue
        bpy.data.images.remove(img)
        continue  # Skip to next image
    
    scene.render.filepath = filepath
    print(f"[{start_index + i}/{end_index}] Rendering: {filename}")  # Show progress

    # Render
    bpy.ops.render.render(write_still=True)
    rendered_count += 1
    
    # Clean up image to save memory
    bpy.data.images.remove(img)

print(f"\n{'='*50}")
print(f" FINISHED!")
print(f" Rendered: {rendered_count} new images")
if skipped_count > 0:
    print(f" Skipped: {skipped_count} existing images")
print(f" Location: {output_path}")
print(f" Format: JPEG (Quality: {scene.render.image_settings.quality})")
print(f"{'='*50}")