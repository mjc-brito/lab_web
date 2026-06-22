from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.
class User(AbstractUser):
    student_number = models.CharField(
        max_length = 6, blank=True, null=True,  unique=True,
        verbose_name="Numero de aluno"
    )

    def __str__(self):
        return f"{self.username} ({self.student_number})"