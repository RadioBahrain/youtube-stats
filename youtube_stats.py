import requests
import csv
import os
import subprocess
import time
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import shutil
from datetime import datetime, timedelta

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

def create_charts():
    """Create visualization charts from historical data"""
    csv_file = "youtube_stats.csv"
    if not os.path.exists(csv_file):
        print("No historical data found for chart generation")
        return
    
    try:
        # Read CSV data
        df = pd.read_csv(csv_file)
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Create charts directory if it doesn't exist
        os.makedirs('charts', exist_ok=True)
        
        # Set up the plotting style
        plt.style.use('default')
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Radio Bahrain YouTube Channel Analytics', fontsize=16, fontweight='bold')
        
        # Chart 1: Subscribers over time
        ax1.plot(df['Date'], df['Subscribers'], marker='o', linewidth=2, markersize=4, color='#1f77b4')
        ax1.set_title('📈 Subscribers Growth')
        ax1.set_ylabel('Subscribers')
        ax1.grid(True, alpha=0.3)
        ax1.tick_params(axis='x', rotation=45)
        
        # Chart 2: Views over time
        ax2.plot(df['Date'], df['Views'], marker='s', linewidth=2, markersize=4, color='#ff7f0e')
        ax2.set_title('👁️ Total Views Growth')
        ax2.set_ylabel('Views')
        ax2.grid(True, alpha=0.3)
        ax2.tick_params(axis='x', rotation=45)
        
        # Chart 3: Videos over time
        ax3.plot(df['Date'], df['Videos'], marker='^', linewidth=2, markersize=4, color='#2ca02c')
        ax3.set_title('🎥 Video Count')
        ax3.set_ylabel('Videos')
        ax3.grid(True, alpha=0.3)
        ax3.tick_params(axis='x', rotation=45)
        
        # Chart 4: Playlists over time
        ax4.plot(df['Date'], df['Playlists'], marker='d', linewidth=2, markersize=4, color='#d62728')
        ax4.set_title('📝 Playlist Count')
        ax4.set_ylabel('Playlists')
        ax4.grid(True, alpha=0.3)
        ax4.tick_params(axis='x', rotation=45)
        
        # Format dates on x-axis
        for ax in [ax1, ax2, ax3, ax4]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
        
        plt.tight_layout()
        plt.savefig('charts/youtube_analytics.png', dpi=300, bbox_inches='tight')
        plt.close()
        
        # Create a summary statistics chart
        create_summary_stats(df)
        
        print("📊 Charts generated successfully!")
        
    except Exception as e:
        print(f"Error creating charts: {e}")

def create_summary_stats(df):
    """Create summary statistics visualization"""
    if len(df) < 2:
        return
        
    # Calculate recent growth (last 7 days vs previous 7 days)
    recent_data = df.tail(14) if len(df) >= 14 else df
    if len(recent_data) >= 2:
        latest = recent_data.iloc[-1]
        previous = recent_data.iloc[0]
        
        # Calculate growth rates
        days_diff = (pd.to_datetime(latest['Date']) - pd.to_datetime(previous['Date'])).days
        if days_diff > 0:
            sub_growth = ((latest['Subscribers'] - previous['Subscribers']) / days_diff)
            view_growth = ((latest['Views'] - previous['Views']) / days_diff)
            video_growth = ((latest['Videos'] - previous['Videos']) / days_diff)
            
            # Create summary chart
            fig, ax = plt.subplots(1, 1, figsize=(10, 6))
            
            metrics = ['Daily Subscriber\nGrowth', 'Daily View\nGrowth', 'Videos Added\n(Total Period)']
            values = [sub_growth, view_growth, latest['Videos'] - previous['Videos']]
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
            
            bars = ax.bar(metrics, values, color=colors, alpha=0.7)
            ax.set_title('📊 Recent Growth Metrics', fontsize=14, fontweight='bold')
            ax.set_ylabel('Daily Average')
            ax.grid(True, alpha=0.3, axis='y')
            
            # Add value labels on bars
            for bar, value in zip(bars, values):
                height = bar.get_height()
                ax.text(bar.get_x() + bar.get_width()/2., height + height*0.05,
                       f'{value:.1f}', ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            plt.savefig('charts/growth_metrics.png', dpi=300, bbox_inches='tight')
            plt.close()
            
def create_backup():
    """Create backup of data files"""
    try:
        backup_dir = "backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Create timestamped backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = f"{backup_dir}/youtube_stats_backup_{timestamp}.csv"
        
        if os.path.exists("youtube_stats.csv"):
            shutil.copy2("youtube_stats.csv", backup_file)
            print(f"📁 Backup created: {backup_file}")
            
            # Keep only last 30 backups
            cleanup_old_backups(backup_dir)
        
    except Exception as e:
        print(f"Warning: Could not create backup: {e}")

def cleanup_old_backups(backup_dir, keep_count=30):
    """Keep only the most recent backups"""
    try:
        backup_files = [f for f in os.listdir(backup_dir) if f.startswith("youtube_stats_backup_")]
        backup_files.sort(reverse=True)  # Most recent first
        
        # Remove old backups
        for old_backup in backup_files[keep_count:]:
            os.remove(os.path.join(backup_dir, old_backup))
            print(f"🗑️ Removed old backup: {old_backup}")
            
    except Exception as e:
        print(f"Warning: Could not cleanup old backups: {e}")

def check_data_integrity():
    """Check if the data looks reasonable"""
    csv_file = "youtube_stats.csv"
    if not os.path.exists(csv_file):
        return True
    
    try:
        df = pd.read_csv(csv_file)
        if len(df) < 2:
            return True
            
        latest_row = df.iloc[-1]
        previous_row = df.iloc[-2]
        
        # Check for unrealistic changes (more than 50% change in one day)
        for column in ['Subscribers', 'Views', 'Videos']:
            if column in df.columns:
                latest_val = float(latest_row[column])
                previous_val = float(previous_row[column])
                
                if previous_val > 0:
                    change_percent = abs((latest_val - previous_val) / previous_val)
                    if change_percent > 0.5:  # 50% change threshold
                        print(f"⚠️ Warning: Large change detected in {column}: {change_percent:.1%}")
                        return False
        
        return True
        
    except Exception as e:
        print(f"Warning: Could not check data integrity: {e}")
        return True

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

# Create backup before making changes
create_backup()

# Save to CSV
csv_file = "youtube_stats.csv"
file_exists = os.path.isfile(csv_file)
latest_stats = [datetime.now().strftime("%Y-%m-%d %H:%M:%S"), subscribers, views, videos, playlists]
with open(csv_file, "a", newline="") as f:
    writer = csv.writer(f)
    if not file_exists:
        writer.writerow(["Date", "Subscribers", "Views", "Videos", "Playlists"])
    writer.writerow(latest_stats)

# Check data integrity
if not check_data_integrity():
    print("⚠️ Data integrity check failed - proceeding with caution")

# Format latest stats for README
latest_stats_str = f"{latest_stats[0]}|{latest_stats[1]}|{latest_stats[2]}|{latest_stats[3]}|{latest_stats[4]}"

# Update README
update_readme(latest_stats)

# Create visualization charts
create_charts()

print(f"✅ Stats saved: Subscribers={subscribers}, Views={views}, Videos={videos}, Playlists={playlists}")

# Run GitHub secret setup only if run locally and not in CI
if __name__ == "__main__":
    # Only try to set up GitHub secrets when not in CI environment
    if not os.getenv("GITHUB_ACTIONS"):
        set_github_secret()
    else:
        print("Running in GitHub Actions environment - using existing secrets")
