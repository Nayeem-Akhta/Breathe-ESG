# ingestion/parsers/utility_parser.py
import numpy as np
import pandas as pd
from decimal import Decimal
from core.models import (
    RawUtilityEntry, NormalizedEntry, AuditLog,
    EmissionFactor, IngestionBatch
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

# India grid emission factors by zone (kg CO2e per kWh)
# Source: CEA India 2023
GRID_FACTORS = {
    'IN_SOUTH': {'factor': Decimal('0.7082'), 'source': 'CEA India 2023'},
    'IN_WEST':  {'factor': Decimal('0.8205'), 'source': 'CEA India 2023'},
    'IN_NORTH': {'factor': Decimal('0.7952'), 'source': 'CEA India 2023'},
    'IN_EAST':  {'factor': Decimal('0.9163'), 'source': 'CEA India 2023'},
    'DEFAULT':  {'factor': Decimal('0.7800'), 'source': 'CEA India 2023 (national avg)'},
}

# Normalize all units to kWh
UNIT_TO_KWH = {
    'KWH': Decimal('1.0'),
    'MWH': Decimal('1000.0'),
    'GWH': Decimal('1000000.0'),
}


def parse_utility_file(file_path, batch: IngestionBatch, organization, uploaded_by):
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

    # Track seen periods per meter to detect overlaps
    seen_periods = {}

    for idx, row in df.iterrows():
        row_num  = idx + 2
        row_dict = row.to_dict()
        parse_error = None

        # ── Parse consumption ──────────────────────────
        raw_value = None
        consumption_raw = str(row.get('consumption_kwh', '')).strip()
        if not consumption_raw or consumption_raw.lower() in ('nan', 'none', ''):
            parse_error = f"Missing consumption value"
        else:
            try:
                raw_value = Decimal(consumption_raw)
            except Exception:
                parse_error = f"Invalid consumption: '{consumption_raw}'"

        # ── Parse unit ─────────────────────────────────
        raw_unit   = str(row.get('consumption_unit', 'kWh')).strip().upper()
        conversion = UNIT_TO_KWH.get(raw_unit)
        if not conversion and not parse_error:
            parse_error = f"Unknown unit: '{raw_unit}'"

        # ── Parse dates ────────────────────────────────
        try:
            from datetime import datetime
            period_start = datetime.strptime(
                str(row.get('billing_period_start', '')).strip(), '%Y-%m-%d'
            ).date()
            period_end = datetime.strptime(
                str(row.get('billing_period_end', '')).strip(), '%Y-%m-%d'
            ).date()
        except Exception:
            if not parse_error:
                parse_error = f"Invalid billing period dates"

        # ── Save Raw Entry ─────────────────────────────
        raw_entry = RawUtilityEntry.objects.create(
            batch=batch,
            organization=organization,
            row_number=row_num,
            raw_data=clean_row_for_json(row_dict),
            parse_status='FAILED' if parse_error else 'SUCCESS',
            parse_error=parse_error or ''
        )

        if parse_error:
            summary['failed'] += 1
            continue

        # ── Normalize to kWh ───────────────────────────
        normalized_value = raw_value * conversion

        # ── Detect overlapping billing periods ─────────
        meter_id  = str(row.get('meter_id', '')).strip()
        period_key = f"{meter_id}_{period_start}"
        flagged    = False
        flag_reason = ''

        if period_key in seen_periods:
            flagged     = True
            flag_reason = f"Overlapping billing period for meter {meter_id}"
            raw_entry.parse_status = 'SUSPICIOUS'
            raw_entry.save()
            summary['suspicious'] += 1
        else:
            seen_periods[period_key] = True

        # ── Get emission factor by grid zone ───────────
        grid_zone  = str(row.get('grid_zone', 'DEFAULT')).strip()
        grid_info  = GRID_FACTORS.get(grid_zone, GRID_FACTORS['DEFAULT'])
        ef_value   = grid_info['factor']
        ef_source  = grid_info['source']

        co2e_kg = normalized_value * ef_value

        # ── Create Normalized Entry ────────────────────
        site_name = str(row.get('site_name', 'Unknown Site')).strip()

        entry = NormalizedEntry.objects.create(
            organization=organization,
            batch=batch,
            source_type=NormalizedEntry.SourceType.UTILITY_ELECTRICITY,
            raw_entry_id=raw_entry.id,
            period_start=period_start,
            period_end=period_end,
            description=f"Electricity - {site_name}",
            category='Electricity',
            scope=NormalizedEntry.Scope.SCOPE_2,
            raw_value=raw_value,
            raw_unit=raw_unit,
            normalized_value=normalized_value,
            normalized_unit='kWh',
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
            after_value={'category': 'Electricity', 'co2e_kg': str(co2e_kg)}
        )

        summary['success'] += 1

    batch.status          = IngestionBatch.Status.COMPLETED
    batch.total_rows      = summary['total']
    batch.successful_rows = summary['success']
    batch.failed_rows     = summary['failed']
    batch.save()

    return summary