from decimal import Decimal, InvalidOperation


def parse_br_decimal(value) -> Decimal | None:
    """
    Converte strings do tipo '   3.749,30' em Decimal('3749.30')
    Aceita número já numérico.
    """
    if value is None:
        return None
    if isinstance(value, (int, float, Decimal)):
        return Decimal(str(value))

    s = str(value).strip()
    if not s:
        return None

    # remove separador de milhar e troca vírgula por ponto
    s = s.replace(".", "").replace(",", ".")
    try:
        return Decimal(s)
    except InvalidOperation:
        return None


def yyyymmdd_or_raise(s: str) -> str:
    if len(s) != 8 or not s.isdigit():
        raise ValueError(
            "Data deve estar no formato yyyymmdd (ex.: 20260120).")
    return s
