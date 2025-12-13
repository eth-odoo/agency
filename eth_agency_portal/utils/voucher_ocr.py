# -*- coding: utf-8 -*-
"""
Voucher OCR Utility - Backward Compatibility Wrapper

Bu dosya geriye dönük uyumluluk için korunmuştur.
Asıl implementasyonlar ocr/ klasöründedir:
- ocr/claude_api.py: Claude API (Ücretli, akıllı)
- ocr/google_vision.py: Google Cloud Vision (1000/ay ücretsiz)
- ocr/tesseract.py: Tesseract OCR (Ücretsiz, yerel)

System Parameters:
- voucher_ocr.provider: 'tesseract', 'google' veya 'claude' (varsayılan: claude)
- google.vision.api_key: Google Cloud Vision API key
- claude.api_key: Claude API key
"""
import logging
import base64

_logger = logging.getLogger(__name__)


def extract_voucher_data(file_content, filename, env=None):
    """
    Extract data from voucher file using OCR

    Args:
        file_content: Binary file content
        filename: Original filename
        env: Odoo environment (optional)

    Returns:
        dict with success status and extracted data
    """
    try:
        from .ocr import scan_voucher_from_base64

        # Convert binary to base64
        base64_content = base64.b64encode(file_content).decode('utf-8')

        # Scan using configured provider
        result = scan_voucher_from_base64(base64_content, env=env)

        if result.get('success'):
            return {
                'success': True,
                'data': result.get('extracted_data', {}),
                'message': 'Voucher scanned successfully'
            }
        else:
            return {
                'success': False,
                'error': result.get('error', 'OCR failed'),
                'data': {
                    'guest_name': '',
                    'guest_surname': '',
                    'hotel_name': '',
                    'room_type': '',
                    'checkin_date': '',
                    'checkout_date': '',
                    'operator_voucher_no': '',
                    'adult_count': 2,
                    'child_count': 0,
                    'room_count': 1,
                    'total_amount': 0,
                    'message': result.get('error', 'Please fill in the form manually.')
                }
            }

    except ImportError as e:
        _logger.warning(f"OCR module not available: {str(e)}")
        return {
            'success': False,
            'error': 'OCR not available',
            'data': {
                'guest_name': '',
                'guest_surname': '',
                'hotel_name': '',
                'room_type': '',
                'checkin_date': '',
                'checkout_date': '',
                'operator_voucher_no': '',
                'adult_count': 2,
                'child_count': 0,
                'room_count': 1,
                'total_amount': 0,
                'message': 'Please fill in the form manually. The voucher file will be attached.'
            }
        }
    except Exception as e:
        _logger.error(f"Voucher OCR error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'data': {
                'guest_name': '',
                'guest_surname': '',
                'hotel_name': '',
                'room_type': '',
                'checkin_date': '',
                'checkout_date': '',
                'operator_voucher_no': '',
                'adult_count': 2,
                'child_count': 0,
                'room_count': 1,
                'total_amount': 0,
                'message': f'OCR error: {str(e)}. Please fill in the form manually.'
            }
        }
