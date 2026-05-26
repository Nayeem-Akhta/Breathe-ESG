# ingestion/views.py

import os
import uuid
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from core.models import IngestionBatch, Organization
from .parsers.sap_parser import parse_sap_file
from .parsers.utility_parser import parse_utility_file
from .parsers.travel_parser import parse_travel_file


PARSER_MAP = {
    'SAP_FUEL':            parse_sap_file,
    'UTILITY_ELECTRICITY': parse_utility_file,
    'TRAVEL':              parse_travel_file,
}


class UploadFileView(APIView):
    """
    POST /api/ingest/upload/
    Accepts: multipart/form-data
    Fields:  file, source_type, organization_id
    """

    def post(self, request):
        file        = request.FILES.get('file')
        source_type = request.data.get('source_type')
        org_id      = request.data.get('organization_id')

        # ── Basic validation ───────────────────────────
        if not file:
            return Response({'error': 'No file provided'}, status=400)

        if source_type not in PARSER_MAP:
            return Response(
                {'error': f'Invalid source_type. Choose from: {list(PARSER_MAP.keys())}'},
                status=400
            )

        try:
            organization = Organization.objects.get(id=org_id)
        except Organization.DoesNotExist:
            return Response({'error': 'Organization not found'}, status=404)

        # ── Save file to disk ──────────────────────────
        upload_dir = os.path.join(settings.BASE_DIR, 'uploads')
        os.makedirs(upload_dir, exist_ok=True)

        file_name = f"{uuid.uuid4()}_{file.name}"
        file_path = os.path.join(upload_dir, file_name)

        with open(file_path, 'wb+') as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        # ── Create IngestionBatch ──────────────────────
        batch = IngestionBatch.objects.create(
            organization=organization,
            source_type=source_type,
            uploaded_by=request.user if request.user.is_authenticated else None,
            file_name=file.name,
            file_path=file_path,
            status=IngestionBatch.Status.PROCESSING,
        )

        # ── Run the correct parser ─────────────────────
        try:
            parser  = PARSER_MAP[source_type]
            summary = parser(
                file_path=file_path,
                batch=batch,
                organization=organization,
                uploaded_by=request.user if request.user.is_authenticated else None,
            )
        except Exception as e:
            batch.status = IngestionBatch.Status.FAILED
            batch.notes  = str(e)
            batch.save()
            return Response({'error': f'Parsing failed: {str(e)}'}, status=500)

        return Response({
            'message':   'File processed successfully',
            'batch_id':  str(batch.id),
            'summary':   summary,
        }, status=201)