# forms.py
from django import forms
from django.core.exceptions import ValidationError
import re
from .models import Attendee, AdminUser

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
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")

    class Meta:
        model = AdminUser  # Use your custom AdminUser model here
        fields = ['email', 'first_name', 'last_name', 'password', 'confirm_password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")

        if password and confirm_password and password != confirm_password:
            raise forms.ValidationError("Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])  # Hash the password
        if commit:
            user.save()
        return user