import re

AD_PHONE_ATTRS = {
    "phone": "telephoneNumber",
    "mobile": "mobile",
    "ip_phone": "ipPhone",
    "other_phone": "otherTelephone",
    "sip_line": "msRTCSIP-Line",
}
PHONE_FIELDS = tuple(AD_PHONE_ATTRS)

# Рабочий номер пишется в AD сразу при правке, поэтому ручным его не считаем.
# Остальные поля существуют только в справочнике — их синхронизация не трогает.
MANUAL_FIELDS = tuple(f for f in PHONE_FIELDS if f != "phone")

_AREA_CODE_RE = re.compile(r"^\s*[\d+\- ]*\(\d+\)\s*")


def normalize_phone(value: str | None) -> str | None:
    """'(812)1003', '8 (812) 1003' -> '1003'."""
    if not value:
        return None
    return _AREA_CODE_RE.sub("", value).strip() or None


def manual_fields(record) -> set[str]:
    """Поля, заполненные админом вручную. NULL — запись старше этого механизма,
    тогда ручными считаются все непустые поля."""
    if record.manual_phone_fields is None:
        return {f for f in MANUAL_FIELDS if getattr(record, f)}
    return {f for f in record.manual_phone_fields.split(",") if f in MANUAL_FIELDS}


def dump_manual_fields(fields: set[str]) -> str:
    return ",".join(f for f in MANUAL_FIELDS if f in fields)
