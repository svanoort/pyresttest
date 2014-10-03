from django.db import models
from django.core import serializers
import json

"""
Models for basic test application
"""

class Person(models.Model):
    login = models.CharField(max_length=100, unique=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255)

    def __str__(self):
        return self.login
