# genres.py

# Core genres with subgenres, expanded electronic categories
MUSIC_GENRES = {
    "electronic": [
        # Main electronic genres
        "electronic", "edm", "dance", "electronica",
        
        # House music variants
        "house", "deep house", "tech house", "progressive house", "tropical house",
        "future house", "electro house", "bass house", "minimal house",
        
        # Techno variants
        "techno", "minimal techno", "industrial techno", "hard techno", "melodic techno",
        
        # Bass music
        "dubstep", "drum and bass", "bass", "future bass", "trap", "hardstyle",
        "drumstep", "breakbeat", "jungle", "neurofunk",
        
        # Trance variants
        "trance", "progressive trance", "psytrance", "uplifting trance",
        "vocal trance", "goa trance", "hard trance",
        
        # Other electronic subgenres
        "ambient", "downtempo", "synthwave", "vaporwave", "lofi",
        "glitch hop", "industrial", "idm", "experimental electronic",
        
        # Fusion genres
        "electropop", "electroclash", "electronic rock", "electronic metal",
        "nu disco", "disco house", "future funk"
    ],
    
    "pop": ["pop", "dance pop", "electropop", "indie pop", "synth-pop", "k-pop", 
            "art pop", "experimental pop", "hyperpop"],
    
    "hip_hop": ["hip hop", "rap", "trap", "drill", "grime", "conscious hip hop",
                "alternative hip hop", "cloud rap", "lo-fi hip hop"],
    
    "rock": ["rock", "alternative rock", "indie rock", "metal", "classic rock", "punk",
             "progressive rock", "electronic rock", "post-rock"],
    
    "rnb": ["r&b", "soul", "funk", "contemporary r&b", "neo soul",
            "future soul", "electronic soul"],
    
    "latin": ["latin", "reggaeton", "latin pop", "salsa", "bachata", "latin rap",
              "latin electronic", "latin house"],
    
    "jazz": ["jazz", "smooth jazz", "jazz fusion", "nu jazz", "electronic jazz",
             "jazz house", "acid jazz"],
    
    "classical": ["classical", "orchestra", "chamber music", "opera", "symphony",
                 "contemporary classical", "minimal classical"],
    
    "world": ["world", "afrobeat", "african electronic", "asian electronic",
              "global bass", "tribal house", "ethnic electronic"],
    
    "experimental": ["experimental", "avant-garde", "noise", "drone",
                    "glitch", "industrial", "sound art"]
}

# Additional electronic artists for better results
ELECTRONIC_ARTISTS = [
    "Daft Punk", "Deadmau5", "Aphex Twin", "Chemical Brothers", "Boards of Canada",
    "Burial", "Four Tet", "Bonobo", "Jon Hopkins", "Tycho", "Flume", "Odesza",
    "Above & Beyond", "Eric Prydz", "Carl Cox", "Nina Kraviz", "Boris Brejcha",
    "Skrillex", "Calvin Harris", "Swedish House Mafia", "Fatboy Slim", "The Prodigy",
    "Underworld", "Massive Attack", "Röyksopp", "Justice", "Disclosure", "Jamie xx"
]

# Popular electronic genres that typically return more results
POPULAR_ELECTRONIC_GENRES = [
    "electronic", "house", "techno", "trance", "dubstep", "drum and bass",
    "edm", "dance", "electronica", "deep house", "tech house", "future bass"
]

POPULAR_ARTISTS = [
"Drake", "Taylor Swift", "Ed Sheeran", "The Weeknd", "Eminem",
"Rihanna", "Justin Bieber", "Ariana Grande", "Post Malone", "Bad Bunny",
"BTS", "Coldplay", "Kanye West", "Lady Gaga", "Bruno Mars"
]

# Flattened list for direct random selection
ALL_GENRES = [genre for sublist in MUSIC_GENRES.values() for genre in sublist]

# Popular genres across all categories
POPULAR_GENRES = [
    "pop", "hip hop", "rap", "rock", "electronic", "edm", "house", "techno",
    "r&b", "latin", "dance pop", "trap", "indie", "deep house", "future bass"
]