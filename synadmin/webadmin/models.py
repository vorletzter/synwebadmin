from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ObjectDoesNotExist
from django.http import request
from django.utils import timezone
from synapse_admin import User
from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from synapse_admin import User as UserAdmin
from synapse_admin import Room as RoomAdmin
import datetime
from functools import wraps


class UserSyncError(Exception):
    pass


class Adminaccount(models.Model):
    username = models.CharField(max_length=200)
    access_token = models.CharField(max_length=200)
    homeserver = models.CharField(max_length=200)
    port = models.IntegerField(default=443)
    device_id = models.CharField(max_length=200)
    server_protocol = models.CharField(max_length=200, default="https://")

    def publish(self):
        self.published_date = timezone.now()
        self.save()

    def __str__(self):
        return self.username


class Tenant(models.Model):
    #user = models.ManyToManyField(settings.AUTH_USER_MODEL)
    adminaccount = models.ForeignKey(Adminaccount, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=200)

    '''
        Django-Model Functions
    '''
    def __str__(self):
        return self.name

    ''' 
        Decorators to make sure, that the API Calls within this Model are only made
        when the Models belong to the Tenant.
        
        Note to self: Values from Forms are checked by Django as well
            I should opt to use only Fields with Choices when working with accounts/rooms
    '''
    def account_belongs_to_self(function):
        @wraps(function)
        def wrapper(self, *args, **kwargs):
            matrix_user_id = kwargs.get('matrix_user_id', None)
            result = self.account_set.filter(name=matrix_user_id).exists()
            if (result):
                return function(self, *args, **kwargs)
            else:
                raise PermissionError("Account does not belong to this tenancy")
        return wrapper

    def room_belongs_to_self(function):
        @wraps(function)
        def wrapper(self, *args, **kwargs):
            matrix_room_id = kwargs.get('matrix_room_id', None)
            result = self.room_set.filter(matrix_room_id=matrix_room_id).exists()
            if (result):
                return function(self, *args, **kwargs)
            else:
                raise PermissionError("Room '"+str(matrix_room_id)+"' does not belong to this tenancy")
        return wrapper


    def get_synapse_user_admin(self):
        return UserAdmin(self.adminaccount.homeserver,
                         self.adminaccount.port,
                         self.adminaccount.access_token,
                         self.adminaccount.server_protocol)

    '''
        Fetch Functions:
        These Functions fetch details from the Server by means of the Model functions
        I Use the model functions to fill the cached values for each model

        Note; Technically we don't need the decorator here, because we try to fetch the Model regardles
            But i keep it for consitancy
    '''
    @room_belongs_to_self
    def fetch_room_details(self, matrix_room_id):
        queryset = self.room_set.filter(matrix_room_id=matrix_room_id).first()
        return queryset.fetch_details()

    @room_belongs_to_self
    def fetch_room_users(self, matrix_room_id):
        queryset = self.room_set.filter(matrix_room_id=matrix_room_id).first()
        return queryset.fetch_users()

    @room_belongs_to_self
    def promote_user_to_admin(self, matrix_room_id, matrix_user_id):
        adm = self.get_roomadmin()
        result = adm.set_admin(matrix_room_id, matrix_user_id)
        return result

    @account_belongs_to_self
    def fetch_users_details(self, matrix_user_id):
        queryset = self.account_set.filter(name=matrix_user_id).first()
        queryset.pull_details()
        return queryset

    '''
       Helper Functions 
    '''
    def get_roomadmin(self):
        return RoomAdmin(self.adminaccount.homeserver,
                         self.adminaccount.port,
                         self.adminaccount.access_token,
                         self.adminaccount.server_protocol)

    def get_useradmin(self):
        return UserAdmin(self.adminaccount.homeserver, self.adminaccount.port, self.adminaccount.access_token, self.adminaccount.server_protocol)


    '''
       Functions to access the reverse relationships of Models belonging to this Tenant
    '''
    def get_accounts(self):
        return self.account_set.all()

    def get_rooms(self):
        return self.room_set.all()

    '''
       Functions to create/modify/delete Rooms/Accounts
       an update the Database accordingly
    '''
    @account_belongs_to_self
    @room_belongs_to_self
    def makejoinroom(self, matrix_user_id, matrix_room_id):
        adm = self.get_useradmin()
        result = adm.join_room(userid=matrix_user_id,
                               roomid=matrix_room_id)
        return result

    def create_user(self, userid, display_name, password):
        ac = Account()
        ac.name = userid
        ac.matrix_user_id = userid
        ac.cached_displayname = display_name
        ac.comment = "Created: " + str(datetime.datetime.now())
        ac.managed_by = self
        return ac.init_user()

    @account_belongs_to_self
    def change_password(self, matrix_user_id, new_password):
        adm = self.get_useradmin()
        return adm.reset_password(matrix_user_id, new_password, logout=True)


    def create_room(self, name, public, encrypted):
        adm = self.get_roomadmin()
        result = adm.create(name=name, public=public, encrypted=encrypted)
        created = Room()
        created.managed_by = self
        created.cached_name = name
        created.matrix_room_id = result.roomid
        created.comment = "Created: "+ str(datetime.datetime.now())
        created.save()
        return created


class Account(models.Model):
    name = models.CharField(max_length=200) # ToDo: Refactor to change everything to matrix_user_id
    matrix_user_id = models.CharField(max_length=200)
    managed_by = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    comment = models.CharField(max_length=200, null=True, blank=True)
    cached_displayname = models.CharField(max_length=200, null=True, blank=True)
    cached_is_guest = models.BooleanField(default=False)
    cached_deactivated = models.BooleanField(default=False)
    cached_shadow_banned = models.BooleanField(default=False)
    cached_consent_version = models.CharField(max_length=200, null=True, blank=True)
    cached_appservice_id = models.CharField(max_length=200, null=True, blank=True)
    cached_creation_ts = models.CharField(max_length=200)
    cached_user_type = models.CharField(max_length=200, null=True, blank=True)
    cached_avatar_url = models.CharField(max_length=400, null=True, blank=True)
    cached_json = models.CharField(max_length=2000, null=True, blank=True)

    def __str__(self):
        return self.name


    def username_available(self):
        synapse_user_admin_api = self.managed_by.get_synapse_user_admin()
        return synapse_user_admin_api.username_available(self.matrix_user_id)


    def save(self, sync=False, *args, **kwargs):
        if sync:
            result = self.push_details()
        super(Account, self).save(*args, **kwargs)

    def init_user(self, password=None):
        synapse_user_admin_api = self.managed_by.get_synapse_user_admin()
        if (self.username_available()): # The Username is available - we create the user
            print (self.matrix_user_id)
            result = synapse_user_admin_api.create_modify(userid=self.matrix_user_id, displayname=self.cached_displayname, password=password)
        else:
            raise UserSyncError("Benutzer bereits auf Server vorhanden")
        if (result):
            self.pull_details() # we get the state from the Server
            # We set the matrix_user_id and name with the values from the server to avoid Issues with differen names
            # FixMe: Implement a proper check in the Forms, to make sure usernames are in the correct form @user:server
            # But for now, we let the Python Matrix Admin Module take care of that....
            return self

        return result # failed state

    '''
       Functions to Sync our Models with Results from an API Call to Synapse
    '''
    def pull_details(self):
        synapse_user_admin_api = self.managed_by.get_synapse_user_admin()
        account_details = synapse_user_admin_api.details(self.name)
        print (account_details)
        self.cached_json = account_details
        self.matrix_user_id = account_details['name']
        self.name = account_details['name']
        self.cached_displayname = account_details['displayname']
        self.cached_is_guest = account_details['is_guest']
        self.cached_consent_version = account_details['consent_version']
        self.cached_appservice_id = account_details['appservice_id']
        self.cached_creation_ts = account_details['creation_ts']
        self.cached_user_type = account_details['user_type']
        self.cached_deactivated = account_details['deactivated']
        self.cached_shadow_banned = account_details['shadow_banned']
        self.cached_avatar_url = account_details['avatar_url']
        self.save()
        return account_details

    def push_details(self):
        synapse_user_admin_api = self.managed_by.get_synapse_user_admin()
        result = synapse_user_admin_api.create_modify(userid=self.matrix_user_id, displayname=self.cached_displayname, avatar_url=self.cached_avatar_url, deactivated=self.cached_deactivated)
        if(result):
            return self
        return result # failed state


class Room(models.Model):
    matrix_room_id = models.CharField(max_length=200)
    managed_by = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    comment = models.CharField(max_length=200)
    cached_name = models.CharField(max_length=200)

    def __str__(self):
        return self.matrix_room_id

    def get_roomadmin(self):
        return RoomAdmin(self.managed_by.adminaccount.homeserver,
                         self.managed_by.adminaccount.port,
                         self.managed_by.adminaccount.access_token,
                         self.managed_by.adminaccount.server_protocol)

    def fetch_details(self):
        room_details = self.get_roomadmin().details(self.matrix_room_id)
        self.cached_name = room_details['name']
        self.save()
        return room_details

    def fetch_users(self):
        result = self.get_roomadmin().list_members(self.matrix_room_id)
        print (result)
        return result


'''
    Model: Profile
    primary used to store the currently Used "Tenanxy" for the User.
    ToDo: Empower User to switch between available tenancys
'''
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    current_tenancy = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True, related_name='current')
    tenancies = models.ManyToManyField(Tenant)
    contact = models.CharField(max_length=200, null=True, blank=True)
    matrix_user_id = models.ForeignKey(Account, on_delete=models.CASCADE, null=True, blank=True)

    @receiver(post_save, sender=User)
    def create_user_profile(sender, instance, created, **kwargs):
        if created:
            Profile.objects.create(user=instance)

    @receiver(post_save, sender=User)
    def save_user_profile(sender, instance, **kwargs):
        instance.profile.save()

    def __str__(self):
        return self.user.__str__()

    def get_available_tenancies(self):
        return self.tenancies.all()

    def set_current_tenancy(self, new_tenancy_id):
        try:
            result = self.tenancies.get(id=new_tenancy_id)
        except ObjectDoesNotExist as e:
            raise PermissionError("Du hast keine Berechtigung hierfür")

        if (result):
            self.current_tenancy = result
            self.save()