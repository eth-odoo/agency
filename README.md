# Agency Modules

Core agency management modules for Odoo 18, designed to work with both Ticket and Travel systems.

## Modules

### eth_agency_core
Base agency module with no hotel dependencies. Includes:
- Agency management and approval workflow
- Agency user authentication
- Permission-based access control
- Membership purposes
- CRM integration

### eth_agency_portal
Self-service web portal for agency users. Features:
- Login/logout
- Dashboard with bonus wallet
- Bonus reservations management
- Profile management
- Uses Travel API for cross-database communication

## Installation

### As Submodule
```bash
git submodule add <repo-url> agency
```

### Odoo Configuration
Add to `addons_path`:
```ini
addons_path = ...,/path/to/agency
```

### Install Modules
```bash
./odoo-bin -d <database> -i eth_agency_core,eth_agency_portal
```

## Configuration

For portal to communicate with Travel API, set these system parameters:
- `eth_agency_portal.travel_api_url` - Travel system URL
- `eth_agency_portal.travel_api_key` - API key (must match Travel API config)

## License
LGPL-3
