from django.core import serializers
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound
import requests

from .models import Adminaccount, Tenant, Account, Room
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .forms import JoinRoomsForm, RoomCreateForm, UserCreateForm, UserSetPasswordForm
from .models import UserSyncError

from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse
from functools import wraps


def handle_tenancy_permission_errors(function):
    @wraps(function)
    def wrapper(request, *args, **kwargs):
        try:
            return function(request, *args, **kwargs)
        except PermissionError as e:
            messages.error(request, "Du hast keine Berechtigungen, um auf diese Ressource zuzugreifen")
            return render(request, 'webadmin/welcome.html')
    return wrapper

def welcome(request):
    return render(request, 'webadmin/welcome.html')

@login_required
def sync(request):
    current_user = request.user
    tenancy = current_user.profile.current_tenancy

    for room in tenancy.get_rooms():
        room.fetch_details()
    messages.info(request, "Räume synchronisiert")
    for account in tenancy.get_accounts():
        account.pull_details()
    messages.info(request, "Accounts synchronisiert")

    return render(request, 'webadmin/welcome.html')

    return HttpResponse(str(output))

@login_required
def user_list(request):
    return render(request, 'webadmin/user_list.html', {'users': request.user.profile.current_tenancy.get_accounts() })

@login_required
def room_list(request):
    return render(request, 'webadmin/room_list.html', {'rooms': request.user.profile.current_tenancy.get_rooms()})

@login_required
@handle_tenancy_permission_errors
def room_details(request, matrix_room_id):
    return render(request,
                  'webadmin/room_details_room.html',
                  {'room_details': request.user.profile.current_tenancy.fetch_room_details(matrix_room_id=matrix_room_id)})

@login_required
@handle_tenancy_permission_errors
def room_users(request, matrix_room_id):
    return render(request,
                  'webadmin/room_details_users.html',
                  {'room_users': request.user.profile.current_tenancy.fetch_room_users(matrix_room_id=matrix_room_id),
                   'room_id': matrix_room_id})

@login_required
@handle_tenancy_permission_errors
def room_powerlevel(request, matrix_room_id, matrix_user_id):
    result = request.user.profile.current_tenancy.promote_user_to_admin(matrix_room_id=matrix_room_id,
                                                                matrix_user_id=matrix_user_id)
    if (result):
        messages.success(request, f"Der Benutzer '{matrix_user_id}' ist nun Admin")
    else:
        messages.error(request, f"Das Setzen der Berechtigung für '{matrix_user_id}' schlug fehl")

    return redirect(room_users, matrix_room_id=matrix_room_id)
    return render(request,
                  'webadmin/room_details_users.html',
                  {'room_users': request.user.profile.current_tenancy.fetch_room_users(matrix_room_id=matrix_room_id),
                   'room_id': matrix_room_id})



@login_required
@handle_tenancy_permission_errors
def user_details(request, matrix_user_id):
    model = request.user.profile.current_tenancy.fetch_users_details(matrix_user_id=matrix_user_id)
    # Just dump everything for now...
    data = [x for x in model.__dict__.items() if not x[0].startswith('_')]
    return render(request,
                      'webadmin/user_details.html',
                      {'user_details': data})

@login_required
def user_create(request):
    if request.method == 'POST': # bound form / data
        form = UserCreateForm(request.POST)
        if form.is_valid(): ## returns true if and places data in cleaned_data attribute
            try:
                current_user = request.user
                result = current_user.profile.current_tenancy.create_user(userid=form.cleaned_data['username'],
                                                                  display_name=form.cleaned_data['displayname'],
                                                                  password=form.cleaned_data['password'],)
                if (result):
                    messages.success(request, f"Der Benutzer '{form.cleaned_data['username']}' wurde als '{result.cached_displayname}' erstellt")
                    return redirect('user_list')
                else:
                    messages.warning(request, f"Es trat ein unbekannter / unbehandelter Fehler auf")
                    return render(request, 'webadmin/user_create.html', {'form': form})
            except UserSyncError as e:
                messages.error(request,  "Fehler bei der Synchronisation der Benutzerdaten: "+ str(e))
        else: # form is not valid
            messages.warning(request, 'Fehler bei der Eingabe - unerwartete oder ungültige Eingabe')
    else: # Unbound Form
        form = UserCreateForm() # create empty form
    return render(request, 'webadmin/user_create.html', {'form': form})

@login_required
@handle_tenancy_permission_errors
def user_set_password(request, matrix_user_id):
    model = request.user.profile.current_tenancy.fetch_users_details(matrix_user_id=matrix_user_id)
    if request.method == 'POST': # bound form / data
        form = UserSetPasswordForm(request.POST)
        if form.is_valid(): ## returns true if and places data in cleaned_data attribute
            try:
                current_user = request.user
                result = current_user.profile.tenancy.change_password(matrix_user_id=matrix_user_id,
                                                                      new_password=form.cleaned_data['new_password'])
                if (result):
                    messages.success(request, f"Die Änderungen für '{model.matrix_user_id}' wurde gespeichert")
                    return redirect('user_list')
                else:
                    messages.warning(request, f"Es trat ein unbekannter / unbehandelter Fehler auf")
                    return render(request, 'webadmin/user_set_password.html', {'form': form, 'account': model})
            except UserSyncError as e:
                messages.error(request,  "Fehler bei der Synchronisation der Benutzerdaten: "+ str(e))
                return render(request, 'webadmin/user_set_password.html', {'form': form, 'account': model})
        else: # form is not valid
            messages.warning(request, 'Fehler bei der Eingabe - unerwartete oder ungültige Eingabe')
    else: # Unbound Form
        form = UserSetPasswordForm() # create empty form
    return render(request, 'webadmin/user_set_password.html', {'form': form, 'account': model})

@login_required
def room_create(request):
    if request.method == 'POST': # bound form / data
        form = RoomCreateForm(request.POST)
        if form.is_valid(): ## returns true if and places data in cleaned_data attribute
           # try:
                current_user = request.user
                result = current_user.profile.current_tenancy.create_room(name=form.cleaned_data['room'],
                                                                  public=form.cleaned_data['public'],
                                                                  encrypted=form.cleaned_data['encrypted'])
                if (result):
                    messages.success(request, f"Der Raum '{form.cleaned_data['room']}' wurde als '{result.matrix_room_id}' erstellt")
                    return redirect('room_list')
                else: # don't know if this ever happsens...
                    messages.error(request, 'Unerwarteter Fehler: Request failed without Error from the Server')
                    return render(request, 'webadmin/room_create.html')
            #except Exception as e: # ToDo: What Exceptions might occur here? Make it specific!! and do not forward e to the frontend!
                messages.error(request,  "Exception: "+ str(e))
        else: # form is not valid
            messages.warning(request, 'Fehler bei der Eingabe - unerwartete Eingabe')
    else: # Unbound Form
        form = RoomCreateForm() # create empty form
    return render(request, 'webadmin/room_create.html', {'form': form})

@login_required
def user_join_room(request, matrix_id):
    if request.method == 'POST': # bound form / data
        form = JoinRoomsForm(request.POST, user=request.user)
        if form.is_valid(): ## returns true if and places data in cleaned_data attribute
            current_user = request.user
            try:
                rooms = form.is_valid_room() #check, if a valid room_id is passed
                for room in rooms:
                    result = current_user.profile.current_tenancy.makejoinroom(matrix_user_id=matrix_id, matrix_room_id=room)
                    if (result):
                       messages.success(request, f"{matrix_id} dem Raum {room} hinzugefügt")
                    else: # don't know if this ever happens...
                        messages.error(request, 'Unerwarteter Fehler: Request failed without Error from the Server')
            except PermissionError as e:
                # ToDo: What Exceptions might occur here? Make it specific!!
                messages.error(request, e)
            return redirect('user_list')
            #return render(request, 'webadmin/user_list.html', {'rooms': request.user.profile.tenancy.get_rooms()})
        else: # form is not valid
            # Happens, if the user has tamperd with the input!
            messages.warning(request, 'Fehler bei der Eingabe - unerwartete Eingabe')
    else: # Unbound Form
        form = JoinRoomsForm(user=request.user)
    return render(request, 'webadmin/join_user_to_room.html', {'form': form, 'matrix_id': matrix_id})

@staff_member_required
def sa_user_list(request):
    messages.error(request, 'Not implemented yet!! ')
    return render(request, 'webadmin/welcome.html')

def set_tenancy(request, tenancy_id):
    try:
        request.user.profile.set_current_tenancy(new_tenancy_id=tenancy_id)
        messages.success(request,
                         f"Du verwaltest nun'{ request.user.profile.current_tenancy}'")
    except PermissionError as e:
        messages.warning(request, 'Du hast keine Berechtigung dies zu tun')
    return render(request, 'webadmin/welcome.html')