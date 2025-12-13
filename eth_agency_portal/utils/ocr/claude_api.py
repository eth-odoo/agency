# -*- coding: utf-8 -*-
"""
Claude API Provider
Ücretli ama en akıllı çözüm - görüntüyü anlayarak veri çıkarır
API Key: https://console.anthropic.com/
"""
import logging
import base64
import json
import requests
from datetime import datetime
from typing import Dict, Any, Optional

_logger = logging.getLogger(__name__)


class ClaudeScanner:
    """Claude API ile voucher tarayan sınıf (Ücretli, Akıllı)"""

    CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def scan_voucher(self, image_data: bytes, media_type: str = "image/jpeg") -> Dict[str, Any]:
        """Voucher görüntüsünü Claude API ile tara"""
        try:
            if not self.api_key:
                return {
                    'success': False,
                    'error': 'Claude API key not configured',
                    'extracted_data': {}
                }

            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # Claude'a gönderilecek prompt
            extraction_prompt = """Bu bir otel/tatil rezervasyon voucher'ı görüntüsüdür. Görüntüyü dikkatlice incele ve aşağıdaki bilgileri JSON formatında çıkar.

DİKKAT EDİLECEK ALANLAR:

1. OTEL ADI (hotel_name):
   - "Hotel", "Resort", "Palace", "Club", "Spa" gibi kelimelerle birlikte olan tam otel adını bul
   - Genellikle voucher'ın üst kısmında veya başlık bölümünde bulunur
   - Örnek: "Rixos Premium Belek", "Titanic Deluxe Bodrum", "Voyage Belek Golf & Spa"

2. ODA TİPİ (room_type):
   - "Room", "Suite", "Villa", "Bungalow", "Deluxe", "Standard", "Superior" gibi kelimeler ara
   - "Room Type", "Accommodation", "Zimmer", "Camera", "Oda Tipi" başlıkları altında olabilir
   - Örnek: "Standard Room", "Deluxe Suite", "Family Room", "Sea View Room"

3. TOUR OPERATOR (operator_name):
   - Voucher'ı düzenleyen şirketin adı - genellikle logoda veya başlıkta
   - Bilinen operatörler: TUI, Coral Travel, Corendon, Anex Tour, Pegas, Bentour, Öger Tours,
     FTI, Thomas Cook, Neckermann, Alltours, Detur, Sunexpress, ITS, ETI, Schauinsland,
     Odeon, Biblio, Jolly Tur, Riviera, Mouzenidis, Tez Tour, Sunway, Jet2, EasyJet Holidays
   - Eğer logoda veya üst kısımda bir tur şirketi adı görüyorsan onu yaz

4. MİSAFİR BİLGİLERİ:
   - guest_name: Misafirin adı (first name) - "Mr", "Mrs", "Ms" gibi ünvanları dahil etme
   - guest_surname: Misafirin soyadı (last name)
   - Genellikle "Guest Name", "Passenger", "Pax", "Name" başlıkları altında

5. TARİHLER:
   - checkin_date: Giriş tarihi (Check-in, Arrival, Anreise, From)
   - checkout_date: Çıkış tarihi (Check-out, Departure, Abreise, Until, To)
   - YYYY-MM-DD formatında döndür

6. KİŞİ VE ODA SAYILARI:
   - adult_count: Yetişkin sayısı (Adult, Pax, Erwachsene, ADT)
   - child_count: Çocuk sayısı (Child, Kind, CHD, Infant)
   - room_count: Oda sayısı (Room, Zimmer, Camera)

7. FİYAT BİLGİLERİ:
   - total_amount: Toplam tutar (Total, Amount, Price, Gesamt) - sadece sayı
   - currency: Para birimi (EUR, USD, GBP, TRY, RUB)

8. DİĞER:
   - operator_voucher_no: Rezervasyon/Voucher numarası (Booking No, Confirmation, Ref)
   - meal_plan: Yemek planı (AI=All Inclusive, FB=Full Board, HB=Half Board, BB=Bed&Breakfast, RO=Room Only)

JSON FORMATI:
{
    "hotel_name": "string veya null",
    "room_type": "string veya null",
    "operator_name": "string veya null",
    "operator_voucher_no": "string veya null",
    "guest_name": "string veya null",
    "guest_surname": "string veya null",
    "checkin_date": "YYYY-MM-DD veya null",
    "checkout_date": "YYYY-MM-DD veya null",
    "adult_count": integer veya null,
    "child_count": integer veya null,
    "room_count": integer veya null,
    "total_amount": float veya null,
    "currency": "string veya null",
    "meal_plan": "string veya null",
    "notes": "string veya null"
}

KURALLAR:
- Sadece JSON döndür, başka açıklama ekleme
- Bulamadığın alanları null yap
- Tarihleri mutlaka YYYY-MM-DD formatında yaz
- Sayıları integer/float olarak yaz, string değil
- Otel adını ve oda tipini tam olarak yaz, kısaltma"""

            headers = {
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }

            payload = {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 1024,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": extraction_prompt
                            }
                        ]
                    }
                ]
            }

            _logger.info("Calling Claude API...")

            response = requests.post(
                self.CLAUDE_API_URL,
                headers=headers,
                json=payload,
                timeout=60
            )

            if response.status_code != 200:
                error_msg = response.text
                try:
                    error_data = response.json()
                    if 'error' in error_data:
                        error_msg = error_data['error'].get('message', error_msg)
                except:
                    pass

                _logger.error(f"Claude API error: {response.status_code} - {error_msg}")
                return {
                    'success': False,
                    'error': f'Claude API error ({response.status_code}): {error_msg}',
                    'extracted_data': {}
                }

            result = response.json()

            # Extract text content
            content = result.get('content', [])
            if not content:
                return {
                    'success': False,
                    'error': 'Empty response from Claude API',
                    'extracted_data': {}
                }

            text_response = content[0].get('text', '')
            _logger.info(f"Claude API response received")
            _logger.debug(f"Response: {text_response[:500]}...")

            # Parse JSON
            try:
                json_text = text_response.strip()
                # Remove markdown code blocks
                if json_text.startswith('```json'):
                    json_text = json_text[7:]
                if json_text.startswith('```'):
                    json_text = json_text[3:]
                if json_text.endswith('```'):
                    json_text = json_text[:-3]
                json_text = json_text.strip()

                extracted_data = json.loads(json_text)
                cleaned_data = self._clean_extracted_data(extracted_data)

                return {
                    'success': True,
                    'extracted_data': cleaned_data,
                    'raw_response': text_response
                }

            except json.JSONDecodeError as e:
                _logger.error(f"JSON parse error: {str(e)}")
                return {
                    'success': False,
                    'error': f'Failed to parse response: {str(e)}',
                    'extracted_data': {},
                    'raw_response': text_response
                }

        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'Claude API timeout - please try again',
                'extracted_data': {}
            }
        except requests.exceptions.RequestException as e:
            _logger.error(f"Claude API request error: {str(e)}")
            return {
                'success': False,
                'error': f'Network error: {str(e)}',
                'extracted_data': {}
            }
        except Exception as e:
            _logger.error(f"Claude scan error: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'extracted_data': {}
            }

    def _clean_extracted_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Çıkarılan veriyi temizle"""
        cleaned = {}

        # String fields
        string_fields = ['guest_name', 'guest_surname', 'operator_name',
                        'operator_voucher_no', 'hotel_name', 'room_type',
                        'meal_plan', 'currency', 'notes']
        for field in string_fields:
            value = data.get(field)
            if value and value != 'null' and str(value).lower() not in ('none', 'null'):
                cleaned[field] = str(value).strip()

        # Date fields
        date_fields = ['checkin_date', 'checkout_date']
        for field in date_fields:
            value = data.get(field)
            if value and value != 'null' and str(value).lower() not in ('none', 'null'):
                cleaned[field] = self._parse_date(str(value))

        # Integer fields
        int_fields = ['adult_count', 'child_count', 'room_count']
        for field in int_fields:
            value = data.get(field)
            if value is not None and str(value).lower() not in ('none', 'null'):
                try:
                    cleaned[field] = int(value)
                except (ValueError, TypeError):
                    pass

        # Float fields
        float_fields = ['total_amount']
        for field in float_fields:
            value = data.get(field)
            if value is not None and str(value).lower() not in ('none', 'null'):
                try:
                    if isinstance(value, str):
                        value = value.replace('€', '').replace('$', '').replace('£', '')
                        value = value.replace(',', '.').replace(' ', '').strip()
                    cleaned[field] = float(value)
                except (ValueError, TypeError):
                    pass

        # Defaults
        if 'adult_count' not in cleaned:
            cleaned['adult_count'] = 2
        if 'child_count' not in cleaned:
            cleaned['child_count'] = 0
        if 'room_count' not in cleaned:
            cleaned['room_count'] = 1

        return cleaned

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Tarih formatını YYYY-MM-DD'ye çevir"""
        if not date_str:
            return None

        date_formats = [
            '%Y-%m-%d',
            '%d.%m.%Y', '%d/%m/%Y', '%d-%m-%Y',
            '%Y/%m/%d', '%Y.%m.%d',
            '%d.%m.%y', '%d/%m/%y', '%d-%m-%y',
            '%d %b %Y', '%d %B %Y',
            '%B %d, %Y', '%b %d, %Y'
        ]

        for fmt in date_formats:
            try:
                date_obj = datetime.strptime(date_str.strip(), fmt)
                return date_obj.strftime('%Y-%m-%d')
            except ValueError:
                continue

        return date_str
