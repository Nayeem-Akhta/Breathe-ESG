# ingestion/parsers/sap_parser.py
import numpy as np
import pandas as pd
from decimal import Decimal
from datetime import datetime
from core.models import (
    RawSAPEntry, NormalizedEntry, AuditLog,
    EmissionFactor, PlantLookup, IngestionBatch
)

def clean_row_for_json(row_dict):
    """
    Convert pandas/numpy types to plain Python types
    so Django's JSONField accepts them.
    """
    cleaned = {}
    for key, value in row_dict.items():
        if isinstance(value, float) and (value != value):  # NaN check
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

# ── Unit conversion to litres ──────────────────────────
UNIT_CONVERSIONS = {
    'L':   {'multiplier': Decimal('1.0'),    'standard_unit': 'litre'},
    'LTR': {'multiplier': Decimal('1.0'),    'standard_unit': 'litre'},
    'GAL': {'multiplier': Decimal('3.78541'),'standard_unit': 'litre'},
    'M3':  {'multiplier': Decimal('1.0'),    'standard_unit': 'm3'},   # keep as m3, don't convert to litres
}

# ── Material → Category + Scope mapping ───────────────
MATERIAL_MAP = {
    'DIES001': {'category': 'Diesel',       'scope': 'SCOPE_1', 'unit': 'litre'},
    'PETR001': {'category': 'Petrol',       'scope': 'SCOPE_1', 'unit': 'litre'},
    'NGAS001': {'category': 'Natural Gas',  'scope': 'SCOPE_1', 'unit': 'm3'},
}

# ── Known valid plant codes ────────────────────────────
KNOWN_PLANTS = ['1000', '2000', '3000']


def parse_sap_date(date_str):
    """SAP exports dates as YYYYMMDD. Convert to Python date."""
    try:
        return datetime.strptime(str(date_str).strip(), '%Y%m%d').date()
    except Exception:
        return None


def is_suspicious(row, normalized_value, org_id):
    """
    Flag a row as suspicious if:
    - Plant code not in lookup table
    - Value is extremely high (> 50,000 litres in one entry)
    """
    reasons = []

    plant_code = str(row.get('WERKS', '')).strip()
    if plant_code not in KNOWN_PLANTS:
        reasons.append(f"Unknown plant code: {plant_code}")

    if normalized_value and normalized_value > Decimal('50000'):
        reasons.append(f"Unusually high quantity: {normalized_value} litres")

    return bool(reasons), ' | '.join(reasons)


def get_emission_factor(category):
    """
    Get emission factor from DB.
    Falls back to hardcoded DEFRA values if not in DB.
    """
    FALLBACK_FACTORS = {
    'Diesel':      {'factor': Decimal('2.68780'), 'source': 'DEFRA 2023', 'unit': 'litre'},
    'Petrol':      {'factor': Decimal('2.31490'), 'source': 'DEFRA 2023', 'unit': 'litre'},
    'Natural Gas': {'factor': Decimal('2.02400'), 'source': 'DEFRA 2023', 'unit': 'm3'},
}

    try:
        ef = EmissionFactor.objects.filter(
            category=category
        ).order_by('-valid_from').first()

        if ef:
            return ef.factor_kg_co2e, ef.source, ef.unit

    except Exception:
        pass

    fb = FALLBACK_FACTORS.get(category)
    if fb:
        return fb['factor'], fb['source'], fb['unit']

    return None, None, None


def parse_sap_file(file_path, batch: IngestionBatch, organization, uploaded_by):
    """
    Main function. Reads SAP CSV, creates Raw + Normalized entries.
    Returns summary dict.
    """
    summary = {'total': 0, 'success': 0, 'failed': 0, 'suspicious': 0}

    try:
        df = pd.read_csv(file_path, dtype=str)
        df.columns = [c.strip() for c in df.columns]  # clean column names
    except Exception as e:
        batch.status = IngestionBatch.Status.FAILED
        batch.notes = f"Could not read file: {str(e)}"
        batch.save()
        return summary

    summary['total'] = len(df)

    for idx, row in df.iterrows():
        row_num = idx + 2      # +2 because idx is 0-based and row 1 is header
        row_dict = row.to_dict()

        # ── Step 1: Parse each field ───────────────────
        parse_error = None

        # Quantity
        parse_error = None
        raw_value = None
        menge_raw = str(row.get('MENGE', '')).strip()
        if not menge_raw or menge_raw.lower() in ('nan', 'none', ''):
            parse_error = f"Invalid quantity: '{menge_raw}'"
        else:
            try:
                raw_value = Decimal(menge_raw)
            except Exception:
                parse_error = f"Invalid quantity: '{menge_raw}'"

        # Date
        activity_date = parse_sap_date(row.get('BUDAT', ''))
        if not activity_date and not parse_error:
            parse_error = f"Invalid date: '{row.get('BUDAT')}'"

        # Unit
        raw_unit = str(row.get('MEINS', '')).strip().upper()
        if raw_unit.lower() in ('nan', 'none', ''):
            raw_unit = ''
        conversion_info = UNIT_CONVERSIONS.get(raw_unit)
        if not conversion_info and not parse_error:
            parse_error = f"Unknown unit: '{raw_unit}'"

        # Material
        material = str(row.get('MATNR', '')).strip()
        if material.lower() in ('nan', 'none'):
            material = ''
        material_info = MATERIAL_MAP.get(material)

        # ── Step 2: Save Raw Entry ─────────────────────
        parse_status = 'FAILED' if parse_error else 'SUCCESS'
        raw_entry = RawSAPEntry.objects.create(
            batch=batch,
            organization=organization,
            row_number=row_num,
            raw_data=clean_row_for_json(row_dict),
            parse_status=parse_status,
            parse_error=parse_error or ''
        )

        if parse_error:
            summary['failed'] += 1
            continue

        # ── Step 3: Normalize ──────────────────────────
        conversion_info  = UNIT_CONVERSIONS.get(raw_unit, {'multiplier': Decimal('1.0'), 'standard_unit': raw_unit})
        normalized_value = raw_value * conversion_info['multiplier']
        normalized_unit  = conversion_info['standard_unit']

        # ── Step 4: Check suspicious ───────────────────
        flagged, flag_reason = is_suspicious(row_dict, normalized_value, organization.id)
        if flagged:
            raw_entry.parse_status = 'SUSPICIOUS'
            raw_entry.save()
            summary['suspicious'] += 1

        # ── Step 5: Get emission factor ────────────────
        category = material_info['category'] if material_info else 'Unknown'
        scope    = material_info['scope']    if material_info else 'SCOPE_1'
        ef_value, ef_source, ef_unit = get_emission_factor(category)

        if not ef_value:
            ef_value  = Decimal('0')
            ef_source = 'Unknown - manual review required'

        co2e_kg = normalized_value * ef_value

        # ── Step 6: Create Normalized Entry ───────────
        plant_code = str(row_dict.get('WERKS', '')).strip()
        plant_name = PlantLookup.objects.filter(
            organization=organization,
            plant_code=plant_code
        ).values_list('plant_name', flat=True).first() or f"Plant {plant_code}"

        entry = NormalizedEntry.objects.create(
            organization=organization,
            batch=batch,
            source_type=NormalizedEntry.SourceType.SAP_FUEL,
            raw_entry_id=raw_entry.id,
            activity_date=activity_date,
            description=f"{category} - {plant_name}",
            category=category,
            scope=scope,
            raw_value=raw_value,
            raw_unit=raw_unit,
            normalized_value=normalized_value,
            normalized_unit=normalized_unit,
            emission_factor=ef_value,
            emission_factor_source=ef_source or '',
            co2e_kg=co2e_kg,
            review_status=NormalizedEntry.ReviewStatus.PENDING,
            is_flagged_auto=flagged,
            flag_reason=flag_reason,
        )

        # ── Step 7: Write Audit Log ────────────────────
        AuditLog.objects.create(
            organization=organization,
            entry=entry,
            user=uploaded_by,
            action=AuditLog.Action.CREATED,
            after_value={
                'category': category,
                'co2e_kg': str(co2e_kg),
                'source': 'SAP ingestion'
            }
        )

        summary['success'] += 1

    # ── Update batch summary ───────────────────────────
    batch.status          = IngestionBatch.Status.COMPLETED
    batch.total_rows      = summary['total']
    batch.successful_rows = summary['success']
    batch.failed_rows     = summary['failed']
    batch.save()

    return summary