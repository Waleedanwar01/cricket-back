from django.db import models

# Create your models here.


class Team(models.Model):
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='team', null=True)
    rank = models.CharField(max_length=200, null=True)
    facebook = models.URLField(max_length=200, blank=True, null=True)
    twitter = models.URLField(max_length=200, blank=True, null=True)
    linkdin = models.URLField(max_length=200, blank=True, null=True)

    def __str__(self):
        return self.name
