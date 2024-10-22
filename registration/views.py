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
from io import BytesIO
from datetime import timedelta

def register(request):
    if request.method == "POST":
        name = request.POST.get('name')
        email = request.POST.get('email')
        department = request.POST.get('department')
        sub_department = request.POST.get('sub_department') 

        attendee = Attendee(
            name=name,
            email=email,
            department=department,
            sub_department=sub_department  
        )
        attendee.save()

        return redirect('success', attendee_id=attendee.id)

    return render(request, 'registration/register.html')

def success(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)

    qr_data = f"http://10.0.0.52:8000/registration/mark_attendance/?attendee_id={attendee.id}"
    qrcode_img = qrcode.make(qr_data)
    canvas = BytesIO()
    qrcode_img.save(canvas, format='PNG')
    canvas.seek(0)

    return HttpResponse(canvas.getvalue(), content_type="image/png")

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