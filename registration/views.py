from django.shortcuts import render, redirect
from .forms import AttendeeForm
from django.http import HttpResponse
from django.utils import timezone
import qrcode
from .models import Attendee
import os
from django.conf import settings  
from django.http import JsonResponse

def register(request):
    if request.method == 'POST':
        form = AttendeeForm(request.POST)  # Create a form instance with the posted data
        if form.is_valid():  # Check if the form is valid
            attendee = form.save(commit=False)  # Create attendee instance but don't save yet
            
            # Generate QR code
            qr_data = f"Name: {attendee.name}, Email: {attendee.email}"  # Use data from form
            qr = qrcode.make(qr_data)

            # Ensure the QR code directory exists
            qr_code_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')  # Use MEDIA_ROOT
            os.makedirs(qr_code_dir, exist_ok=True)  # Create the directory if it doesn't exist
            
            # Save the QR code image
            qr_code_filename = f'{attendee.name}_qr.png'
            qr_code_path = os.path.join(qr_code_dir, qr_code_filename)  # Save using name
            qr.save(qr_code_path)

            # Save the relative URL of the QR code in the database
            attendee.qr_code = os.path.join('qr_codes', qr_code_filename)  # Store relative path
            attendee.save()  # Now save the attendee instance to the database
            
            return redirect('success', attendee_id=attendee.id)  # Redirect to success view with attendee ID
    else:
        form = AttendeeForm()  # Create a new form instance for GET requests

    return render(request, 'registration/register.html', {'form': form})

def success(request, attendee_id):
    try:
        attendee = Attendee.objects.get(id=attendee_id)
    except Attendee.DoesNotExist:
        return render(request, 'registration/error.html', {'message': 'Attendee not found!'})

    qr_code_image_path = attendee.qr_code

    return render(request, 'registration/success.html', {
        'attendee': attendee,
        'qr_code_image_path': qr_code_image_path,
    })

def mark_attendance(request):
    attendee_id = request.GET.get('attendee_id')
    if attendee_id:
        try:
            attendee = Attendee.objects.get(id=attendee_id)
            # Update the attendance status
            # Assuming you have an `is_present` field in your model
            attendee.is_present = True  # Set this to True if using an is_present field
            attendee.attendance_time = timezone.now()  # Log the time
            attendee.save()
            return JsonResponse({'success': True, 'message': 'Attendance marked successfully!'})
        except Attendee.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Attendee not found.'})
    return JsonResponse({'success': False, 'message': 'Invalid request.'})