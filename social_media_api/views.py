from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.reverse import reverse


class ApiRootView(GenericAPIView):
    permission_classes = (IsAuthenticated,)

    @extend_schema(
        responses={
            200: inline_serializer(
                name="ApiRootResponse",
                fields={
                    "Auth endpoints": serializers.URLField(),
                    "Managing own profile endpoints": serializers.URLField(),
                    "Retrieving users and posts endpoints": serializers.URLField(),
                },
            )
        }
    )
    def get(self, request, format=None):
        return Response(
            {
                "Auth endpoints": {
                    "register": reverse(
                        "user:register", request=request, format=format
                    ),
                    "login": reverse(
                        "user:login", request=request, format=format
                    ),
                    "logout": reverse(
                        "user:logout", request=request, format=format
                    ),
                },
                "Managing own profile endpoints": {
                    "view profile and posts": reverse(
                        "user:user-detail",
                        request=request,
                        format=format,
                        kwargs={"pk": request.user.id},
                    ),
                    "manage profile": reverse(
                        "user:manage-detail", request=request, format=format
                    ),
                    "upload_profile_image": reverse(
                        "user:manage-upload-image",
                        request=request,
                        format=format,
                    ),
                    "change_password": reverse(
                        "user:manage-change-password",
                        request=request,
                        format=format,
                    ),
                    "create post": reverse(
                        "feed:post-list", request=request, format=format
                    ),
                },
                "Retrieving users and posts endpoints": {
                    "users list": reverse(
                        "user:user-list", request=request, format=format
                    ),
                    "posts of users you follow": reverse(
                        "feed:post-followed-authors-posts",
                        request=request,
                        format=format,
                    ),
                    "posts that you liked": reverse(
                        "feed:post-liked-posts", request=request, format=format
                    ),
                    "hashtags list": reverse(
                        "feed:hashtag-list", request=request, format=format
                    ),
                    "your postponed posts": reverse(
                        "feed:postponed-post-list",
                        request=request,
                        format=format,
                    ),
                },
            }
        )