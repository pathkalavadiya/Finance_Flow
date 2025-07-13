from django.db import models

# Create your models here.
class Registration(models.Model):
    name = models.CharField(max_length=50)
    email = models.EmailField()
    mob = models.CharField(max_length=10)
    password = models.CharField(max_length=8)
    add = models.TextField()

    def __str__(self):
        return self.email