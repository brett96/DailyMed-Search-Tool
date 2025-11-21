# DailyMed Excipient Search Web Application

A Django-based web application for searching DailyMed drug information with excipient (inactive ingredient) filtering capabilities.

## Features

- **Drug Name Autocomplete**: Search for drugs with autocomplete suggestions after 3 characters
- **Excipient Filtering**: Select excipients by category or manually enter specific excipient names
- **Sorted Results**: Results are automatically sorted into two categories:
  - **Free from Selected Excipients**: Drugs that don't contain any of the selected excipients
  - **Contains Selected Excipients**: Drugs that contain one or more selected excipients (highlighted in results)
- **Comprehensive Drug Information**: View drug name, dosage, drug type, route, NDC, packager name, active ingredients, inactive ingredients, and links to DailyMed

## Tech Stack

- **Backend**: Django 4.2+ with Django REST Framework
- **Frontend**: Django Templates with HTMX and Alpine.js
- **Styling**: Tailwind CSS
- **API Client**: Custom DailyMed API client (dailymed_client.py)

## Installation

1. **Clone or navigate to the project directory**

2. **Create a virtual environment**:
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # macOS/Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Run database migrations** (if needed):
   ```bash
   python manage.py migrate
   ```

5. **Create a superuser** (optional, for admin access):
   ```bash
   python manage.py createsuperuser
   ```

## Running the Application

1. **Start the development server**:
   ```bash
   python manage.py runserver
   ```

2. **Open your browser** and navigate to:
   ```
   http://localhost:8000
   ```

## Usage

### Searching for Drugs

1. **Enter a drug name** in the search box. After typing 3 characters, autocomplete suggestions will appear.
2. **Select excipients to filter by**:
   - Click "Browse by Category" to see excipients organized by category (Sweeteners, Preservatives, Dyes, etc.)
   - Or manually type an excipient name and press Enter
3. **Click "Search"** to find drugs matching your criteria.

### Understanding Results

- **Results Free from Selected Excipients**: These drugs do not contain any of the excipients you selected. These appear first.
- **Results Containing Selected Excipients**: These drugs contain one or more of the selected excipients. The matching excipients are highlighted in yellow.

### Result Information

Each result displays:
- **Drug Name**: The full name of the drug
- **Dosage**: Active ingredient strengths
- **Drug Type**: Form of the drug (e.g., Tablet, Capsule)
- **Route**: Route of administration (e.g., Oral)
- **NDC**: National Drug Code
- **Packager**: Name of the packaging company
- **Active Ingredients**: List of active ingredients with strengths
- **Inactive Ingredients**: List of inactive ingredients/excipients (highlighted if they match your search)
- **DailyMed Link**: Click to view full drug information on DailyMed website

## API Endpoints

The application provides REST API endpoints:

- `GET /api/drug-autocomplete/?q=<query>`: Get drug name suggestions
- `GET /api/search/?drug=<drug_name>&excipients=<exc1,exc2,...>`: Search for drugs with excipient filtering

## Project Structure

```
.
├── dailymed_web/          # Django project settings
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── search/                # Main search application
│   ├── services.py        # DailyMed API service layer
│   ├── api_views.py       # DRF API endpoints
│   ├── views.py           # Django views
│   └── urls.py            # URL routing
├── templates/             # HTML templates
│   ├── base.html
│   └── search/
│       └── search.html
├── dailymed_client.py     # Original DailyMed API client
├── manage.py
└── requirements.txt
```

## Development Notes

- The application uses the DailyMed v2 REST API
- Search results are fetched and parsed from SPL (Structured Product Labeling) XML documents
- The search process may take a moment as each result requires fetching and parsing XML data
- Results are limited to 25 per page by default (configurable via API)

## Future Enhancements

This is a basic implementation. Future updates may include:
- User registration and authentication
- Terms of use
- Additional search and filtering capabilities
- Download/export capabilities
- Enhanced sorting options
- Pagination for results
- Caching for improved performance


