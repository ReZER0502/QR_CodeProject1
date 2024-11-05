from django.shortcuts import render, redirect
from django.utils import timezone
import qrcode
from .models import Attendee
from django.shortcuts import get_object_or_404
from io import BytesIO
from datetime import timedelta
from django.core.files.base import ContentFile
from django.http import HttpResponse
from PIL import Image, ImageDraw, ImageFont
import os
from django.contrib import messages
from .forms import RegistrationForm
from .forms import AdminUserCreationForm
from django.contrib.auth import authenticate,login, get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.conf import settings
from .models import Attendee, AdminWhitelist, AdminRequest
import logging

def approve_admin_request(request, request_id):
    if request.method == 'POST':
        admin_request = get_object_or_404(AdminRequest, id=request_id)
        admin_request.is_approved = True
        admin_request.save()
        messages.success(request, f"Admin request for {admin_request.user.email} has been approved.")
        return redirect('admin_dashboard')

logging.basicConfig(level=logging.DEBUG)

def register_admin(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')

            # EMAIL WHITELISTING DITO. MEANING ONLY AUTHORIZED EMAILS ARE ALLOWED TO REGISTER
            if not AdminWhitelist.objects.filter(email=email).exists():
                messages.error(request, "This email is not authorized to register as an admin.")
                return redirect('register_admin')
            admin_user = form.save()
            if admin_user:
                logging.debug(f"Admin user created with email: {admin_user.email}")
            else:
                logging.error("Admin user creation failed.")
            try:
                admin_request = AdminRequest.objects.create(user=admin_user)
                logging.debug(f"AdminRequest created for user: {admin_user.email}")
            except Exception as e:
                logging.error(f"Error creating AdminRequest: {str(e)}")
            
            messages.success(request, "Admin registered successfully.")
            return redirect('register_admin')
        else:
            logging.error(f"Form is invalid: {form.errors}")
    else:
        form = AdminUserCreationForm()

    return render(request, 'registration/register_admin.html', {'form': form})

def admin_dashboard(request):
    admin_requests = AdminRequest.objects.all()  
    return render(request, 'registration/admin_dashboard.html', {'admin_requests': admin_requests})

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                existing_attendee = Attendee.objects.filter(email=form.cleaned_data['email']).first()
                if existing_attendee:
                    print(f"Existing attendee found: {existing_attendee.id}, email: {existing_attendee.email}")
                    messages.error(request, "This email is already registered.")
                    return render(request, 'registration/register.html', {'form': form})
                attendee = Attendee.objects.create(
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data['email'],
                    department=form.cleaned_data['department'],
                    sub_department=form.cleaned_data['sub_department'],
                )
                qr_data = f"{settings.BASE_URL}/registration/mark_attendance/?attendee_id={attendee.id}"
                qrcode_img = qrcode.make(qr_data)
                canvas = BytesIO()
                qrcode_img.save(canvas, format='PNG')
                canvas.seek(0)
                qr_code_file = ContentFile(canvas.getvalue(), name=f'qr_code_{attendee.first_name}_{attendee.last_name}.png')
                attendee.qr_code.save(f'qr_code_{attendee.id}.png', qr_code_file)
                attendee.save()

                messages.success(request, "Registration Successful!")  
                return redirect('success', attendee_id=attendee.id)

            except Exception as e:
                messages.error(request, "An error occurred while registering. Please try again.")
                print(f"Error: {e}")
                return render(request, 'registration/register.html', {'form': form})

    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {'form': form})

def register_success(request):
    return render(request, 'registration/regiter_success.html')

def success(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)
    return render(request, 'registration/success.html', {'attendee': attendee})

def mark_attendance(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
    
    if request.user.is_authenticated:
        try:
            admin_request = AdminRequest.objects.get(user=request.user)
            if not admin_request.is_approved:
                messages.error(request, "Unauthorized admin!!!!")
                return render(request, 'registration/mark_attendance.html', {
                    'error': 'Unauthorized admin!!!!'
                })
            attendee_id = request.GET.get('attendee_id')
            if attendee_id:
                try:
                    attendee = Attendee.objects.get(id=attendee_id)

                    if attendee.is_present:
                        return render(request, 'res.html', {
                            'success': False,
                            'message': 'Attendee already marked present!'
                        })
                    else:
                        attendee.is_present = True
                        # Cubao_NCR-MANILA TIME INTERVAL
                        attendee.present_time = timezone.now() + timedelta(hours=8)
                        attendee.save()
                    attendee_name = f"{attendee.first_name} {attendee.last_name}"

                    return render(request, 'res.html', {
                        'success': True,
                        'message': 'Attendance marked successfully!',
                        'attendee_name': attendee_name
                    })

                except Attendee.DoesNotExist:
                    return render(request, 'res.html', {
                        'success': False,
                        'message': 'Attendee not found.'
                    })

            return render(request, 'res.html', {
                'success': False,
                'message': 'Invalid request.'
            })

        except AdminRequest.DoesNotExist:
            return render(request, 'registration/mark_attendance.html', {
                'error': 'You need to register as an admin first.'
            })

    return render(request, 'registration/mark_attendance.html', {
        'error': 'Please log in to mark attendance.'
    })

#'C:\Windows\Fonts\ArialNova-Bold.ttf' Pwede natin tong palitan, depende kay sir ron.

def download_attendee_info(request, attendee_id):
    try:
        attendee = Attendee.objects.get(id=attendee_id)
         #Eto yung sa background. Change natin right after implementing the design 
        background_path = os.path.join('C:/xampp/htdocs/test/FINAL/static/img/my_qr.jpg')
        background = Image.open(background_path)
        image_width = 600
        image_height = 800
        background = background.resize((image_width, image_height))
        
        overlay = Image.new('RGBA', (image_width, image_height), (255, 255, 255, 0))  
        draw = ImageDraw.Draw(overlay)

        font_path = os.path.join('C:\Windows\Fonts\ArialNova-Bold.ttf')
        small_font = ImageFont.truetype(font_path, 24)
        department_text = f"Department: {attendee.department}"
        sub_department_text = f"Sub-Department: {attendee.sub_department}"
        
        name_position = (50, 100)
        department_position = (50, 200)
        sub_department_position = (50, 250)
        
        full_name = f"Name: {attendee.first_name} {attendee.last_name}"
        draw.text(name_position, full_name, font=small_font, fill='black')
        draw.text(department_position, department_text, font=small_font, fill='black')
        draw.text(sub_department_position, sub_department_text, font=small_font, fill='black')
        line_position = (50, 300, image_width - 50, 300)
        draw.line(line_position, fill="gray", width=3)
        qr_code_position = (150, 350)  
        qr_code_image = Image.open(attendee.qr_code.path)
        qr_code_image = qr_code_image.resize((300, 300))  
        overlay.paste(qr_code_image, qr_code_position, qr_code_image.convert('RGBA'))
        final_image = Image.alpha_composite(background.convert('RGBA'), overlay)

        response = HttpResponse(content_type='image/png')
        final_image = final_image.convert('RGB')  
        final_image.save(response, 'PNG')
        response['Content-Disposition'] = f'attachment; filename="{attendee.first_name}_{attendee.last_name}_info.png"'

        return response

    except Attendee.DoesNotExist:
        return HttpResponse("Attendee not found", status=404)
    except Exception as e:
        return HttpResponse(f"Error: {str(e)}", status=500)
