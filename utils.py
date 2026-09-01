"""
utils.py - helpers that don't belong to the DB layer:
  - Indian-style amount-in-words converter (Lakh/Crore, not Million/Billion)
  - QR code generation (UPI payment string) as an inline base64 data URI
  - WhatsApp deep-link builder
"""

import base64
import io
import urllib.parse

import qrcode

_ONES = [
    "", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine",
    "Ten", "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen",
    "Seventeen", "Eighteen", "Nineteen"
]
_TENS = [
    "", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"
]


def _two_digits(n):
    if n < 20:
        return _ONES[n]
    return (_TENS[n // 10] + (" " + _ONES[n % 10] if n % 10 else "")).strip()


def _three_digits(n):
    if n >= 100:
        return (_ONES[n // 100] + " Hundred" +
                (" " + _two_digits(n % 100) if n % 100 else "")).strip()
    return _two_digits(n)


def number_to_words_indian(num):
    """Convert an integer to words using the Indian numbering system
    (Crore / Lakh / Thousand) rather than the Western Million/Billion.
    """
    num = int(round(num))
    if num == 0:
        return "Zero"

    crore = num // 10000000
    num %= 10000000
    lakh = num // 100000
    num %= 100000
    thousand = num // 1000
    num %= 1000
    hundred = num

    parts = []
    if crore:
        parts.append(_three_digits(crore) + " Crore")
    if lakh:
        parts.append(_three_digits(lakh) + " Lakh")
    if thousand:
        parts.append(_three_digits(thousand) + " Thousand")
    if hundred:
        parts.append(_three_digits(hundred))

    return " ".join(parts).strip()


def amount_in_words(amount):
    """Return 'Rupees X Only' for the given numeric amount (paise ignored)."""
    words = number_to_words_indian(amount)
    return f"Rupees {words} Only"


def generate_upi_qr_data_uri(upi_id, payee_name, amount, note="Ganesh Chanda", txn_ref=None):
    """Build a standard UPI deep link (upi://pay?...) and render it as a QR
    code, returned as a base64 data: URI so it can go straight into an
    <img src="..."> with no extra static file to manage.
    """
    params = {
        "pa": upi_id,
        "pn": payee_name,
        "am": f"{amount:.2f}",
        "cu": "INR",
        "tn": note,
    }
    if txn_ref:
        params["tr"] = txn_ref

    upi_uri = "upi://pay?" + urllib.parse.urlencode(params)

    img = qrcode.make(upi_uri, box_size=6, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def whatsapp_link(phone, message):
    """Build a wa.me deep link. `phone` should include country code, digits only.
    Returns None if no phone number is available (caller should handle that).
    """
    if not phone:
        return None
    digits = "".join(ch for ch in phone if ch.isdigit())
    if not digits:
        return None
    text = urllib.parse.quote(message)
    return f"https://wa.me/{digits}?text={text}"
