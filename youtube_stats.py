import requests
import csv
import os
import subprocess
import time
from datetime import datetime

def make_api_request(url, max_retries=3, delay=1):
    """Make API request with retry logic"""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {delay} seconds...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff
            else:
                raise

# Authenticate with GitHub CLI and set secret (only needed for local setup)
def set_github_secret():
    try:
        # Check if we're in a GitHub Actions environment
        if os.getenv("GITHUB_ACTIONS"):
            print("Running in GitHub Actions, skipping GitHub CLI authentication")
            return
            
        # Check if we already have authentication
        try:
            subprocess.run(["gh", "auth", "status"], check=True, capture_output=True)
            print("GitHub CLI already authenticated")
        except subprocess.CalledProcessError:
            # Only attempt login if not already authenticated
            print("Attempting GitHub CLI authentication...")
            subprocess.run(["gh", "auth", "login"], check=True)
        
        # Get the auth token
        token = subprocess.run(["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
        # Set the token as a GitHub secret
        subprocess.run([
            "gh", "secret", "set", "YOUTUBE_API_KEY",
            "--body", os.getenv("YOUTUBE_API_KEY", ""),
            "--repo", "RadioBahrain/youtube-stats"
        ], check=True)
        print("GitHub secret set successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error setting GitHub secret: {e}")
        print("Note: This is only needed for initial local setup. In GitHub Actions, secrets are already configured.")

# Update README with latest stats
def update_readme(latest_stats):
    readme_path = "README.md"
    with open(readme_path, "r") as f:
        content = f.read()
    
    # Extract data from latest_stats array
    last_updated, subscribers, views, videos, playlists = latest_stats
    
    # Replace placeholders with actual values
    content = content.replace("{{last_updated}}", last_updated)
    content = content.replace("{{subscribers}}", f"{int(subscribers):,}")
    content = content.replace("{{views}}", f"{int(views):,}")
    content = content.replace("{{videos}}", str(videos))
    content = content.replace("{{playlists}}", str(playlists))
    
    with open(readme_path, "w") as f:
        f.write(content)

# Fetch YouTube stats
API_KEY = os.getenv("YOUTUBE_API_KEY")
if not API_KEY:
    print("Error: YOUTUBE_API_KEY environment variable is not set")
    exit(1)

CHANNEL_ID = "UCylIWXb8bRI0KcDeJG6H8rw"

# Fetch channel statistics
channel_url = f"https://www.googleapis.com/youtube/v3/channels?part=statistics&id={CHANNEL_ID}&key={API_KEY}"
print("Fetching channel statistics...")
channel_response = make_api_request(channel_url)
if "error" in channel_response:
    print(f"Error fetching channel stats: {channel_response['error']['message']}")
    exit(1)
stats = channel_response["items"][0]["statistics"]
subscribers = stats["subscriberCount"]
views = stats["viewCount"]
videos = stats["videoCount"]

# Fetch playlists
playlist_url = f"https://www.googleapis.com/youtube/v3/playlists?part=snippet&channelId={CHANNEL_ID}&key={API_KEY}&maxResults=50"
print("Fetching playlists...")
playlist_response = make_api_request(playlist_url)
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
update_readme(latest_stats)

print(f"Stats saved: Subscribers={subscribers}, Views={views}, Videos={videos}, Playlists={playlists}")

# Run GitHub secret setup only if run locally and not in CI
if __name__ == "__main__":
    # Only try to set up GitHub secrets when not in CI environment
    if not os.getenv("GITHUB_ACTIONS"):
        set_github_secret()
    else:
        print("Running in GitHub Actions environment - using existing secrets")
