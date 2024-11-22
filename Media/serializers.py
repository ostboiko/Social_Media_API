import datetime
from zoneinfo import ZoneInfo

from django.core.exceptions import BadRequest
from django.db import transaction
from django.urls import reverse
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers
from Media.models import HashTag, Post, PostImage, Comment
from social_media_api import settings


def get_full_url(url: str) -> str:
    return f"{settings.BASE_URL}{url}"


class HashtagSerializer(serializers.ModelSerializer):
    class Meta:
        model = HashTag
        fields = ("id", "name")


class HashtagListSerializer(serializers.ModelSerializer):
    detail_url = serializers.SerializerMethodField()

    @staticmethod
    @extend_schema_field(OpenApiTypes.URI_TPL)
    def get_detail_url(instance):
        return get_full_url(instance.get_absolute_url())

    class Meta:
        model = HashTag
        fields = ("id", "name", "detail_url")


class PostSerializer(serializers.ModelSerializer):
    hashtags = HashtagSerializer(many=True, read_only=False, required=False)

    class Meta:
        model = Post
        fields = ("id", "text", "hashtags")

    def create(self, validated_data):
        hashtags_data = validated_data.pop("hashtags", [])
        post = Post.objects.create(**validated_data)

        for hashtag in hashtags_data:
            new_hashtag = HashTag.objects.get_or_create(
                name=dict(hashtag).get("name")
            )
            post.hashtags.add(new_hashtag[0])
        post.save()

        return post

    def update(self, instance, validated_data):
        with transaction.atomic():
            hashtags_data = validated_data.pop("hashtags", [])

            # Updating own fields of Post instance
            for key, value in validated_data.items():
                setattr(instance, key, value)

            # Updating hashtags of posts and removing hashtags without posts
            new_hashtag_names = set(
                [hashtag["name"] for hashtag in hashtags_data]
            )
            old_hashtag_names = set(
                list(instance.hashtags.values_list("name", flat=True))
            )

            hashtags_to_add = list(
                new_hashtag_names.difference(old_hashtag_names)
            )
            hashtags_to_remove = list(
                old_hashtag_names.difference(new_hashtag_names)
            )

            for hashtag in hashtags_to_add:
                new_hashtag = HashTag.objects.get_or_create(name=hashtag)
                instance.hashtags.add(new_hashtag[0])

            for hashtag in hashtags_to_remove:
                old_hashtag = HashTag.objects.get(name=hashtag)
                related_posts = old_hashtag.posts.all().exclude(id=instance.id)
                num_posts = related_posts.count()

                if num_posts == 0:
                    old_hashtag.delete()
                else:
                    instance.hashtags.remove(old_hashtag)

            instance.save()

            return instance


class PostImageListSerializer(serializers.ModelSerializer):
    delete_image_url = serializers.SerializerMethodField()

    @staticmethod
    @extend_schema_field(OpenApiTypes.URI_TPL)
    def get_delete_image_url(instance):
        return get_full_url(
            reverse("feed:post-image-delete", kwargs={"pk": instance.id})
        )

    class Meta:
        model = PostImage
        fields = ("id", "image", "delete_image_url")


class PostListSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(many=False)
    author_url = serializers.SerializerMethodField()
    hashtags = serializers.StringRelatedField(many=True)
    num_likes = serializers.IntegerField()
    num_comments = serializers.IntegerField()
    images = PostImageListSerializer(many=True, read_only=True)
    detail_url = serializers.SerializerMethodField(read_only=True)
    has_like_from_user = serializers.BooleanField()
    like_toggle = serializers.SerializerMethodField()

    @staticmethod
    @extend_schema_field(OpenApiTypes.URI_TPL)
    def get_author_url(instance):
        return get_full_url(instance.author.get_absolute_url())

    @staticmethod
    @extend_schema_field(OpenApiTypes.URI_TPL)
    def get_detail_url(instance):
        return get_full_url(instance.get_absolute_url())

    @staticmethod
    @extend_schema_field(OpenApiTypes.URI_TPL)
    def get_like_toggle(instance):
        return get_full_url(
            reverse("feed:post-like-toggle", kwargs={"pk": instance.id})
        )

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "author_url",
            "text",
            "hashtags",
            "num_likes",
            "num_comments",
            "images",
            "detail_url",
            "has_like_from_user",
            "like_toggle",
        )


class HashtagDetailSerializer(serializers.ModelSerializer):
    posts = PostListSerializer(many=True, read_only=True)

    class Meta:
        model = HashTag
        fields = ("id", "name", "posts")


class PostponedPostListSerializer(serializers.ModelSerializer):
    hashtags = HashtagListSerializer(many=True, read_only=True)
    images = PostImageListSerializer(many=True, read_only=True)
    detail_url = serializers.SerializerMethodField()

    @staticmethod
    @extend_schema_field(OpenApiTypes.URI_TPL)
    def get_detail_url(instance):
        return get_full_url(
            reverse("feed:postponed-post-detail", kwargs={"pk": instance.id})
        )

    class Meta:
        model = Post
        fields = (
            "id",
            "published_at",
            "text",
            "hashtags",
            "images",
            "detail_url",
        )


class PostponedPostDetailSerializer(PostSerializer):
    hashtags = HashtagListSerializer(
        many=True, read_only=False, required=False
    )
    images = PostImageListSerializer(many=True, read_only=True)
    image_upload_url = serializers.SerializerMethodField()

    @staticmethod
    @extend_schema_field(OpenApiTypes.URI_TPL)
    def get_image_upload_url(instance):
        return get_full_url(
            reverse("feed:post-image-upload", kwargs={"pk": instance.id})
        )

    class Meta:
        model = Post
        fields = (
            "id",
            "published_at",
            "text",
            "hashtags",
            "images",
            "image_upload_url",
        )

    def create(self, validated_data):
        time_now = datetime.datetime.now(ZoneInfo("Europe/Berlin"))
        published_at = validated_data["published_at"]

        if published_at > time_now:
            post = super(PostSerializer, self).create(validated_data)

            post.is_published = False
            post.save()

            return post

        else:
            raise BadRequest("Publishing time should be greater than now.")


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()
    author_url = serializers.SerializerMethodField()

    @staticmethod
    @extend_schema_field(OpenApiTypes.URI_TPL)
    def get_author_url(instance):
        return get_full_url(instance.author.get_absolute_url())

    class Meta:
        model = Comment
        fields = ("id", "author", "author_url", "text")


class CommentCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = ("id", "text")


class PostDetailSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(many=False)
    author_url = serializers.SerializerMethodField()
    hashtags = HashtagListSerializer(many=True, read_only=True)
    num_likes = serializers.IntegerField()
    image_upload_url = serializers.SerializerMethodField()
    images = PostImageListSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    has_like_from_user = serializers.BooleanField()
    like_toggle = serializers.SerializerMethodField()
    users_who_liked_url = serializers.SerializerMethodField()

    @staticmethod
    @extend_schema_field(OpenApiTypes.URI_TPL)
    def get_author_url(instance):
        return get_full_url(instance.author.get_absolute_url())

    @staticmethod
    @extend_schema_field(OpenApiTypes.URI_TPL)
    def get_image_upload_url(instance):
        return get_full_url(
            reverse("feed:post-image-upload", kwargs={"pk": instance.id})
        )

    @staticmethod
    @extend_schema_field(OpenApiTypes.URI_TPL)
    def get_like_toggle(instance):
        return get_full_url(
            reverse("feed:post-like-toggle", kwargs={"pk": instance.id})
        )

    @staticmethod
    @extend_schema_field(OpenApiTypes.URI_TPL)
    def get_users_who_liked_url(instance):
        return get_full_url(
            reverse("feed:post-users-who-liked", kwargs={"pk": instance.id})
        )

    class Meta:
        model = Post
        fields = (
            "id",
            "author",
            "author_url",
            "text",
            "hashtags",
            "num_likes",
            "comments",
            "image_upload_url",
            "images",
            "has_like_from_user",
            "like_toggle",
            "users_who_liked_url",
        )


class PostImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostImage
        fields = ("id", "image")