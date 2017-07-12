from django.http import HttpResponse, HttpResponseRedirect
from django.template import RequestContext, loader
from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout, hashers
from forms import LoginForm, ForgottenPasswordForm
from django.views.generic import TemplateView,View
from django.core.mail import send_mail
from django.db import transaction
from account.views import *
import random, string
import time, datetime

class LoginView(TemplateView):
	"""
    **Author**:
        Martin Zalondek + 1
    **Description**:
        Class for user login
    **Attributes**:
        *template_name* (str): Name of template for class, template is rendered after method run
    """

	template_name = "pages/portalLogin/index.html"

	def get(self, request, *args, **kwargs):
		"""
    	**Description**:
		Method verificates if user is logged in. If yes, redirects him to user profile.
		Otherwise render login form. Method also reads GET request 'next' - URL of page to be redirect on after login.

    	:param request: HTTP request
    	:param args:
		:param kwargs:

    	:return: HTTP redirect
    	:return: rendered template
    	"""

		if request.user.is_authenticated():
			return redirect('/account/profile')
		if request.GET.get('next') is not None:
			next_url = request.GET.get('next')

			form = LoginForm(initial={'next_url_field': next_url})

			return render(request, self.template_name, {'info': "Please sign in first!", 'form': form})

		else:
			next_url = "/account/profile"
			form = LoginForm(initial={'next_url_field': next_url})

		return render(request, self.template_name, {'form': form})

	@transaction.commit_on_success
	def post(self, request, *args, **kwargs):
		"""
    	**Description**:
		Method processes login form. Search for user by username (unique) or email address.
		If somebody matched, compare hashed passwords. If successful, login and redirect to given
		URL by GET request ('next') otherwise render error.

    	:param request: HTTP request
    	:param args:
		:param kwargs:

    	:return: HTTP redirect
    	:return: rendered template (form - login form, info - notification, error - error message, success - success message)
    	"""

		if request.user.is_authenticated():
			return redirect('/account/profile')
		form = LoginForm(request.POST)
		if form.is_valid():
			user = authenticate(username=form.cleaned_data['login'].lower(), password=form.cleaned_data['password'])
			if user is not None:
				if user.is_active:
					login(request,user)
					user.reset_pw_attempt_counter()
					user.save()
					return redirect(form.cleaned_data['next_url_field'])
				else:
					info_message = "Your account is not activated. If you don\'t have activation link, <a href=\"/userRegistration/activateAccount\">resend it here.</a>"
					return render(request, self.template_name, {'info': info_message, 'form': form})
			elif User.existUserWithMail(form.cleaned_data['login']) == True:
				user = User.getUserByEmail(form.cleaned_data['login'])
				if user is not None:
					is_pw_correct = hashers.check_password(form.cleaned_data['password'],user.password)
					if is_pw_correct:
						if user.is_active:
							user.backend = 'django.contrib.auth.backends.ModelBackend'
							login(request,user)
							user.reset_pw_attempt_counter()
							user.save()
							return redirect(form.cleaned_data['next_url_field'])
						else:
							info_message = "Your account is not activated. If you don\'t have activation link, <a href=\"/userRegistration/activateAccount\">resend it here.</a>"
							return render(request, self.template_name, {'info': info_message, 'form': form})
					else:
						if user.pw_attempt_counter == 3:
							error_message = "Password for this username was reset and sent to your e-mail!"
							new_password = user.generateRandomPassword()
							user.reset_pw_attempt_counter()
							user.save()
							user.set_password(new_password)
							user.save()
							if len(user.email) > 0:
								send_mail('New password - OpenScience Data', 'Your new password is: '+new_password, 'paisontp@gmail.com', [user.email], fail_silently=False)
							user.save()
							return render(request, self.template_name, {'info': error_message, 'form': form})
						else:
							error_message = "Wrong password for this username/email!"
							user.inc_pw_attempt_counter()
							user.save()
							return render(request, self.template_name, {'error': error_message, 'form': form})
				elif User.isUserRegisteredByPortal(user) == True:
					error_message = "This username or email does not exist."
					return render(request, self.template_name, {'error': error_message, 'form': form})
			else:
				user = User.getUserByUsername(form.cleaned_data['login'])
				if user is not None:
					if user.pw_attempt_counter == 3:
						error_message = "Password for this username was reset and sent to your e-mail!"
						new_password = user.generateRandomPassword()
						user.reset_pw_attempt_counter()
						user.save()
						user.set_password(new_password)
						user.save()
						if len(user.email) > 0:
							send_mail('New password - OpenScience Data', 'Your new password is: '+new_password, 'paisontp@gmail.com', [user.email], fail_silently=False)

						return render(request, self.template_name, {'info': error_message, 'form': form})
					else:
						error_message = "Wrong password for this username/email!"
						user.inc_pw_attempt_counter()
						user.save()
						return render(request, self.template_name, {'error': error_message, 'form': form})
			error_message = "The provided username/email and password do not match! Try again."
			return render(request, self.template_name, {'error': error_message, 'form': form})
		else:
			return render(request, self.template_name, {'form': form})


class LogoutView(TemplateView):
	"""
    **Author**:
        Martin Zalondek + 1
    **Description**:
        Class for user logout
    **Attributes**:
        *template_name* (str): Name of template for class, template is rendered after method run
    """

	template_name = "pages/home.html"

	def get(self, request, *args, **kwargs):
		"""
    	**Description**:
		Method logouts user and redirect to homepage.

    	:param request: HTTP request
    	:param args:
		:param kwargs:

    	:return: HTTP redirect
    	"""

		logout(request)
		template = loader.get_template(self.template_name)
		context = RequestContext(request)
		return HttpResponse(template.render(context))

class ForgottenPasswordView(TemplateView):
	"""
    **Author**:
        Martin Zalondek + 1
    **Description**:
        Class for managing forgotten password
    **Attributes**:
        *template_name* (str): Name of template for class, template is rendered after method run
    """

	template_name = "pages/portalLogin/forgottenPassword.html"

	@transaction.commit_on_success
	def post(self, request, *args, **kwargs):
		"""
    	**Description**:
		Method processes form of forgotten password. Check if inserted mail exists in database.
		If yes, reset password and send it to given email address. If not render error.

    	:param request: HTTP request
    	:param args:
		:param kwargs:

    	:return: rendered template (form - login form, error - error message, success - success message)
    	"""

		if request.user.is_authenticated():
			return redirect('/account/profile')
		else:
			form = ForgottenPasswordForm(request.POST)
			if form.is_valid():
				user = User.getUserByEmailFromPortal(form.cleaned_data['email_address'])
				if user:
					new_password = user.generateRandomPassword()
					user.set_password(new_password)
					user.save()
					send_mail('New password - OpenScience Data', 'Your new password is: '+new_password, 'paisontp@gmail.com', [form.cleaned_data['email_address']], fail_silently=False)
					success_message = 'New password has been sent to your email address.'
					template = loader.get_template(self.template_name)
					context = RequestContext(request, {'form': form, 'success': success_message})
					return HttpResponse(template.render(context))
				else:
					error_message = 'User with this e-mail address doesn\'t exist.'
					template = loader.get_template(self.template_name)
					context = RequestContext(request, {'form': form, 'error': error_message})
					return HttpResponse(template.render(context))
		template = loader.get_template(self.template_name)
		context = RequestContext(request, {'form': form})
		return HttpResponse(template.render(context))

	def get(self, request, *args, **kwargs):
		"""
    	**Description**:
		Method renders form for forgotten password. If user is logged in, redirect to his profile.

    	:param request: HTTP request
    	:param args:
		:param kwargs:

		:return: HTTP redirect
    	:return: rendered template (form - login form, error - error message, success - success message)
    	"""

		if request.user.is_authenticated():
			return redirect('/account/profile')
		form = ForgottenPasswordForm()
		template = loader.get_template(self.template_name)
		context = RequestContext(request, {'form': form})
		return HttpResponse(template.render(context))

