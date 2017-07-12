from django.conf.urls import patterns, include, url
from .views import *
from django.views.decorators.cache import cache_page

urlpatterns = [
		url(r'^/tags$',cache_page(-1)(FacetsTagsView.as_view()), name='tags_view'),
		url(r'^/users$',FacetsUsersView.as_view(), name='users_view')

	    ]
