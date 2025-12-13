# -*- coding: utf-8 -*-
"""
Voucher OCR Base Module
Provider seçimi ve ortak fonksiyonlar
"""
import logging
import base64
import re
from datetime import datetime
from typing import Dict, Any, Optional

_logger = logging.getLogger(__name__)

# Provider sabitleri
PROVIDER_TESSERACT = 'tesseract'
PROVIDER_GOOGLE = 'google'
PROVIDER_CLAUDE = 'claude'

PROVIDERS = {
    PROVIDER_TESSERACT: 'Tesseract OCR (Free, Local)',
    PROVIDER_GOOGLE: 'Google Cloud Vision (1000/month Free)',
    PROVIDER_CLAUDE: 'Claude API (Paid, Smart)'
}

OCR_AVAILABLE = True


def parse_voucher_text(text: str) -> Dict[str, Any]:
    """OCR metnini parse edip voucher bilgilerini çıkar - ortak fonksiyon"""
    data = {}
    text_upper = text.upper()

    # Guest name - çeşitli formatları dene
    name_patterns = [
        r'(?:GUEST|NAME|PAX|PASSENGER|MİSAFİR|MISAFIR)[:\s]*([A-ZÇĞİÖŞÜa-zçğıöşü]+)\s+([A-ZÇĞİÖŞÜa-zçğıöşü]+)',
        r'(?:MR|MRS|MS|MISS)[.\s]+([A-ZÇĞİÖŞÜa-zçğıöşü]+)\s+([A-ZÇĞİÖŞÜa-zçğıöşü]+)',
    ]
    for pattern in name_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            data['guest_name'] = match.group(1).title()
            data['guest_surname'] = match.group(2).title()
            break

    # Operator name
    operators = ['TUI', 'CORAL TRAVEL', 'CORENDON', 'ANEX', 'PEGASUS', 'FTI',
                'THOMAS COOK', 'NECKERMANN', 'ALLTOURS', 'DETUR', 'SUNEXPRESS',
                'PEGAS', 'BENTOUR', 'ÖGER', 'OGER', 'ITS', 'ETI', 'SCHAUINSLAND',
                'ODEON', 'BIBLIO', 'JOLLY', 'RIVIERA', 'MOUZENIDIS', 'TEZ TOUR']
    for op in operators:
        if op in text_upper:
            data['operator_name'] = op
            break

    # Voucher number
    voucher_patterns = [
        r'(?:VOUCHER|BOOKING|RESERVATION|CONF|REF)[.\s#:No]*([A-Z0-9-]{6,})',
        r'\b([A-Z]{2,3}[0-9]{6,})\b'
    ]
    for pattern in voucher_patterns:
        match = re.search(pattern, text_upper)
        if match:
            data['operator_voucher_no'] = match.group(1)
            break

    # Dates
    date_patterns = [
        r'(\d{1,2})[./](\d{1,2})[./](\d{2,4})',
        r'(\d{4})-(\d{1,2})-(\d{1,2})'
    ]
    dates_found = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text)
        for match in matches:
            try:
                if len(match[2]) == 4:  # DD.MM.YYYY
                    date_str = f"{match[2]}-{match[1].zfill(2)}-{match[0].zfill(2)}"
                elif len(match[0]) == 4:  # YYYY-MM-DD
                    date_str = f"{match[0]}-{match[1].zfill(2)}-{match[2].zfill(2)}"
                else:  # DD.MM.YY
                    year = f"20{match[2]}" if int(match[2]) < 50 else f"19{match[2]}"
                    date_str = f"{year}-{match[1].zfill(2)}-{match[0].zfill(2)}"

                # Validate date
                datetime.strptime(date_str, '%Y-%m-%d')
                if date_str not in dates_found:
                    dates_found.append(date_str)
            except:
                continue

    if len(dates_found) >= 2:
        dates_found.sort()
        data['checkin_date'] = dates_found[0]
        data['checkout_date'] = dates_found[1]
    elif len(dates_found) == 1:
        data['checkin_date'] = dates_found[0]

    # Person counts
    adult_match = re.search(r'(\d+)\s*(?:ADULT|ADT|YETISKIN|YETIŞKIN|ERW|PAX)', text_upper)
    if adult_match:
        data['adult_count'] = int(adult_match.group(1))
    else:
        data['adult_count'] = 2

    child_match = re.search(r'(\d+)\s*(?:CHILD|CHD|COCUK|ÇOCUK|KIND|INF)', text_upper)
    if child_match:
        data['child_count'] = int(child_match.group(1))
    else:
        data['child_count'] = 0

    # Room count
    room_match = re.search(r'(\d+)\s*(?:ROOM|ODA|ZIMMER|CAMERA)', text_upper)
    if room_match:
        data['room_count'] = int(room_match.group(1))
    else:
        data['room_count'] = 1

    # Total amount
    amount_patterns = [
        r'(?:TOTAL|AMOUNT|TUTAR|TOPLAM|PRICE|GESAMT|TOTALE)[:\s]*([0-9.,\s]+)',
        r'([0-9]{1,3}(?:[.,\s][0-9]{3})*(?:[.,][0-9]{2}))\s*(?:EUR|USD|€|\$|TRY|₺|GBP|£)'
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text_upper)
        if match:
            try:
                amount_str = match.group(1).replace(' ', '').strip()
                # Handle European format (1.234,56 -> 1234.56)
                if ',' in amount_str and '.' in amount_str:
                    if amount_str.rfind(',') > amount_str.rfind('.'):
                        # 1.234,56 format
                        amount_str = amount_str.replace('.', '').replace(',', '.')
                    else:
                        # 1,234.56 format
                        amount_str = amount_str.replace(',', '')
                elif ',' in amount_str:
                    amount_str = amount_str.replace(',', '.')

                amount = float(amount_str)
                if 10 <= amount <= 100000:  # Reasonable range
                    data['total_amount'] = amount
                    break
            except:
                continue

    # Hotel name
    hotel_patterns = [
        r'(?:HOTEL|OTEL|RESORT|CLUB)[:\s]*([A-Za-z\s&\-\']+?)(?:\n|,|\d|$)',
        r'([A-Z][A-Za-z]+\s+(?:HOTEL|RESORT|PALACE|CLUB|INN|SUITES))'
    ]
    for pattern in hotel_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            hotel_name = match.group(1).strip()
            if len(hotel_name) > 3:
                data['hotel_name'] = hotel_name
                break

    return data


def scan_voucher_from_base64(base64_image: str, api_key: str = None, provider: str = None, env=None) -> Dict[str, Any]:
    """
    Base64 kodlu görüntüden voucher tara

    Provider seçenekleri (System Parameters'dan ayarlanır):
    - 'tesseract': Tesseract OCR (Ücretsiz, yerel kurulum gerekli)
    - 'google': Google Cloud Vision API (Aylık 1000 ücretsiz)
    - 'claude': Claude API (Ücretli, daha akıllı)

    System Parameters:
    - voucher_ocr.provider: 'tesseract', 'google' veya 'claude' (varsayılan: claude)
    - google.vision.api_key: Google Cloud Vision API key
    - claude.api_key: Claude API key
    """
    try:
        # Get env from parameter or from request
        if env is None:
            try:
                from odoo.http import request
                env = request.env
            except:
                pass

        ICP = None
        if env:
            ICP = env['ir.config_parameter'].sudo()

        # Provider seçimi - default to claude
        if not provider and ICP:
            provider = ICP.get_param('voucher_ocr.provider', PROVIDER_CLAUDE)
        elif not provider:
            provider = PROVIDER_CLAUDE

        _logger.info(f"Using voucher OCR provider: {provider}")

        image_data = base64.b64decode(base64_image)

        if provider == PROVIDER_TESSERACT:
            from .tesseract import TesseractScanner
            scanner = TesseractScanner()
            return scanner.scan_voucher(image_data)

        elif provider == PROVIDER_GOOGLE:
            from .google_vision import GoogleVisionScanner
            if not api_key and ICP:
                api_key = ICP.get_param('google.vision.api_key')

            if not api_key:
                return {
                    'success': False,
                    'error': 'Google Cloud Vision API key not configured. Set google.vision.api_key in System Parameters.',
                    'extracted_data': {}
                }

            scanner = GoogleVisionScanner(api_key=api_key)
            return scanner.scan_voucher(image_data)

        elif provider == PROVIDER_CLAUDE:
            from .claude_api import ClaudeScanner
            if not api_key and ICP:
                api_key = ICP.get_param('claude.api_key')

            if not api_key:
                return {
                    'success': False,
                    'error': 'Claude API key not configured. Set claude.api_key in System Parameters.',
                    'extracted_data': {}
                }

            # Detect media type
            media_type = "image/jpeg"
            if image_data[:8] == b'\x89PNG\r\n\x1a\n':
                media_type = "image/png"
            elif image_data[:2] == b'\xff\xd8':
                media_type = "image/jpeg"

            scanner = ClaudeScanner(api_key=api_key)
            return scanner.scan_voucher(image_data, media_type)

        else:
            return {
                'success': False,
                'error': f'Unknown provider: {provider}. Use "tesseract", "google" or "claude".',
                'extracted_data': {}
            }

    except Exception as e:
        _logger.error(f"Voucher scan error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'extracted_data': {}
        }
