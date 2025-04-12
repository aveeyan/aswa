import requests
import random
import time
import logging
from modules.genres import (MUSIC_GENRES, ALL_GENRES, POPULAR_GENRES, 
                   ELECTRONIC_ARTISTS, POPULAR_ELECTRONIC_GENRES, POPULAR_ARTISTS)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Deezer API base URL
DEEZER_API_BASE = "https://api.deezer.com"

class DeezerClient:
    def __init__(self):
        self.api_base = DEEZER_API_BASE
        # Combine mainstream and electronic artists
        self.popular_artists = POPULAR_ARTISTS + ELECTRONIC_ARTISTS
        
        # Cache the genres for efficient access
        self.all_genres = ALL_GENRES
        self.popular_genres = POPULAR_GENRES
        self.electronic_genres = MUSIC_GENRES["electronic"]
        self.popular_electronic = POPULAR_ELECTRONIC_GENRES

        # Track history for navigation - unlimited length
        self.track_history = []
        self.current_track_index = -1
        
        # Track IDs we've already seen to avoid duplicates
        self.seen_track_ids = set()
        
        # Parameters for randomization
        self.max_offset = 1000  # Reduced to avoid API issues
        self.letters = 'abcdefghijklmnopqrstuvwxyz'
        self.request_delay = 0.05  # Small delay to avoid rate limits
        self.request_timeout = 5  # Timeout for API requests
        
        # Try to preload initial tracks, but don't crash if it fails
        try:
            self._preload_tracks(10)  # Reduced to 10 for faster startup
        except Exception as e:
            logger.error(f"Error during initial track preloading: {e}")
            # Make sure we have at least one track to display
            self._fallback_track()

    def _fallback_track(self):
        """Create a fallback track if we can't get anything from API"""
        fallback = {
            "id_deezer": 0,
            "title": "Random Music",
            "link": "https://www.deezer.com",
            "is_explicit": False,
            "preview": "",
            "artist": "Various Artists",
            "album": "Random Selection",
            "cover": "https://e-cdns-images.dzcdn.net/images/cover/1000x1000-000000-80-0-0.jpg",
            "cover_xl": "https://e-cdns-images.dzcdn.net/images/cover/1000x1000-000000-80-0-0.jpg"
        }
        self.track_history = [fallback]
        self.current_track_index = 0
        return fallback

    def _get_random_genre(self, electronic_bias=0.4, popular_bias=0.6):
        """Get a random genre with adjusted bias"""
        try:
            if random.random() < electronic_bias:
                # Select electronic genre
                if random.random() < popular_bias:
                    return random.choice(self.popular_electronic)
                return random.choice(self.electronic_genres)
            else:
                # Select from all genres with focus on diversity
                if random.random() < popular_bias:
                    return random.choice(self.popular_genres)
                return random.choice(self.all_genres)
        except Exception as e:
            logger.error(f"Error selecting genre: {e}")
            return "pop"  # Default to pop if something goes wrong

    def _preload_tracks(self, count=10):
        """Preload a batch of tracks for smooth navigation"""
        logger.info(f"Preloading {count} tracks...")
        tracks = []
        attempts = 0
        max_attempts = count * 3  # Allow for some failures
        
        # Try to get unique tracks up to count
        while len(tracks) < count and attempts < max_attempts:
            attempts += 1
            try:
                # Use different strategies to increase randomness
                track = self.get_random_track(add_to_history=False, preloading=True)
                    
                if track:
                    tracks.append(track)
            except Exception as e:
                logger.error(f"Error during track preloading (attempt {attempts}): {e}")
            
            # Small delay to avoid API rate limits
            time.sleep(self.request_delay)
        
        logger.info(f"Successfully preloaded {len(tracks)} tracks")
        
        # If this is initial load, set them as track history
        if not self.track_history:
            self.track_history = tracks if tracks else [self._fallback_track()]
            self.current_track_index = 0
        
        return tracks

    def get_multiple_tracks(self, count=10):
        """Fetch multiple unique random tracks"""
        try:
            logger.info(f"Getting {count} multiple tracks...")
            # Clear existing history if any
            self.track_history = []
            self.current_track_index = -1
            
            # Get fresh tracks
            tracks = self._preload_tracks(count)
            if not tracks:  # If we couldn't get any tracks
                tracks = [self._fallback_track()]
                
            return tracks
        except Exception as e:
            logger.error(f"Error in get_multiple_tracks: {e}")
            return [self._fallback_track()]

    def get_next_track(self):
        """Get the next track in the history or a new random track if we're at the end"""
        try:
            logger.info("Getting next track...")
            # If we're near the end, try to preload more tracks
            if len(self.track_history) > 0 and self.current_track_index >= len(self.track_history) - 3:
                try:
                    # Get some new tracks in the background
                    new_tracks = []
                    for _ in range(5):  # Reduced to 5 for faster response
                        track = self.get_random_track(add_to_history=False)
                        if track:
                            new_tracks.append(track)
                    
                    # Append them to history
                    if new_tracks:
                        self.track_history.extend(new_tracks)
                        logger.info(f"Added {len(new_tracks)} new tracks to history")
                except Exception as e:
                    logger.error(f"Error preloading new tracks: {e}")
            
            # If we have tracks in history, move to next one
            if self.track_history:
                # If at the end, we now have new tracks to move to
                if self.current_track_index < len(self.track_history) - 1:
                    self.current_track_index += 1
                    return self.track_history[self.current_track_index]
            
            # If we somehow still don't have tracks, get a fresh one
            new_track = self.get_random_track(add_to_history=False)
            if new_track:
                self.track_history.append(new_track)
                self.current_track_index = len(self.track_history) - 1
                return new_track
                
            # Last resort fallback
            if not self.track_history:
                return self._fallback_track()
            return self.track_history[self.current_track_index]
            
        except Exception as e:
            logger.error(f"Error in get_next_track: {e}")
            # If something went wrong, return a fallback track
            return self._fallback_track()

    def get_previous_track(self):
        """Get the previous track in the history"""
        try:
            logger.info("Getting previous track...")
            if not self.track_history:
                return self._fallback_track()
                
            if self.current_track_index <= 0:
                # If at beginning, stay at first track
                self.current_track_index = 0
                return self.track_history[0]
            
            # Move to previous track
            self.current_track_index -= 1
            return self.track_history[self.current_track_index]
        except Exception as e:
            logger.error(f"Error in get_previous_track: {e}")
            return self._fallback_track()

    def _get_random_artist(self):
        """Get random artist"""
        try:
            if random.random() < 0.4:
                return random.choice(ELECTRONIC_ARTISTS)
            return random.choice(self.popular_artists)
        except Exception as e:
            logger.error(f"Error selecting artist: {e}")
            return "Daft Punk"  # Default if something goes wrong

    def _random_by_artist(self):
        """Get a random track by searching for a random artist"""
        artist = self._get_random_artist()
        url = f"{self.api_base}/search/track"
        params = {
            "q": f"artist:'{artist}'",
            "limit": 25,  # Reduced for faster response
            "index": random.randint(0, min(100, self.max_offset))
        }
        
        return self._fetch_and_process_track(url, params)
        
    def _random_by_genre(self):
        """Get a random track by searching for a random genre"""
        genre = self._get_random_genre()
        url = f"{self.api_base}/search/track"
        params = {
            "q": f"genre:'{genre}'",
            "limit": 25,  # Reduced for faster response
            "index": random.randint(0, min(100, self.max_offset))
        }
        
        return self._fetch_and_process_track(url, params)
        
    def _random_by_letter(self):
        """Get a random track by searching for a random letter or letter combination"""
        # Get 1-2 random letters for truly random results (reduced from 3)
        num_letters = random.randint(1, 2)
        letters = ''.join(random.choice(self.letters) for _ in range(num_letters))
        
        url = f"{self.api_base}/search/track"
        params = {
            "q": letters,
            "limit": 25,  # Reduced for faster response
            "index": random.randint(0, min(200, self.max_offset))
        }
        
        return self._fetch_and_process_track(url, params)
        
    def _random_by_year(self):
        """Get a random track by searching for a random year"""
        # Random year between 1970 and current year (narrowed range)
        year = random.randint(1970, 2023)
        
        url = f"{self.api_base}/search/track"
        params = {
            "q": f"year:'{year}'",
            "limit": 25,  # Reduced for faster response
            "index": random.randint(0, min(100, self.max_offset))
        }
        
        return self._fetch_and_process_track(url, params)
        
    def _random_by_combined(self):
        """Get a random track using a combination of search terms"""
        # Choose random combinations of search terms
        search_components = []
        
        # Maybe add a genre
        if random.random() < 0.5:
            search_components.append(f"genre:'{self._get_random_genre()}'")
        
        # Maybe add a year
        if random.random() < 0.3:
            decade = random.randint(197, 202) * 10  # 1970s to 2020s
            search_components.append(f"year:'{decade}'")
        
        # Maybe add a random letter
        if random.random() < 0.7 or not search_components:
            # Ensure we have at least one component
            search_components.append(random.choice(self.letters))
            
        query = " ".join(search_components)
        
        url = f"{self.api_base}/search/track"
        params = {
            "q": query,
            "limit": 25,  # Reduced for faster response
            "index": random.randint(0, min(100, self.max_offset))
        }
        
        return self._fetch_and_process_track(url, params)
        
    def _fetch_and_process_track(self, url, params):
        """Fetch tracks using the provided URL and parameters, then select a random track"""
        try:
            logger.debug(f"Fetching from {url} with params {params}")
            response = requests.get(url, params=params, timeout=self.request_timeout)
            
            if response.status_code == 200:
                response_json = response.json()
                tracks = response_json.get("data", [])
                
                if not tracks:
                    logger.debug("No tracks returned from API")
                    return None
                    
                # Filter out tracks we've already seen
                unseen_tracks = [t for t in tracks if t["id"] not in self.seen_track_ids]
                
                # If we have unseen tracks, use those
                if unseen_tracks:
                    random_track = random.choice(unseen_tracks)
                # If all tracks have been seen, still return something if tracks exist
                elif tracks:
                    random_track = random.choice(tracks)
                    # Refresh seen_track_ids if it gets too large (memory management)
                    if len(self.seen_track_ids) > 5000:  # Reduced threshold
                        logger.info("Resetting seen_track_ids cache")
                        self.seen_track_ids = set()
                else:
                    return None
                    
                # Add to seen track IDs
                self.seen_track_ids.add(random_track["id"])
                return self._get_json_for_frontend(random_track)
            else:
                logger.warning(f"API error {response.status_code}: {response.text}")
                return None
        except requests.exceptions.Timeout:
            logger.warning("API request timed out")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request error: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error processing track: {e}")
            return None

    def get_random_track(self, add_to_history=True, preloading=False):
        """Fetch a truly random track using various randomization strategies"""
        strategy_attempts = 0
        max_strategy_attempts = 3  # Reduced to avoid getting stuck
        
        strategies = [
            self._random_by_artist,
            self._random_by_genre,
            self._random_by_letter,
            # These two are less reliable, so added as fallbacks
            self._random_by_year,
            self._random_by_combined
        ]
        
        # Shuffle strategies for even more randomness
        random.shuffle(strategies)
        
        # Try to get a track first with more reliable strategies
        while strategy_attempts < max_strategy_attempts:
            strategy_attempts += 1
            
            for strategy in strategies[:3]:  # Try the first 3 shuffled strategies
                try:
                    track = strategy()
                    if track:
                        # If this is a standalone request and we want to add to history
                        if add_to_history and not preloading:
                            self.track_history.append(track)
                            self.current_track_index = len(self.track_history) - 1
                        
                        return track
                except Exception as e:
                    logger.error(f"Strategy error: {e}")
                
                # Small delay to avoid API rate limits
                time.sleep(self.request_delay)
        
        # If we're still here, try letter search as last resort
        try:
            return self._random_by_letter()
        except Exception as e:
            logger.error(f"Final strategy error: {e}")
            # If everything fails and we need a track now, return a fallback
            if not self.track_history or not preloading:
                return self._fallback_track()
            return None
    
    def get_track_by_search(self, query, extended_json=False):
        """Fetch tracks from a search query"""
        try:
            url = f"{self.api_base}/search/track"
            params = {
                "q": query,
                "limit": 10,
                "order": "RANKING"  # Sort by relevance
            }
            
            response = requests.get(url, params=params, timeout=self.request_timeout)
            response.raise_for_status()
            
            response_json = response.json()
            tracks = response_json.get("data", [])
            
            if tracks:
                if extended_json:
                    return response_json
                else:
                    return [self._get_json_for_frontend(track) for track in tracks]
            else:
                logger.warning(f"No tracks found for query: {query}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching tracks by search: {e}")
            return None

    def get_track_by_id(self, track_id, extended_json=False):
        """Fetch track by ID"""
        try:
            url = f"{self.api_base}/track/{track_id}"
            response = requests.get(url, timeout=self.request_timeout)
            if response.status_code == 200:
                response_json = response.json()
                if extended_json:
                    return response_json
                else:
                    return self._get_json_for_frontend(response_json)
            else:
                logger.warning(f"Error fetching track by ID: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error fetching track by ID: {e}")
            return None

    def _get_json_for_frontend(self, json):
        """Format the JSON response for frontend use"""
        try:
            result = {
                "id_deezer": json["id"],
                "title": json["title"],
                "link": json["link"],
                "is_explicit": json["explicit_lyrics"],
                "preview": json["preview"],
                "artist": json["artist"]["name"],
                "album": json["album"]["title"],
                "cover": json["album"]["cover_big"],
                "cover_xl": json["album"]["cover_xl"]
            }
            return result
        except KeyError as e:
            logger.error(f"Missing key in track data: {e}, data: {json}")
            # Return a partial result with what we have
            result = {
                "id_deezer": json.get("id", 0),
                "title": json.get("title", "Unknown Title"),
                "link": json.get("link", ""),
                "is_explicit": json.get("explicit_lyrics", False),
                "preview": json.get("preview", ""),
                "artist": json.get("artist", {}).get("name", "Unknown Artist"),
                "album": json.get("album", {}).get("title", "Unknown Album"),
                "cover": json.get("album", {}).get("cover_big", ""),
                "cover_xl": json.get("album", {}).get("cover_xl", "")
            }
            return result