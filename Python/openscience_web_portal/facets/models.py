from django.db import models
from djangotoolbox import fields

class FacetsTagsModel(models.Model):

	tag_name = models.CharField(max_length = 50)
	tag_count = models.BigIntegerField()
	timestamp = models.DateTimeField()
