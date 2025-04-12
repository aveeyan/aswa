import requests
import random
from genres import (MUSIC_GENRES, ALL_GENRES, POPULAR_GENRES, 
                   ELECTRONIC_ARTISTS, POPULAR_ELECTRONIC_GENRES, POPULAR_ARTISTS)

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

    def _get_random_genre(self, electronic_bias=0.4, popular_bias=0.7):
        """
        Get a random genre with bias towards electronic and popular genres.
        electronic_bias: probability of selecting electronic genre
        popular_bias: probability of selecting from popular genres when not electronic
        """
        if random.random() < electronic_bias:
            # Select electronic genre
            if random.random() < popular_bias:
                return random.choice(self.popular_electronic)
            return random.choice(self.electronic_genres)
        else:
            # Select from all genres
            if random.random() < popular_bias:
                return random.choice(self.popular_genres)
            return random.choice(self.all_genres)

    def _get_random_artist(self, electronic_bias=0.4):
        """Get random artist with bias towards electronic artists."""
        if random.random() < electronic_bias:
            return random.choice(ELECTRONIC_ARTISTS)
        return random.choice(self.popular_artists)

    def _generate_random_query(self):
        """Generate a search query using artist, genre, or combination."""
        query_types = [
            # Artist-based query
            lambda: random.choice(self.popular_artists),
            # Genre-based query
            lambda: f"genre:'{self._get_random_genre()}'",
            # Combined artist and genre
            lambda: f"artist:'{self._get_random_artist()}' genre:'{self._get_random_genre()}'",
            # Electronic-focused query
            lambda: f"genre:'{random.choice(self.popular_electronic)}'"
        ]
        weights = [0.3, 0.3, 0.2, 0.2]
        return random.choices(query_types, weights=weights)[0]()

    def get_random_track(self, limit=1, extended_json=False, max_retries=3):
        """
        Fetch a randomly selected track from a pool of tracks without genre or specific filtering.
        """
        url = f"{self.api_base}/search/track"  # Specifically search tracks
        
        for attempt in range(max_retries):
            params = {
                "q": self._generate_random_query(),
                "limit": 100,  # Maximum allowed by Deezer
                "index": random.randint(0, 200)  # More conservative index range
            }
            
            response = requests.get(url, params=params)
            if response.status_code == 200:
                response_json = response.json()
                tracks = response_json.get("data", [])
                if tracks:
                    random_track = random.choice(tracks)
                    if extended_json:
                        return response_json
                    else:
                        return self._get_json_for_frontend(random_track)
                else:
                    if attempt < max_retries - 1:
                        print("No tracks found. Retrying with new query...")
                    else:
                        print("Maximum retries reached. Could not find tracks.")
            else:
                print(f"Error fetching tracks: {response.status_code}")
                return None
        
        return None
    
    def get_searched_track(self, query, extended_json=False):
        """
        Fetch the top track from a search query.
        
        Args:
            query (str): Search query string
            extended_json (bool): Whether to return full response or just track data
            
        Returns:
            dict: Track information or None if no tracks found
        """
        url = f"{self.api_base}/search/track"
        params = {
            "q": query,
            "limit": 1,  # Only need the top result
            "order": "RANKING"  # Sort by relevance
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            response_json = response.json()
            tracks = response_json.get("data", [])
            
            if tracks:
                if extended_json:
                    return response_json
                else:
                    return self._get_json_for_frontend(tracks[0])
            else:
                print(f"No tracks found for query: {query}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Error fetching track: {str(e)}")
            return None


    def get_track_by_genre(self, genre="pop", limit=100, extended_json=False):
        """
        Search for tracks based on genre and return a randomly selected track with detailed information.
        """
        url = f"{self.api_base}/search/track"
        params = {
            "q": f"genre:'{genre}'",
            "limit": limit,
            "index": random.randint(0, 200)
        }
        
        response = requests.get(url, params=params)
        if response.status_code == 200:
            response_json = response.json()
            tracks = response_json.get("data", [])
            if tracks:
                random_track = random.choice(tracks)
                if extended_json:
                    return response_json
                else:
                    return self._get_json_for_frontend(random_track)
            else:
                print("No tracks found for this genre.")
                return None
        else:
            print(f"Error fetching tracks: {response.status_code}")
            return None

    def get_track_by_id(self, track_id, extended_json=False):
        """
        Fetch detailed information about a track using its ID.
        """
        url = f"{self.api_base}/track/{track_id}"
        response = requests.get(url)
        if response.status_code == 200:
            response_json = response.json()
            if extended_json:
                return response_json
            else:
                return self._get_json_for_frontend(response_json)
        else:
            print(f"Error fetching track by ID: {response.status_code}")
            return None

    def _get_json_for_frontend(self, json):
        """Format the JSON response for frontend use."""
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

if __name__ == "__main__":
    deezer_client = DeezerClient()
    y = deezer_client.get_searched_track("where are u now")
    print(y)