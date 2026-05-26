# core/models.py

import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser


#LAYER 0 — Organization (Multi-tenancy root)
# ─────────────────────────────────────────

class Organization(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        
# LAYER 1 — Custom User
# ─────────────────────────────────────────

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        null=True,       # null for superadmin who belongs to no org
        blank=True,
        related_name='users'
    )

    class Role(models.TextChoices):
        ADMIN    = 'ADMIN',    'Admin'
        ANALYST  = 'ANALYST',  'Analyst'
        VIEWER   = 'VIEWER',   'Viewer'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.ANALYST
    )

    def __str__(self):
        return f"{self.username} ({self.organization})"
    
# LAYER 2 — Ingestion Batch
# Every file upload creates one of these
# ─────────────────────────────────────────

class IngestionBatch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='batches'
    )

    class SourceType(models.TextChoices):
        SAP_FUEL              = 'SAP_FUEL',              'SAP Fuel & Procurement'
        UTILITY_ELECTRICITY   = 'UTILITY_ELECTRICITY',   'Utility Electricity'
        TRAVEL                = 'TRAVEL',                'Corporate Travel'

    source_type = models.CharField(max_length=30, choices=SourceType.choices)
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='batches'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file_name   = models.CharField(max_length=500)
    file_path   = models.CharField(max_length=1000, blank=True)

    class Status(models.TextChoices):
        PENDING    = 'PENDING',    'Pending'
        PROCESSING = 'PROCESSING', 'Processing'
        COMPLETED  = 'COMPLETED',  'Completed'
        FAILED     = 'FAILED',     'Failed'

    status          = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    total_rows      = models.IntegerField(default=0)
    successful_rows = models.IntegerField(default=0)
    failed_rows     = models.IntegerField(default=0)
    notes           = models.TextField(blank=True)

    def __str__(self):
        return f"{self.source_type} | {self.file_name} | {self.uploaded_at.date()}"

    class Meta:
        ordering = ['-uploaded_at']
        verbose_name_plural = 'Ingestion Batches'    
        
# LAYER 3 — Raw Tables (never modified)
# ─────────────────────────────────────────

class RawSAPEntry(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch        = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='sap_entries')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    row_number   = models.IntegerField()
    raw_data     = models.JSONField()         # entire CSV row stored as-is

    class ParseStatus(models.TextChoices):
        SUCCESS    = 'SUCCESS',    'Success'
        FAILED     = 'FAILED',     'Failed'
        SUSPICIOUS = 'SUSPICIOUS', 'Suspicious'

    parse_status = models.CharField(max_length=20, choices=ParseStatus.choices)
    parse_error  = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SAP Row {self.row_number} | Batch {self.batch_id}"

    class Meta:
        verbose_name = 'Raw SAP Entry'
        verbose_name_plural = 'Raw SAP Entries'


class RawUtilityEntry(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch        = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='utility_entries')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    row_number   = models.IntegerField()
    raw_data     = models.JSONField()

    class ParseStatus(models.TextChoices):
        SUCCESS    = 'SUCCESS',    'Success'
        FAILED     = 'FAILED',     'Failed'
        SUSPICIOUS = 'SUSPICIOUS', 'Suspicious'

    parse_status = models.CharField(max_length=20, choices=ParseStatus.choices)
    parse_error  = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Utility Row {self.row_number} | Batch {self.batch_id}"


class RawTravelEntry(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    batch        = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='travel_entries')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    row_number   = models.IntegerField()
    raw_data     = models.JSONField()

    class ParseStatus(models.TextChoices):
        SUCCESS    = 'SUCCESS',    'Success'
        FAILED     = 'FAILED',     'Failed'
        SUSPICIOUS = 'SUSPICIOUS', 'Suspicious'

    parse_status = models.CharField(max_length=20, choices=ParseStatus.choices)
    parse_error  = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Travel Row {self.row_number} | Batch {self.batch_id}"
    
    
# LAYER 4 — Normalized Entry (the heart)
# One row per activity, regardless of source
# ─────────────────────────────────────────

class NormalizedEntry(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='entries')
    batch        = models.ForeignKey(IngestionBatch, on_delete=models.CASCADE, related_name='normalized_entries')

    # Source tracking
    class SourceType(models.TextChoices):
        SAP_FUEL            = 'SAP_FUEL',            'SAP Fuel & Procurement'
        UTILITY_ELECTRICITY = 'UTILITY_ELECTRICITY', 'Utility Electricity'
        TRAVEL              = 'TRAVEL',              'Corporate Travel'

    source_type  = models.CharField(max_length=30, choices=SourceType.choices)
    raw_entry_id = models.UUIDField()   # UUID of RawSAPEntry / RawUtilityEntry / RawTravelEntry

    # When did this activity happen
    activity_date = models.DateField(null=True, blank=True)
    period_start  = models.DateField(null=True, blank=True)
    period_end    = models.DateField(null=True, blank=True)

    # What it is
    description = models.CharField(max_length=500)
    category    = models.CharField(max_length=100)   # "Diesel", "Electricity", "Flight"

    class Scope(models.TextChoices):
        SCOPE_1 = 'SCOPE_1', 'Scope 1 - Direct'
        SCOPE_2 = 'SCOPE_2', 'Scope 2 - Electricity'
        SCOPE_3 = 'SCOPE_3', 'Scope 3 - Value Chain'

    scope = models.CharField(max_length=10, choices=Scope.choices)

    # The measurement
    raw_value        = models.DecimalField(max_digits=15, decimal_places=4)
    raw_unit         = models.CharField(max_length=50)
    normalized_value = models.DecimalField(max_digits=15, decimal_places=4)
    normalized_unit  = models.CharField(max_length=50)

    # Carbon calculation
    emission_factor        = models.DecimalField(max_digits=15, decimal_places=6)
    emission_factor_source = models.CharField(max_length=200)
    co2e_kg                = models.DecimalField(max_digits=15, decimal_places=4)

    # Review state
    class ReviewStatus(models.TextChoices):
        PENDING  = 'PENDING',  'Pending Review'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        FLAGGED  = 'FLAGGED',  'Flagged for Clarification'

    review_status = models.CharField(max_length=20, choices=ReviewStatus.choices, default=ReviewStatus.PENDING)
    reviewed_by   = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='reviewed_entries')
    reviewed_at   = models.DateTimeField(null=True, blank=True)
    review_note   = models.TextField(blank=True)

    # Manual edits
    is_edited      = models.BooleanField(default=False)
    original_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    edited_by      = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='edited_entries')
    edited_at      = models.DateTimeField(null=True, blank=True)
    edit_reason    = models.TextField(blank=True)

    # Auto suspicious flag
    is_flagged_auto = models.BooleanField(default=False)
    flag_reason     = models.CharField(max_length=500, blank=True)

    # Audit lock — once True, nothing can change this row
    is_locked  = models.BooleanField(default=False)
    locked_at  = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.category} | {self.co2e_kg} kg CO2e | {self.review_status}"

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = 'Normalized Entries'
        
        
# LAYER 5 — Audit Log (append-only history)
# ─────────────────────────────────────────

class AuditLog(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE)
    entry        = models.ForeignKey(NormalizedEntry, on_delete=models.CASCADE, related_name='audit_logs')
    user         = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    class Action(models.TextChoices):
        CREATED  = 'CREATED',  'Created'
        EDITED   = 'EDITED',   'Edited'
        APPROVED = 'APPROVED', 'Approved'
        REJECTED = 'REJECTED', 'Rejected'
        FLAGGED  = 'FLAGGED',  'Flagged'
        LOCKED   = 'LOCKED',   'Locked'

    action       = models.CharField(max_length=20, choices=Action.choices)
    timestamp    = models.DateTimeField(auto_now_add=True)
    before_value = models.JSONField(null=True, blank=True)
    after_value  = models.JSONField(null=True, blank=True)
    ip_address   = models.GenericIPAddressField(null=True, blank=True)

    def __str__(self):
        return f"{self.action} | {self.entry_id} | {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
        
        
# LAYER 6 — Supporting Tables
# ─────────────────────────────────────────

class EmissionFactor(models.Model):
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    category       = models.CharField(max_length=100)   # "Diesel", "Electricity_IN"
    unit           = models.CharField(max_length=50)    # "litre", "kWh"
    factor_kg_co2e = models.DecimalField(max_digits=15, decimal_places=6)
    source         = models.CharField(max_length=200)   # "DEFRA 2023"
    region         = models.CharField(max_length=10, blank=True)  # "IN", "UK"
    valid_from     = models.DateField()
    valid_to       = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.category} | {self.factor_kg_co2e} kg CO2e/{self.unit} | {self.source}"


class PlantLookup(models.Model):
    id           = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='plants')
    plant_code   = models.CharField(max_length=50)    # "1000", "PLANT_DE_01"
    plant_name   = models.CharField(max_length=255)   # "Frankfurt Manufacturing"
    country      = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.plant_code} → {self.plant_name}"

    class Meta:
        unique_together = ['organization', 'plant_code']