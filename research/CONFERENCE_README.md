# Conference Map and Calendar - Documentation

## Overview
The conference map and calendar have been extracted into a separate file for easier maintenance and editing.

## File Structure

### `research/conferences.qmd`
This is the new standalone file containing:
- Interactive map showing conference locations using ipyleaflet
- Styled calendar table listing all conferences with details
- Conference data stored in a Python list that's easy to edit

### `research/index.qmd`
The main research page that includes the conferences file using:
```
{{< include conferences.qmd >}}
```

## How to Edit Conferences

1. Open `research/conferences.qmd`
2. Find the `conferences` list in the first Python code block (around line 33)
3. Add, remove, or modify conference entries

### Conference Entry Format
Each conference needs these fields:
```python
{
    "name": "Conference Name",
    "location": "City, State",
    "lat": 37.7749,              # Latitude coordinate
    "lon": -122.4194,            # Longitude coordinate
    "start_date": "YYYY-MM-DD",  # Start date
    "end_date": "YYYY-MM-DD",    # End date
    "type": "Conference",        # Type: Conference, Summit, Symposium, or Workshop
    "url": "https://..."         # URL to conference website
}
```

### Finding Coordinates
To find latitude and longitude for a location:
1. Go to Google Maps
2. Search for the location
3. Right-click on the location pin
4. Click on the coordinates to copy them
5. First number is latitude, second is longitude

## Benefits of This Structure

1. **Easy to Edit**: All conference data is in one clearly marked location
2. **Maintainable**: Separated concerns - conferences.qmd handles the map/table, index.qmd handles the main research page
3. **Reusable**: The conferences.qmd file could be included in other pages if needed
4. **Version Control**: Changes to conference data won't clutter the main research page history

## Rendering
The conference section will automatically appear at the bottom of the research page, after the Research Areas section.
