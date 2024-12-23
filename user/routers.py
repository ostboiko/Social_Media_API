from rest_framework.routers import Route, DynamicRoute, SimpleRouter


class CustomDetailRouterWithoutInstancePK(SimpleRouter):
    """
    A router for read-only APIs, which doesn't use trailing slashes.
    """

    routes = [
        Route(
            url=r"^{prefix}/$",
            mapping={
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
            },
            name="{basename}-detail",
            detail=True,
            initkwargs={"suffix": "Detail"},
        ),
        DynamicRoute(
            url=r"^{prefix}/{url_path}/$",
            name="{basename}-{url_name}",
            detail=True,
            initkwargs={},
        ),
    ]
