from django.shortcuts import render, redirect
from .forms import AttendeeForm
from django.http import HttpResponse
from django.utils import timezone
import qrcode
from .models import Attendee
import os
from django.conf import settings  
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import logging

def register(request):
    if request.method == 'POST':
        form = AttendeeForm(request.POST)  
        if form.is_valid():  
            attendee = form.save(commit=False)  
            
            qr_data = f"Name: {attendee.name}, Email: {attendee.email}"  
            qr = qrcode.make(qr_data)

            qr_code_dir = os.path.join(settings.MEDIA_ROOT, 'qr_codes')  
            os.makedirs(qr_code_dir, exist_ok=True) 
            
            qr_code_filename = f'{attendee.name}_qr.png'
            qr_code_path = os.path.join(qr_code_dir, qr_code_filename) 
            qr.save(qr_code_path)

            attendee.qr_code = os.path.join('qr_codes', qr_code_filename) 
            attendee.save()  
            
            return redirect('success', attendee_id=attendee.id) 
    else:
        form = AttendeeForm()  

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
    logging.debug(f'Received attendee_id: {attendee_id}')  
    if attendee_id:
        try:
            attendee = Attendee.objects.get(id=attendee_id)
            attendee.is_present = True  
            attendee.present_time = timezone.now() 
            attendee.save()
            return JsonResponse({'success': True, 'message': 'Attendance marked successfully!'})
        except Attendee.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Attendee not found.'})
    return JsonResponse({'success': False, 'message': 'Invalid request.'})