"""
FleetFlow – RBAC Permission Mixins & Decorators.

Provides:
- RoleRequiredMixin: CBV mixin that checks user role
- role_required: FBV decorator equivalent
- Permission constants per role

Role hierarchy (broad → narrow):
  ALL_ROLES        – any authenticated user with any role (or no role = read-only access)
  DISPATCHER_ROLES – Manager + Dispatcher (can create/modify trips, fuel logs, etc.)
  SAFETY_ROLES     – Manager + Safety Officer
  FINANCIAL_ROLES  – Manager + Financial Analyst
  MANAGER_ROLES    – Manager only
"""
from functools import wraps
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from apps.users.models import Role


# ── Role permission sets ────────────────────────────────────────────────────
MANAGER_ROLES = {Role.RoleName.MANAGER}

DISPATCHER_ROLES = {
    Role.RoleName.MANAGER,
    Role.RoleName.DISPATCHER,
}

SAFETY_ROLES = {
    Role.RoleName.MANAGER,
    Role.RoleName.SAFETY_OFFICER,
}

FINANCIAL_ANALYST_ROLES = {
    Role.RoleName.MANAGER,
    Role.RoleName.FINANCIAL_ANALYST,
}

ALL_ROLES = {
    Role.RoleName.MANAGER,
    Role.RoleName.DISPATCHER,
    Role.RoleName.SAFETY_OFFICER,
    Role.RoleName.FINANCIAL_ANALYST,
}


class RoleRequiredMixin(LoginRequiredMixin):
    """
    CBV mixin enforcing role-based access.

    Rules:
    - Superusers always pass.
    - If allowed_roles is ALL_ROLES (the default), any authenticated user passes
      regardless of whether they have a role assigned yet. This lets newly
      registered users browse read-only views while waiting for a role assignment.
    - Otherwise the user's role.name must be in allowed_roles.

    Usage:
        class MyView(RoleRequiredMixin, View):
            allowed_roles = DISPATCHER_ROLES
    """

    allowed_roles: set = ALL_ROLES

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        # Superusers bypass all role checks
        if request.user.is_superuser:
            return super().dispatch(request, *args, **kwargs)

        # ALL_ROLES views: any logged-in user is allowed
        if self.allowed_roles == ALL_ROLES:
            return super().dispatch(request, *args, **kwargs)

        # Check the user's assigned role
        user_role = getattr(request.user.role, "name", None)
        if user_role not in self.allowed_roles:
            raise PermissionDenied(
                "You do not have permission to access this page. "
                "Contact your Manager to be assigned the correct role."
            )

        return super().dispatch(request, *args, **kwargs)


def role_required(*roles):
    """
    FBV decorator for role-based access control.

    Usage:
        @role_required(Role.RoleName.MANAGER, Role.RoleName.DISPATCHER)
        def my_view(request): ...
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect("users:login")
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)
            user_role = getattr(request.user.role, "name", None)
            if user_role not in roles:
                raise PermissionDenied(
                    "You do not have the required role for this action."
                )
            return view_func(request, *args, **kwargs)
        return wrapped_view
    return decorator
