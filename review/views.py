# review/views.py

from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models import NormalizedEntry, AuditLog, IngestionBatch, Organization


def get_org(request):
    """Helper to get organization from request."""
    org_id = request.query_params.get('organization_id') or request.data.get('organization_id')
    try:
        return Organization.objects.get(id=org_id)
    except Organization.DoesNotExist:
        return None


# ─────────────────────────────────────────
# 1. List all normalized entries
# GET /api/review/entries/?organization_id=xxx
# Optional filters: ?status=PENDING&source=SAP_FUEL&scope=SCOPE_1&flagged=true
# ─────────────────────────────────────────
class EntryListView(APIView):
    def get(self, request):
        org = get_org(request)
        if not org:
            return Response({'error': 'organization_id required'}, status=400)

        entries = NormalizedEntry.objects.filter(organization=org)

        # ── Filters ───────────────────────────────────
        review_status = request.query_params.get('status')
        if review_status:
            entries = entries.filter(review_status=review_status)

        source = request.query_params.get('source')
        if source:
            entries = entries.filter(source_type=source)

        scope = request.query_params.get('scope')
        if scope:
            entries = entries.filter(scope=scope)

        flagged = request.query_params.get('flagged')
        if flagged == 'true':
            entries = entries.filter(is_flagged_auto=True)

        # ── Serialize ──────────────────────────────────
        data = []
        for e in entries.order_by('-created_at'):
            data.append({
                'id':                    str(e.id),
                'source_type':           e.source_type,
                'category':              e.category,
                'description':           e.description,
                'scope':                 e.scope,
                'activity_date':         str(e.activity_date) if e.activity_date else None,
                'period_start':          str(e.period_start) if e.period_start else None,
                'period_end':            str(e.period_end) if e.period_end else None,
                'raw_value':             str(e.raw_value),
                'raw_unit':              e.raw_unit,
                'normalized_value':      str(e.normalized_value),
                'normalized_unit':       e.normalized_unit,
                'emission_factor':       str(e.emission_factor),
                'emission_factor_source': e.emission_factor_source,
                'co2e_kg':               str(e.co2e_kg),
                'review_status':         e.review_status,
                'is_flagged_auto':       e.is_flagged_auto,
                'flag_reason':           e.flag_reason,
                'is_locked':             e.is_locked,
                'is_edited':             e.is_edited,
                'review_note':           e.review_note,
                'reviewed_by':           str(e.reviewed_by) if e.reviewed_by else None,
                'reviewed_at':           str(e.reviewed_at) if e.reviewed_at else None,
                'created_at':            str(e.created_at),
                'batch_id':              str(e.batch_id),
            })

        return Response({
            'count':   len(data),
            'entries': data
        })


# ─────────────────────────────────────────
# 2. Get single entry detail
# GET /api/review/entries/<id>/
# ─────────────────────────────────────────
class EntryDetailView(APIView):
    def get(self, request, entry_id):
        try:
            entry = NormalizedEntry.objects.get(id=entry_id)
        except NormalizedEntry.DoesNotExist:
            return Response({'error': 'Entry not found'}, status=404)

        # Get full audit trail for this entry
        logs = AuditLog.objects.filter(entry=entry).order_by('timestamp')
        audit_trail = [{
            'action':       log.action,
            'timestamp':    str(log.timestamp),
            'user':         str(log.user) if log.user else 'System',
            'before_value': log.before_value,
            'after_value':  log.after_value,
        } for log in logs]

        return Response({
            'id':                    str(entry.id),
            'source_type':           entry.source_type,
            'category':              entry.category,
            'description':           entry.description,
            'scope':                 entry.scope,
            'activity_date':         str(entry.activity_date) if entry.activity_date else None,
            'raw_value':             str(entry.raw_value),
            'raw_unit':              entry.raw_unit,
            'normalized_value':      str(entry.normalized_value),
            'normalized_unit':       entry.normalized_unit,
            'emission_factor':       str(entry.emission_factor),
            'emission_factor_source': entry.emission_factor_source,
            'co2e_kg':               str(entry.co2e_kg),
            'review_status':         entry.review_status,
            'is_flagged_auto':       entry.is_flagged_auto,
            'flag_reason':           entry.flag_reason,
            'is_locked':             entry.is_locked,
            'review_note':           entry.review_note,
            'audit_trail':           audit_trail,
        })


# ─────────────────────────────────────────
# 3. Approve an entry
# POST /api/review/entries/<id>/approve/
# Body: { "organization_id": "xxx", "note": "looks good" }
# ─────────────────────────────────────────
class ApproveEntryView(APIView):
    def post(self, request, entry_id):
        try:
            entry = NormalizedEntry.objects.get(id=entry_id)
        except NormalizedEntry.DoesNotExist:
            return Response({'error': 'Entry not found'}, status=404)

        # Cannot approve a locked entry
        if entry.is_locked:
            return Response({'error': 'Entry is already locked and cannot be modified'}, status=400)

        # Snapshot before state for audit log
        before = {
            'review_status': entry.review_status,
            'is_locked':     entry.is_locked,
        }

        # Approve and lock
        entry.review_status = NormalizedEntry.ReviewStatus.APPROVED
        entry.reviewed_by   = request.user if request.user.is_authenticated else None
        entry.reviewed_at   = timezone.now()
        entry.review_note   = request.data.get('note', '')
        entry.is_locked     = True
        entry.locked_at     = timezone.now()
        entry.save()

        # Write audit log
        AuditLog.objects.create(
            organization=entry.organization,
            entry=entry,
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.APPROVED,
            before_value=before,
            after_value={
                'review_status': entry.review_status,
                'is_locked':     True,
                'note':          entry.review_note,
            }
        )

        return Response({
            'message':  'Entry approved and locked',
            'entry_id': str(entry.id),
            'locked':   True,
        })


# ─────────────────────────────────────────
# 4. Reject an entry
# POST /api/review/entries/<id>/reject/
# Body: { "organization_id": "xxx", "note": "wrong unit used" }
# ─────────────────────────────────────────
class RejectEntryView(APIView):
    def post(self, request, entry_id):
        try:
            entry = NormalizedEntry.objects.get(id=entry_id)
        except NormalizedEntry.DoesNotExist:
            return Response({'error': 'Entry not found'}, status=404)

        if entry.is_locked:
            return Response({'error': 'Entry is locked and cannot be modified'}, status=400)

        before = {'review_status': entry.review_status}

        entry.review_status = NormalizedEntry.ReviewStatus.REJECTED
        entry.reviewed_by   = request.user if request.user.is_authenticated else None
        entry.reviewed_at   = timezone.now()
        entry.review_note   = request.data.get('note', '')
        entry.save()

        AuditLog.objects.create(
            organization=entry.organization,
            entry=entry,
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.REJECTED,
            before_value=before,
            after_value={
                'review_status': entry.review_status,
                'note':          entry.review_note,
            }
        )

        return Response({
            'message':  'Entry rejected',
            'entry_id': str(entry.id),
        })


# ─────────────────────────────────────────
# 5. Flag an entry for clarification
# POST /api/review/entries/<id>/flag/
# Body: { "organization_id": "xxx", "note": "check this value with client" }
# ─────────────────────────────────────────
class FlagEntryView(APIView):
    def post(self, request, entry_id):
        try:
            entry = NormalizedEntry.objects.get(id=entry_id)
        except NormalizedEntry.DoesNotExist:
            return Response({'error': 'Entry not found'}, status=404)

        if entry.is_locked:
            return Response({'error': 'Entry is locked and cannot be modified'}, status=400)

        before = {'review_status': entry.review_status}

        entry.review_status = NormalizedEntry.ReviewStatus.FLAGGED
        entry.reviewed_by   = request.user if request.user.is_authenticated else None
        entry.reviewed_at   = timezone.now()
        entry.review_note   = request.data.get('note', '')
        entry.save()

        AuditLog.objects.create(
            organization=entry.organization,
            entry=entry,
            user=request.user if request.user.is_authenticated else None,
            action=AuditLog.Action.FLAGGED,
            before_value=before,
            after_value={
                'review_status': entry.review_status,
                'note':          entry.review_note,
            }
        )

        return Response({
            'message':  'Entry flagged for clarification',
            'entry_id': str(entry.id),
        })


# ─────────────────────────────────────────
# 6. Dashboard summary
# GET /api/review/dashboard/?organization_id=xxx
# ─────────────────────────────────────────
class DashboardSummaryView(APIView):
    def get(self, request):
        org = get_org(request)
        if not org:
            return Response({'error': 'organization_id required'}, status=400)

        entries = NormalizedEntry.objects.filter(organization=org)

        # Count by status
        pending  = entries.filter(review_status='PENDING').count()
        approved = entries.filter(review_status='APPROVED').count()
        rejected = entries.filter(review_status='REJECTED').count()
        flagged  = entries.filter(review_status='FLAGGED').count()
        suspicious = entries.filter(is_flagged_auto=True).count()

        # Total CO2e by scope (only approved)
        from django.db.models import Sum
        scope1 = entries.filter(scope='SCOPE_1', review_status='APPROVED').aggregate(
            total=Sum('co2e_kg'))['total'] or 0
        scope2 = entries.filter(scope='SCOPE_2', review_status='APPROVED').aggregate(
            total=Sum('co2e_kg'))['total'] or 0
        scope3 = entries.filter(scope='SCOPE_3', review_status='APPROVED').aggregate(
            total=Sum('co2e_kg'))['total'] or 0

        # Recent batches
        batches = IngestionBatch.objects.filter(
            organization=org
        ).order_by('-uploaded_at')[:5]

        recent_batches = [{
            'id':              str(b.id),
            'source_type':     b.source_type,
            'file_name':       b.file_name,
            'status':          b.status,
            'total_rows':      b.total_rows,
            'successful_rows': b.successful_rows,
            'failed_rows':     b.failed_rows,
            'uploaded_at':     str(b.uploaded_at),
        } for b in batches]

        return Response({
            'review_summary': {
                'pending':    pending,
                'approved':   approved,
                'rejected':   rejected,
                'flagged':    flagged,
                'suspicious': suspicious,
            },
            'co2e_by_scope': {
                'scope_1_kg': str(scope1),
                'scope_2_kg': str(scope2),
                'scope_3_kg': str(scope3),
                'total_kg':   str(float(scope1) + float(scope2) + float(scope3)),
            },
            'recent_batches': recent_batches,
        })