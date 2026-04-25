from django.urls import path

from . import views


app_name = "chat"

urlpatterns = [
    path("", views.home, name="home"),
    path("conversations/", views.conversation_list_create, name="conversation_list_create"),
    path("conversations/<uuid:conversation_id>/", views.conversation_detail, name="conversation_detail"),
    path(
        "conversations/<uuid:conversation_id>/title/",
        views.conversation_title_update,
        name="conversation_title_update",
    ),
    path(
        "conversations/<uuid:conversation_id>/model/",
        views.conversation_model_update,
        name="conversation_model_update",
    ),
    path(
        "conversations/<uuid:conversation_id>/messages/",
        views.message_create,
        name="message_create",
    ),
    path("models/", views.models_list, name="models_list"),
    path("health/", views.health_check, name="health_check"),
]