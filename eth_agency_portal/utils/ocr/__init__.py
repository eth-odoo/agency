# -*- coding: utf-8 -*-
"""
Voucher OCR Providers
Bu modül farklı OCR provider'larını destekler.

Provider'lar lazy import edilir - sadece kullanıldığında yüklenir.
"""

from .base import scan_voucher_from_base64, OCR_AVAILABLE, PROVIDERS

__all__ = ['scan_voucher_from_base64', 'OCR_AVAILABLE', 'PROVIDERS']
