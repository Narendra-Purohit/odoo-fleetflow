"""FleetFlow – users app URLs."""
from django.urls import path
from apps.users import views

app_name = "users"

urlpatterns = [
    # Auth (public)
    path("login/", views.LoginView.as_view(), name="login"),
    path("logout/", views.LogoutView.as_view(), name="logout"),
    path("register/", views.RegisterView.as_view(), name="register"),

    # OTP password reset (public – 3 steps)
    path("forgot-password/", views.ForgotPasswordView.as_view(), name="forgot_password"),
    path("verify-otp/", views.VerifyOTPView.as_view(), name="verify_otp"),
    path("set-new-password/", views.SetNewPasswordView.as_view(), name="set_new_password"),

    # User management (Manager only)
    path("list/", views.UserListView.as_view(), name="user_list"),
    path("create/", views.UserCreateView.as_view(), name="user_create"),
    path("<int:pk>/edit/", views.UserEditView.as_view(), name="user_edit"),
    path("<int:pk>/delete/", views.UserDeleteView.as_view(), name="user_delete"),

    # Own account
    path("profile/", views.ProfileView.as_view(), name="profile"),
    path("change-password/", views.ChangePasswordView.as_view(), name="change_password"),
]
