from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, hashers
from upload_app.models import DatasetModel
from searchDataset.views import SearchDatasetView
from forms import SearchUsersForm
from django.views.generic import TemplateView,View
from django.core.mail import send_mail
from django.db import transaction
from .models import *
from account.views import *
from google.appengine.api import search
import time, datetime
import re
import json



class FacetsTagsView(TemplateView):

	"""
	**Author**: Martin Zalondek


	**Description**: View displays tags on browse/tags page. Top 20 tags are displayed.


	**Attributes**:
		**template_name** (str): Path to the facets template
`	"""

	template_name = "pages/facets/tags.html"


	def get(self, request, *args, **kwargs):
		"""
		**Description**: Method fetches tags from search database and stores them in Datastore. Tags in Datastore are
		updated every update_period.


		"""

		update_period_minutes = 720
		tag_facets = []
		cached_tags = FacetsTagsModel.objects.order_by('-tag_count')
		date_now = datetime.datetime.now()
		if not cached_tags:
			tag_facets = self.createFacets(date_now)

		else:
			diff = date_now - cached_tags[0].timestamp
			diff_minutes = diff.seconds / 60

			if diff_minutes >= update_period_minutes:
				FacetsTagsModel.objects.all().delete()
				tag_facets = self.createFacets(date_now)

			else:
				for tag in cached_tags:
					tag_facets.append({'name':tag.tag_name,'count':tag.tag_count})
		
		return render(request, self.template_name,{'tags':tag_facets})

	def createFacets(self,date_now):
		"""
		**Description**: Method fetches top 20 tags from search database.

		
		"""
		active_index = 'dataset_index'
		tags = []
		index = search.Index(active_index)
		options=search.QueryOptions(returned_fields=[],limit=50)
		f_options = search.FacetOptions(discovery_limit=100,discovery_value_limit=20,depth=900)
		facetsQuery = search.Query(query_string="", options=options, 
						facet_options = f_options, enable_facet_discovery=True)
		facets_results = index.search(facetsQuery)

		for facetResult in facets_results.facets:
			for f in facetResult.values:
				tag = FacetsTagsModel(tag_name=f.label,tag_count=f.count,timestamp=date_now)
				tag.save()
				tags.append({'name':f.label,'count':f.count})
		return tags

class FacetsUsersView(TemplateView):

	"""
	**Author**: Martin Zalondek


	**Description**: This view displays users and sorts them by amount of uploaded dataset.


	**Attributes**:
		**template_name** (str): Path to the facets template
`	"""

	template_name = "pages/facets/users.html"


	def get(self, request, *args, **kwargs):
		"""
		**Description**: Method fetches top 20 tags from search database on loading and handles search queries on users. Users are
		sorted by amount of their uploaded datasets.

		
		"""
		active_index = "user_index"
		limit = 50
		page = 1
		results = []
		query_raw = ""

		if request.GET.get('search_bar') is not None:
			query_raw = request.GET.get('search_bar')
			if query_raw <> "":					
				final_query = "user_name_tokenized: "+SearchDatasetView.validate_search_term(query_raw)			
			else:
				final_query = ""
		else:
			query_raw = final_query = ""

		searchForm = SearchUsersForm(initial={'search_bar': query_raw})
		
		if request.GET.get('page') is not None and request.GET.get('page') != "":
			if int(request.GET.get('page')) == 0:
				page = 1
			else:
				page = int(request.GET.get('page'))
			offset = (limit * page) - limit
		else:
			offset = 0

		try:
			index = search.Index(active_index)

			sort1 = search.SortExpression(expression='dataset_counter', direction=search.SortExpression.DESCENDING, default_value=0)
			sortops = search.SortOptions(expressions=[sort1])


			options=search.QueryOptions(offset=offset,
				limit=limit,
				#sort_options = sortops,
				returned_fields=['user_name', 'dataset_counter','profile_image'],
				sort_options = sortops
				)
			searchQuery = search.Query(query_string=final_query, options=options)

			search_results = index.search(searchQuery)

			number_of_results = search_results.number_found	#number of all available results
			number_of_pages = int((number_of_results / limit)) + 1
			number_of_returned_results = len(search_results.results)


			for doc in search_results:
				user_name = doc.field('user_name').value
				dataset_count = int(doc.field('dataset_counter').value)
				profile_image = doc.field('profile_image').value
				results.append({'user_name':user_name,'dataset_count':dataset_count,'profile_image':profile_image})



		except search.Error:
			return render(request, self.template_name, {'error': 'We are sorry. Search failed. Try again later please.'})

		searchForm = SearchUsersForm(initial={'search_bar': query_raw})
		return render(request, self.template_name, {'form': searchForm,'number_of_results':number_of_results, 'results':results, 'page': page, 'number_of_pages':number_of_pages, 'search_query':query_raw})
