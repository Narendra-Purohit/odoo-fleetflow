"""
FleetFlow – Users App Views.

Auth flows:
- Login / Logout
- Register (public self-registration, no role — manager assigns later)
- ForgotPasswordView   → step 1: enter email → OTP sent
- VerifyOTPView        → step 2: enter 6-digit OTP from email
- SetNewPasswordView   → step 3: enter + confirm new password

User management (Manager only):
- UserListView / UserCreateView / UserEditView / UserDeleteView

Own account:
- ProfileView / ChangePasswordView
"""
import logging
from django.contrib.auth import login, logout, update_session_auth_hash, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings

from apps.users.forms import (
    LoginForm, RegisterForm, UserCreateForm, UserEditForm,
    ForgotPasswordForm, OTPVerificationForm, SetNewPasswordForm,
    FleetPasswordChangeForm, UserProfileForm,
)
from apps.users.models import UserProfile, Role, PasswordResetOTP
from apps.users.permissions import RoleRequiredMixin, MANAGER_ROLES

User = get_user_model()
logger = logging.getLogger(__name__)


# ── Auth ──────────────────────────────────────────────────────────────────────

class LoginView(View):
    template_name = "users/login.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("analytics:dashboard")
        return render(request, self.template_name, {"form": LoginForm()})

    def post(self, request):
        form = LoginForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.full_name}!")
            return redirect(request.GET.get("next", "analytics:dashboard"))
        return render(request, self.template_name, {"form": form})


class LogoutView(View):
    def post(self, request):
        logout(request)
        messages.info(request, "You have been signed out.")
        return redirect("users:login")


class RegisterView(View):
    """
    Public self-registration.
    New users create an account without a role — a Manager assigns roles later
    via the User Management section.
    """
    template_name = "users/register.html"

    def get(self, request):
        if request.user.is_authenticated:
            return redirect("analytics:dashboard")
        return render(request, self.template_name, {"form": RegisterForm()})

    def post(self, request):
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            login(request, user)
            messages.success(
                request,
                f"Welcome to FleetFlow, {user.first_name or user.username}! "
                "Your account is active. A Manager will assign your role shortly."
            )
            return redirect("analytics:dashboard")
        return render(request, self.template_name, {"form": form})


# ── OTP Password Reset (3-step flow) ──────────────────────────────────────────

class ForgotPasswordView(View):
    """Step 1: User enters their email. We generate an OTP and email it."""
    template_name = "users/forgot_password.html"

    def get(self, request):
        return render(request, self.template_name, {"form": ForgotPasswordForm()})

    def post(self, request):
        form = ForgotPasswordForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data["email"]
            user = User.objects.get(email__iexact=email)
            otp_obj = PasswordResetOTP.generate_for(user)

            # Send OTP email
            try:
                send_mail(
                    subject="FleetFlow – Password Reset OTP",
                    message=(
                        f"Hello {user.first_name or user.username},\n\n"
                        f"Your one-time password (OTP) for resetting your FleetFlow password is:\n\n"
                        f"  {otp_obj.otp}\n\n"
                        f"This OTP is valid for {PasswordResetOTP.OTP_EXPIRY_MINUTES} minutes.\n"
                        "Do not share it with anyone.\n\n"
                        "If you did not request this, please ignore this email.\n\n"
                        "– The FleetFlow Team"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )
                messages.success(
                    request,
                    f"A 6-digit OTP has been sent to {email}. Check your inbox (and spam folder)."
                )
            except Exception as exc:
                logger.error("OTP email failed for %s: %s", email, exc)
                messages.error(request, "Failed to send OTP email. Please try again later.")
                return render(request, self.template_name, {"form": form})

            # Store email in session for next steps
            request.session["otp_reset_email"] = email
            return redirect("users:verify_otp")
        return render(request, self.template_name, {"form": form})


class VerifyOTPView(View):
    """Step 2: User enters the 6-digit OTP from their email."""
    template_name = "users/verify_otp.html"

    def _get_email(self, request):
        return request.session.get("otp_reset_email")

    def get(self, request):
        if not self._get_email(request):
            messages.warning(request, "Please start the password reset process first.")
            return redirect("users:forgot_password")
        return render(request, self.template_name, {"form": OTPVerificationForm()})

    def post(self, request):
        email = self._get_email(request)
        if not email:
            return redirect("users:forgot_password")

        form = OTPVerificationForm(request.POST)
        if form.is_valid():
            entered_otp = form.cleaned_data["otp"]
            try:
                user = User.objects.get(email__iexact=email)
                otp_obj = PasswordResetOTP.objects.filter(user=user, otp=entered_otp).first()
                if otp_obj and otp_obj.is_valid():
                    otp_obj.is_used = True
                    otp_obj.save()
                    request.session["otp_reset_verified_uid"] = user.pk
                    messages.success(request, "OTP verified! Please set your new password.")
                    return redirect("users:set_new_password")
                else:
                    messages.error(request, "Invalid or expired OTP. Please try again.")
            except User.DoesNotExist:
                messages.error(request, "Account not found.")
        return render(request, self.template_name, {"form": form})


class SetNewPasswordView(View):
    """Step 3: User enters and confirms their new password."""
    template_name = "users/set_new_password.html"

    def _get_user(self, request):
        uid = request.session.get("otp_reset_verified_uid")
        if uid:
            try:
                return User.objects.get(pk=uid)
            except User.DoesNotExist:
                pass
        return None

    def get(self, request):
        user = self._get_user(request)
        if not user:
            messages.warning(request, "Session expired. Please start again.")
            return redirect("users:forgot_password")
        return render(request, self.template_name, {"form": SetNewPasswordForm(user=user)})

    def post(self, request):
        user = self._get_user(request)
        if not user:
            return redirect("users:forgot_password")

        form = SetNewPasswordForm(user=user, data=request.POST)
        if form.is_valid():
            form.save()
            # Clear session keys
            request.session.pop("otp_reset_email", None)
            request.session.pop("otp_reset_verified_uid", None)
            messages.success(request, "Password reset successfully! You can now log in.")
            return redirect("users:login")
        return render(request, self.template_name, {"form": form})


# ── User Management (Manager only) ───────────────────────────────────────────

class UserListView(RoleRequiredMixin, View):
    template_name = "users/user_list.html"
    allowed_roles = MANAGER_ROLES

    def get(self, request):
        users = User.objects.select_related("role", "profile").all()
        return render(request, self.template_name, {"users": users})


class UserCreateView(RoleRequiredMixin, View):
    template_name = "users/user_form.html"
    allowed_roles = MANAGER_ROLES

    def get(self, request):
        return render(request, self.template_name, {"form": UserCreateForm(), "action": "Create"})

    def post(self, request):
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserProfile.objects.get_or_create(user=user)
            messages.success(request, f"User '{user.email}' created.")
            return redirect("users:user_list")
        return render(request, self.template_name, {"form": form, "action": "Create"})


class UserEditView(RoleRequiredMixin, View):
    template_name = "users/user_form.html"
    allowed_roles = MANAGER_ROLES

    def get(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        return render(request, self.template_name, {
            "form": UserEditForm(instance=target),
            "action": "Edit",
            "target_user": target,
        })

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        form = UserEditForm(request.POST, instance=target)
        if form.is_valid():
            form.save()
            messages.success(request, f"User '{target.email}' updated.")
            return redirect("users:user_list")
        return render(request, self.template_name, {
            "form": form,
            "action": "Edit",
            "target_user": target,
        })


class UserDeleteView(RoleRequiredMixin, View):
    """Manager can delete a user (soft-delete: deactivate OR hard-delete)."""
    allowed_roles = MANAGER_ROLES

    def post(self, request, pk):
        target = get_object_or_404(User, pk=pk)
        if target == request.user:
            messages.error(request, "You cannot delete your own account.")
            return redirect("users:user_list")
        if target.is_superuser:
            messages.error(request, "Superuser accounts cannot be deleted here.")
            return redirect("users:user_list")
        email = target.email
        target.delete()
        messages.success(request, f"User '{email}' has been permanently removed.")
        return redirect("users:user_list")


# ── Own Account ────────────────────────────────────────────────────────────────

class ProfileView(LoginRequiredMixin, View):
    template_name = "users/profile.html"

    def get(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        return render(request, self.template_name, {"profile_form": UserProfileForm(instance=profile)})

    def post(self, request):
        profile, _ = UserProfile.objects.get_or_create(user=request.user)
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully.")
        return render(request, self.template_name, {"profile_form": form})


class ChangePasswordView(LoginRequiredMixin, View):
    template_name = "users/change_password.html"

    def get(self, request):
        return render(request, self.template_name, {"form": FleetPasswordChangeForm(user=request.user)})

    def post(self, request):
        form = FleetPasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password changed successfully.")
            return redirect("users:profile")
        return render(request, self.template_name, {"form": form})
