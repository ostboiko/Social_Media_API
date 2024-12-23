from django.contrib.auth import get_user_model
from django.db.models import Q, Count, Prefetch, Exists, OuterRef
from django.http import HttpResponseRedirect
from django.urls import reverse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    inline_serializer,
)
from rest_framework import viewsets, status, mixins, generics
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from Media.models import Like, Post
from user.models import Follow
from user.serializers import (
    UserInfoSerializer,
    UserInfoListSerializer,
    ManageUserProfileSerializer,
    ProfileImageSerializer,
    UserCreateSerializer,
    UserChangePasswordSerializer,
)


class Pagination(PageNumberPagination):
    page_size = 25
    max_page_size = 100
    page_size_query_param = "page_size"


class UserInfoViewSet(viewsets.ReadOnlyModelViewSet):
    """Endpoint for retrieving basic users' info."""

    permission_classes = (IsAuthenticated,)
    pagination_class = Pagination

    def get_queryset(self):
        queryset = get_user_model().objects.all()

        if self.action == "retrieve":
            user = self.request.user
            retrieved_user = self.kwargs.get("pk")

            posts = Prefetch(
                "posts",
                queryset=Post.objects.filter(is_published=True)
                .annotate(
                    num_likes=Count("likes", distinct=True),
                    num_comments=Count("comments", distinct=True),
                    has_like_from_user=Exists(
                        Like.objects.filter(user=user, post=OuterRef("pk"))
                    ),
                )
                .prefetch_related("images", "hashtags"),
            )
            queryset = queryset.prefetch_related(posts)

            queryset = queryset.annotate(
                is_followed_by_user=Exists(
                    Follow.objects.filter(
                        follower=user, following=retrieved_user
                    )
                ),
                num_followers=Count("followers", distinct=True),
            ).annotate(num_followings=Count("followings", distinct=True))

        if self.action == "list":
            search_string = self.request.query_params.get("search", None)
            if search_string:
                queryset = queryset.filter(
                    Q(username__icontains=search_string)
                    | Q(first_name__icontains=search_string)
                    | Q(last_name__icontains=search_string)
                ).distinct()

        return queryset

    def get_serializer_class(self):
        if self.action in ["list", "followers", "followings"]:
            return UserInfoListSerializer

        return UserInfoSerializer

    def get_serializer_context(self):
        """Extra context provided to the serializer class."""

        context = super().get_serializer_context()

        if self.action == "retrieve":
            context["user"] = self.request.user

        return context

    @action(methods=["GET"], detail=True, url_path="followers")
    def followers(self, request, pk=None):
        """Endpoint for getting a list of user's followers."""
        retrieved_user = self.get_object()

        follow_relations = Follow.objects.filter(following=retrieved_user)
        followers = get_user_model().objects.filter(
            followings__in=follow_relations
        )

        serializer = UserInfoListSerializer(followers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(methods=["GET"], detail=True, url_path="followings")
    def followings(self, request, pk=None):
        """Endpoint for getting a list of user's followings."""
        retrieved_user = self.get_object()

        follow_relations = Follow.objects.filter(follower=retrieved_user)
        followings = get_user_model().objects.filter(
            followers__in=follow_relations
        )

        serializer = UserInfoListSerializer(followings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, url_path="follow_toggle")
    def follow_toggle(self, request, pk=None):
        """Endpoint for following and un-following specific user."""
        retrieved_user = self.get_object()
        active_user = request.user

        is_followed_by_user = Follow.objects.filter(
            follower=active_user, following=retrieved_user
        ).exists()

        if is_followed_by_user:
            follow_relation = Follow.objects.filter(
                follower=active_user, following=retrieved_user
            )
            follow_relation.delete()
        else:
            Follow.objects.create(
                follower=active_user, following=retrieved_user
            )

        return HttpResponseRedirect(
            request.META.get("HTTP_REFERER", retrieved_user.get_absolute_url())
        )

    @extend_schema(
        parameters=[
            OpenApiParameter("id", OpenApiTypes.INT, OpenApiParameter.PATH)
        ]
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(self, request, *args, **kwargs)


class ManageUserProfileViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """Endpoint where logged-in user can manage their personal information."""

    queryset = get_user_model().objects.all()
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user

    def get_serializer_class(self):
        if self.action == "upload_image":
            return ProfileImageSerializer

        if self.action == "change_password":
            return UserChangePasswordSerializer

        return ManageUserProfileSerializer

    @action(methods=["POST"], detail=True, url_path="upload_profile_image")
    def upload_image(self, request, pk=None):
        """Endpoint where logged-in user can upload their new profile image."""

        user = self.get_object()
        serializer = self.get_serializer(user, data=request.data)

        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(methods=["DELETE"], detail=True, url_path="delete_profile_image")
    def delete_image(self, request, pk=None):
        """Endpoint where logged-in user can delete their own profile image."""

        user = self.get_object()
        user.profile_image = None
        user.save()

        return HttpResponseRedirect(
            request.META.get("HTTP_REFERER", reverse("user:manage-detail"))
        )

    @action(methods=["POST"], detail=True, url_path="change_password")
    def change_password(self, request):
        """Endpoint where logged-in user can change their password."""
        user = self.get_object()
        serializer = self.get_serializer(data=request.data)

        serializer.is_valid(raise_exception=True)
        if not user.check_password(serializer.data.get("old_password")):
            return Response(
                {"old_password": ["Wrong password."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.set_password(serializer.data.get("new_password"))
        user.save()

        return Response("Success.", status=status.HTTP_200_OK)


class CreateUserView(generics.CreateAPIView):
    """Endpoint for registering new users."""

    queryset = get_user_model().objects.all()
    serializer_class = UserCreateSerializer
    permission_classes = (AllowAny,)


class CreateTokenView(ObtainAuthToken):
    """Login endpoint."""

    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES


@extend_schema(
    responses={200: inline_serializer(name="LogoutResponse", fields={})}
)
class LogoutAPIView(APIView):
    """Endpoint for invalidating user token."""

    permission_classes = (IsAuthenticated,)

    @staticmethod
    def get(request):
        request.user.auth_token.delete()
        return Response(status=status.HTTP_200_OK)