from django.urls import include, path
from rest_framework import routers

from Media.views import (
    HashTagViewSet,
    PostViewSet,
    ImageDeleteView,
    PostponedPostViewSet,
    PostImageUploadView,
)

router = routers.DefaultRouter()
router.register("hashtags", HashTagViewSet, basename="hashtag")
router.register("posts", PostViewSet, basename="post")
router.register(
    "postponed_posts", PostponedPostViewSet, basename="postponed-post"
)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "post_images/<int:pk>/delete/",
        ImageDeleteView.as_view(),
        name="post-image-delete",
    ),
    path(
        "posts/<int:pk>/upload_image/",
        PostImageUploadView.as_view(),
        name="post-image-upload",
    ),
]

app_name = "Media"
