import requests
import csv
import os
import subprocess
from datetime import datetime

# Authenticate with GitHub CLI and set secret
def set_github_secret():
    try:
        # Ensure gh CLI is installed and authenticated
        subprocess.run(["gh", "auth", "login"], check=True)
        # Get the auth token
        token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
        # Set the token as a GitHub secret
        subprocess.run([
            "gh", "secret", "set", "YOUTUBE_API_KEY",
            "--body", os.getenv("YOUTUBE_API_KEY", "AIzaSyDFwpcKOitR9NQ-7GssXLmClVog1y1SsGs"),
            "--repo", "aldoyh/youtube-stats"
        ], check=True)
        print("GitHub secret set successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error setting GitHub secret: {e}")
        exit(1)

# Update README with latest stats
def update_readme(latest_stats):
    readme_path = "README.md"
    with open(readme_path, "r") as f:
        content = f.read()
    # Replace placeholder with latest stats
    new_content = content.replace("{{latest_stats}}", latest_stats)
    with open(readme_path, "w") as f:
        f.write(new_content)

# Fetch YouTube stats
API_KEY = os.getenv("YOUTUBE_API_KEY", "AIzaSyDFwpcKOitR9NQ-7GssXLmClVog1y1SsGs")
CHANNEL_ID = "UCylIWXb8bRI0KcDeJG6H8rw"

# Fetch channel statistics
channel_url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={CHANNEL_ID}&key={API_KEY}"
channel_response = requests.get(channel_url).json()
if "error" in channel_response:
    print(f"Error fetching channel stats: {channel_response['error']['message']}")
    exit(1)
stats = channel_response["items"][0]["statistics"]
subscribers = stats["subscriberCount"]
views = stats["viewCount"]
videos = stats["videoCount"]

# Fetch playlists
playlist_url = f"https://www.googleapis.com/youtube/v3/playlists?part=snippet&channelId={CHANNEL_ID}&key={API_KEY}&maxResults=50"
playlist_response = requests.get(playlist_url).json()
if "error" in playlist_response:
    print(f"Error fetching playlists: {playlist_response['error']['message']}")
    exit(1)
playlists = len(playlist_response["items"])

# Save to CSV
csv_file = "youtube_stats.csv"
file_exists = os.path.isfile(csv_file)
latest_stats = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), subscribers, views, videos, playlists]
with open(csv_file, "a", newline="") as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow(["Date", "Subscribers", "Views", "Videos", "Playlists"])
    writer.writerow(latest_stats)

# Format latest stats for README
latest_stats_str = f"{latest_stats[0]}|{latest_stats[1]}|{latest_stats[2]}|{latest_stats[3]}|{latest_stats[4]}"

# Update README
update_readme(latest_stats_str)

print(f"Stats saved: Subscribers={subscribers}, Views={views}, Videos={videos}, Playlists={playlists}")

# Run GitHub secret setup if run locally
if __name__ == "__main__":
    set_github_secret()
