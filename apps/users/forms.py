"""
FleetFlow – Users App Forms.

Includes:
- LoginForm: email-based authentication
- RegisterForm: public self-registration (no role — assigned by manager post-registration)
- UserCreateForm: manager creates user with role assignment
- UserEditForm: manager edits existing user (role, active status)
- ForgotPasswordForm: step 1 — enter email to receive OTP
- OTPVerificationForm: step 2 — enter 6-digit OTP
- SetNewPasswordForm: step 3 — enter and confirm new password
- FleetPasswordChangeForm: authenticated user changes own password
- UserProfileForm: user updates auxiliary profile info
"""
from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, SetPasswordForm
from django.contrib.auth import get_user_model

from apps.users.models import UserProfile, Role

User = get_user_model()


# ── Authentication ─────────────────────────────────────────────────────────────

class LoginForm(AuthenticationForm):
    """Styled login form using email as identifier."""
    username = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={"placeholder": "you@fleetflow.com", "autofocus": True}),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "••••••••"}),
    )


# ── Public Registration ────────────────────────────────────────────────────────

class RegisterForm(forms.ModelForm):
    """
    Public self-registration form.

    New users register without a role — a Manager assigns roles later.
    Account starts as active so the user can log in immediately.
    """
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Min. 8 characters"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Repeat password"}),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "username", "role"]
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last name"}),
            "email": forms.EmailInput(attrs={"placeholder": "Work email address"}),
            "username": forms.TextInput(attrs={"placeholder": "Short username (e.g. jdoe)"}),
        }
        help_texts = {}

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        if p1 and len(p1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        user.set_password(self.cleaned_data["password1"])
        user.is_active = True
        if commit:
            user.save()
        return user


# ── Manager User Management ────────────────────────────────────────────────────

class UserCreateForm(forms.ModelForm):
    """Manager form to create a new system user with role assignment."""
    password1 = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Min. 8 characters"}),
    )
    password2 = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Repeat password"}),
    )

    class Meta:
        model = User
        fields = ["email", "username", "first_name", "last_name", "role"]

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Passwords do not match.")
        if p1 and len(p1) < 8:
            raise forms.ValidationError("Password must be at least 8 characters.")
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    """Manager form to edit an existing user: name, role, and active status."""
    class Meta:
        model = User
        fields = ["first_name", "last_name", "role", "is_active"]
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last name"}),
        }
        labels = {"is_active": "Account Active"}
        help_texts = {
            "is_active": "Uncheck to deactivate this user without deleting them.",
        }


# ── OTP Password Reset (3-step flow) ──────────────────────────────────────────

class ForgotPasswordForm(forms.Form):
    """Step 1: User provides their registered email."""
    email = forms.EmailField(
        label="Registered Email",
        widget=forms.EmailInput(attrs={"placeholder": "you@fleetflow.com", "autofocus": True}),
    )

    def clean_email(self):
        email = self.cleaned_data.get("email", "").lower()
        if not User.objects.filter(email__iexact=email, is_active=True).exists():
            raise forms.ValidationError("No active account found with this email address.")
        return email


class OTPVerificationForm(forms.Form):
    """Step 2: User enters the 6-digit OTP sent to their email."""
    otp = forms.CharField(
        label="One-Time Password",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            "placeholder": "6-digit code",
            "autofocus": True,
            "inputmode": "numeric",
            "autocomplete": "one-time-code",
            "style": "letter-spacing:0.3em;font-size:1.3rem;text-align:center;",
        }),
    )

    def clean_otp(self):
        return self.cleaned_data.get("otp", "").strip()


class SetNewPasswordForm(SetPasswordForm):
    """Step 3: User sets a new password after OTP verification."""
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={"placeholder": "New password (min. 8 chars)", "autofocus": True}),
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Repeat new password"}),
    )


# ── Own Account ────────────────────────────────────────────────────────────────

class FleetPasswordChangeForm(PasswordChangeForm):
    """Styled wrapper around Django's PasswordChangeForm."""
    old_password = forms.CharField(
        label="Current Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Current password", "autofocus": True}),
    )
    new_password1 = forms.CharField(
        label="New Password",
        widget=forms.PasswordInput(attrs={"placeholder": "New password (min. 8 chars)"}),
    )
    new_password2 = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={"placeholder": "Repeat new password"}),
    )


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile auxiliary data."""
    class Meta:
        model = UserProfile
        fields = ["phone", "department", "avatar", "bio"]
        widgets = {
            "bio": forms.Textarea(attrs={"rows": 3}),
            "phone": forms.TextInput(attrs={"placeholder": "+91 98765 43210"}),
            "department": forms.TextInput(attrs={"placeholder": "e.g. Operations"}),
        }
