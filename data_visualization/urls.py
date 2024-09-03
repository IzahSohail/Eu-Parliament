from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('vote/<str:vote_id>/', views.vote_detail, name='vote_detail'),
    path('mep/<int:mep_id>/', views.mep_info, name='mep_info'),
]
