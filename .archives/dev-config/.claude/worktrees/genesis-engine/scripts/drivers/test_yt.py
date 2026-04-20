from youtube_transcript_api import YouTubeTranscriptApi


print(f"Type: {type(YouTubeTranscriptApi)}")
try:
    print("Trying to instantiate and call list()...")
    api = YouTubeTranscriptApi()
    print(api.list("mAvvO89B2N0"))
except Exception as e:
    print(f"Instantiation/Call failed: {e}")

from youtube_transcript_api import YouTubeTranscriptApi as YTA


print(f"Module member: {YTA}")
