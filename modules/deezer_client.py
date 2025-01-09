import requests
import random
import string

# Deezer API base URL
DEEZER_API_BASE = "https://api.deezer.com"

class DeezerClient:
    def __init__(self):
        self.api_base = DEEZER_API_BASE
        # Common letters that typically return results
        self._common_letters = 'aeiourstlnm'

    def _generate_random_query(self):
        """Generate a random search query with higher chance of results."""
        query_types = [
            # Single common letter (highest success rate)
            lambda: random.choice(self._common_letters),
            # Two common letters
            lambda: ''.join(random.choices(self._common_letters, k=2)),
            # Single any letter
            lambda: random.choice(string.ascii_lowercase)
        ]
        
        # Weight heavily towards common letters
        weights = [0.6, 0.3, 0.1]
        query_generator = random.choices(query_types, weights=weights)[0]
        return query_generator()

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

    def get_track_by_genre(self, genre="pop", limit=1, extended_json=False):
        """
        Search for tracks based on genre and return a randomly selected track with detailed information.
        """
        url = f"{self.api_base}/search/track"
        params = {
            "q": f"genre:'{genre}'",
            "limit": 100,
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
    y = deezer_client.get_random_track()
    print(y)