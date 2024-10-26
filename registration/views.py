from django.shortcuts import render, redirect
from django.utils import timezone
import qrcode
from .models import Attendee
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
import logging
from io import BytesIO
from datetime import timedelta
from django.core.files.base import ContentFile

def register(request):
    if request.method == 'POST':
        # Create the attendee object
        attendee = Attendee.objects.create(
            name=request.POST['name'],
            email=request.POST['email'],
            department=request.POST['department'],
            sub_department=request.POST['sub_department'],
        )
        attendee.save()
        # Generate QR code
        qr_data = f"http://10.0.0.52:8000/registration/mark_attendance/?attendee_id={attendee.id}"
        qrcode_img = qrcode.make(qr_data)
        canvas = BytesIO()
        qrcode_img.save(canvas, format='PNG')
        canvas.seek(0)
        
        # Create ContentFile for QR code
        qr_code_file = ContentFile(canvas.getvalue(), name=f'qr_code_{attendee.id}.png')
        attendee.qr_code.save(f'qr_code_{attendee.id}.png', qr_code_file)  # Save QR code to attendee model
        attendee.save() 

        # Redirect to the success view with the attendee_id
        return redirect('success', attendee_id=attendee.id)

    return render(request, 'registration/register.html')

def success(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)
    return render(request, 'registration/success.html', {'attendee': attendee})

def mark_attendance(request):
    attendee_id = request.GET.get('attendee_id')
    logging.debug(f'Received attendee_id: {attendee_id}')  
    if attendee_id:
        try:
            attendee = Attendee.objects.get(id=attendee_id)
            attendee.is_present = True  
            utc_now = timezone.now()
            manila_cubao_time = utc_now + timedelta(hours=8)
            attendee.present_time = manila_cubao_time 
            attendee.save()
            return JsonResponse({'success': True, 'message': 'Attendance marked successfully!'})
        except Attendee.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Attendee not found.'})
    return JsonResponse({'success': False, 'message': 'Invalid request.'})