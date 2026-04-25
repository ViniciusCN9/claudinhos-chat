from __future__ import annotations

from django import forms

from .services.ollama_service import get_model_choices


class ConversationCreateForm(forms.Form):
    content = forms.CharField(
        max_length=6000,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Envie a primeira mensagem...",
                "autocomplete": "off",
            }
        ),
    )
    model_name = forms.ChoiceField(choices=())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["model_name"].choices = get_model_choices()


class ConversationModelForm(forms.Form):
    model_name = forms.ChoiceField(choices=())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["model_name"].choices = get_model_choices()


class ConversationRenameForm(forms.Form):
    title = forms.CharField(
        max_length=160,
        widget=forms.TextInput(
            attrs={
                "placeholder": "Nome do chat",
            }
        ),
    )


class MessageForm(forms.Form):
    content = forms.CharField(
        max_length=6000,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Digite sua mensagem...",
            }
        ),
    )