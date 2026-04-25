from django.urls import include, path


urlpatterns = [
    path("", include("apps.chat.urls")),
]