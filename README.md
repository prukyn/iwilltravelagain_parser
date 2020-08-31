# iwilltravelagain_parser

A parser parse data from site  https://iwilltravelagain.com/ and for each region collect existing events.

it collect next fields:
- region
- event title
- category
- location
- website

Parser uses next algorithm:
1. Get regions from first page
2. Get param 'data-post-id' that uses for an API https://iwilltravelagain.com/wp-json/FH/activities?post_id=DATA_POST_ID&key=rows_2_grid_activities
3. API return all events for current region.
4. Pool objects collect data from events
5. Save parsed data to csv.
