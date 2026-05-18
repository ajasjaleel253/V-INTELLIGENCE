import cv2
import numpy as np
import pandas as pd
import ast
from scipy.interpolate import interp1d
from ultralytics import YOLO
from alpr.sort.sort import Sort
from .utils_alpr import get_car, read_license_plate, write_csv

class LicensePlateDetector:
    def __init__(self, model_path_yolo, model_path_plate):
        self.coco_model = YOLO(model_path_yolo)
        self.license_plate_detector = YOLO(model_path_plate)
        self.mot_tracker = Sort()
        self.vehicles = [2, 3, 5, 7]  

    def interpolate_bounding_boxes(self, data):
        frame_numbers = np.array([int(row['frame_nmr']) for row in data])
        car_ids = np.array([int(float(row['car_id'])) for row in data])
        car_bboxes = np.array([list(map(float, row['car_bbox'][1:-1].split())) for row in data])
        license_plate_bboxes = np.array([list(map(float, row['license_plate_bbox'][1:-1].split())) for row in data])

        interpolated_data = []
        unique_car_ids = np.unique(car_ids)
        for car_id in unique_car_ids:
            frame_numbers_ = [p['frame_nmr'] for p in data if int(float(p['car_id'])) == int(float(car_id))]

            # Filter data for a specific car ID
            car_mask = car_ids == car_id
            car_frame_numbers = frame_numbers[car_mask]
            car_bboxes_interpolated = []
            license_plate_bboxes_interpolated = []

            first_frame_number = car_frame_numbers[0]

            for i in range(len(car_bboxes[car_mask])):
                frame_number = car_frame_numbers[i]
                car_bbox = car_bboxes[car_mask][i]
                license_plate_bbox = license_plate_bboxes[car_mask][i]

                if i > 0:
                    prev_frame_number = car_frame_numbers[i - 1]
                    prev_car_bbox = car_bboxes_interpolated[-1]
                    prev_license_plate_bbox = license_plate_bboxes_interpolated[-1]

                    if frame_number - prev_frame_number > 1:
                        frames_gap = frame_number - prev_frame_number
                        x = np.array([prev_frame_number, frame_number])
                        x_new = np.linspace(prev_frame_number, frame_number, num=frames_gap, endpoint=False)
                        interp_func = interp1d(x, np.vstack((prev_car_bbox, car_bbox)), axis=0, kind='linear')
                        interpolated_car_bboxes = interp_func(x_new)
                        interp_func = interp1d(x, np.vstack((prev_license_plate_bbox, license_plate_bbox)), axis=0, kind='linear')
                        interpolated_license_plate_bboxes = interp_func(x_new)

                        car_bboxes_interpolated.extend(interpolated_car_bboxes[1:])
                        license_plate_bboxes_interpolated.extend(interpolated_license_plate_bboxes[1:])

                car_bboxes_interpolated.append(car_bbox)
                license_plate_bboxes_interpolated.append(license_plate_bbox)

            for i in range(len(car_bboxes_interpolated)):
                frame_number = first_frame_number + i
                row = {}
                row['frame_nmr'] = str(frame_number)
                row['car_id'] = str(car_id)
                row['car_bbox'] = ' '.join(map(str, car_bboxes_interpolated[i]))
                row['license_plate_bbox'] = ' '.join(map(str, license_plate_bboxes_interpolated[i]))

                if str(frame_number) not in frame_numbers_:
                    row['license_plate_bbox_score'] = '0'
                    row['license_number'] = '0'
                    row['license_number_score'] = '0'
                else:
                    original_row = [p for p in data if int(p['frame_nmr']) == frame_number and int(float(p['car_id'])) == int(float(car_id))][0]
                    row['license_plate_bbox_score'] = original_row['license_plate_bbox_score'] if 'license_plate_bbox_score' in original_row else '0'
                    row['license_number'] = original_row['license_number'] if 'license_number' in original_row else '0'
                    row['license_number_score'] = original_row['license_number_score'] if 'license_number_score' in original_row else '0'

                interpolated_data.append(row)

        return interpolated_data

    def process_video(self, video_path, output_csv_path):
        """ Runs YOLO + SORT + OCR """
        cap = cv2.VideoCapture(video_path)
        results = {}
        frame_nmr = -1
        ret = True

        while ret:
            frame_nmr += 1
            ret, frame = cap.read()
            if ret:
                results[frame_nmr] = {}
                # detect vehicles
                detections = self.coco_model(frame)[0]
                detections_ = []
                for detection in detections.boxes.data.tolist():
                    x1, y1, x2, y2, score, class_id = detection
                    if int(class_id) in self.vehicles:
                        detections_.append([x1, y1, x2, y2, score])

                # track vehicles
                track_ids = self.mot_tracker.update(np.asarray(detections_))

                # detect license plates
                license_plates = self.license_plate_detector(frame)[0]
                for license_plate in license_plates.boxes.data.tolist():
                    x1, y1, x2, y2, score, class_id = license_plate

                    # assign license plate to car
                    xcar1, ycar1, xcar2, ycar2, car_id = get_car(license_plate, track_ids)

                    if car_id != -1:
                        # crop license plate
                        license_plate_crop = frame[int(y1):int(y2), int(x1): int(x2), :]
                        
                        # process license plate
                        license_plate_crop_gray = cv2.cvtColor(license_plate_crop, cv2.COLOR_BGR2GRAY)
                        _, license_plate_crop_thresh = cv2.threshold(license_plate_crop_gray, 64, 255, cv2.THRESH_BINARY_INV)

                        # read license plate number
                        license_plate_text, license_plate_text_score = read_license_plate(license_plate_crop_thresh)

                        if license_plate_text is not None:
                            results[frame_nmr][car_id] = {
                                'car': {'bbox': [xcar1, ycar1, xcar2, ycar2]},
                                'license_plate': {
                                    'bbox': [x1, y1, x2, y2],
                                    'text': license_plate_text,
                                    'bbox_score': score,
                                    'text_score': license_plate_text_score
                                }
                            }
        cap.release()
        write_csv(results, output_csv_path)
        return results
    
    def draw_border(self, img, top_left, bottom_right, color=(0, 255, 0), thickness=10, line_length_x=200, line_length_y=200):
        x1, y1 = top_left
        x2, y2 = bottom_right

        cv2.line(img, (x1, y1), (x1, y1 + line_length_y), color, thickness)  # -- top-left
        cv2.line(img, (x1, y1), (x1 + line_length_x, y1), color, thickness)

        cv2.line(img, (x1, y2), (x1, y2 - line_length_y), color, thickness)  # -- bottom-left
        cv2.line(img, (x1, y2), (x1 + line_length_x, y2), color, thickness)

        cv2.line(img, (x2, y1), (x2 - line_length_x, y1), color, thickness)  # -- top-right
        cv2.line(img, (x2, y1), (x2, y1 + line_length_y), color, thickness)

        cv2.line(img, (x2, y2), (x2, y2 - line_length_y), color, thickness)  # -- bottom-right
        cv2.line(img, (x2, y2), (x2 - line_length_x, y2), color, thickness)

        return img

    def visualize(self, video_path, csv_path, output_video_path):
        """ Draws boxes and saves video """
        results = pd.read_csv(csv_path)
        cap = cv2.VideoCapture(video_path)
        
        # 1. Get Video Properties FIRST
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # 2. Define Codec (WebM format for browser compatibility)
        fourcc = cv2.VideoWriter_fourcc(*'vp80')
        
        
        final_output_path = output_video_path.replace('.mp4', '.webm')
        out = cv2.VideoWriter(final_output_path, fourcc, fps, (width, height))

        license_plate = {}
        for car_id in np.unique(results['car_id']):
            max_ = np.amax(results[results['car_id'] == car_id]['license_number_score'])
            license_plate[car_id] = {
                'license_crop': None,
                'license_plate_number': results[(results['car_id'] == car_id) & (results['license_number_score'] == max_)]['license_number'].iloc[0]
            }
            cap.set(cv2.CAP_PROP_POS_FRAMES, results[(results['car_id'] == car_id) & (results['license_number_score'] == max_)]['frame_nmr'].iloc[0])
            ret, frame = cap.read()

            x1, y1, x2, y2 = ast.literal_eval(results[(results['car_id'] == car_id) & (results['license_number_score'] == max_)]['license_plate_bbox'].iloc[0].replace('[ ', '[').replace('   ', ' ').replace('  ', ' ').replace(' ', ','))

            license_crop = frame[int(y1):int(y2), int(x1):int(x2), :]
            license_crop = cv2.resize(license_crop, (int((x2 - x1) * 400 / (y2 - y1)), 400))

            license_plate[car_id]['license_crop'] = license_crop

        frame_nmr = -1
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        ret = True
        while ret:
            ret, frame = cap.read()
            frame_nmr += 1
            if ret:
                df_ = results[results['frame_nmr'] == frame_nmr]
                for row_indx in range(len(df_)):
                    # draw car
                    car_x1, car_y1, car_x2, car_y2 = ast.literal_eval(df_.iloc[row_indx]['car_bbox'].replace('[ ', '[').replace('   ', ' ').replace('  ', ' ').replace(' ', ','))
                    self.draw_border(frame, (int(car_x1), int(car_y1)), (int(car_x2), int(car_y2)), (0, 255, 0), 25, line_length_x=200, line_length_y=200)

                    # draw license plate
                    x1, y1, x2, y2 = ast.literal_eval(df_.iloc[row_indx]['license_plate_bbox'].replace('[ ', '[').replace('   ', ' ').replace('  ', ' ').replace(' ', ','))
                    cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 0, 255), 12)

                    # crop license plate
                    license_crop = license_plate[df_.iloc[row_indx]['car_id']]['license_crop']
                    H, W, _ = license_crop.shape

                out.write(frame)
            else:
                break # Stop loop if no frame returned
                
        out.release()
        cap.release()
        return final_output_path