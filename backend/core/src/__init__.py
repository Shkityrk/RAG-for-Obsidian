__all__ = ["app_object"]


def __getattr__(name: str):
    if name == "app_object":
        from .app import app_object

        return app_object
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

