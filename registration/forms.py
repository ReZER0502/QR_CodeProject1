# forms.py
from django import forms
from django.core.exceptions import ValidationError
import re
from .models import Attendee, AdminUser, AdminWhitelist

class AddWhitelistForm(forms.Form):
    email = forms.EmailField(label="Email to Whitelist", max_length=100)
class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Attendee  
        fields = ['first_name', 'last_name', 'email', 'department', 'sub_department']

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not re.match("^[a-zA-Z]+$", first_name):
            raise ValidationError('First Name not applicable.')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if not re.match("^[a-zA-Z]+$", last_name):
            raise ValidationError('Last Name not applicable.')
        return last_name

class AdminUserCreationForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}),
        label='Password'
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm Password'}),
        label='Confirm Password'
    )

    class Meta:
        model = AdminUser  # Use your custom AdminUser model here
        fields = ['email', 'first_name', 'last_name', 'password', 'confirm_password']

        # Optionally add custom widgets for other fields
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])  # Hash 
        if commit:
            user.save()
        return user
    
class AdminWhitelistForm(forms.ModelForm):
    class Meta:
        model = AdminWhitelist
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email to whitelist'})
        }