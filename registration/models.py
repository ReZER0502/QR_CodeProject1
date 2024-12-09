from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_migrate, pre_delete

class AdminUserManager(BaseUserManager):
    def create_user(self, email, first_name, last_name, password=None):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, first_name=first_name, last_name=last_name)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, first_name, last_name, password=None):
        user = self.create_user(email, first_name, last_name, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self._db)
        return user

class AdminUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = AdminUserManager()

    USERNAME_FIELD = 'email'  # Use email as the unique identifier
    REQUIRED_FIELDS = ['first_name', 'last_name']  # Only these fields are required

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

# Signal to prevent permanent admin deletion
def prevent_admin_deletion(sender, instance, **kwargs):
    permanent_admin_email = ["gcagbayani@natcco.coop", "gjhalos@natcco.coop"]
    
    if instance.email == permanent_admin_email:
        raise Exception("The permanent admin user cannot be deleted.")

# Connect the delete signal to prevent the permanent admin deletion
pre_delete.connect(prevent_admin_deletion, sender=AdminUser)

# Admin whitelist model
class AdminWhitelist(models.Model):
    email = models.EmailField(unique=True)
    added_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class Attendee(models.Model):
    first_name = models.CharField(max_length=20)
    last_name = models.CharField(max_length=20, default='N/A')
    email = models.EmailField(max_length=254, unique=True)
    department = models.CharField(max_length=100)
    is_present = models.BooleanField(default=False)
    present_time = models.DateTimeField(null=True, blank=True)
    sub_department = models.CharField(max_length=100, blank=True, null=True)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

@receiver(post_migrate)
def create_permanent_admin(sender, **kwargs):
    #gamit tayo hashmap para makapag store ng permanent admins
    permanent_admins = [
        {
            "email": "gcagbayani@natcco.coop",
            "first_name": "GC",
            "last_name": "Agbayani",
            "password": "gc_agbayaniIControl-DCU2024"
        },
        {
            "email": "gjhalos@natcco.coop", 
            "first_name": "Geronimo",
            "last_name": "Halos",
            "password": "gj_halosIControl-DCU2024"
        }
    ]
    
    for admin in permanent_admins:
        if not AdminUser.objects.filter(email=admin['email']).exists():
            AdminUser.objects.create_superuser(
                email=admin['email'],
                first_name=admin['first_name'],
                last_name=admin['last_name'],
                password=admin['password']
            )
            print(f"Permanent admin user '{admin['email']}' created.")
        else:
            print(f"Permanent admin user '{admin['email']}' already exists.")
        
