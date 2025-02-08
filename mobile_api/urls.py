from django.urls import path
from .views import *

urlpatterns = [
    path('ping', PingView.as_view(), name='ping'),
    path('sources', ApiYandexGPTView.as_view(), name='sources'),
    path('questions', ApiGiminiQuestionsView.as_view(), name='questions'),
    path('sign-up', RegisterUserView.as_view(), name='sign-up'),
    path('sign-in', UserSigninView.as_view(), name='sign-in'),
]
