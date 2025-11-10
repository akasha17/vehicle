
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django import forms
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q

from .models import Profile, Vehicle, MaintenanceLog, FuelLog

def is_app_admin(user):
    """True if user is superuser or Profile.role == 'admin' (case-insensitive)."""
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    try:
        role = getattr(user, "profile").role
        return (role or "").lower() == "admin"
    except Exception:
        return False

def get_user_role(user):
    """Return normalized role or None."""
    try:
        return (getattr(user, "profile").role or "").lower()
    except Exception:
        return None

def role_required(*allowed_roles):
    """
    Require one of the roles (case-insensitive) or admin.
    Uses named route 'login' when not authenticated.
    """
    allowed_roles = tuple((r or "").lower() for r in allowed_roles)
    def decorator(view_func):
        @wraps(view_func)
        @login_required(login_url='login')
        def _wrapped(request, *args, **kwargs):
            if request.user.is_superuser or is_app_admin(request.user):
                return view_func(request, *args, **kwargs)
            role = get_user_role(request.user)
            if role in allowed_roles:
                return view_func(request, *args, **kwargs)
            raise PermissionDenied
        return _wrapped
    return decorator

class MaintenanceForm(forms.ModelForm):
    class Meta:
        model = MaintenanceLog
        fields = ["vehicle", "description", "date", "next_due"]

    def __init__(self, *args, **kwargs):
        vehicles_qs = kwargs.pop("vehicles_qs", None)
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.now().date()
        if vehicles_qs is not None:
            self.fields["vehicle"].queryset = vehicles_qs

class FuelForm(forms.ModelForm):
    class Meta:
        model = FuelLog
        fields = ["vehicle", "date", "liters", "cost", "odometer"]

    def __init__(self, *args, **kwargs):
        vehicles_qs = kwargs.pop("vehicles_qs", None)
        super().__init__(*args, **kwargs)
        self.fields["date"].initial = timezone.now().date()
        if vehicles_qs is not None:
            self.fields["vehicle"].queryset = vehicles_qs


try:
    from geopy.geocoders import Nominatim
    _GEOCODER_AVAILABLE = True
except Exception:
    _GEOCODER_AVAILABLE = False

class VehicleForm(forms.ModelForm):
    place_name = forms.CharField(required=False, label="Place Name")

    class Meta:
        model = Vehicle
        fields = ["registration_no", "make", "model", "year", "status", "current_driver", "place_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["current_driver"].queryset = User.objects.filter(profile__role__iexact="driver")
        self.fields["current_driver"].required = False
       

    def save(self, commit=True):
        instance = super().save(commit=False)
        place = self.cleaned_data.get("place_name")
        if place and _GEOCODER_AVAILABLE:
            try:
                geolocator = Nominatim(user_agent="vehicle_fleet_system")
                loc = geolocator.geocode(place)
                if loc:
                    if hasattr(instance, "latitude"):
                        instance.latitude = loc.latitude
                    if hasattr(instance, "longitude"):
                        instance.longitude = loc.longitude
                    if hasattr(instance, "last_location_time"):
                        instance.last_location_time = timezone.now()
            except Exception as e:
                print("Geocoding error:", e)
        if commit:
            instance.save()
        return instance

class AssignVehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["current_driver", "status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["current_driver"].queryset = User.objects.filter(profile__role__iexact="driver")
        self.fields["current_driver"].required = False


class VehicleLocationForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ["latitude", "longitude"]


def index(request):
    return render(request, "index.html")


def login_view(request):
    """
    Unified login: strict redirect by role.
    Superuser with no profile -> admin.
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")
        user = authenticate(request, username=username, password=password)
        if user is None:
            return render(request, "login.html", {"error": "Invalid credentials"})

        login(request, user)
        role = get_user_role(user)
        print(f"[LOGIN] user={user.username} is_superuser={user.is_superuser} role={role!r}")

        if role == "admin" or (role is None and user.is_superuser):
            return redirect("admin_dashboard")
        elif role == "staff":
            return redirect("staff_dashboard")
        elif role == "driver":
            return redirect("driver_dashboard")

        logout(request)
        return render(request, "login.html", {"error": "Role not assigned to this user."})

    return render(request, "login.html")

def login_unified(request):
    return login_view(request)

def logout_view(request):
    logout(request)
    return redirect("login")

@login_required(login_url='login')
def whoami(request):
    role = get_user_role(request.user)
    assigned = Vehicle.objects.filter(current_driver=request.user).count()
    return render(request, "whoami.html", {"user_obj": request.user, "role": role, "assigned": assigned})

#admin
@role_required('admin')
def admin_dashboard(request):
    vehicles = Vehicle.objects.all()
    profiles = Profile.objects.all()
    maintenance_logs = MaintenanceLog.objects.select_related("vehicle").all()
    fuel_logs = FuelLog.objects.select_related("vehicle").all()

    total_vehicles = vehicles.count()
    assigned = vehicles.filter(current_driver__isnull=False).count()
    not_assigned = vehicles.filter(current_driver__isnull=True).count()
    under_maintenance = vehicles.filter(status="maintenance").count()
    active = vehicles.filter(status="active").count()

    return render(request, "admin/admin_dashboard.html", {
        "vehicles": vehicles,
        "profiles": profiles,
        "maintenance_logs": maintenance_logs,
        "fuel_logs": fuel_logs,
        "chart_data": {
            "total_vehicles": total_vehicles,
            "assigned": assigned,
            "not_assigned": not_assigned,
            "under_maintenance": under_maintenance,
            "active": active,
        },
    })

@role_required('admin')
def register_staff(request):
    """Create Staff/Admin with chosen role."""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")
        role = (request.POST.get("role", "staff") or "staff").lower()

        if not username or not password:
            return render(request, "admin/register_staff.html", {"error": "Username and password are required."})

        if User.objects.filter(username=username).exists():
            return render(request, "admin/register_staff.html", {"error": "Username already exists."})

        user = User.objects.create_user(username=username, email=email, password=password)
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        Profile.objects.get_or_create(user=user, defaults={"role": role})
        messages.success(request, f"User '{username}' created as {role}.")
        return redirect("admin_dashboard")

    return render(request, "admin/register_staff.html")

@role_required('admin')
def add_driver(request):
    """Create Driver accounts; role forced to 'driver'."""
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")
        first_name = request.POST.get("first_name", "")
        last_name = request.POST.get("last_name", "")

        if not username or not password:
            return render(request, "driver/add.html", {"error": "Username and password are required."})

        if User.objects.filter(username=username).exists():
            return render(request, "driver/add.html", {"error": "Username already exists."})

        user = User.objects.create_user(username=username, email=email, password=password)
        user.first_name = first_name
        user.last_name = last_name
        user.save()

        Profile.objects.get_or_create(user=user, defaults={"role": "driver"})
        messages.success(request, f"Driver '{username}' created.")
        return redirect("admin_dashboard")

    return render(request, "driver/add.html")

@role_required('admin')
def delete_profile(request, pk):
    """Delete a Profile and linked User."""
    profile = get_object_or_404(Profile, pk=pk)
    if profile.user:
        profile.user.delete()
    profile.delete()
    messages.success(request, "User deleted successfully.")
    return redirect("admin_dashboard")


# Vehicles 
@role_required('admin', 'staff')
def add_vehicle(request):
    if request.method == "POST":
        form = VehicleForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle added.")
            return redirect("vehicle_list")
    else:
        form = VehicleForm()
    return render(request, "vehicles/add.html", {"form": form})

@role_required('admin', 'staff')
def vehicle_list(request):
    """List with search/filter + header stats."""
    qs = Vehicle.objects.select_related('current_driver').all()
    q = (request.GET.get('q') or '').strip()
    status = (request.GET.get('status') or '').strip()

    if q:
        qs = qs.filter(
            Q(registration_no__icontains=q) |
            Q(make__icontains=q) |
            Q(model__icontains=q)
        )
    if status:
        qs = qs.filter(status=status)

    total = qs.count()
    assigned = qs.filter(current_driver__isnull=False).count()
    maintenance = qs.filter(status='maintenance').count()

    return render(request, "vehicles/list.html", {
        "vehicles": qs.order_by("registration_no"),
        "q": q,
        "status_active": status,
        "stats": {"total": total, "assigned": assigned, "maintenance": maintenance},
    })

@role_required('admin', 'staff')
def assign_vehicle(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == "POST":
        form = AssignVehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle updated.")
            return redirect("vehicle_list")
    else:
        form = AssignVehicleForm(instance=vehicle)
    return render(request, "vehicles/assign.html", {"form": form, "vehicle": vehicle})

@role_required('admin', 'staff')
def edit_vehicle(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    if request.method == "POST":
        form = VehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            messages.success(request, "Vehicle updated.")
            return redirect("vehicle_list")
    else:
        form = VehicleForm(instance=vehicle)
    return render(request, "vehicles/edit.html", {"form": form, "vehicle": vehicle})

@role_required('admin', 'staff')
def delete_vehicle(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    vehicle.delete()
    messages.success(request, "Vehicle deleted successfully.")
    return redirect("vehicle_list")

@role_required('admin', 'staff', 'driver')
def vehicle_detail(request, pk):
    """
    Admin/Staff can view any vehicle.
    Driver can view only if assigned.
    """
    v = get_object_or_404(Vehicle, pk=pk)
    role = get_user_role(request.user)
    if role == "driver" and v.current_driver_id != request.user.id and not is_app_admin(request.user):
        raise PermissionDenied

    maintenance = v.maintenance_logs.order_by("-date")[:10]
    fuel = v.fuel_logs.order_by("-date")[:10]

    return render(request, "vehicles/detail.html", {
        "vehicle": v,
        "maintenance": maintenance,
        "fuel_logs": fuel,
    })


@role_required('admin')
def maintenance_list(request):
    items = MaintenanceLog.objects.select_related("vehicle").order_by("-date")
    return render(request, "maintenance/list.html", {"items": items})

@role_required('admin')
def fuel_logs(request):
    items = FuelLog.objects.select_related("vehicle").order_by("-date")
    return render(request, "fuel/list.html", {"items": items})


# Staff

@role_required('staff')
def staff_dashboard(request):
    vehicles = Vehicle.objects.all().select_related("current_driver")
    maintenance = MaintenanceLog.objects.select_related("vehicle").order_by("-date")[:10]
    fuel_logs = FuelLog.objects.select_related("vehicle").order_by("-date")[:10]
    return render(request, "staff/staff_dashboard.html", {
        "vehicles": vehicles,
        "maintenance": maintenance,
        "fuel_logs": fuel_logs,
    })

@role_required('staff')
def staff_assign_vehicle(request, pk):
    vehicle = get_object_or_404(Vehicle, pk=pk)
    success = False
    if request.method == "POST":
        form = AssignVehicleForm(request.POST, instance=vehicle)
        if form.is_valid():
            form.save()
            success = True
    else:
        form = AssignVehicleForm(instance=vehicle)
    return render(request, "vehicles/assign.html", {"form": form, "vehicle": vehicle, "success": success})


# Driver

@role_required('driver')
def driver_dashboard(request):
    vehicles_qs = Vehicle.objects.filter(current_driver=request.user)
    maintenance = MaintenanceLog.objects.filter(vehicle__in=vehicles_qs).order_by("-date")[:10]
    fuel_logs = FuelLog.objects.filter(vehicle__in=vehicles_qs).order_by("-date")[:10]

    mform = MaintenanceForm(vehicles_qs=vehicles_qs)
    fform = FuelForm(vehicles_qs=vehicles_qs)

    if request.method == "POST":
        if "maintenance_submit" in request.POST:
            mform = MaintenanceForm(request.POST, vehicles_qs=vehicles_qs)
            if mform.is_valid():
                m = mform.save(commit=False)
                m.created_by = request.user
                m.save()
                messages.success(request, "Maintenance log saved successfully!")
                return redirect("driver_dashboard")

        elif "fuel_submit" in request.POST:
            fform = FuelForm(request.POST, vehicles_qs=vehicles_qs)
            if fform.is_valid():
                f = fform.save(commit=False)
                f.created_by = request.user
                f.save()
                messages.success(request, "Fuel log saved successfully!")
                return redirect("driver_dashboard")

    return render(request, "driver/driver_dashboard.html", {
        "vehicles": vehicles_qs,
        "maintenance": maintenance,
        "fuel_logs": fuel_logs,
        "mform": mform,
        "fform": fform,
    })


# Profile

@login_required(login_url='login')
def profile(request):
    return render(request, "admin/profile.html", {
        "user_obj": request.user,
        "profile": getattr(request.user, "profile", None),
    })




def register_user(request):
    """
    Public registration; creates user with 'staff' role by default.
    Remove from urls.py if you don't need public signup.
    """
    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        email = request.POST.get("email", "")
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")
        if password != confirm_password:
            return render(request, "register.html", {"error": "Passwords do not match."})
        if User.objects.filter(username=username).exists():
            return render(request, "register.html", {"error": "Username already taken."})
        user = User.objects.create_user(username=username, email=email, password=password)
        Profile.objects.get_or_create(user=user, defaults={"role": "staff"})
        return redirect("login")
    return render(request, "register.html")


# Tracking 
@role_required('admin', 'staff')
def vehicle_track_data(request):
    """
    Return JSON for map polling. Skips vehicles with missing lat/lng.
    """
    data = []
    for v in Vehicle.objects.all():
        lat = getattr(v, "latitude", None)
        lng = getattr(v, "longitude", None)
        if lat is None or lng is None:
            continue
        data.append({
            "id": v.id,
            "reg": v.registration_no,
            "make": v.make,
            "model": v.model,
            "status": v.status,
            "driver": getattr(v.current_driver, "username", None),
            "lat": float(lat),
            "lng": float(lng),
            "updated": getattr(v, "last_location_time", None).isoformat() if getattr(v, "last_location_time", None) else None,
        })
    return JsonResponse({"vehicles": data})

@role_required('admin', 'staff')
def update_vehicle_location(request, pk):
    """
    Manual latitude/longitude updater.
    """
    v = get_object_or_404(Vehicle, pk=pk)
    if request.method == "POST":
        form = VehicleLocationForm(request.POST, instance=v)
        if form.is_valid():
            obj = form.save(commit=False)
            if hasattr(obj, "last_location_time"):
                obj.last_location_time = timezone.now()
            obj.save()
            messages.success(request, "Location updated.")
            return redirect("admin_dashboard")
    else:
        form = VehicleLocationForm(instance=v)
    return render(request, "vehicles/update_location.html", {"form": form, "vehicle": v})


def custom_permission_denied_view(request, exception=None):
    return render(request, "403.html", status=403)

handler403 = custom_permission_denied_view
