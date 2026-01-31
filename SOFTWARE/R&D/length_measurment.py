import cv2
import numpy as np
import csv
from datetime import datetime
import math
import os

class ReferenceObject:
    def __init__(self, real_length_cm, name="Reference"):
        self.real_length_cm = real_length_cm
        self.name = name
        self.pixel_length = None
        self.pixels_per_cm = None
        self.distance_from_camera = None
    
    def set_pixel_length(self, pixel_length, distance_cm=None):
        self.pixel_length = pixel_length
        self.pixels_per_cm = pixel_length / self.real_length_cm
        if distance_cm:
            self.distance_from_camera = distance_cm
        return self.pixels_per_cm
    
    def get_scale_factor(self):
        if self.pixels_per_cm is None:
            raise ValueError("Pixel length not set. Call set_pixel_length() first.")
        return self.pixels_per_cm

class UnderwaterObject:
    def __init__(self, name="Target Object"):
        self.name = name
        self.pixel_length = None
        self.real_length_cm = None
        self.angle = 0
        self.estimated_distance = None
    
    def set_pixel_length(self, pixel_length):
        self.pixel_length = pixel_length
    
    def set_angle_correction(self, angle_degrees):
        self.angle = angle_degrees
    
    def set_estimated_distance(self, distance_cm):
        self.estimated_distance = distance_cm
    
    def calculate_length(self, reference, apply_distance_correction=True, 
                        apply_angle_correction=True, apply_refraction_correction=False):
        
        if self.pixel_length is None:
            raise ValueError("Pixel length not set for target object")
        
        scale_factor = reference.get_scale_factor()
        base_length = self.pixel_length / scale_factor
        
        corrections_applied = []
        
        # Distance correction if object is at different distance than reference
        if apply_distance_correction and self.estimated_distance and reference.distance_from_camera:
            if abs(self.estimated_distance - reference.distance_from_camera) > 1:  # Only if different by >1cm
                distance_ratio = self.estimated_distance / reference.distance_from_camera
                base_length = base_length * distance_ratio
                corrections_applied.append(f"Distance (×{distance_ratio:.2f})")
        
        # Angle correction for tilted objects
        if apply_angle_correction and self.angle != 0:
            angle_factor = 1 / math.cos(math.radians(self.angle))
            base_length = base_length * angle_factor
            corrections_applied.append(f"Angle {self.angle}° (×{angle_factor:.2f})")
        
        # Underwater refraction correction
        # Only use this if you have a specific reason (e.g., calibrated in air)
        if apply_refraction_correction:
            REFRACTION_FACTOR = 0.75
            base_length = base_length * REFRACTION_FACTOR
            corrections_applied.append(f"Refraction (×{REFRACTION_FACTOR})")
        
        self.real_length_cm = base_length
        
        # Print applied corrections for transparency
        if corrections_applied:
            print(f"   Corrections applied: {', '.join(corrections_applied)}")
        else:
            print(f"   No corrections applied (same conditions as reference)")
        
        return self.real_length_cm

class ROVCamera:
    def __init__(self, camera_index=0):
        self.camera_index = camera_index
        self.cap = None
        self.current_frame = None
        self.click_points = []

    def start_camera(self):
        self.cap = cv2.VideoCapture(self.camera_index)
        if not self.cap.isOpened():
            raise ValueError(f"Cannot open camera {self.camera_index}")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        
        print(f"✓ Camera started successfully")
        return True
    
    def live_view(self, window_name="ROV Camera - SPACE: Capture | Q: Quit"):
        if self.cap is None:
            self.start_camera()
        
        print("\n📹 Live View Active")
        print("  SPACE - Capture frame")
        print("  Q     - Quit")

        while True: 
            ret, frame = self.cap.read()
            if not ret:
                print("Failed to grab frame")
                break
            
            # Draw crosshair for centering
            h, w = frame.shape[:2]
            cv2.line(frame, (w//2 - 20, h//2), (w//2 + 20, h//2), (0, 255, 0), 2)
            cv2.line(frame, (w//2, h//2 - 20), (w//2, h//2 + 20), (0, 255, 0), 2)

            cv2.putText(frame, "SPACE: Capture | Q: Quit", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            cv2.imshow(window_name, frame)
            
            key = cv2.waitKey(1) & 0xFF
            if key == ord(' '):
                self.current_frame = frame.copy()
                print("✓ Frame captured!")
                cv2.destroyAllWindows()
                return self.current_frame
            elif key == ord('q') or key == ord('Q'):
                cv2.destroyAllWindows()
                return None
    
    def measure_distance(self, image, window_name="Click 2 points - ENTER: Confirm | ESC: Cancel"):
        self.click_points = []
        display = image.copy()

        def mouse_callback(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN:
                if len(self.click_points) < 2:
                    self.click_points.append((x, y))
                    cv2.circle(display, (x, y), 5, (0, 0, 255), -1)
                    cv2.putText(display, str(len(self.click_points)), (x+10, y-10),
                               cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

                    if len(self.click_points) == 2:
                        cv2.line(display, self.click_points[0], self.click_points[1], 
                                (0, 255, 0), 2)
                        p1, p2 = self.click_points
                        distance = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
                        mid_x = (p1[0] + p2[0]) // 2
                        mid_y = (p1[1] + p2[1]) // 2
                        cv2.putText(display, f"{distance:.1f} px", (mid_x, mid_y-10), 
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 0), 2)
                
                cv2.imshow(window_name, display)
        
        cv2.imshow(window_name, display)
        cv2.setMouseCallback(window_name, mouse_callback)

        print("\n📏 Click two points on the object")
        print("  Left Click - Mark point")
        print("  ENTER      - Confirm measurement")
        print("  ESC        - Cancel")

        while True:
            key = cv2.waitKey(1) & 0xFF
            if key == 27:  
                cv2.destroyAllWindows()
                return None
            elif key == 13 and len(self.click_points) == 2:  
                break
        
        cv2.destroyAllWindows()
        
        if len(self.click_points) == 2:
            p1, p2 = self.click_points
            distance = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            return distance
        return None
    
    def release(self):
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()

class MeasurementSession:
    """Main session controller for ROV measurements"""
    def __init__(self):
        self.reference = None
        self.objects = []
        self.camera = None
        self.measurements_history = []
        self.use_refraction_correction = False  # Default: OFF

    def setup_camera(self, camera_index=0):
        """Initialize camera system"""
        self.camera = ROVCamera(camera_index)
        self.camera.start_camera()
        print("✓ Camera setup complete")

    def calibrate_reference(self, real_length_cm, distance_from_camera_cm, name="ROV Reference"):
        print(f"\n{'='*60}")
        print("CALIBRATION - ROV-Attached Reference")
        print(f"{'='*60}")
        print(f"Reference: {name} ({real_length_cm} cm)")
        print(f"Distance from camera: {distance_from_camera_cm} cm")
        print("\n⚠️  Make sure reference is clearly visible in frame")

        frame = self.camera.live_view()
        if frame is None:
            print("❌ Calibration cancelled")
            return False
        
        print("\n📏 Click on both ends of the reference object")
        ref_pixels = self.camera.measure_distance(frame, "Measure Reference Object")

        if ref_pixels is None:
            print("❌ Reference measurement cancelled")
            return False
        
        self.reference = ReferenceObject(real_length_cm, name)
        self.reference.set_pixel_length(ref_pixels, distance_from_camera_cm)

        print(f"\n✓ Calibration successful!")
        print(f"   Pixel length: {ref_pixels:.2f} px")
        print(f"   Scale factor: {self.reference.pixels_per_cm:.4f} pixels/cm")
        print(f"   You can now measure objects at ~{distance_from_camera_cm} cm distance")
        print(f"\n   Refraction correction: {'ENABLED' if self.use_refraction_correction else 'DISABLED'}")
        
        return True
    
    def measure_object(self, name="Target", estimated_distance_cm=None, angle_degrees=0):
        if self.reference is None:
            print("❌ ERROR: Must calibrate reference first!")
            return None
        
        print(f"\n{'='*60}")
        print(f"MEASURING: {name}")
        print(f"{'='*60}")
        
        # Use reference distance if not specified
        if estimated_distance_cm is None:
            estimated_distance_cm = self.reference.distance_from_camera
            print(f"Using reference distance: {estimated_distance_cm} cm")
        else:
            print(f"Target distance: {estimated_distance_cm} cm")

        frame = self.camera.live_view()
        if frame is None:
            print("❌ Measurement cancelled")
            return None
        
        print(f"\n📏 Click on both ends of: {name}")
        obj_pixels = self.camera.measure_distance(frame, f"Measure {name}")

        if obj_pixels is None:
            print("❌ Measurement cancelled")
            return None
        
        # Calculate with corrections
        target = UnderwaterObject(name)
        target.set_pixel_length(obj_pixels)
        target.set_angle_correction(angle_degrees)
        target.set_estimated_distance(estimated_distance_cm)
        
        real_length = target.calculate_length(
            self.reference, 
            apply_distance_correction=True,
            apply_angle_correction=True,
            apply_refraction_correction=self.use_refraction_correction
        )

        print(f"\n✓ Measurement complete:")
        print(f"   Object: {name}")
        print(f"   Pixel length: {obj_pixels:.2f} px")
        print(f"   Real length: {real_length:.2f} cm")
        if angle_degrees != 0:
            print(f"   Angle: {angle_degrees}°")
        
        measurement_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'object_name': name,
            'pixel_length': obj_pixels,
            'angle_degrees': angle_degrees,
            'estimated_distance_cm': estimated_distance_cm,
            'real_length_cm': real_length,
            'reference_name': self.reference.name,
            'scale_factor': self.reference.pixels_per_cm,
            'refraction_corrected': self.use_refraction_correction
        }

        self.measurements_history.append(measurement_data)
        self.objects.append(target)

        return real_length
     
    def save_results(self, filename="rov_measurements.csv"):
        """Save all measurements to CSV file"""
        if not self.measurements_history:
            print("❌ No measurements to save")
            return False 
        
        fieldnames= ['timestamp', 'object_name', 'pixel_length', 'angle_degrees', 
                         'estimated_distance_cm', 'real_length_cm', 'reference_name', 
                         'scale_factor', 'refraction_corrected']
        
        file_exists = os.path.isfile(filename)

        if file_exists:
            print(f"\nFile {filename} already exists.")
            choice = input("  Append new data to existing file? (y/n) [y]: ").strip().lower()

            if choice == "n":
                new_filename = input("   Enter new filename: ").strip()
                if new_filename:
                    if not new_filename.endswith('.csv'):
                        new_filename += '.csv'
                    filename = new_filename
                    file_exists = os.path.isfile(filename)
                else: 
                    print("   ⚠️  Invalid filename. Using original with '_new' suffix.")
                    filename = filename.replace('.csv', '_new.csv')
                    file_exists = False
        mode = 'a' if file_exists else 'w'

        
        with open(filename, mode, newline='') as csvfile: 
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            for measurement in self.measurements_history:
                writer.writerow(measurement)
        
        if file_exists:
            print(f"\n✓ Data appended to {filename} SUCCESSFULLY.")
        else:
            print(f"\n✓ New file created: {filename} SUCCESSFULLY.")
        print(f"\n✓ Results saved to {filename}")
        print(f"   Total measurements: {len(self.measurements_history)}")
        return True
    
    def display_summary(self):
        """Display summary of all measurements"""
        if not self.measurements_history:
            print("\n⚠️  No measurements recorded yet")
            return
        
        print(f"\n{'='*70}")
        print("MEASUREMENT SUMMARY")
        print(f"{'='*70}")
        print(f"Reference: {self.reference.name} ({self.reference.real_length_cm} cm)")
        print(f"Reference distance: {self.reference.distance_from_camera} cm")
        print(f"Refraction correction: {'ENABLED' if self.use_refraction_correction else 'DISABLED'}")
        print(f"\nTotal measurements: {len(self.measurements_history)}")
        print(f"\n{'Object Name':<25} {'Length (cm)':<15} {'Distance':<12} {'Angle':<10}")
        print(f"{'-'*70}")

        for measurement in self.measurements_history:
            name = measurement['object_name'][:24]
            length = measurement['real_length_cm']
            distance = measurement['estimated_distance_cm']
            angle = measurement['angle_degrees']
            print(f"{name:<25} {length:<15.2f} {distance:<12.1f} {angle:<10.0f}°")
    
    def cleanup(self):
        if self.camera is not None:
            self.camera.release()
        print("\n✓ Session closed")


def main():
    print("="*70)
    print(" ROV UNDERWATER MEASUREMENT SYSTEM")
    print("="*70)
    print("\nThis system uses an ROV-attached reference for measurements.")
    
    session = MeasurementSession()
    
    try:
        print("\n[STEP 1: CAMERA SETUP]")
        session.setup_camera(0)  
        
        print("\n[STEP 2: REFRACTION CORRECTION SETTING]")
        
        refraction_choice = input("Enable refraction correction? (y/n) [n]: ").strip().lower()
        session.use_refraction_correction = (refraction_choice == 'y')
        
        if session.use_refraction_correction:
            print("   ✓ Refraction correction ENABLED")
        else:
            print("   ✓ Refraction correction DISABLED (underwater calibration mode)")
        
        print("\n[STEP 3: CALIBRATE REFERENCE]")
        print("\nEnter reference object details:")
        
        while True:
            try:
                ref_length = float(input("  Reference length (cm) [e.g., 20]: "))
                if ref_length > 0:
                    break
                print("  ⚠️  Length must be positive")
            except ValueError:
                print("  ⚠️  Please enter a valid number")
        
        while True:
            try:
                ref_distance = float(input("  Distance from camera to reference (cm) [e.g., 30]: "))
                if ref_distance > 0:
                    break
                print("  ⚠️  Distance must be positive")
            except ValueError:
                print("  ⚠️  Please enter a valid number")
        
        # Calibrate
        success = session.calibrate_reference(
            real_length_cm=ref_length,
            distance_from_camera_cm=ref_distance,
            name="ROV Reference Object"
        )
        
        if not success:
            print("\n❌ Calibration failed. Exiting...")
            session.cleanup()
            return
        
        print("\n[STEP 4: MEASURE OBJECTS]")
        print("\nYou can now measure objects.")
        print("Try to keep objects at approximately the same distance as reference.")
        
        while True:
            print("\n" + "-"*60)
            choice = input("\nEnter object name (or 'done' to finish): ").strip()
            
            if choice.lower() == 'done':
                break
            
            if not choice:
                print("⚠️  Please enter a name")
                continue
            
            dist_input = input(f"  Distance to object (cm) [Enter for {ref_distance}]: ").strip()
            if dist_input:
                try:
                    obj_distance = float(dist_input)
                except ValueError:
                    print("  ⚠️  Invalid distance, using reference distance")
                    obj_distance = None
            else:
                obj_distance = None
            
            angle_input = input("  Viewing angle (degrees) [Enter for 0]: ").strip()
            if angle_input:
                try:
                    obj_angle = float(angle_input)
                except ValueError:
                    print("  ⚠️  Invalid angle, using 0°")
                    obj_angle = 0
            else:
                obj_angle = 0
            
            session.measure_object(
                name=choice,
                estimated_distance_cm=obj_distance,
                angle_degrees=obj_angle
            )
        
        print("\n[STEP 5: RESULTS]")
        session.display_summary()
        
        save_choice = input("\nSave results to CSV? (y/n): ").strip().lower()
        if save_choice == 'y':
            filename = input("Filename [rov_measurements.csv]: ").strip()
            if not filename:
                filename = "rov_measurements.csv"
            if not filename.endswith('.csv'):
                filename += '.csv'
            session.save_results(filename)
        
        print("\n" + "="*70)
        print("MEASUREMENT SESSION COMPLETE")
        print("="*70)
        print("\n✓ All measurements completed successfully!")
        print(f"✓ Total objects measured: {len(session.measurements_history)}")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Session interrupted by user")
    except Exception as e:
        print(f"\n❌ Error occurred: {e}")
    finally:
        session.cleanup()


if __name__ == "__main__":
    main()