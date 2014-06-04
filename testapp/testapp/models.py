from django.db import models
from django.core import serializers
import json

"""
Models for basic test application
"""

class UserModel(models.Model):
    login = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.login
