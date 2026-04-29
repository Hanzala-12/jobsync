# 🌍 Location Validation & Normalization Feature

## Overview
JobSync Pro now includes intelligent location validation and normalization using the free RestCountries API. Users can search for jobs by entering locations like "Lahore, Pakistan" or just "Lahore", and the system automatically validates and normalizes the country name.

---

## ✨ Features

### 1. **Country Validation**
- Uses RestCountries API (free, no API key required)
- Validates country names and returns official names
- Supports country codes (e.g., "PK", "US", "GB")
- Handles partial matches (e.g., "Pak" → "Pakistan")

### 2. **Location Normalization**
- Accepts flexible input formats:
  - "Lahore, Pakistan"
  - "Lahore, PK"
  - Just "Pakistan"
  - Just "Lahore"
- Returns structured location data:
  - City name
  - Official country name
  - Country code (ISO 3166-1 alpha-2)
  - Full location string

### 3. **Static City Database**
- Fallback city database for common cities
- Supports major cities in:
  - Pakistan (Lahore, Karachi, Islamabad, etc.)
  - India (Mumbai, Delhi, Bangalore, etc.)
  - USA (New York, San Francisco, Seattle, etc.)
  - UK (London, Manchester, Birmingham, etc.)
  - Canada (Toronto, Vancouver, Montreal, etc.)

---

## 📁 Files Created/Modified

### New File: `core/geo.py`
```python
# Functions:
- get_countries() → Fetch all countries from RestCountries API
- get_cities_for_country(country_code) → Get cities for a country
- validate_and_normalize_location(city, country) → Validate and normalize location
```

### Modified: `core/job_search.py`
- Added `from core.geo import validate_and_normalize_location`
- Updated `search_jobs_jsearch()` to accept `location_raw` parameter
- Location is validated before being sent to JSearch API

### Modified: `core/daily_scout.py`
- Updated to use `location_raw` parameter
- Passes location through validation pipeline

### Modified: `backend/routers/jobs.py`
- Added optional `location` query parameter to `/jobs/search`
- Integrated with JSearch API when location is provided
- Falls back to existing APIs when no location specified

---

## 🚀 Usage

### API Endpoint

**GET** `/jobs/search?query=software engineer&location=Lahore, Pakistan`

**Parameters:**
- `query` (required): Job search query
- `location` (optional): Location in format "City, Country" or just "Country"

**Example Requests:**
```bash
# Search with city and country
GET /jobs/search?query=developer&location=Lahore, Pakistan

# Search with just country
GET /jobs/search?query=engineer&location=Pakistan

# Search with country code
GET /jobs/search?query=designer&location=Lahore, PK

# Search without location (uses existing APIs)
GET /jobs/search?query=developer
```

---

### Python Code Usage

```python
from core.geo import validate_and_normalize_location
from core.job_search import search_jobs_jsearch

# Validate location
location = validate_and_normalize_location("Lahore", "Pakistan")
print(location)
# Output: {
#     "city": "Lahore",
#     "country": "Pakistan",
#     "country_code": "PK",
#     "full_location": "Lahore, Pakistan"
# }

# Search jobs with location
jobs = search_jobs_jsearch("software engineer", location_raw="Lahore, Pakistan")
```

---

## 🔧 How It Works

### Step 1: User Input
User provides location in flexible format:
- "Lahore, Pakistan"
- "Lahore, PK"
- "Pakistan"
- "Lahore"

### Step 2: Parse Input
System splits input by comma:
- Part 1: City (if present)
- Part 2: Country (if present)

### Step 3: Validate Country
- Fetch all countries from RestCountries API
- Match user input against:
  - Common name (e.g., "Pakistan")
  - Official name (e.g., "Islamic Republic of Pakistan")
  - Country code (e.g., "PK")
- Return matched country with code

### Step 4: Build Query
- Combine validated city and country
- Create full location string: "Lahore, Pakistan"
- Append to job search query: "software engineer in Lahore, Pakistan"

### Step 5: Search Jobs
- Send normalized query to JSearch API
- Return results with accurate location filtering

---

## 📊 Location Data Structure

```python
{
    "city": "Lahore",                    # User-provided city
    "country": "Pakistan",               # Validated country name
    "country_code": "PK",                # ISO 3166-1 alpha-2 code
    "full_location": "Lahore, Pakistan"  # Combined location string
}
```

---

## 🌐 RestCountries API

**Endpoint:** `https://restcountries.com/v3.1/all`

**Features:**
- ✅ Free to use
- ✅ No API key required
- ✅ Returns 250+ countries
- ✅ Includes official names, codes, regions

**Data Returned:**
- Common name (e.g., "Pakistan")
- Official name (e.g., "Islamic Republic of Pakistan")
- Country code (e.g., "PK")
- Region (e.g., "Asia")

---

## 🎯 Benefits

### For Users
- ✅ Flexible location input
- ✅ Automatic country validation
- ✅ No need to remember exact country names
- ✅ Support for country codes
- ✅ Better job search results

### For Developers
- ✅ Clean, reusable location validation
- ✅ Structured location data
- ✅ Easy integration with job APIs
- ✅ Fallback mechanisms
- ✅ No additional API keys needed

---

## 🔄 Integration Points

### 1. **Job Search API** (`/jobs/search`)
- Accepts optional `location` parameter
- Validates and normalizes location
- Passes to JSearch API

### 2. **Daily Scout** (`/scout/run`)
- Accepts `location` in request body
- Validates before searching
- Saves jobs with normalized location

### 3. **CLI Menu** (Future)
- Prompt user for location
- Validate input
- Display normalized location
- Search with validated location

---

## 📝 Example Scenarios

### Scenario 1: Full Location
**Input:** "Lahore, Pakistan"
**Validation:** ✅ City: Lahore, Country: Pakistan (PK)
**Query:** "software engineer in Lahore, Pakistan"

### Scenario 2: Country Only
**Input:** "Pakistan"
**Validation:** ✅ Country: Pakistan (PK)
**Query:** "software engineer in Pakistan"

### Scenario 3: Country Code
**Input:** "Lahore, PK"
**Validation:** ✅ City: Lahore, Country: Pakistan (PK)
**Query:** "software engineer in Lahore, Pakistan"

### Scenario 4: Partial Match
**Input:** "Lahore, Pak"
**Validation:** ✅ City: Lahore, Country: Pakistan (PK)
**Query:** "software engineer in Lahore, Pakistan"

---

## 🚧 Future Enhancements

1. **City Validation API**
   - Replace static CITIES_DB with Geonames API
   - Validate city names against country
   - Suggest corrections for typos

2. **Geocoding**
   - Convert location to coordinates
   - Enable radius-based job search
   - Show jobs on map

3. **Location Autocomplete**
   - Suggest cities as user types
   - Show popular locations
   - Recent searches

4. **Multi-Location Search**
   - Search multiple locations at once
   - "Remote or Lahore or Karachi"
   - Combine results

---

## ✅ Status

✅ **Core Module:** `core/geo.py` created
✅ **Job Search:** Updated with location validation
✅ **API Endpoint:** `/jobs/search` accepts location parameter
✅ **Daily Scout:** Integrated with location validation
✅ **Git:** All changes committed and pushed
✅ **Documentation:** Complete

---

## 🎉 Ready to Use!

The location validation feature is now live and ready to use. Try it out:

1. **API:** `GET /jobs/search?query=developer&location=Lahore, Pakistan`
2. **Daily Scout:** Include location in request body
3. **Frontend:** Update Jobs page to add location input field

**Your JobSync Pro now has intelligent, validated location-based job search!** 🌍🚀
