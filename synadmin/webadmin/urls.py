from django.urls import path
from . import views

urlpatterns = [
    path('', views.welcome, name='welcome'),
    path('sync', views.sync, name='sync'),
    path('settenancy/<int:tenancy_id>', views.set_tenancy, name='set_tenancy'),
    path('room', views.room_list, name='room_list'),
    path('room/create', views.room_create, name='room_create'),
    path('room/<str:matrix_room_id>/details', views.room_details, name='room_details'),
    path('room/<str:matrix_room_id>/users', views.room_users, name='room_users'),
    path('room/<str:matrix_room_id>/users/<str:matrix_user_id>/powerlevel',
         views.room_powerlevel,
         name='room_powerlevel'),
    path('user', views.user_list, name='user_list'),
    path('user/create', views.user_create, name='user_create'),
    path('user/<str:matrix_user_id>', views.user_details, name='user_details'),
    path('user/<str:matrix_user_id>/onboard', views.user_onboard, name='user_onboard'),
    path('user/<str:matrix_user_id>/setpassword', views.user_set_password, name='user_set_password'),
    path('user/<str:matrix_id>/join/', views.user_join_room, name='user_join'),
    path('serveradmin/user', views.sa_user_list, name='sa_user_list'),
]