from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # du kan lägga till fler fält senare (tenant, role etc)
    pass