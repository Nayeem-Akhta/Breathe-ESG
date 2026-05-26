from django.contrib import admin
from .models import (
    Organization, User, IngestionBatch,
    RawSAPEntry, RawUtilityEntry, RawTravelEntry,
    NormalizedEntry, AuditLog, EmissionFactor, PlantLookup
) 

admin.site.register(Organization)
admin.site.register(User)
admin.site.register(IngestionBatch)
admin.site.register(RawSAPEntry)
admin.site.register(RawUtilityEntry)
admin.site.register(RawTravelEntry)
admin.site.register(NormalizedEntry)
admin.site.register(AuditLog)
admin.site.register(EmissionFactor)
admin.site.register(PlantLookup)
# Register your models here.
