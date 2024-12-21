import os
import uuid

from django.contrib.auth import get_user_model
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    """Define a model manager for user model with email as authentication field."""

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError("The given email must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user with the given email and password."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        """Create and save a SuperUser with the given email and password."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


def profile_image_file_path(instance, filename) -> str:
    _, extension = filename.split(".")

    filename = f"{slugify(instance.username)}-{uuid.uuid4()}.{extension}"

    return os.path.join("uploads/profile_images/", filename)


class User(AbstractUser):
    username_validator = UnicodeUsernameValidator()

    email = models.EmailField(_("email address"), unique=True)
    bio = models.CharField(max_length=150, blank=True)
    username = models.CharField(
        _("username"),
        max_length=150,
        unique=True,
        null=True,
        blank=True,
        help_text=_(
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        ),
        validators=[username_validator],
        error_messages={
            "unique": _("A user with that username already exists."),
        },
    )
    profile_image = models.ImageField(
        blank=True, null=True, upload_to=profile_image_file_path
    )

    def __str__(self):
        return self.get_full_name()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []
    objects = UserManager()

    def get_absolute_url(self):
        return reverse("user:user-detail", kwargs={"pk": self.id})


class Follow(models.Model):
    follower = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="followings"
    )
    following = models.ForeignKey(
        get_user_model(), on_delete=models.CASCADE, related_name="followers"
    )

    class Meta:
        unique_together = ("follower", "following")
