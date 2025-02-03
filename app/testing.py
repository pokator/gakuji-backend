from lyricsgenius import Genius
from geniusdotpy.genius import Genius as GeniusSearch
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import random

# User-Agent Rotation
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/88.0.4324.96 Safari/537.36",
]

proxy_list_http = [
    "http://51.222.32.193:3128",
    "http://63.143.57.115:80",
    "http://135.148.149.92:3128",
]
proxy = {
    "http": random.choice(proxy_list_http)
}
# Set up Genius API
GENIUS_ACCESS_TOKEN = "8vBphHXB7yhgAb7l1t6pSgDF4pp8KpTfzSvKiRGSeZ0g3gLel39ZJ21Tyjhw43uC"
genius = Genius(GENIUS_ACCESS_TOKEN, user_agent=random.choice(USER_AGENTS))
genius_search = GeniusSearch(client_access_token=GENIUS_ACCESS_TOKEN)
genius_search.excluded_terms = ["Romanized", "English", "Translation", "Türkçe", "Português"]


def scrape_lyrics_with_selenium(url):
    """Scrape lyrics from Genius using Selenium."""
    
    options = Options()
    options.add_argument("--headless")  # Run in headless mode
    options.add_argument(f"user-agent={random.choice(USER_AGENTS)}")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    
    # 🚀 **Speed Boost: Block images & scripts**  
    options.add_argument("--blink-settings=imagesEnabled=false")
    options.add_experimental_option("prefs", {
        "profile.managed_default_content_settings.images": 2,  # Disable images
        "profile.managed_default_content_settings.stylesheets": 2,  # Disable CSS
        "profile.managed_default_content_settings.javascript": 1,  # Keep JS enabled
    })
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    
    try:
        driver.get(url) # Allow page to load

        # Find all divs where data-lyrics-container="true"
        lyrics_elements = WebDriverWait(driver, 5).until(
            EC.presence_of_all_elements_located((By.XPATH, '//div[@data-lyrics-container="true"]'))
        )

        lyrics = "\n".join([elem.text for elem in lyrics_elements if elem.text.strip()])
        return lyrics

    except Exception as e:
        print("Error scraping lyrics:", e)
        return None

    finally:
        driver.quit()


def get_lyrics(artist, title):
    """Retrieve lyrics from Genius API or scrape if necessary."""
    
    songs = genius_search.search(title)
    song_id = None
    url = None

    for track in songs:
        if artist in track.artist.name:
            song_id = track.id
            url = track.url
            break

    lyrics = None
    # if song_id:
    #     print("Using Genius API...")
    #     song_data = genius.search_song(song_id=song_id)
    #     if song_data:
    #         lyrics = song_data.lyrics  

    if not lyrics and url:
        print("Scraping Genius page for lyrics...")
        lyrics = scrape_lyrics_with_selenium(url)

    return lyrics


# Example Usage
artist = "Yoko Takahashi"
title = "魂のルフラン"
lyrics = get_lyrics(artist, title)

if lyrics:
    print("\n🎵 Lyrics Found:\n", lyrics, "...")  # Print first 500 characters
else:
    print("\n❌ Lyrics not found.")
