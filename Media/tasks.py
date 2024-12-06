from social_media_api.celery import app

from Media.models import Post


@app.task
def publish_postponed_post(post_id: int) -> None:
    post = Post.objects.get(id=post_id)
    post.publish()
