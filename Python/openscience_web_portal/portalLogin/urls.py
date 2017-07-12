
from django.conf.urls import patterns, include, url
from portalLogin.views import *

urlpatterns = [

	    url(r'^/$',LoginView.as_view(), name='index'),
	    url(r'^/index$',LoginView.as_view(), name='index'),
	    url(r'^/logout$',LogoutView.as_view(), name='logout'),
	    url(r'^/forgottenPassword$',ForgottenPasswordView.as_view(), name='forgottenPassword'),
]