from django.shortcuts import render, redirect
from django.utils import timezone
import qrcode
from .models import Attendee
from django.shortcuts import get_object_or_404
from io import BytesIO
from datetime import timedelta
from django.core.files.base import ContentFile
from django.http import HttpResponse, HttpResponseForbidden
from PIL import Image
from django.contrib import messages
from .forms import RegistrationForm
from .forms import AdminUserCreationForm
from django.contrib.auth import authenticate,login
from django.contrib.auth.decorators import login_required
from django.conf import settings
from .models import Attendee, AdminWhitelist, AdminRequest
import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.http import HttpResponseForbidden
from .forms import AdminWhitelistForm
from .models import AdminWhitelist, AdminRequest

def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Check if the email is in the whitelist and approved
        try:
            admin = AdminWhitelist.objects.get(email=email, is_approved=True)
        except AdminWhitelist.DoesNotExist:
            return render(request, 'registration/login.html', {'error': 'This email is not whitelisted or approved.'})

        # Authenticate the user
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)
            return redirect('admin_dashboard')  # Redirect to admin dashboard
        else:
            return render(request, 'registration/login.html', {'error': 'Invalid credentials.'})

    return render(request, 'registration/login.html')

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

            # EMAIL WHITELISTING DITO. MEANING ONLY AUTHORIZED EMAILS ARE ALLOWED TO REGISTER PAG GUSTO MAG PA ADMIN
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

@login_required
def admin_dashboard(request):
    if AdminWhitelist.objects.filter(email=request.user.email, is_approved=True).exists():
        # Handle the form submission for adding a whitelisted email
        if request.method == 'POST':
            form = AdminWhitelistForm(request.POST)
            if form.is_valid():
                email = form.cleaned_data.get('email')

                # Check if the email is already whitelisted
                if AdminWhitelist.objects.filter(email=email).exists():
                    form.add_error('email', 'This email is already whitelisted.')
                else:
                    # Automatically approve the whitelisted email
                    AdminWhitelist.objects.create(email=email, is_approved=True)
                    return redirect('admin_dashboard')
        else:
            form = AdminWhitelistForm()

        # Fetch pending admin requests (this is the original logic)
        admin_requests = AdminRequest.objects.filter(is_approved=False)
        return render(request, 'registration/admin_dashboard.html', {
            'admin_requests': admin_requests,
            'form': form
        })
    else:
        return HttpResponseForbidden('You do not have permission to access this page.')

#register for attendees
def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            try:
                existing_attendee = Attendee.objects.filter(email=form.cleaned_data['email']).first()
                if existing_attendee:
                    messages.error(request, "This email is already registered.")
                    return render(request, 'registration/register.html', {'form': form})

                # Create the attendee record
                attendee = Attendee.objects.create(
                    first_name=form.cleaned_data['first_name'],
                    last_name=form.cleaned_data['last_name'],
                    email=form.cleaned_data['email'],
                    department=form.cleaned_data['department'],
                    sub_department=form.cleaned_data['sub_department'],
                )
                
                # Generate QR code
                qr_data = f"{settings.BASE_URL}/registration/mark_attendance/?attendee_id={attendee.id}"
                qrcode_img = qrcode.make(qr_data)

                # Convert QR code to RGBA to avoid mode conflicts
                qrcode_img = qrcode_img.convert("RGBA")

                # Load the background image
                background = Image.open('C:/xampp/htdocs/test/FINAL/static/img/my_template.jpg')

                # Ensure background is also in RGBA mode
                background = background.convert("RGBA")

                # Resize the QR code to fit the background (adjust sizes as needed)
                qrcode_img = qrcode_img.resize((700, 700))
                background_width, background_height = background.size
                qr_width, qr_height = qrcode_img.size

                # Calculate position to center the QR code
                position = ((background_width - qr_width) // 2, (background_height - qr_height) // 2)

                # Paste the QR code onto the background image (with transparency)
                background.paste(qrcode_img, position, qrcode_img)

                # Save the final image to a BytesIO object
                canvas = BytesIO()
                background.save(canvas, format='PNG')
                canvas.seek(0)
                qr_code_file = ContentFile(canvas.getvalue(), name=f'qr_code_{attendee.first_name}_{attendee.last_name}.png')

                # Save QR code to attendee record
                attendee.qr_code.save(f'qr_code_{attendee.id}.png', qr_code_file)
                attendee.save()

                # Prepare and send the email with the attached QR code
                subject = 'Your Registration QR Code'
                html_message = render_to_string('registration/email_template.html', {'attendee': attendee, 'qr_data': qr_data})
                plain_message = strip_tags(html_message)
                email = EmailMessage(
                    subject,
                    plain_message,
                    to=[attendee.email],
                )
                email.attach(f'qr_code_{attendee.first_name}_{attendee.last_name}.png', canvas.getvalue(), 'image/png')

                email.send()

                messages.success(request, "Registration successful! QR code sent to your email.")
                return redirect('success', attendee_id=attendee.id)

            except Exception as e:
                messages.error(request, "An error occurred while registering. Please try again.")
                print(f"Error: {e}")
                return render(request, 'registration/register.html', {'form': form})
    else:
        form = RegistrationForm()

    return render(request, 'registration/register.html', {'form': form})

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

def download_qr(request, attendee_id):
    attendee = get_object_or_404(Attendee, id=attendee_id)
    if not attendee.qr_code:
        return HttpResponse("QR code not found.", status=404)
    qr_code_file_path = attendee.qr_code.path
    with open(qr_code_file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type="image/png")
        response['Content-Disposition'] = f'attachment; filename="qr_code_{attendee.first_name}_{attendee.last_name}.png"'
        return response