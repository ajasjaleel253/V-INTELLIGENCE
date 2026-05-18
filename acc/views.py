import datetime
import uuid
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password, check_password
from functools import wraps
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.urls import reverse

from acc.models import OwnerAccount
from LicensePlate.models import Owner, Vehicle, Violation, Insurance, Country

# =====================================
#           Owner Login 
# =====================================
def owner_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.session.get('owner_id'):
            messages.error(request, "Access Denied: Please login first.")
            return redirect('user_login')
        return view_func(request, *args, **kwargs)
    return wrapper

# ===============================
#   REGISTER NEW OWNER ACCOUNT
# ===============================
def register_view(request):
    if request.session.get('owner_id'):
        return redirect('dashboard')

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        if OwnerAccount.objects.filter(email=email).exists():
            messages.error(request, "Email is already registered.")
            return redirect('register')

        hashed_password = make_password(password)
        owner_account = OwnerAccount.objects.create(email=email, password=hashed_password)

        
        default_country, _ = Country.objects.get_or_create(
            name="Unknown", 
            defaults={'iso_code': 'UNK', 'phone_code': '+00', 'driving_side': 'R'}
        )
        
   
        random_plate = f"PENDING-{uuid.uuid4().hex[:6].upper()}"
        dummy_vehicle, _ = Vehicle.objects.get_or_create(
            license_plate=random_plate,
            defaults={
                'country': default_country,
                'vehicle_type': 'N/A',
                'manufacturer': 'Pending Registration',
                'model': 'N/A',
                'color': 'N/A',
                'fuel_type': 'N/A',
                'registration_year': 2024,
                'engine_capacity': 0,
                'emission_norm': 'N/A',
                'chassis_number': random_plate,
                'engine_number': random_plate,
            }
        )

        temp_name = email.split('@')[0].capitalize()

        Owner.objects.get_or_create(
            email=email,
            defaults={
                'full_name': temp_name,
                'country': default_country,
                'date_of_birth': datetime.date(2000, 1, 1),
                'vehicle': dummy_vehicle 
            }
        )

        request.session['owner_id'] = owner_account.id
        messages.success(request, "Account created successfully!")
        return redirect('dashboard')

    return render(request, "acc/register.html")
# ===============================
#           USER LOGIN
# ===============================
def user_login_view(request):
    if request.session.get('owner_id'):
        return redirect('dashboard')

    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")

        try:
            owner = OwnerAccount.objects.get(email=email)
            if check_password(password, owner.password):
                request.session['owner_id'] = owner.id
                return redirect('dashboard')
            else:
                messages.error(request, "Invalid password.")
        except OwnerAccount.DoesNotExist:
            messages.error(request, "Email not registered.")

    return render(request, "acc/user_login.html")

# ===============================
#       ADMIN LOGIN
# ===============================
def admin_login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('home_page')

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")

        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_staff:
            login(request, user)
            messages.success(request, "Command Uplink Established.")
            return HttpResponseRedirect(reverse('home_page')) 
        elif user is not None:
            messages.error(request, "Access Denied: Insufficient rank.")
        else:
            messages.error(request, "Invalid Command credentials.")

    return render(request, "acc/admin_login.html")

@staff_member_required(login_url='admin_login')
def home(request):
    return render(request, "LicensePlate/home.html")

@staff_member_required(login_url='admin_login')
def license_plate_detection(request):
    return render(request, "LicensePlate/scanner.html")
# ===============================
#           LOGOUT
# ===============================
def logout_view(request):
    if request.session.get('owner_id'):
        del request.session['owner_id']
    logout(request) 
    messages.success(request, "You have been logged out.")
    return redirect('user_login')

# ===============================
#       OWNER DASHBOARD
# ===============================
@owner_login_required
def dashboard_view(request):
    owner_id = request.session.get('owner_id')

    try:
        owner_account = OwnerAccount.objects.get(id=owner_id)
        owner_obj = Owner.objects.get(email=owner_account.email)
    except (OwnerAccount.DoesNotExist, Owner.DoesNotExist):
        messages.error(request, "Owner data not found.")
        return redirect('user_login')

    # --- Profile Updates ---
    if request.method == "POST" and request.POST.get("action") == "update_profile":
        owner_obj.full_name = request.POST.get("full_name", owner_obj.full_name)
        owner_obj.contact_number = request.POST.get("contact_number", owner_obj.contact_number)
        owner_obj.address = request.POST.get("address", owner_obj.address)
        owner_obj.city = request.POST.get("city", owner_obj.city)
        owner_obj.state = request.POST.get("state", owner_obj.state)
        
        dob = request.POST.get("date_of_birth")
        if dob: 
            owner_obj.date_of_birth = dob
            
        owner_obj.save()
        messages.success(request, "Profile updated successfully.")
        return redirect('dashboard')

    # Fetch vehicle data
    vehicles_data = []
    if owner_obj.vehicle:
        vehicle = owner_obj.vehicle
        insurance = Insurance.objects.filter(vehicle=vehicle).first()
        violations = Violation.objects.filter(vehicle=vehicle).order_by('-violation_date')
        
        vehicles_data.append({
            "owner": owner_obj,
            "vehicle": vehicle,
            "plate": vehicle.license_plate, 
            "insurance": insurance,
            "violations": violations
        })

    return render(request, "acc/dashboard.html", {
        "owner": owner_account,
        "owner_obj": owner_obj,
        "vehicles_data": vehicles_data
    })
# ===============================
#           PAY FINE
# ===============================
@owner_login_required
def pay_fine_api(request, violation_id):
    if request.method == "POST":
        try:
            violation = Violation.objects.get(id=violation_id)
            violation.is_paid = True
            violation.save()
            return render(request, 'acc/dashboard.html')
        except Violation.DoesNotExist:
            pass
    return redirect('dashboard')


