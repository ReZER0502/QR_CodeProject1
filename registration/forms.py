# forms.py
from django import forms
from django.core.exceptions import ValidationError
import re
from .models import Attendee, AdminUser, AdminWhitelist, Event, QRTemplate 
from django import forms
from django.core.exceptions import ValidationError

class AttendeeUploadForm(forms.Form):
    file = forms.FileField() 
class QRTemplateForm(forms.ModelForm):
    event = forms.ModelChoiceField(
        queryset = Event.objects.all(),
        empty_label = "Select an event",
        widget = forms.Select(attrs = {'class': 'form-control'})
    )
    class Meta:
        model = QRTemplate 
        fields = ['event', 'image']

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['name', 'date', 'attendees_count']  
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter event name'}),
            'date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'attendees_count': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter attendees count'}),
        }


class AdminWhitelistForm(forms.ModelForm):
    class Meta:
        model = AdminWhitelist
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email to whitelist'})
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        # Check if the email already exists in the whitelist
        if AdminWhitelist.objects.filter(email=email).exists():
            raise ValidationError("This email is already whitelisted.")
        return email

    def save(self, commit=True):
        # Save the email into the whitelist table
        admin_email = super().save(commit=False)
        if commit:
            admin_email.save()  # Save the whitelist entry
        return admin_email


class RegistrationForm(forms.ModelForm):
    class Meta:
        model = Attendee  
        fields = ['first_name', 'last_name', 'email', 'department', 'sub_department', 'event']
    event = forms.ModelChoiceField(queryset=Event.objects.all(), required=True, label="Event", empty_label="Select Event")
    
   # def clean_email(self):
    #    email = self.cleaned_data.get('email')
     #   if not email.endswith('@natcco.coop'):
      #      raise ValidationError("Only @natcco.coop emails are allowed.")
       # return email

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
        model = AdminUser
        fields = ['email', 'first_name', 'last_name', 'password', 'confirm_password']
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
        user.set_password(self.cleaned_data["password"])  # Hash pass
        if commit:
            user.save()
        return user