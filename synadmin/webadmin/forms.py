from django import forms
from django.core.exceptions import ValidationError
from django.forms import ModelForm

from .models import Tenant, User, Room, Account


class RoomCreateForm(forms.Form):
    room = forms.CharField(label="room")
    room.widget.attrs.update({'class': 'input', 'placeholder': 'Name'})
    public = forms.BooleanField(label="public", required=False)
    encrypted = forms.BooleanField(label="public", required=False)


    def get_validated_data(self): # runs on validation
        data = self.cleaned_data['room']

        if not '!' in data:
            raise ValidationError("Room name must be internal name (starting with !)")

        if not ':' in data:
            raise ValidationError("Room must container Homeserver (:synod.im)")

        return data

class UserCreateForm(forms.Form):
    username = forms.CharField(label="username")
    username.widget.attrs.update({'class': 'input', 'placeholder': 'Name'})
    password = forms.CharField(label="password")
    password.widget.attrs.update({'class': 'input', 'placeholder': 'Name'})
    displayname = forms.CharField(label="displayname")
    displayname.widget.attrs.update({'class': 'input', 'placeholder': 'Name'})

    def get_validated_data(self): # runs on validation
        data = self.cleaned_data['room']

        if not '@' in data:
            raise ValidationError("Username must start with @")

        if not ':' in data:
            raise ValidationError("User must container Homeserver (:synod.im)")

        return data

class UserSetPasswordForm(forms.Form):
    new_password = forms.CharField(label="password")
    new_password.widget.attrs.update({'class': 'input', 'placeholder': 'Neues Passwort'})

    def get_validated_data(self): # runs on validation
        data = self.cleaned_data['room']
        return data

class JoinRoomsForm(forms.Form):
    rooms = forms.MultipleChoiceField(label="rooms", choices = [])

    # We need to overwrite __imit__ in Order to pass the request.user argument
    # Otherwise we won't have Access to User.profile.tenancy.get_rooms()
    # ToDo: Check, weather Django checks if the user has modified the html
    def __init__(self, *args, **kwargs):
        current_user = kwargs.pop('user', None)
        super(JoinRoomsForm, self).__init__(*args, **kwargs)
        rooms = []
        for room in current_user.profile.current_tenancy.get_rooms():
            rooms.append((room.matrix_room_id, room.cached_name))
        self.fields['rooms'] = forms.MultipleChoiceField(
            choices=rooms)  # your query here
        self.fields['rooms'].widget.attrs = {'class': 'select is-multiple is-large'}

    def is_valid_room(self):
        # ToDo Filter out bad charcaters and such...
        data = self.cleaned_data['rooms']
        return data


class SetTenancyForm(forms.Form):
    tenancy = forms.CharField(label="username")
    tenancy.widget.attrs.update({'class': 'input', 'placeholder': 'Name'})

    def get_validated_data(self): # runs on validation
        data = self.cleaned_data['room']
        return data