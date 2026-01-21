# rss_feed_etl/config/feeds.py

"""
RSS feed configuration file.
Defines RSS feed names and URLs for ETL ingestion.

Add or remove feeds as needed.
"""

FEEDS = [
    {
        "name": "Department of War General Officer Announcements",
        "url": "https://www.war.gov/DesktopModules/ArticleCS/RSS.ashx?ContentType=9&Site=945&max=100",
        "filters": {
            "link_keywords": ["general-officer", "flag-officer", "senior-enlisted"],
            # "title_keywords": ["promotion", "assignment", "nomination", "general", "admiral"],
            # "summary_keywords": ["promotion", "command", "assignment"]
        }
    },
    # {
    #     "name": "U.S. Army News",
    #     "url": "https://www.army.mil/rss/static/1.xml"
    # },
    # {
    #     "name": "National Guard News",
    #     "url": "http://www.nationalguard.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=688&Category=11199&max=20"
    # },
    # {
    #     "name": "National Guard Overseas Operations",
    #     "url": "http://www.nationalguard.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=688&Category=11200&max=20"
    # },
    # {
    #     "name": "Department of War News",
    #     "url": "https://www.war.gov/News/RSS/"
    # },
    # {
    #     "name": "U.S. Navy Top Stories",
    #     "url": "https://www.navy.mil/DesktopModules/ArticleCS/RSS.ashx?ContentType=1&Site=1067&max=10"
    # },
    # Add more feeds here...
]
