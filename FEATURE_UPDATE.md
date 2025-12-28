# YouTube Video Search - Feature Update Summary

## Changes Implemented

### 1. **Custom Date-Time Range Selection** ✅
- Added a new mode selector in the sidebar allowing users to choose between:
  - **Predefined Periods**: Quick selection of common time ranges (Last 3 months, Last 1 month, etc.)
  - **Custom Date-Time Range**: Precise date and time selection

#### Custom Date-Time Range Features:
- **From Date & To Date**: Date pickers for selecting the start and end dates
- **From Time & To Time**: Time pickers for selecting specific hours and minutes
- **Duration Display**: Shows the total duration of the selected range
- **Validation**: Ensures start date-time is before end date-time
- **Timezone Support**: All times are in IST (Asia/Kolkata timezone)

### 2. **Increased Record Threshold** ✅
- **Previous Limit**: 500 records per search
- **New Limit**: 1500 records per search
- This allows fetching 3x more videos in a single search operation

### 3. **Enhanced Backend Support**
Updated `utils/utils.py` to support:
- Optional `published_after` and `published_before` parameters
- Custom date-time range filtering using YouTube API's time filters
- Backward compatibility with existing predefined period searches

### 4. **Improved File Naming**
- Predefined periods: `youtube_videos_{query}_{period}_{timestamp}.xlsx`
- Custom ranges: `youtube_videos_{query}_custom_{start_date}_{end_date}_{timestamp}.xlsx`

## How to Use

### Option 1: Predefined Periods
1. Select "Predefined Periods" in the sidebar
2. Choose a time period from the dropdown (e.g., "Last 7 days")
3. Enter your search query
4. Click "🚀 Start Search"

### Option 2: Custom Date-Time Range
1. Select "Custom Date-Time Range" in the sidebar
2. Set the **From Date** and **From Time**
3. Set the **To Date** and **To Time**
4. Review the duration display to confirm your selection
5. Enter your search query
6. Click "🚀 Start Search"

## Technical Details

### API Parameters Used
- **publishedAfter**: RFC 3339 timestamp for the start of the search range
- **publishedBefore**: RFC 3339 timestamp for the end of the search range
- **maxResults**: 50 per request (YouTube API maximum)
- **order**: date (newest first)

### Record Fetching
- The system will paginate through results until it reaches 1500 records or runs out of results
- Uses API key rotation to handle quota limits
- Removes duplicate videos based on video_id

### Timezone Handling
- All times are displayed and processed in IST (Asia/Kolkata)
- UTC timestamps from YouTube API are automatically converted to IST

## Dependencies
Updated `requirements.txt` to include:
- `aiohttp` - Async HTTP client for API requests
- `pandas` - Data manipulation and analysis
- `pytz` - Timezone handling
- `openpyxl` - Excel file handling

## Example Use Cases

1. **Find videos from a specific week**: 
   - From: 2025-12-15 00:00
   - To: 2025-12-22 23:59

2. **Find videos from a specific day**:
   - From: 2025-12-20 00:00
   - To: 2025-12-20 23:59

3. **Find videos from business hours**:
   - From: 2025-12-20 09:00
   - To: 2025-12-20 17:00

## Notes
- The YouTube API has daily quota limits (10,000 units per key)
- Each search request costs 100 quota units
- With 1500 records max and 50 per request, you'll use up to 3000 quota units per search
- Multiple API keys can be configured for rotation
