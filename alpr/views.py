from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Sum
from datetime import date
import pandas as pd
from collections import Counter
from django.http import HttpResponse
from .models import VideoUpload
from .services import start_processing

# Import Database models from the SECOND app
from LicensePlate.models import (
    Vehicle, 
    Owner, 
    Insurance, 
    Documents, 
    Violation
)

def upload_video(request):
    if request.method == 'POST' and request.FILES.get('video'):
        video = request.FILES['video']
        instance = VideoUpload.objects.create(video_file=video)
        start_processing(instance.id)
        return redirect('video_detail', video_id=instance.id)
    return render(request, 'upload.html')

def video_detail(request, video_id):
    video = get_object_or_404(VideoUpload, id=video_id)
    license_plates = []
    if video.is_processed and video.csv_file:
        try:
            df = pd.read_csv(video.csv_file.path)
            if 'license_number' in df.columns:
                df = df[df['license_number'] != '0']
                for car_id in df['car_id'].unique():
                    car_group = df[df['car_id'] == car_id]
                    if 'license_number_score' in df.columns:
                        best_row = car_group.sort_values('license_number_score', ascending=False).iloc[0]
                        confidence = round(float(best_row['license_number_score']), 3)
                    else:
                        best_row = car_group.iloc[0]
                        confidence = 0.0
                    license_plates.append({
                        'car_id': int(car_id),
                        'plate': str(best_row['license_number']).strip().upper(),
                        'confidence': confidence
                    })
        except Exception as e:
            print(f"Error reading CSV: {e}")
    return render(request, 'detail.html', {'video': video, 'license_plates': license_plates})

# ==========================================
#  THE FIXED VERIFICATION VIEW
# ==========================================
def verification_dashboard(request, video_id):
    video = get_object_or_404(VideoUpload, id=video_id)
    verified_data = []
    
    if video.is_processed and video.csv_file:
        try:
            df = pd.read_csv(video.csv_file.path)
            
            # Check if we have the necessary columns
            if 'car_id' in df.columns and 'license_number' in df.columns:
                
                # 1. CLEANING
                df = df[df['license_number'] != '0']
                df = df.dropna(subset=['license_number'])

                # 2. GROUPING
                for car_id in df['car_id'].unique():
                    car_group = df[df['car_id'] == car_id]
                    candidates = car_group['license_number'].astype(str).tolist()
                    
                    if not candidates:
                        continue

                    # 3. MAJORITY VOTE
                    best_plate = Counter(candidates).most_common(1)[0][0].strip().upper()

                    # Database Fetch Logic
                    try:
                        vehicle = Vehicle.objects.get(license_plate=best_plate)
                        
                        try:
                            owner_name = vehicle.owner.full_name
                        except:
                            owner_name = "Unknown Owner"

                        # -- Insurance Check --
                        insurance_valid = False
                        try:
                            ins = vehicle.insurance
                            if ins.expiry_date >= date.today() and ins.active:
                                insurance_valid = True
                        except:
                            pass

                        # -- PUC Check --
                        puc_valid = False
                        try:
                            if hasattr(vehicle, 'documents'):
                                puc_valid = vehicle.documents.pollution_certificate
                        except:
                            pass
                        
                        # -- RC Check (FIXED) --
                        # Directly accesses the boolean field on the Vehicle model
                        rc_valid = vehicle.registration_valid  

                        # -- Violations Check --
                        unpaid_violations = Violation.objects.filter(
                                vehicle=vehicle,
                                is_paid=False
                            )

                        total_fines = unpaid_violations.aggregate(
                            Sum('fine_amount')
                        )['fine_amount__sum'] or 0

                        has_violation = unpaid_violations.exists()

                        violation_types = [
                            v.get_violation_type_display()
                            for v in unpaid_violations
                        ]
                        
                        status = {
                            'plate': best_plate,
                            'found': True,
                            'owner': owner_name,
                            'model': f"{vehicle.manufacturer} {vehicle.model}",
                            'color': vehicle.color,
                            'insurance_valid': insurance_valid,
                            'puc_valid': puc_valid,
                            'rc_valid': rc_valid,  
                            'fines': total_fines,
                            'has_violation': has_violation,
                            'violation_types': violation_types,
                        }

                    except Vehicle.DoesNotExist:
                        status = {
                            'plate': best_plate,
                            'found': False,
                            'error': "Not found in registry"
                        }
                    
                    verified_data.append(status)

        except Exception as e:
            print(f"Error processing verification: {e}")

    context = {
        'video': video,
        'verified_vehicles': verified_data,
        'today': date.today()
    }
    
    return render(request, 'verification.html', context)


def generate_notification(request, plate, msg_type):
    # 1. Get vehicle data (FIX: Use license_plate, not plate)
    vehicle = get_object_or_404(Vehicle, license_plate=plate)
    
    # 2. Check Statuses manually to be safe
    # Insurance
    is_ins_valid = False
    try:
        is_ins_valid = (vehicle.insurance.active and vehicle.insurance.expiry_date >= date.today())
    except: pass

    # PUC
    is_puc_valid = False
    try:
        is_puc_valid = vehicle.documents.pollution_certificate
    except: pass

    # RC (Direct Check)
    is_rc_valid = vehicle.registration_valid

    # Fines
    fines = 0
    has_fines = False
    try:
        total = vehicle.violation_set.filter(is_paid=False).aggregate(total=Sum('fine_amount'))['total']
        if total and total > 0:
            fines = total
            has_fines = True
    except: pass

    # 3. Identify Missing Items
    missing = []
    if not is_ins_valid: missing.append("Insurance")
    if not is_puc_valid: missing.append("PUC (Pollution Certificate)")
    if not is_rc_valid: missing.append("Registration Certificate (RC)")
    if has_fines: missing.append(f"Unpaid Fines (${fines})")
    
    issues_str = ", ".join(missing)
    owner_name = vehicle.owner.full_name if hasattr(vehicle, 'owner') else "Vehicle Owner"

    # 4. Format the Content
    if msg_type == 'email':
        filename = f"email_{plate}.txt"
        content = f"""Subject: Urgent: Vehicle Documentation Notice - {plate}

Dear {owner_name},

This is an automated notification regarding your vehicle {vehicle.model} ({plate}).
Our system has flagged the following issues:
{chr(10).join(['- ' + item for item in missing])}

Please update your records or pay the outstanding fines immediately.

Regards,
Traffic Management Dept."""

    else: # SMS Format
        filename = f"sms_{plate}.txt"
        content = f"MSG: Hi {owner_name}, your vehicle {plate} has pending issues: {issues_str}. Please clear them ASAP. -Traffic Dept."

    # 5. Return as a downloadable file
    response = HttpResponse(content, content_type='text/plain')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def vehicle_search(request):
    query = request.GET.get('q')
    verified_vehicles = None 

    if query:
        # We only search if the user typed something
        verified_vehicles = Vehicle.objects.filter(license_plate__icontains=query)

    context = {
        'verified_vehicles': verified_vehicles,
        'query': query,
    }
    
    return render(request, 'vehicle_search.html', context)


# ==========================================
#  NEW: VEHICLE DETAILS VIEW
# ==========================================
def vehicle_details(request, license_plate):
    # Fetch the vehicle based on the license plate clicked
    vehicle = get_object_or_404(
        Vehicle.objects.select_related("owner", "insurance"), 
        license_plate=license_plate
    )

    # Safely try to get the driving license if it exists
    try:
        driving_license = vehicle.owner.drivinglicense
    except Exception:
        driving_license = None

    # Pass the actual ORM objects directly to the template
    context = {
        'data': {
            'vehicle': vehicle,
            'owner': getattr(vehicle, 'owner', None),
            'license': driving_license,
            'insurance': getattr(vehicle, 'insurance', None),
            'violations': vehicle.violation_set.all()
        }
    }

    return render(request, 'vehicle_details.html', context)