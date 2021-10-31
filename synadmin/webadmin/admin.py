from django.contrib import admin
from .models import Adminaccount, Tenant, Account, Room, Profile
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

# Register your models here.

admin.site.register(Adminaccount)

class AccountAdmin(admin.ModelAdmin):
    list_display = ('name', 'cached_displayname', 'managed_by' ,'cached_creation_ts', 'cached_deactivated')
    readonly_fields = ['cached_creation_ts', 'cached_deactivated', 'cached_is_guest',
                       'cached_appservice_id', 'cached_user_type', 'cached_shadow_banned',
                       'cached_json', 'cached_consent_version']
admin.site.register(Account, AccountAdmin)


class RoomAdmin(admin.ModelAdmin):
    list_display = ('matrix_room_id', 'cached_name', 'managed_by')

admin.site.register(Room, RoomAdmin)
#admin.site.register(Tenant)

class RoomInline(admin.StackedInline):
    model = Room
    can_delete = True
    verbose_name_plural = 'Rooms'
    #fk_name = 'room'

class AccountInline(admin.StackedInline):
    model = Account
    can_delete = True
    verbose_name_plural = 'Accounts'
    #fk_name = 'account'

class CustomTenantAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    inlines = (RoomInline, AccountInline)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomTenantAdmin, self).get_inline_instances(request, obj)

admin.site.register(Tenant, CustomTenantAdmin)


class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'
    fk_name = 'user'

class CustomUserAdmin(UserAdmin):
    inlines = (ProfileInline, )

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return list()
        return super(CustomUserAdmin, self).get_inline_instances(request, obj)


admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)