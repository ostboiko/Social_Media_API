from rest_framework.permissions import SAFE_METHODS, BasePermission

from Media.models import Post


class IsPostAuthorOrIfAuthenticatedReadOnly(BasePermission):
    """
    The request is authenticated as the object author,
    or is a read-only request for authenticated users.
    """

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return bool(request.user and request.user.is_authenticated)

        obj_type = obj.__class__

        if obj_type == Post:
            return obj.author == request.user

        return obj.post.author == request.user


class IsPostAuthorUser(BasePermission):
    """
    The request is authenticated as the object author.
    """

    def has_object_permission(self, request, view, obj):
        obj_type = obj.__class__

        if obj_type == Post:
            return obj.author == request.user

        return obj.post.author == request.user


class IsAdminOrIfAuthenticatedReadOnly(BasePermission):
    """
    The request is authenticated as an admin user,
    or is a read-only request for authenticated users.
    """

    def has_permission(self, request, view):
        return bool(
            (
                request.method in SAFE_METHODS
                and request.user
                and request.user.is_authenticated
            )
            or (request.user and request.user.is_staff)
        )