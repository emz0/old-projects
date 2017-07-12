from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, hashers
from forms import SearchForm
from django.views.generic import TemplateView,View
from django.core.mail import send_mail
from django.db import transaction
from account.views import *
from django.utils.safestring import mark_safe
from google.appengine.api import search
import time, datetime
import re
import json
from upload_app.views import unquote

active_index = 'dataset_index'

class SearchDatasetView(TemplateView):

	"""
	**Author**:
		Martin Zalondek + 1

	**Description**:
		This class handles GET requests for dataset search

	**Attributes**:
		**template_name** (str): Path to the search template
`	"""

	template_name = "pages/searchDataset/index.html"

	def get(self, request, *args, **kwargs):

		"""
		**Description**:
			This method handles GET requests. It looks for search query string in the request header
			and if it is found the search process is run. Returned results are then rendered in the loaded
			template and listed on the page.

		:param self:
		:param request: Includes a search query string submitted from a search form.
		:param *args:
		:param **kwargs:
		:return:
		"""
		
		number_of_results = 0
		results = []
		limit = 300

		
		if request.GET.get('search_bar') is not None:

			query = ""
			term_raw = unquote(request.GET.get('search_bar'))
			term = SearchDatasetView.validate_search_term(term_raw)
			# term = term_array.decode('utf-8','replace')
			filters = {'search_bar': term_raw,
					'authors':False,
					'citations': False,
					'titles': False,
					'descriptions': False,
					'tags': False,
					'time':4
					}
			if term <> "":	
				query = "("
				if request.GET.get('authors') is not None:
					query += "(author_tokenized:"+term+") OR "
					filters['authors'] = True

				if request.GET.get('citations') is not None:
					query += "(citation:"+term+") OR "
					filters['citations'] = True

				if request.GET.get("titles") is not None:
					query += "(title_tokenized:"+term+") OR "
					filters['titles'] = True

				if request.GET.get("descriptions") is not None:
					query += "(description:"+term+") OR "
					filters['descriptions'] = True
				if request.GET.get("tags") is not None:
					query += "(tag:"+term+") OR "
					filters['tags'] = True
				
				if query == "(":	
					query = "(author_tokenized: "+term+") OR (citation:"+term+") OR (title_tokenized:"+term+") OR (description:"+term+") OR (tag:"+term+") AND "
					filters = {'search_bar': term_raw,
					'authors':True,
					'citations':True,
					'titles': True,
					'descriptions':True,
					'tags': True					
					}	
				
				else:
					query = query[:-4] + ") AND "
			else:
				filters = {'search_bar': term_raw,
					'authors':True,
					'citations':True,
					'titles': True,
					'descriptions':True,
					'tags': True					
					}

			if request.GET.get("time") is not None and request.GET.get("time") != '4':
				time_index = request.GET.get("time")

				if time_index == '0':
					oldest_date = datetime.datetime.strftime(datetime.datetime.now()-datetime.timedelta(days=1),'%Y-%m-%d')
					filters['time'] = 0
				elif time_index =='1':
					oldest_date = datetime.datetime.strftime(datetime.datetime.now()-datetime.timedelta(weeks=1),'%Y-%m-%d')
					filters['time'] = 1
				elif time_index =='2':
					oldest_date = datetime.datetime.strftime(datetime.datetime.now()-datetime.timedelta(days=30),'%Y-%m-%d')
					filters['time'] = 2
				elif time_index =='3':
					today = datetime.date.today()
					oldest_date = datetime.datetime.strftime(datetime.datetime.today().replace(year=today.year - 1),'%Y-%m-%d')
					filters['time'] = 3
				query  += "uploaded >= \""+oldest_date+"\""
			else:
				query = query[:-4]
				filters['time'] = 4

			searchForm = SearchForm(initial=filters)

			try:
				index = search.Index(active_index)


				sortops = search.SortOptions(match_scorer=search.MatchScorer())

				options=search.QueryOptions(
					limit=limit,
					returned_fields=['title', 'author', 'uploaded','description','id_datastore','url_alias', 'tag'],
					sort_options = sortops					
					)
				searchQuery = search.Query(query_string=query, options=options)
				# print "\n\n final_query: "+query

				search_results = index.search(searchQuery)				

				number_of_results = search_results.number_found	#number of all available results
				#number_of_pages = int((number_of_results / limit)) + 1
				number_of_returned_results = len(search_results.results)


				for doc in search_results:
					title = doc.field('title').value
					author = doc.field('author').value
					uploaded = doc.field('uploaded').value
					#description = doc.field('description').value
					description = mark_safe(self.create_snippets(term_raw,doc.field('description').value))
					id_datastore = doc.field('id_datastore').value
					url_alias = doc.field('url_alias').value
					
					tags = [field.value for field in doc['tag']]
					
					results.append([title,author,uploaded,description,id_datastore,url_alias,tags])

			except search.Error:				
				return render(request, self.template_name, {'error': 'We are sorry. Search failed. Try again later please.'})
		else:	
			searchForm = SearchForm(initial={
				'authors': True,
				'citations': True,
				'titles': True,
				'descriptions': True,
				'tags': True,
				'time':4
				})
			return render(request, self.template_name,{'form': searchForm})
			
		return render(request, self.template_name, {'form': searchForm,'number_of_results':number_of_results, 'results':results, 'search_query':query})

	@staticmethod
	def validate_search_term(term):
		# term_array = str(term).replace('\\','').split()
		term_array = term.split()
		valide_term = ""
		for t in term_array:
			valide_term += "\""+ unquote(t).replace('"','') + "\" OR "
		valide_term = valide_term[:-3]
		return valide_term

	def create_snippets(self,searched_word,text):
		
		max_snippet_len = 500
		padd_front= 3
		padd_back = 3

		if not re.match('\w+',searched_word):	#if searched word doesn't contain at least 1 alphanumeric character			
			return text[:max_snippet_len]+"..."	#return first max_snippet_len characters
		
		searched_word = ' '.join(searched_word.split()).replace(" ","|")
		pattern = "\\b("+searched_word+")+\\b"
		
		
		text_array = text.split()

		i = 0
		snippet_index = 0
		match_index = []
		snippets = []
		regx = re.compile(pattern,flags=re.I)
		for word in text_array:			
			if regx.search(word):	#check if the searched word matches 				
				match_index.append(i)
				text_array[i] = "<div style=\"color:#20b975; display:inline-block;\">"+word+"</div>"
				start_index = max(i-padd_front,0)
				end_index = min(i+padd_back,len(text_array)-1)
				if len(snippets) > 0 and snippets[snippet_index - 1][1] >= start_index:	
					snippets[snippet_index - 1] = (snippets[snippet_index-1][0], end_index)
				else:
					snippets.append((start_index,end_index))
					snippet_index = snippet_index + 1		
			i = i + 1
		
		if not snippets:
			return text[:max_snippet_len]+"..."	#return first max_snippet_len characters

		snippet_text = ""
		for s in snippets:			
			snippet = " ".join(text_array[s[0]:s[1]+1]) 
			if len(snippet+snippet_text) > max_snippet_len:
				break
			if s[0] > 0:	#if the matched word is NOT at first place in the description, add "..." in front of the string
				snippet_text += " ".join(text_array[s[0]:s[1]+1]) 
			else:
				snippet_text += " ".join(text_array[s[0]:s[1]+1]) 
			if s[1] < len(text_array) - 1:	#if the matched word is NOT at last index in the description, add trailing "..."
				snippet_text += "..."
		#text = re.sub(r""+pattern,r"<strong>\1</strong>",r""+text,flags=re.I)

		
		return snippet_text


class AutocompleteView(View):

	"""
	**Author**:
		Martin Zalondek

	**Description**:
		This class handles GET requests for dataset autocomplete.


	**Attributes**:
`	"""

	def get(self, request, *args, **kwargs):

		"""
		**Description**:
			This method handles GET requests. The requests are asynchronously sent when user types a letter in a search bar.
			This method then returns names of datasets that were found(max 5).

		:param self:
		:param request: Includes a search query string from the search bar.
		:param *args:
		:param **kwargs:
		:return: results in JSON format
		"""


		term_raw = unquote(request.GET.get('search_string'))
		term = SearchDatasetView.validate_search_term(term_raw)
		# term = unquote(term_array.decode('utf-8','replace'))
		query = "(title_tokenized:"+ term + ") OR (tag_tokenized:"+ term + ")"
		
		limit = 5
		results = []		

		index = search.Index(active_index)
		

		options=search.QueryOptions(limit=limit,			
		 	returned_fields=['title','tag','title_tokenized']
		 	#returned_expressions = [search.FieldExpression(name='tag_snip', expression='snippet(\"'+term+'\",tag_tokenized, 15)')]
		 	)
		searchQuery = search.Query(query_string=query, options=options)

		search_results = index.search(searchQuery)

		results = []
		result = {'resultName': '', 'resultType': ''}
		ret_words = set()
		for doc in search_results:			
			title = doc.field('title').value
			tags = [field.value for field in doc['tag']]	
			#for expr in doc.expressions:  # iterate over the computed fields
				# if expr.name == 'title_tokenized':
				# 	title_snip = expr.value
				# 	print "\n\n\n\nsnipet title: "+title_snip+"\n"
					
				# if expr.name == 'tag_snip':
				# 	tag_snip = expr.value
				# 	print "\n\nsnipet tag: "+tag_snip+"\n"	
			
			if re.search(term_raw,title,re.IGNORECASE):
				if title not in ret_words:
					results.append({'resultName': title, 'resultType': 'Dataset Title'})
					ret_words.add(title)
			for tag in tags:
				if re.search(term_raw,tag,re.IGNORECASE):	
					if tag not in ret_words:				
						results.append({'resultName': tag, 'resultType': 'Tag'})
						ret_words.add(tag)
		
		r = HttpResponse(json.dumps({'results': results}), content_type="application/json")
		return r

