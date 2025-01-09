from deezer_client import DeezerClient  

class SwipingLogic:
    def __init__(self, deezer_client, queue_size=5):
        """
        Initialize the SwipingLogic to store user preferences and manage the track queue.

        Args:
            deezer_client (DeezerClient): An instance of DeezerClient to fetch tracks.
            queue_size (int): Number of tracks to preload in the queue.
        """
        self.deezer_client = deezer_client
        self.queue_size = queue_size
        self.liked_tracks = []  # Tracks the user has liked
        self.disliked_tracks = []  # Tracks the user has disliked
        self.track_queue = []  # Preloaded track queue
        self.previous_tracks = []  # Tracks the user has listened to
        self._preload_queue()  # Load initial tracks into the queue

    def _preload_queue(self):
        """
        Preload the track queue with random tracks.
        """
        while len(self.track_queue) < self.queue_size:
            track = self.deezer_client.get_random_track(limit=1)
            if track:
                self.track_queue.append(track)

    def get_next_track(self):
        """
        Get the next track in the queue and preload another.

        Returns:
            dict: The next track in the queue.
        """
        if not self.track_queue:
            self._preload_queue()  # Ensure queue is filled if empty

        next_track = self.track_queue.pop(0)  # Get the next track in the queue

        # Add the track to the previous_tracks history
        self.previous_tracks.append(next_track)

        # Keep the previous_tracks list within bounds (e.g., last 10 tracks)
        if len(self.previous_tracks) > 10:
            self.previous_tracks.pop(0)

        self._preload_queue()  # Replenish the queue
        return next_track

    def get_previous_track(self):
        """
        Get the most recently played track.

        Returns:
            dict: The last played track, or None if no previous tracks are available.
        """
        if self.previous_tracks:
            return self.previous_tracks[-1]
        else:
            print("No previous tracks available.")
            return None

    def like_track(self, track):
        """
        Handle the event when a user likes a track.

        Args:
            track (dict): The track that was liked.
        """
        self.liked_tracks.append(track)

    def dislike_track(self, track):
        """
        Handle the event when a user dislikes a track.

        Args:
            track (dict): The track that was disliked.
        """
        self.disliked_tracks.append(track)

    def get_liked_tracks(self):
        """
        Get the list of tracks the user has liked.

        Returns:
            list: A list of liked tracks.
        """
        return self.liked_tracks

    def get_disliked_tracks(self):
        """
        Get the list of tracks the user has disliked.

        Returns:
            list: A list of disliked tracks.
        """
        return self.disliked_tracks
