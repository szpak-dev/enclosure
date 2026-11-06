from django.db import models

class ExampleRecordModel(models.Model):
    id = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=120)
