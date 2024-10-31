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
from django.contrib.auth import authenticate,login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Attendee

def register_admin(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            form.save()  # Save the admin user
            messages.success(request, "Admin registered successfully.")
            return redirect('register_admin')  # Redirect to the login page
    else:
        form = AdminUserCreationForm()

    return render(request, 'registration/register_admin.html', {'form': form})

def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')
    
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                # Check if the email is already registered
                existing_attendee = Attendee.objects.filter(email=form.cleaned_data['email']).first()
                if existing_attendee:
                    print(f"Existing attendee found: {existing_attendee.id}, email: {existing_attendee.email}")
                    messages.error(request, "This email is already registered.")
                    return render(request, 'registration/register.html', {'form': form})

                # Create the attendee after validating the form
                attendee = Attendee.objects.create(
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data['email'],
                    department=form.cleaned_data['department'],
                    sub_department=form.cleaned_data['sub_department'],
                )

                # Now attendee is defined, you can use it to generate the QR code
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

#time delta is not indicated
def mark_attendance(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)

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
                        attendee.present_time = timezone.now()
                        attendee.save()

                    # Use first_name and last_name instead of name
                    attendee_name = f"{attendee.first_name} {attendee.last_name}"

                    return render(request, 'res.html', {
                        'success': True,
                        'message': 'Attendance marked successfully!',
                        'attendee_name': attendee_name  # Corrected line
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

        else:
            return render(request, 'registration/mark_attendance.html', {
                'error': 'Invalid credentials. Please try again.'
            })

    return render(request, 'registration/mark_attendance.html')


#'C:\Windows\Fonts\ArialNova-Bold.ttf' We can change this

def download_attendee_info(request, attendee_id):
    try:
        attendee = Attendee.objects.get(id=attendee_id)
         #Eto yung sa background. Change natin right after implementing the design 
        background_path = os.path.join('C:/xampp/htdocs/test/QR_CodeProject1/static/img/my_qr.jpg')
        background = Image.open(background_path)
        image_width = 600
        image_height = 800
        background = background.resize((image_width, image_height))
        
        overlay = Image.new('RGBA', (image_width, image_height), (255, 255, 255, 0))  
        draw = ImageDraw.Draw(overlay)

        font_path = os.path.join('C:\Windows\Fonts\ArialNova-Bold.ttf')
        font = ImageFont.truetype(font_path, 36)
        small_font = ImageFont.truetype(font_path, 24)

        first_name = f"Name: {attendee.first_name}"
        last_name = attendee.last_name
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
