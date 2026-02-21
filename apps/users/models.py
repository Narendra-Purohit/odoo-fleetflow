"""
FleetFlow – Users App Models.

Implements:
- CustomUser: email-based auth, role assignment
- Role: permission grouping (MANAGER / DISPATCHER / SAFETY_OFFICER)
- UserProfile: auxiliary data separated from auth model
"""
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.utils import timezone

from .managers import CustomUserManager


class Role(models.Model):
    """
    Named role that maps to a set of Django permissions.

    Design rationale: Using a separate Role model (instead of abusing
    Django groups directly) gives us a clean domain concept that can
    carry display names, descriptions, and additional metadata.
    """

    class RoleName(models.TextChoices):
        MANAGER = "MANAGER", "Fleet Manager"
        DISPATCHER = "DISPATCHER", "Dispatcher"
        SAFETY_OFFICER = "SAFETY_OFFICER", "Safety Officer"
        FINANCIAL_ANALYST = "FINANCIAL_ANALYST", "Financial Analyst"

    name = models.CharField(
        max_length=20,
        choices=RoleName.choices,
        unique=True,
        help_text="System role controlling permission scope.",
    )
    description = models.TextField(blank=True)

    class Meta:
        verbose_name = "Role"
        verbose_name_plural = "Roles"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.get_name_display()


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """
    Primary authentication model using email as login identifier.

    Design rationale: AbstractBaseUser gives full control over auth fields
    without inheriting unnecessary fields from AbstractUser. Role FK allows
    clean RBAC without duplicating Django group concepts.
    """

    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(max_length=150, unique=True)
    first_name = models.CharField(max_length=60, blank=True)
    last_name = models.CharField(max_length=60, blank=True)
    role = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="users",
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    objects = CustomUserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return f"{self.email} ({self.role})"

    @property
    def full_name(self) -> str:
        """Return display-friendly full name."""
        return f"{self.first_name} {self.last_name}".strip() or self.email

    @property
    def is_manager(self) -> bool:
        return bool(self.role and self.role.name == Role.RoleName.MANAGER)

    @property
    def is_dispatcher(self) -> bool:
        return bool(self.role and self.role.name == Role.RoleName.DISPATCHER)

    @property
    def is_safety_officer(self) -> bool:
        return bool(self.role and self.role.name == Role.RoleName.SAFETY_OFFICER)

    @property
    def is_financial_analyst(self) -> bool:
        return bool(self.role and self.role.name == Role.RoleName.FINANCIAL_ANALYST)


class UserProfile(models.Model):
    """
    Extends CustomUser with non-auth auxiliary information.

    Design rationale: Separation of concerns — auth data stays in CustomUser,
    personal/contact data lives here. Avoids a bloated user model.
    """

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="profile",
    )
    phone = models.CharField(max_length=20, blank=True)
    department = models.CharField(max_length=100, blank=True)
    avatar = models.ImageField(upload_to="avatars/", null=True, blank=True)
    bio = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"

    def __str__(self) -> str:
        return f"Profile({self.user.email})"


class PasswordResetOTP(models.Model):
    """
    Stores a time-limited 6-digit OTP for password reset via email.

    Design:
    - OTP expires after OTP_EXPIRY_MINUTES minutes.
    - is_used prevents replay attacks.
    - Old OTPs for the same user are deleted when a new one is requested.
    """

    OTP_LENGTH = 6
    OTP_EXPIRY_MINUTES = 10

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="password_reset_otps",
    )
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Password Reset OTP"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"OTP for {self.user.email} (used={self.is_used})"

    def is_valid(self) -> bool:
        """Return True if OTP is unused and within the expiry window."""
        import random, string
        from django.utils import timezone
        from datetime import timedelta
        if self.is_used:
            return False
        expiry = self.created_at + timedelta(minutes=self.OTP_EXPIRY_MINUTES)
        return timezone.now() <= expiry

    @classmethod
    def generate_for(cls, user) -> "PasswordResetOTP":
        """
        Delete all existing OTPs for user and create a fresh one.
        Returns the new PasswordResetOTP instance (otp field is the 6-digit code).
        """
        import random
        cls.objects.filter(user=user).delete()
        code = "".join([str(random.randint(0, 9)) for _ in range(cls.OTP_LENGTH)])
        return cls.objects.create(user=user, otp=code)
