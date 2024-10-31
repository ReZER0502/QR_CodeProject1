from django.db import models
import qrcode
from io import BytesIO
from django.contrib.auth.models import  AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.files.base import ContentFile 
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

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

class AdminUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class AdminUser(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    objects = AdminUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']