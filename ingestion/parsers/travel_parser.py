# ingestion/parsers/travel_parser.py
import numpy as np
import pandas as pd
from decimal import Decimal
from datetime import datetime
from core.models import (
    RawTravelEntry, NormalizedEntry, AuditLog, IngestionBatch
)

def clean_row_for_json(row_dict):
    cleaned = {}
    for key, value in row_dict.items():
        if isinstance(value, float) and (value != value):
            cleaned[key] = None
        elif isinstance(value, (np.integer,)):
            cleaned[key] = int(value)
        elif isinstance(value, (np.floating,)):
            cleaned[key] = float(value)
        elif isinstance(value, np.bool_):
            cleaned[key] = bool(value)
        else:
            cleaned[key] = str(value) if value is not None else None
    return cleaned

# Emission factors per km per person (kg CO2e)
# Source: DEFRA 2023 / ICAO
TRAVEL_FACTORS = {
    'FLIGHT': {
        'ECONOMY':  {'factor': Decimal('0.1553'), 'source': 'DEFRA 2023'},
        'BUSINESS': {'factor': Decimal('0.4286'), 'source': 'DEFRA 2023'},
        'FIRST':    {'factor': Decimal('0.6116'), 'source': 'DEFRA 2023'},
        'DEFAULT':  {'factor': Decimal('0.1553'), 'source': 'DEFRA 2023'},
    },
    'HOTEL': {
        'DEFAULT':  {'factor': Decimal('31.0000'), 'source': 'DEFRA 2023 (per night)'},
    },
    'GROUND_TRANSPORT': {
        'CAR':      {'factor': Decimal('0.1714'), 'source': 'DEFRA 2023 (per km)'},
        'TAXI':     {'factor': Decimal('0.1714'), 'source': 'DEFRA 2023 (per km)'},
        'DEFAULT':  {'factor': Decimal('0.1714'), 'source': 'DEFRA 2023 (per km)'},
    },
}

# Airport code → city distance lookup (km, approximate great circle)
# In real deployment this would use an aviation API
AIRPORT_DISTANCES = {
    ('BLR', 'LHR'): Decimal('8434'),
    ('BOM', 'JFK'): Decimal('12541'),
    ('DEL', 'DXB'): Decimal('2194'),
    ('BLR', 'SIN'): Decimal('3362'),
    ('DEL', 'LHR'): Decimal('6710'),
    ('BOM', 'LHR'): Decimal('7189'),
}


def get_flight_distance(origin, destination):
    """Look up distance between airport codes."""
    key  = (origin.upper(), destination.upper())
    rkey = (destination.upper(), origin.upper())
    return AIRPORT_DISTANCES.get(key) or AIRPORT_DISTANCES.get(rkey)


def parse_travel_file(file_path, batch: IngestionBatch, organization, uploaded_by):
    summary = {'total': 0, 'success': 0, 'failed': 0, 'suspicious': 0}

    try:
        df = pd.read_csv(file_path, dtype=str)
        df.columns = [c.strip().lower() for c in df.columns]
    except Exception as e:
        batch.status = IngestionBatch.Status.FAILED
        batch.notes  = f"Could not read file: {str(e)}"
        batch.save()
        return summary

    summary['total'] = len(df)

    for idx, row in df.iterrows():
        row_num  = idx + 2
        row_dict = row.to_dict()
        parse_error = None
        flagged     = False
        flag_reason = ''

        travel_type = str(row.get('travel_type', '')).strip().upper()
        travel_class = str(row.get('travel_class', 'DEFAULT')).strip().upper()
        origin      = str(row.get('origin', '')).strip().upper()
        destination = str(row.get('destination', '')).strip().upper()

        # ── Parse date ─────────────────────────────────
        try:
            activity_date = datetime.strptime(
                str(row.get('travel_date', '')).strip(), '%Y-%m-%d'
            ).date()
        except Exception:
            parse_error = f"Invalid date: '{row.get('travel_date')}'"

        # ── Determine distance ─────────────────────────
        distance = None
        raw_distance = str(row.get('distance_km', '')).strip()

        if raw_distance and raw_distance.lower() not in ('nan', 'none', ''):
            try:
                distance = Decimal(raw_distance)
            except Exception:
                distance = None

        if travel_type == 'FLIGHT' and not distance:
            # Try airport code lookup
            distance = get_flight_distance(origin, destination)
            if not distance and not parse_error:
                flagged     = True
                flag_reason = f"Unknown airport codes: {origin} → {destination}"
                # Still proceed but flag it
                distance    = Decimal('0')

        if travel_type == 'HOTEL' and not distance:
            # Hotels use nights not distance
            distance = Decimal('1')

        if distance is None:
            distance = Decimal('0')

        # ── Save Raw Entry ─────────────────────────────
        raw_entry = RawTravelEntry.objects.create(
            batch=batch,
            organization=organization,
            row_number=row_num,
            raw_data=clean_row_for_json(row_dict),
            parse_status='FAILED' if parse_error else ('SUSPICIOUS' if flagged else 'SUCCESS'),
            parse_error=parse_error or ''
        )

        if parse_error:
            summary['failed'] += 1
            continue

        if flagged:
            summary['suspicious'] += 1

        # ── Get emission factor ────────────────────────
        type_factors   = TRAVEL_FACTORS.get(travel_type, TRAVEL_FACTORS['GROUND_TRANSPORT'])
        class_factor   = type_factors.get(travel_class, type_factors['DEFAULT'])
        ef_value       = class_factor['factor']
        ef_source      = class_factor['source']

        # ── Calculate CO2e ─────────────────────────────
        # Flight/Ground: factor per km | Hotel: factor per night
        co2e_kg = distance * ef_value

        # ── Determine scope ────────────────────────────
        # All travel is Scope 3
        scope = NormalizedEntry.Scope.SCOPE_3

        # ── Build description ──────────────────────────
        if travel_type == 'FLIGHT':
            description = f"Flight ({travel_class}) - {origin} → {destination}"
        elif travel_type == 'HOTEL':
            description = f"Hotel ({travel_class}) - {destination}"
        else:
            description = f"Ground Transport - {origin} → {destination}"

        entry = NormalizedEntry.objects.create(
            organization=organization,
            batch=batch,
            source_type=NormalizedEntry.SourceType.TRAVEL,
            raw_entry_id=raw_entry.id,
            activity_date=activity_date,
            description=description,
            category=travel_type.title(),
            scope=scope,
            raw_value=distance,
            raw_unit='km' if travel_type != 'HOTEL' else 'night',
            normalized_value=distance,
            normalized_unit='km' if travel_type != 'HOTEL' else 'night',
            emission_factor=ef_value,
            emission_factor_source=ef_source,
            co2e_kg=co2e_kg,
            review_status=NormalizedEntry.ReviewStatus.PENDING,
            is_flagged_auto=flagged,
            flag_reason=flag_reason,
        )

        AuditLog.objects.create(
            organization=organization,
            entry=entry,
            user=uploaded_by,
            action=AuditLog.Action.CREATED,
            after_value={'category': travel_type, 'co2e_kg': str(co2e_kg)}
        )

        summary['success'] += 1

    batch.status          = IngestionBatch.Status.COMPLETED
    batch.total_rows      = summary['total']
    batch.successful_rows = summary['success']
    batch.failed_rows     = summary['failed']
    batch.save()

    return summary