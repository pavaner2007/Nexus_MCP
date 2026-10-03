"""
app/testing/mock_tool_schemas.py
=================================
Realistic MCP / JSON Schema tool definitions for 20 individual SerpApi engines
plus the single Universal_Search schema used by this project.

These schemas are used exclusively by benchmark_tokens.py to measure the
prompt-token reduction from exposing 1 unified tool vs. 20 raw engine tools.

Each schema follows the MCP spec:
  {
    "name": str,
    "description": str,
    "inputSchema": {
      "type": "object",
      "properties": { param: {"type": ..., "description": ...} },
      "required": [...]
    }
  }
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# 20 individual SerpApi engine tool schemas
# ---------------------------------------------------------------------------

TWENTY_ENGINE_SCHEMAS: list[dict] = [
    # 1. Google Shopping
    {
        "name": "google_shopping_search",
        "description": (
            "Search Google Shopping for products, prices, and retailers. "
            "Returns structured product listings including price, source, rating, "
            "review count, and thumbnail. Use for any query involving purchasing, "
            "price comparison, or product discovery."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Product name, description, or search query (e.g. 'iPhone 15 Pro 256GB').",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of product results to return. Default 10, max 100.",
                    "default": 10,
                },
                "country": {
                    "type": "string",
                    "description": "Two-letter country code for localised pricing (e.g. 'us', 'in', 'gb'). Default 'us'.",
                    "default": "us",
                },
                "min_price": {
                    "type": "number",
                    "description": "Minimum price filter in local currency.",
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum price filter in local currency.",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["relevance", "price_low", "price_high", "rating"],
                    "description": "Sort order for results.",
                    "default": "relevance",
                },
            },
            "required": ["query"],
        },
    },
    # 2. Google Scholar
    {
        "name": "google_scholar_search",
        "description": (
            "Search Google Scholar for peer-reviewed academic papers, citations, "
            "preprints, and scholarly literature. Returns author list, publication "
            "venue, year, citation count, and PDF link when available. Use for "
            "research queries, literature reviews, and citation lookups."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Research topic, paper title, or author name.",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return. Default 10, max 20.",
                    "default": 10,
                },
                "as_ylo": {
                    "type": "integer",
                    "description": "Filter results published from this year onwards (inclusive).",
                },
                "as_yhi": {
                    "type": "integer",
                    "description": "Filter results published up to this year (inclusive).",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["relevance", "date"],
                    "description": "Sort by relevance (default) or most recent publication date.",
                    "default": "relevance",
                },
                "include_patents": {
                    "type": "boolean",
                    "description": "Include patents in scholar results. Default false.",
                    "default": False,
                },
                "include_citations": {
                    "type": "boolean",
                    "description": "Include citation articles. Default true.",
                    "default": True,
                },
            },
            "required": ["query"],
        },
    },
    # 3. Google Local
    {
        "name": "google_local_search",
        "description": (
            "Search Google Local / Maps for businesses, restaurants, services, "
            "and points of interest. Returns name, address, phone, rating, review "
            "count, hours, and coordinates. Use for any query involving physical "
            "locations, 'near me' searches, or local business discovery."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Business type or name and optional location (e.g. 'coffee shops near downtown Seattle').",
                },
                "location": {
                    "type": "string",
                    "description": "City, zip code, or 'lat,lng' coordinates to centre the search.",
                },
                "radius_miles": {
                    "type": "number",
                    "description": "Search radius in miles from the location. Default 5.",
                    "default": 5,
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of local results to return. Default 10, max 20.",
                    "default": 10,
                },
                "min_rating": {
                    "type": "number",
                    "description": "Minimum star rating filter (1.0 – 5.0).",
                },
                "open_now": {
                    "type": "boolean",
                    "description": "If true, only return businesses currently open.",
                    "default": False,
                },
            },
            "required": ["query"],
        },
    },
    # 4. Google Patents
    {
        "name": "google_patents_search",
        "description": (
            "Search Google Patents for patent filings, prior art, patent status, "
            "and inventor/assignee information. Returns patent number, title, "
            "abstract, filing date, grant date, assignee, and status. Use for "
            "IP research, prior art searches, and patent landscape analysis."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Technology description, patent number, inventor name, or keyword.",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of patents to return. Default 10, max 50.",
                    "default": 10,
                },
                "status": {
                    "type": "string",
                    "enum": ["all", "granted", "pending", "expired"],
                    "description": "Filter by patent status. Default 'all'.",
                    "default": "all",
                },
                "type": {
                    "type": "string",
                    "enum": ["all", "utility", "design", "plant"],
                    "description": "Filter by patent type. Default 'all'.",
                    "default": "all",
                },
                "date_from": {
                    "type": "string",
                    "description": "Filter patents filed on or after this date (YYYY-MM-DD).",
                },
                "date_to": {
                    "type": "string",
                    "description": "Filter patents filed on or before this date (YYYY-MM-DD).",
                },
                "assignee": {
                    "type": "string",
                    "description": "Filter patents by assignee / company name (e.g. 'Apple Inc.').",
                },
            },
            "required": ["query"],
        },
    },
    # 5. Google Jobs
    {
        "name": "google_jobs_search",
        "description": (
            "Search Google Jobs for open job postings. Returns job title, company, "
            "location, salary range (when available), job type, and direct application "
            "link. Use for any query about job openings, hiring, or employment opportunities."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Job title, role, or skill set (e.g. 'senior Python engineer remote').",
                },
                "location": {
                    "type": "string",
                    "description": "City, state, or country to filter jobs geographically.",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of job listings to return. Default 10, max 50.",
                    "default": 10,
                },
                "date_posted": {
                    "type": "string",
                    "enum": ["any", "past_hour", "past_day", "past_week", "past_month"],
                    "description": "Filter by how recently the job was posted.",
                    "default": "any",
                },
                "employment_type": {
                    "type": "string",
                    "enum": ["all", "full_time", "part_time", "contractor", "intern"],
                    "description": "Filter by employment type.",
                    "default": "all",
                },
                "remote": {
                    "type": "boolean",
                    "description": "If true, only return remote-eligible positions.",
                    "default": False,
                },
            },
            "required": ["query"],
        },
    },
    # 6. Google Finance
    {
        "name": "google_finance_search",
        "description": (
            "Retrieve stock prices, financial summaries, earnings data, and market "
            "indices from Google Finance. Returns current price, daily change, market "
            "cap, P/E ratio, and recent news headlines for the queried ticker or company."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Ticker symbol or company name (e.g. 'AAPL', 'Tesla', 'NIFTY 50').",
                },
                "exchange": {
                    "type": "string",
                    "description": "Stock exchange code to disambiguate (e.g. 'NASDAQ', 'NSE', 'LSE').",
                },
                "include_news": {
                    "type": "boolean",
                    "description": "Include recent financial news headlines. Default true.",
                    "default": True,
                },
                "period": {
                    "type": "string",
                    "enum": ["1d", "5d", "1m", "6m", "1y", "5y"],
                    "description": "Historical price period for chart data. Default '1d'.",
                    "default": "1d",
                },
            },
            "required": ["query"],
        },
    },
    # 7. Google Maps
    {
        "name": "google_maps_search",
        "description": (
            "Search Google Maps for directions, place details, coordinates, and "
            "route information. Returns place name, formatted address, GPS coordinates, "
            "place ID, opening hours, and user rating. Use when precise map data, "
            "navigation context, or address geocoding is needed."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Place name, address, or category (e.g. 'Eiffel Tower', '1600 Pennsylvania Ave NW').",
                },
                "ll": {
                    "type": "string",
                    "description": "Latitude and longitude for proximity search in format '@lat,lng,zoom' (e.g. '@40.7128,-74.0060,14z').",
                },
                "type": {
                    "type": "string",
                    "description": "Place type filter (e.g. 'restaurant', 'hospital', 'atm').",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of map results to return. Default 10.",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    # 8. Google Flights
    {
        "name": "google_flights_search",
        "description": (
            "Search Google Flights for available flights, prices, and schedules "
            "between two airports or cities. Returns airline, flight number, "
            "departure/arrival times, duration, stops, and fare class. Use for "
            "any query about air travel, ticket prices, or route availability."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "departure_id": {
                    "type": "string",
                    "description": "IATA airport code or city name for departure (e.g. 'BLR', 'New York').",
                },
                "arrival_id": {
                    "type": "string",
                    "description": "IATA airport code or city name for arrival (e.g. 'DEL', 'London').",
                },
                "outbound_date": {
                    "type": "string",
                    "description": "Outbound flight date in YYYY-MM-DD format.",
                },
                "return_date": {
                    "type": "string",
                    "description": "Return flight date in YYYY-MM-DD format. Omit for one-way.",
                },
                "travel_class": {
                    "type": "integer",
                    "enum": [1, 2, 3, 4],
                    "description": "1=Economy, 2=Premium Economy, 3=Business, 4=First. Default 1.",
                    "default": 1,
                },
                "adults": {
                    "type": "integer",
                    "description": "Number of adult passengers. Default 1.",
                    "default": 1,
                },
                "currency": {
                    "type": "string",
                    "description": "Currency code for price display (e.g. 'USD', 'INR', 'EUR'). Default 'USD'.",
                    "default": "USD",
                },
            },
            "required": ["departure_id", "arrival_id", "outbound_date"],
        },
    },
    # 9. Google Hotels
    {
        "name": "google_hotels_search",
        "description": (
            "Search Google Hotels for available accommodations with pricing, ratings, "
            "and amenity information. Returns hotel name, star rating, price per night, "
            "address, guest score, and featured amenities. Use for travel accommodation "
            "queries or hotel price comparisons."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Destination city, region, or specific hotel name.",
                },
                "check_in_date": {
                    "type": "string",
                    "description": "Check-in date in YYYY-MM-DD format.",
                },
                "check_out_date": {
                    "type": "string",
                    "description": "Check-out date in YYYY-MM-DD format.",
                },
                "adults": {
                    "type": "integer",
                    "description": "Number of adult guests. Default 2.",
                    "default": 2,
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of hotel results to return. Default 10.",
                    "default": 10,
                },
                "min_price": {
                    "type": "number",
                    "description": "Minimum nightly rate filter in local currency.",
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum nightly rate filter in local currency.",
                },
                "star_rating": {
                    "type": "integer",
                    "enum": [1, 2, 3, 4, 5],
                    "description": "Minimum hotel star rating filter.",
                },
                "amenities": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Required amenities (e.g. ['free_wifi', 'pool', 'parking']).",
                },
            },
            "required": ["query", "check_in_date", "check_out_date"],
        },
    },
    # 10. Google Images
    {
        "name": "google_images_search",
        "description": (
            "Search Google Images and return image results with title, source URL, "
            "thumbnail, full-size image URL, and source domain. Use when the user "
            "needs visual content, image references, or wants to find images of a "
            "specific subject, product, or place."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search term for images (e.g. 'golden retriever puppy', 'Eiffel Tower night').",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of images to return. Default 10, max 100.",
                    "default": 10,
                },
                "safe_search": {
                    "type": "string",
                    "enum": ["active", "moderate", "off"],
                    "description": "Safe search level. Default 'moderate'.",
                    "default": "moderate",
                },
                "image_type": {
                    "type": "string",
                    "enum": ["any", "face", "photo", "clipart", "lineart", "animated"],
                    "description": "Filter by image type.",
                    "default": "any",
                },
                "color": {
                    "type": "string",
                    "description": "Filter by dominant colour (e.g. 'red', 'black', 'white').",
                },
                "license": {
                    "type": "string",
                    "enum": ["any", "cc", "commercial"],
                    "description": "Filter by licence type. Default 'any'.",
                    "default": "any",
                },
            },
            "required": ["query"],
        },
    },
    # 11. Google News
    {
        "name": "google_news_search",
        "description": (
            "Search Google News for recent news articles on any topic. Returns "
            "article headline, source, publication date, snippet, and link. "
            "Use for current events, breaking news, recent developments, or "
            "tracking news coverage of a specific topic or entity."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "News topic, event, or entity name.",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of news articles to return. Default 10, max 100.",
                    "default": 10,
                },
                "language": {
                    "type": "string",
                    "description": "BCP-47 language code for results (e.g. 'en', 'hi', 'es'). Default 'en'.",
                    "default": "en",
                },
                "country": {
                    "type": "string",
                    "description": "Two-letter country code to localise news (e.g. 'us', 'in', 'gb').",
                    "default": "us",
                },
                "date_range": {
                    "type": "string",
                    "enum": ["any", "past_hour", "past_day", "past_week", "past_month", "past_year"],
                    "description": "Recency filter for articles.",
                    "default": "any",
                },
                "topic": {
                    "type": "string",
                    "enum": ["all", "world", "business", "technology", "entertainment", "sports", "science", "health"],
                    "description": "News topic category filter.",
                    "default": "all",
                },
            },
            "required": ["query"],
        },
    },
    # 12. Google Trends
    {
        "name": "google_trends_search",
        "description": (
            "Retrieve Google Trends data for search interest over time, related "
            "queries, and geographic breakdown for a given keyword or topic. "
            "Returns interest-over-time scores (0–100), top related queries, "
            "and region-level breakdown. Use for market research, trend analysis, "
            "or understanding search popularity."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Keyword or topic to analyse trends for.",
                },
                "date_range": {
                    "type": "string",
                    "description": "Time period (e.g. 'now 1-d', 'now 7-d', 'today 12-m', '2020-01-01 2024-01-01').",
                    "default": "today 12-m",
                },
                "geo": {
                    "type": "string",
                    "description": "Two-letter country code to scope trends geographically (e.g. 'US', 'IN'). Default worldwide.",
                    "default": "",
                },
                "category": {
                    "type": "integer",
                    "description": "Trends category ID to narrow the topic context (0 = all categories).",
                    "default": 0,
                },
                "compare_terms": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Up to 4 additional terms to compare with the primary query.",
                },
            },
            "required": ["query"],
        },
    },
    # 13. Google Events
    {
        "name": "google_events_search",
        "description": (
            "Search Google Events for upcoming public events, concerts, conferences, "
            "and local happenings. Returns event name, date and time, venue, "
            "address, ticket link, and description snippet. Use for queries about "
            "upcoming events, concerts, sports matches, or local activities."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Event type, name, or topic (e.g. 'Taylor Swift concert', 'AI conference Bangalore').",
                },
                "location": {
                    "type": "string",
                    "description": "City or region to search events in.",
                },
                "date_range": {
                    "type": "string",
                    "enum": ["any", "today", "tomorrow", "this_week", "this_weekend", "next_week", "this_month"],
                    "description": "When the event should occur.",
                    "default": "any",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of events to return. Default 10.",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
    },
    # 14. Google Lens
    {
        "name": "google_lens_search",
        "description": (
            "Perform a visual search using Google Lens on a provided image URL. "
            "Returns visually similar images, identified objects, product matches, "
            "and related search queries. Use when the user provides an image URL "
            "and wants to identify, match, or find similar visual content."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "Publicly accessible URL of the image to analyse.",
                },
                "country": {
                    "type": "string",
                    "description": "Two-letter country code for localised results. Default 'us'.",
                    "default": "us",
                },
                "language": {
                    "type": "string",
                    "description": "Language code for result text. Default 'en'.",
                    "default": "en",
                },
            },
            "required": ["url"],
        },
    },
    # 15. Google Play Store
    {
        "name": "google_play_search",
        "description": (
            "Search the Google Play Store for Android applications. Returns app name, "
            "developer, rating, number of reviews, price, category, and install count. "
            "Use for queries about mobile apps, Android software recommendations, "
            "or app comparisons."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "App name, category, or keyword (e.g. 'best note-taking app', 'Spotify').",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of app results to return. Default 10.",
                    "default": 10,
                },
                "category": {
                    "type": "string",
                    "description": "Play Store category filter (e.g. 'PRODUCTIVITY', 'GAME_ACTION', 'HEALTH_AND_FITNESS').",
                },
                "price": {
                    "type": "string",
                    "enum": ["all", "free", "paid"],
                    "description": "Filter by app price. Default 'all'.",
                    "default": "all",
                },
                "min_rating": {
                    "type": "number",
                    "description": "Minimum average rating filter (1.0 – 5.0).",
                },
                "country": {
                    "type": "string",
                    "description": "Two-letter country code for the Play Store region. Default 'us'.",
                    "default": "us",
                },
            },
            "required": ["query"],
        },
    },
    # 16. Google Autocomplete
    {
        "name": "google_autocomplete",
        "description": (
            "Retrieve Google search autocomplete suggestions for a partial query string. "
            "Returns an ordered list of suggested completions as Google would display "
            "them in the search bar. Use when you want to understand related search "
            "terms, query variations, or popular search completions for a topic."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Partial query string to autocomplete (e.g. 'best python lib').",
                },
                "language": {
                    "type": "string",
                    "description": "Language code for suggestions. Default 'en'.",
                    "default": "en",
                },
                "country": {
                    "type": "string",
                    "description": "Country code to localise suggestions. Default 'us'.",
                    "default": "us",
                },
            },
            "required": ["query"],
        },
    },
    # 17. YouTube Search
    {
        "name": "youtube_search",
        "description": (
            "Search YouTube for videos matching a query. Returns video title, "
            "channel name, view count, upload date, duration, description snippet, "
            "and direct URL. Use for queries about video content, tutorials, "
            "reviews, or entertainment on YouTube."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Video search query (e.g. 'Python tutorial beginners 2024', 'iPhone 15 review').",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of video results to return. Default 10.",
                    "default": 10,
                },
                "date_uploaded": {
                    "type": "string",
                    "enum": ["any", "past_hour", "today", "this_week", "this_month", "this_year"],
                    "description": "Filter by upload recency.",
                    "default": "any",
                },
                "duration": {
                    "type": "string",
                    "enum": ["any", "short", "medium", "long"],
                    "description": "Filter by video duration. Short <4min, medium 4-20min, long >20min.",
                    "default": "any",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["relevance", "upload_date", "view_count", "rating"],
                    "description": "Sort order for results.",
                    "default": "relevance",
                },
                "video_type": {
                    "type": "string",
                    "enum": ["any", "video", "channel", "playlist", "movie"],
                    "description": "Filter by content type.",
                    "default": "video",
                },
            },
            "required": ["query"],
        },
    },
    # 18. eBay Search
    {
        "name": "ebay_search",
        "description": (
            "Search eBay for product listings including both new and used items. "
            "Returns listing title, price, condition, seller rating, shipping cost, "
            "and listing URL. Use for queries about second-hand goods, collectibles, "
            "auction items, or price comparisons with eBay specifically."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Product name or description to search on eBay.",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of listings to return. Default 10, max 50.",
                    "default": 10,
                },
                "condition": {
                    "type": "string",
                    "enum": ["all", "new", "used", "refurbished"],
                    "description": "Filter by item condition.",
                    "default": "all",
                },
                "min_price": {
                    "type": "number",
                    "description": "Minimum listing price in USD.",
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum listing price in USD.",
                },
                "listing_type": {
                    "type": "string",
                    "enum": ["all", "auction", "buy_it_now"],
                    "description": "Filter by listing type.",
                    "default": "all",
                },
                "free_shipping": {
                    "type": "boolean",
                    "description": "If true, only return listings with free shipping.",
                    "default": False,
                },
            },
            "required": ["query"],
        },
    },
    # 19. Walmart Search
    {
        "name": "walmart_search",
        "description": (
            "Search Walmart's product catalogue for items sold on Walmart.com "
            "or in-store. Returns product name, price, availability, customer "
            "rating, review count, and seller (Walmart or third-party). Use for "
            "Walmart-specific price lookups, grocery items, or bulk goods queries."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Product name or keyword to search on Walmart.",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of products to return. Default 10.",
                    "default": 10,
                },
                "min_price": {
                    "type": "number",
                    "description": "Minimum price filter in USD.",
                },
                "max_price": {
                    "type": "number",
                    "description": "Maximum price filter in USD.",
                },
                "availability": {
                    "type": "string",
                    "enum": ["all", "in_stock", "pickup_today"],
                    "description": "Filter by item availability.",
                    "default": "all",
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["best_match", "price_low", "price_high", "best_seller", "best_rated"],
                    "description": "Sort order for results. Default 'best_match'.",
                    "default": "best_match",
                },
                "store_id": {
                    "type": "string",
                    "description": "Walmart store ID for in-store availability check.",
                },
            },
            "required": ["query"],
        },
    },
    # 20. Yelp Search
    {
        "name": "yelp_search",
        "description": (
            "Search Yelp for local businesses, restaurants, and services with "
            "crowd-sourced reviews and ratings. Returns business name, address, "
            "phone, Yelp rating, review count, price tier, hours, and categories. "
            "Use for local business queries where Yelp review depth is specifically "
            "needed, or for restaurant discovery with community review context."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Business type or name (e.g. 'best tacos', 'auto mechanic').",
                },
                "location": {
                    "type": "string",
                    "description": "City, zip code, neighbourhood, or address string.",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of business listings to return. Default 10, max 50.",
                    "default": 10,
                },
                "radius_meters": {
                    "type": "integer",
                    "description": "Search radius in metres (max 40000). Default 8000.",
                    "default": 8000,
                },
                "categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Yelp category aliases to filter by (e.g. ['mexican', 'pizza']).",
                },
                "price_tiers": {
                    "type": "array",
                    "items": {"type": "integer", "enum": [1, 2, 3, 4]},
                    "description": "Price tier filter: 1=$, 2=$$, 3=$$$, 4=$$$$.",
                },
                "open_now": {
                    "type": "boolean",
                    "description": "If true, only return businesses currently open.",
                    "default": False,
                },
                "sort_by": {
                    "type": "string",
                    "enum": ["best_match", "rating", "review_count", "distance"],
                    "description": "Sort order for results. Default 'best_match'.",
                    "default": "best_match",
                },
            },
            "required": ["query", "location"],
        },
    },
]

# ---------------------------------------------------------------------------
# Single Universal_Search schema (what this project exposes)
# ---------------------------------------------------------------------------

UNIVERSAL_SEARCH_SCHEMA: dict = {
    "name": "Universal_Search",
    "description": (
        "Search the web for any query — products, prices, academic papers, research, "
        "local businesses, patents, or general information. Automatically selects "
        "the best SerpApi engine (Google Shopping, Scholar, Local, Patents, or base "
        "Search) based on semantic analysis of the query. Supports dual-engine "
        "routing for ambiguous queries that span two domains. Returns structured, "
        "typed results with routing metadata."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "The natural-language search query. Can be anything — a product "
                    "name, research topic, local business search, patent lookup, or "
                    "general question. The router will automatically choose the right engine."
                ),
            },
        },
        "required": ["query"],
    },
}
