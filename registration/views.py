from django.shortcuts import render, redirect
from django.utils import timezone
import qrcode
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
from .models import Attendee, AdminWhitelist
import logging
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from .forms import AdminWhitelistForm
from django.contrib.messages import get_messages
import os
import csv
from django.http import HttpResponseRedirect
from django.http import JsonResponse
from .models import Attendee

def reset_attendance(request):
    if request.method == 'POST':
        # Update all attendees to reset their attendance
        Attendee.objects.update(is_present=False, present_time=None)
        
        # Display success message
        messages.success(request, "Attendance has been reset for all attendees.")
        
        # Redirect back to the admin dashboard (or wherever appropriate)
        return redirect('admin_dashboard') 
    
#Live monitoring function para di na kailangan refresh
@login_required
def get_attendees_status(request):
    attendees = Attendee.objects.all()
    data = [{
        'first_name': attendee.first_name,
        'last_name': attendee.last_name,
        'is_present': attendee.is_present  # True/False value
    } for attendee in attendees]

    return JsonResponse({'attendees': data})


def admin_login(request):
    permanent_admin_emails = ["gcagbayani@natcco.coop", "gjhalos@natcco.coop"]  # Hardcoded permanent admins

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Check if the email belongs to a permanent admin
        if email in permanent_admin_emails:
            user = authenticate(request, username=email, password=password)
            if user is not None:
                login(request, user)
                return redirect('admin_dashboard')  # Redirect to the admin dashboard
            else:
                return render(request, 'registration/login.html', {'error': 'Invalid credentials.'})

        # For non-permanent admins, deny access to the dashboard
        return render(request, 'registration/login.html', {'error': 'Restricted Area!'})

    return render(request, 'registration/login.html')

logging.basicConfig(level=logging.DEBUG)
def register_admin(request):
    if request.method == 'POST':
        form = AdminUserCreationForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')

            # Check whitelist
            if not AdminWhitelist.objects.filter(email=email).exists():
                messages.error(request, "This email is not authorized to register as an admin.")
                return redirect('register_admin')
            
            admin_user = form.save()
            if admin_user:
                logging.debug(f"Admin user created with email: {admin_user.email}")
            else:
                logging.error("Admin user creation failed.")
            
            messages.success(request, "Admin registered successfully.")
            return redirect('register_admin')
        else:
            logging.error(f"Form is invalid: {form.errors}")
    else:
        form = AdminUserCreationForm()

    # Get all messages (errors/success) to pass them to the template
    storage = get_messages(request)
    messages_list = [msg.message for msg in storage]

    return render(request, 'registration/register_admin.html', {
        'form': form,
        'messages': messages_list
    })

# Define permanent admin emails as a constant
PERMANENT_ADMIN_EMAILS = ["gcagbayani@natcco.coop", "gjhalos@natcco.coop"]

@login_required
def admin_dashboard(request):
    # Restrict access to permanent admins only
    if request.user.email not in PERMANENT_ADMIN_EMAILS:
        return HttpResponseForbidden('You do not have permission to access this page.')

    # Handle form submission for adding local admins
    if request.method == 'POST':
        form = AdminWhitelistForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')

            # Add email to the whitelist if not already present
            _, created = AdminWhitelist.objects.get_or_create(email=email)
            if created:
                messages.success(request, f"{email} has been whitelisted.")
                return redirect('admin_dashboard')  # Prevent resubmission on refresh
            else:
                form.add_error('email', 'This email is already whitelisted.')
    else:
        form = AdminWhitelistForm()

    # Fetch all whitelisted emails to display in the dashboard
    whitelisted_emails = AdminWhitelist.objects.all()
    attendees = Attendee.objects.all()

    return render(request, 'registration/admin_dashboard.html', {
        'form': form,
        'whitelisted_emails': whitelisted_emails,
        'attendees': attendees,
    })
    
@login_required
def download_attendees_csv(request):
    # Restrict to permanent admins or users with the necessary permissions
    if request.user.email not in PERMANENT_ADMIN_EMAILS:
        return HttpResponseForbidden("You do not have permission to perform this action.")

    # Create the HttpResponse object with the appropriate CSV header
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="attendees.csv"'

    writer = csv.writer(response)
    # Write the header row
    writer.writerow(['First Name', 'Last Name', 'Email', 'Status'])

    # Query all attendees and write their data
    attendees = Attendee.objects.all()
    for attendee in attendees:
        writer.writerow([
            attendee.first_name,
            attendee.last_name,
            attendee.email,
            'Present' if attendee.is_present else 'Absent'
        ])

    return response


def edit_user_profile(request):
    if request.user.username == "permanentadmin":
        return HttpResponseForbidden("You cannot modify the permanent admin user.")

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

                background_path = os.path.join(settings.BASE_DIR, 'staticfiles', 'img', 'my_template.jpg')
                background = Image.open(background_path)
            
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
    # Handle login if a user is not logged in
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)
        if user is not None:
            login(request, user)

    if request.user.is_authenticated:
        # Check if the logged-in user is the permanent admin
        permanent_admin_email = ["gcagbayani@natcco.coop", "gjhalos@natcco.coop"]
        if request.user.email in permanent_admin_email:
            # Skip whitelist checks for the permanent admin
            return handle_attendance_logic(request)

        # Check if the user is in the whitelist
        if AdminWhitelist.objects.filter(email=request.user.email).exists():
            return handle_attendance_logic(request)

        # If not whitelisted, show an error message
        messages.error(request, "You are not authorized to mark attendance.")
        return render(request, 'registration/mark_attendance.html', {
            'error': 'You are not authorized to mark attendance.'
        })

    return render(request, 'registration/mark_attendance.html', {
        'error': 'Please log in to mark attendance.'
    })


def handle_attendance_logic(request):
    # Process the attendance logic
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
                # Mark the attendee as present
                attendee.is_present = True
                attendee.present_time = timezone.now() + timedelta(hours=8)  #Cubao Manila Timezone
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