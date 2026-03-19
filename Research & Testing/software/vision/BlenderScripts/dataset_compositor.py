import bpy
import os

# ========= SETTINGS =========
dataset_path = r"C:\Users\nadah\OneDrive\Desktop\dataset\images"
output_path = r"C:\Users\nadah\OneDrive\Desktop\dataset\images-filters"
start_index = 300
end_index = 600
image_node_name = "Image"
# ============================

scene = bpy.context.scene

# Enable compositor
scene.use_nodes = True
tree = scene.node_tree

# Render settings
scene.render.engine = 'CYCLES'
scene.cycles.samples = 64

# Try GPU rendering
try:
    scene.cycles.device = 'GPU'
    print("GPU rendering enabled")
except:
    print("GPU not available, using CPU")

# Get compositor image node
if image_node_name not in tree.nodes:
    raise Exception(f"Node '{image_node_name}' not found in compositor")

image_node = tree.nodes[image_node_name]

# Create output folder if it doesn't exist
os.makedirs(output_path, exist_ok=True)

# Get images from dataset folder
all_images = [f for f in os.listdir(dataset_path)
              if f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp'))]

all_images.sort()

total_images = len(all_images)

# Validate indices
if start_index > total_images:
    start_index = total_images

if end_index > total_images:
    end_index = total_images

selected_images = all_images[start_index-1:end_index]

print("\n" + "="*50)
print(f"Selected images {start_index} to {end_index}")
print(f"Total images to process: {len(selected_images)}")
print(f"Output folder: {output_path}")
print("="*50 + "\n")

skipped_count = 0
rendered_count = 0

for i, img_name in enumerate(selected_images):

    img_path = os.path.join(dataset_path, img_name)

    # Load image
    img = bpy.data.images.load(img_path, check_existing=True)
    image_node.image = img

    # --- MATCH RENDER SIZE TO ORIGINAL IMAGE ---
    scene.render.resolution_x = img.size[0]
    scene.render.resolution_y = img.size[1]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'JPEG'
    # -------------------------------------------

    base_name = os.path.splitext(img_name)[0]
    filename = f"{base_name}.jpg"
    filepath = os.path.join(output_path, filename)

    # Skip if file already exists
    if os.path.exists(filepath):
        print(f"!!Skipping !!{filename} (already exists)")
        skipped_count += 1
        bpy.data.images.remove(img)
        continue

    scene.render.filepath = filepath

    print(f"[{i+1}/{len(selected_images)}] Rendering {filename}")

    bpy.ops.render.render(write_still=True)

    rendered_count += 1

    # Free memory
    bpy.data.images.remove(img, do_unlink=True)
    bpy.ops.outliner.orphans_purge(do_recursive=True)

print("\n" + "="*50)
print("FINISHED")
print(f"Rendered images: {rendered_count}")
print(f"Skipped images: {skipped_count}")
print(f"Output location: {output_path}")
print("="*50)