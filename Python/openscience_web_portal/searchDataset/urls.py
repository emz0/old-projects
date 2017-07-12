
from django.conf.urls import patterns, include, url
from searchDataset.views import *
from datasetPage.views import *



urlpatterns = [
		url(r'^/$',cache_page(-1)(SearchDatasetView.as_view()), name='index'),
	    	url(r'^/index$',SearchDatasetView.as_view(), name='index'),
	    	url(r'^/(?P<search_query>.*)/$',SearchDatasetView.as_view(), name='search_query'),
	    	url(r'^/api/autoComplete$',AutocompleteView.as_view(), name='api_autocomplete'),
			url(r'^/datasetPage/(?P<dataset_id>.*)/$',DatasetPageView.as_view(), name='dataset')
			
	    ]