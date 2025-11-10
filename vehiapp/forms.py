from django import forms
from django.contrib.auth.models import User
from .models import Profile, Vehicle

class CreateUserForm(forms.Form):
    username = forms.CharField(max_length=150, required=True)
    email = forms.EmailField(required=False)
    password = forms.CharField(widget=forms.PasswordInput, required=True)
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES, initial='staff')

class StaffProfileForm(forms.ModelForm):
    """Extra profile fields for staff (phone, address) — if you have these in Profile extend accordingly."""
    class Meta:
        model = Profile
        fields = ['role']  # add other profile fields if present

class DriverForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['role']  # driver-specific profile fields — keep role so we can set it

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['registration_no', 'make', 'model', 'year', 'status', 'current_driver']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # restrict current_driver choices to Users who have Profile.role == 'driver'
        driver_qs = User.objects.filter(profile__role='driver')
        self.fields['current_driver'].queryset = driver_qs
        self.fields['current_driver'].required = False
