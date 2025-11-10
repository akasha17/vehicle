# vehiapp/urls.py
from django.urls import path
from django.core.exceptions import PermissionDenied
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_user, name='register'),
    path('accounts/login/', views.login_view), 
    path("whoami/", views.whoami, name="whoami"),


    # Admin 
    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/register-staff/', views.register_staff, name='register_staff'),
    path('admin/add-driver/', views.add_driver, name='add_driver'),

    #Vehicle
    path('admin/vehicles/', views.vehicle_list, name='vehicle_list'),
    path('admin/vehicles/add/', views.add_vehicle, name='add_vehicle'),
    path('admin/vehicles/<int:pk>/edit/', views.edit_vehicle, name='edit_vehicle'),
    path('admin/vehicles/<int:pk>/assign/', views.assign_vehicle, name='assign_vehicle'),
    path('admin/vehicles/<int:pk>/delete/', views.delete_vehicle, name='delete_vehicle'),
    path('admin/profiles/<int:pk>/delete/', views.delete_profile, name='delete_profile'),
    path('vehicles/<int:pk>/', views.vehicle_detail, name='vehicle_detail'),
   
    path('admin/vehicles/track-data/', views.vehicle_track_data, name='vehicle_track_data'),
    path('admin/vehicles/<int:pk>/update-location/', views.update_vehicle_location, name='update_vehicle_location'),


    path('admin/profile/', views.profile, name='profile'),
    path('admin/maintenance/', views.maintenance_list, name='maintenance_list'),
    path('admin/fuel/', views.fuel_logs, name='fuel_logs'),
    path('admin/profiles/<int:pk>/delete/', views.delete_profile, name='delete_profile'),

    
    path('staff/dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('staff/vehicles/<int:pk>/assign/', views.staff_assign_vehicle, name='staff_assign_vehicle'),
   
    path('staff/vehicles/add/', views.add_vehicle, name='staff_add_vehicle'),


    path('driver/dashboard/', views.driver_dashboard, name='driver_dashboard'),

   
    path(
        "403-test/",
        lambda request: (_ for _ in ()).throw(PermissionDenied())
    ),
]


handler403 = views.custom_permission_denied_view
