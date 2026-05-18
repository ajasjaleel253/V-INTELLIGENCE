import threading
import os
import csv
from django.conf import settings
from .models import VideoUpload
from .core.algorithm import LicensePlateDetector

def run_alpr_pipeline(video_instance_id):
    # Retrieve the DB object
    video_instance = VideoUpload.objects.get(id=video_instance_id)
    
    # Update status
    video_instance.status = "Processing: Detecting Vehicles..."
    video_instance.save()

    try:
        # 1. Define Paths
        input_video_path = video_instance.video_file.path
        
        # Create unique filenames based on video ID
        csv_name = f"results_{video_instance.id}.csv"
        csv_path = os.path.join(settings.MEDIA_ROOT, 'csvs', csv_name)
        
        interpolated_csv_name = f"interpolated_{video_instance.id}.csv"
        interpolated_csv_path = os.path.join(settings.MEDIA_ROOT, 'csvs', interpolated_csv_name)
        
        output_video_name = f"processed_{video_instance.id}.webm" 
        output_video_path = os.path.join(settings.MEDIA_ROOT, 'processed', output_video_name)

        # Ensure output directories exist
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'csvs'), exist_ok=True)
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'processed'), exist_ok=True)

        # 2. Initialize the AI Model
        detector = LicensePlateDetector(
            model_path_yolo='yolov8n.pt', 
            model_path_plate='license_plate_detector.pt'
        )

        # 3. STEP 1: Process Video (YOLO + Sort + OCR)
        # This saves the raw data to csv_path
        detector.process_video(input_video_path, csv_path)

        # 4. STEP 2: Interpolate Missing Data
        video_instance.status = "Processing: Refining Data..."
        video_instance.save()
        
        # Read the raw CSV we just created
        with open(csv_path, 'r') as file:
            reader = csv.DictReader(file)
            data = list(reader)
        
        # Run interpolation
        interpolated_data = detector.interpolate_bounding_boxes(data)

        # Write the interpolated data to a NEW CSV file
        header = ['frame_nmr', 'car_id', 'car_bbox', 'license_plate_bbox', 'license_plate_bbox_score', 'license_number', 'license_number_score']
        with open(interpolated_csv_path, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=header)
            writer.writeheader()
            writer.writerows(interpolated_data)

        # 5. STEP 3: Visualize (Draw on Video)
        video_instance.status = "Processing: Rendering Video..."
        video_instance.save()
        
        detector.visualize(input_video_path, interpolated_csv_path, output_video_path)

        # 6. Finalize Database Entry
        video_instance.processed_video.name = f"processed/{output_video_name}"
        video_instance.csv_file.name = f"csvs/{interpolated_csv_name}"
        video_instance.is_processed = True
        video_instance.status = "Completed"
        video_instance.save()

    except Exception as e:
        print(f"Error processing video: {e}")
        video_instance.status = f"Error: {str(e)}"
        video_instance.save()

def start_processing(video_instance_id):
    thread = threading.Thread(target=run_alpr_pipeline, args=(video_instance_id,))
    thread.start()