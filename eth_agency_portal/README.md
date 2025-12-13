# ETH Agency Portal

Agency Portal modülü, acentelerin Travel sistemiyle etkileşim kurmasını sağlayan self-servis bir portaldır.

## Kurulum

### Gereksinimler

- Odoo 18
- `eth_agency_core` modülü
- `eth_travel_api` modülü (API endpoint'leri için)

### Modül Kurulumu

1. Modülü `custom_addons` klasörüne kopyalayın
2. Odoo'yu yeniden başlatın
3. Apps menüsünden "Agency Portal" modülünü kurun

## Yapılandırma

### System Parameters

Portal'ın çalışması için aşağıdaki sistem parametrelerinin ayarlanması gerekir:

```
Settings > Technical > Parameters > System Parameters
```

| Parametre | Değer | Açıklama |
|-----------|-------|----------|
| `eth_travel_api.api_key` | `agency-portal-secret-key` | Travel API'nin kabul ettiği API anahtarı |
| `eth_agency_portal.travel_api_url` | `http://localhost:8069` | Travel API'nin çalıştığı URL |
| `eth_agency_portal.travel_api_key` | `agency-portal-secret-key` | Portal'ın kullandığı API anahtarı (yukarıdakiyle aynı olmalı) |
| `eth_agency_portal.api_timeout` | `30` | API istek zaman aşımı (saniye) |

**Önemli:** `eth_travel_api.api_key` ve `eth_agency_portal.travel_api_key` değerleri aynı olmalıdır.

### Farklı Sunucu Yapılandırması

Eğer Travel API farklı bir sunucuda çalışıyorsa:

```
eth_agency_portal.travel_api_url = http://travel-server.example.com:8069
```

## Özellikler

### Sayfalar

| URL | Açıklama |
|-----|----------|
| `/agency/login` | Acente kullanıcı girişi |
| `/agency/dashboard` | Ana panel |
| `/agency/users` | Kullanıcı yönetimi |
| `/agency/settings` | Ayarlar ve profil |
| `/agency/bonus-reservation` | Bonus rezervasyonları |
| `/agency/bonus-wallet` | Bonus cüzdan |
| `/agency/bonus/contracts` | Bonus kontratları |

### API Endpoint'leri

Portal, Travel API'ye aşağıdaki istekleri yapar:

| Portal Endpoint | Travel API Endpoint | Açıklama |
|-----------------|---------------------|----------|
| `/agency/api/markets` | `/api/travel/markets` | Market listesi |
| `/agency/api/operators` | `/api/travel/operators` | Operatör listesi |
| `/agency/api/agency-hotels` | `/api/travel/agency/interested-hotels` | Acente otelleri |
| `/agency/api/hotel-rooms` | `/api/travel/hotels/{id}/room-types` | Otel oda tipleri |
| `/agency/api/bonus-reservations` | `/api/travel/bonus/reservations` | Bonus rezervasyonları |

## Sorun Giderme

### "Error loading master data: Failed to load hotels"

Bu hata genellikle API yapılandırmasının eksik olduğunu gösterir:

1. System Parameters'da `eth_agency_portal.travel_api_url` ayarlandığından emin olun
2. `eth_travel_api.api_key` ve `eth_agency_portal.travel_api_key` değerlerinin eşleştiğini kontrol edin
3. `eth_travel_api` modülünün kurulu ve aktif olduğunu doğrulayın

### API Bağlantı Hatası

Browser konsolunda (F12) Network sekmesini kontrol edin:

- **401 Unauthorized**: API key yanlış veya eksik
- **Connection refused**: Travel API URL yanlış veya sunucu çalışmıyor
- **Timeout**: `eth_agency_portal.api_timeout` değerini artırın

### Sayfa Dashboard'a Yönlendiriyor

Controller'da bir hata oluşuyor olabilir. Odoo loglarını kontrol edin:

```
tail -f /var/log/odoo/odoo.log | grep -i "bonus\|agency"
```

## Geliştirme

### Dosya Yapısı

```
eth_agency_portal/
├── controllers/
│   ├── __init__.py
│   ├── base.py              # Base controller ve helper'lar
│   ├── auth.py              # Login/logout
│   ├── dashboard.py         # Ana panel
│   ├── user_management.py   # Kullanıcı yönetimi
│   ├── settings.py          # Ayarlar
│   ├── bonus_wallet.py      # Bonus cüzdan
│   └── bonus_management.py  # Bonus rezervasyonları
├── models/
│   └── travel_api_client.py # Travel API istemcisi
├── templates/
│   ├── auth_templates.xml
│   ├── base_templates.xml
│   ├── dashboard_templates.xml
│   ├── settings_templates.xml
│   ├── bonus_wallet_templates.xml
│   └── bonus_reservation_template.xml
├── static/src/
│   ├── css/
│   └── js/
│       ├── portal.js
│       ├── bonus_wallet.js
│       └── bonus_reservation.js
├── data/
│   └── portal_config_data.xml
├── security/
│   └── ir.model.access.csv
└── i18n/
    └── tr.po                # Türkçe çeviriler
```

### API Client Kullanımı

```python
api_client = request.env['travel.api.client'].sudo()

# Token gerektirmeyen endpoint'ler
result = api_client.get_markets()
result = api_client.get_operators()
result = api_client.get_hotel_room_types(hotel_id)

# Token gerektiren endpoint'ler
token = request.session.get('agency_token')
result = api_client.get_agency_interested_hotels(token)
result = api_client.get_bonus_reservations(token, filters)
result = api_client.create_bonus_reservation(token, data)
```

## Lisans

LGPL-3
