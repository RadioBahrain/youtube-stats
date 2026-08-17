#!/usr/bin/env python3
"""
YouTube Stats Tracker for Radio Bahrain
Fetches and tracks YouTube channel statistics with visualization and backup features.
"""

import csv
import os
import sys
import time
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

import requests
import pandas as pd
import matplotlib
# Set backend before importing pyplot to avoid configuration issues
matplotlib.use('Agg')  # Use non-interactive backend for server environments
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class Config:
    """Configuration management for the application."""
    
    def __init__(self):
        """Initialize configuration from environment variables."""
        self.api_key = os.getenv("YOUTUBE_API_KEY")
        self.channel_id = "UCylIWXb8bRI0KcDeJG6H8rw"  # Radio Bahrain
        self.csv_file = "youtube_stats.csv"
        self.backup_dir = "backups"
        self.charts_dir = "charts"
        self.readme_path = "README.md"
        self.max_retries = 3
        self.request_timeout = 10
        self.backup_retention_count = 30
        
    def validate(self) -> bool:
        """Validate required configuration."""
        if not self.api_key:
            logger.error("❌ Error: YOUTUBE_API_KEY environment variable is not set")
            return False
        return True


class YouTubeAPIClient:
    """Client for interacting with YouTube Data API v3."""
    
    def __init__(self, api_key: str, timeout: int = 10, max_retries: int = 3):
        """
        Initialize YouTube API client.
        
        Args:
            api_key: YouTube Data API v3 key
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.api_key = api_key
        self.timeout = timeout
        self.max_retries = max_retries
        self.base_url = "https://www.googleapis.com/youtube/v3"
        
    def _make_request(self, url: str) -> Dict:
        """
        Make API request with retry logic and exponential backoff.
        
        Args:
            url: API endpoint URL
            
        Returns:
            JSON response from API
            
        Raises:
            requests.exceptions.RequestException: If request fails after all retries
        """
        delay = 1
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Making API request (attempt {attempt + 1}/{self.max_retries})")
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
                data = response.json()
                
                # Check for API errors
                if "error" in data:
                    error_msg = data["error"].get("message", "Unknown API error")
                    error_code = data["error"].get("code", "N/A")
                    logger.error(f"API Error (code {error_code}): {error_msg} [URL: {url}]")
                    raise requests.exceptions.RequestException(f"API Error (code {error_code}): {error_msg}")
                    
                return data
                
            except requests.exceptions.RequestException as e:
                logger.warning(f"API request attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    logger.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
                else:
                    logger.error(f"All retry attempts failed")
                    raise
                    
    def get_channel_statistics(self, channel_id: str) -> Dict[str, int]:
        """
        Fetch channel statistics.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Dictionary with subscribers, views, and video count
        """
        url = f"{self.base_url}/channels?part=statistics&id={channel_id}&key={self.api_key}"
        logger.info("Fetching channel statistics...")
        
        response = self._make_request(url)
        
        if not response.get("items"):
            raise ValueError("No channel data found in API response")
            
        stats = response["items"][0]["statistics"]
        
        return {
            "subscribers": int(stats.get("subscriberCount", 0)),
            "views": int(stats.get("viewCount", 0)),
            "videos": int(stats.get("videoCount", 0))
        }
        
    def get_playlist_count(self, channel_id: str) -> int:
        """
        Fetch number of playlists for a channel.
        
        Args:
            channel_id: YouTube channel ID
            
        Returns:
            Number of playlists
            
        Note:
            This method handles pagination to count all playlists,
            even if there are more than 50. Has a safety limit of 100 pages
            to prevent infinite loops from malformed API responses.
        """
        url = f"{self.base_url}/playlists?part=snippet&channelId={channel_id}&key={self.api_key}&maxResults=50"
        logger.info("Fetching playlists...")
        
        total_playlists = 0
        next_page_token = None
        max_pages = 100  # Safety limit: max 5000 playlists (50 per page * 100 pages)
        page_count = 0
        
        # Handle pagination to get all playlists
        while True:
            if page_count >= max_pages:
                logger.warning(f"Reached maximum page limit ({max_pages}). Total playlists so far: {total_playlists}")
                break
                
            page_url = url
            if next_page_token:
                page_url += f"&pageToken={next_page_token}"
                
            response = self._make_request(page_url)
            total_playlists += len(response.get("items", []))
            page_count += 1
            
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break
                
            logger.debug(f"Fetching next page of playlists... (total so far: {total_playlists})")
        
        return total_playlists


class DataManager:
    """Manages data storage, backup, and validation."""
    
    def __init__(self, csv_file: str, backup_dir: str, backup_retention: int = 30):
        """
        Initialize data manager.
        
        Args:
            csv_file: Path to CSV data file
            backup_dir: Directory for backups
            backup_retention: Number of backups to retain
        """
        self.csv_file = csv_file
        self.backup_dir = backup_dir
        self.backup_retention = backup_retention
        
    def create_backup(self) -> Optional[str]:
        """
        Create timestamped backup of data file.
        
        Returns:
            Path to backup file or None if no data to backup
        """
        try:
            os.makedirs(self.backup_dir, exist_ok=True)
            
            if not os.path.exists(self.csv_file):
                logger.info("No existing data file to backup")
                return None
                
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(self.backup_dir, f"youtube_stats_backup_{timestamp}.csv")
            
            shutil.copy2(self.csv_file, backup_file)
            logger.info(f"📁 Backup created: {backup_file}")
            
            self._cleanup_old_backups()
            
            return backup_file
            
        except Exception as e:
            logger.warning(f"Could not create backup: {e}")
            return None
            
    def _cleanup_old_backups(self):
        """Remove old backup files, keeping only recent ones."""
        try:
            backup_files = [
                f for f in os.listdir(self.backup_dir) 
                if f.startswith("youtube_stats_backup_") and f.endswith(".csv")
            ]
            backup_files.sort(reverse=True)  # Most recent first
            
            for old_backup in backup_files[self.backup_retention:]:
                file_path = os.path.join(self.backup_dir, old_backup)
                os.remove(file_path)
                logger.info(f"🗑️ Removed old backup: {old_backup}")
                
        except Exception as e:
            logger.warning(f"Could not cleanup old backups: {e}")
            
    def save_stats(self, stats: Dict[str, int]) -> bool:
        """
        Save statistics to CSV file.
        
        Args:
            stats: Dictionary containing channel statistics
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            file_exists = os.path.isfile(self.csv_file)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            with open(self.csv_file, "a", newline="") as f:
                writer = csv.writer(f)
                
                if not file_exists:
                    writer.writerow(["Date", "Subscribers", "Views", "Videos", "Playlists"])
                    
                writer.writerow([
                    timestamp,
                    stats["subscribers"],
                    stats["views"],
                    stats["videos"],
                    stats["playlists"]
                ])
                
            logger.info(f"✅ Stats saved: Subscribers={stats['subscribers']}, Views={stats['views']}, Videos={stats['videos']}, Playlists={stats['playlists']}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save stats: {e}")
            return False
            
    def check_data_integrity(self) -> bool:
        """
        Check if recent data changes look reasonable.
        
        Returns:
            True if data looks valid, False if suspicious changes detected
        """
        if not os.path.exists(self.csv_file):
            return True
            
        try:
            df = pd.read_csv(self.csv_file)
            if len(df) < 2:
                return True
                
            latest_row = df.iloc[-1]
            previous_row = df.iloc[-2]
            
            # Check for unrealistic changes (more than 50% change in one day)
            for column in ['Subscribers', 'Views', 'Videos']:
                if column not in df.columns:
                    continue
                    
                latest_val = float(latest_row[column])
                previous_val = float(previous_row[column])
                
                if previous_val > 0:
                    change_percent = abs((latest_val - previous_val) / previous_val)
                    if change_percent > 0.5:  # 50% change threshold
                        logger.warning(f"⚠️ Large change detected in {column}: {change_percent:.1%}")
                        return False
                        
            return True
            
        except Exception as e:
            logger.warning(f"Could not check data integrity: {e}")
            return True
            
    def get_latest_stats(self) -> Optional[List]:
        """
        Get the most recent statistics from CSV.
        
        Returns:
            List of latest stats or None if no data exists
        """
        if not os.path.exists(self.csv_file):
            return None
            
        try:
            df = pd.read_csv(self.csv_file)
            if len(df) == 0:
                return None
            return df.iloc[-1].tolist()
        except Exception as e:
            logger.warning(f"Could not read latest stats: {e}")
            return None


class ChartGenerator:
    """Generates visualization charts from historical data."""
    
    def __init__(self, csv_file: str, charts_dir: str):
        """
        Initialize chart generator.
        
        Args:
            csv_file: Path to CSV data file
            charts_dir: Directory to save charts
        """
        self.csv_file = csv_file
        self.charts_dir = charts_dir
        
    def create_charts(self) -> bool:
        """
        Create all visualization charts.
        
        Returns:
            True if charts created successfully, False otherwise
        """
        if not os.path.exists(self.csv_file):
            logger.warning("No historical data found for chart generation")
            return False
            
        try:
            df = pd.read_csv(self.csv_file)
            df['Date'] = pd.to_datetime(df['Date'])
            
            os.makedirs(self.charts_dir, exist_ok=True)
            
            # Create main analytics dashboard
            self._create_main_dashboard(df)
            
            # Create summary statistics chart
            if len(df) >= 2:
                self._create_summary_stats(df)
                
            logger.info("📊 Charts generated successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Error creating charts: {e}")
            return False
            
    def _create_main_dashboard(self, df: pd.DataFrame):
        """Create main analytics dashboard with 4 charts."""
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
            if len(df) > 7:
                ax.xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
            else:
                ax.xaxis.set_major_locator(mdates.DayLocator())
                
        plt.tight_layout()
        output_path = os.path.join(self.charts_dir, 'youtube_analytics.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
    def _create_summary_stats(self, df: pd.DataFrame):
        """Create summary statistics visualization."""
        if len(df) < 2:
            return
            
        # Calculate recent growth (last 7 days vs previous 7 days)
        recent_data = df.tail(14) if len(df) >= 14 else df
        
        if len(recent_data) < 2:
            return
            
        latest = recent_data.iloc[-1]
        previous = recent_data.iloc[0]
        
        # Calculate growth rates
        days_diff = (pd.to_datetime(latest['Date']) - pd.to_datetime(previous['Date'])).days
        
        if days_diff <= 0:
            days_diff = 1
            
        sub_growth = (latest['Subscribers'] - previous['Subscribers']) / days_diff
        view_growth = (latest['Views'] - previous['Views']) / days_diff
        video_growth = latest['Videos'] - previous['Videos']
        
        # Create summary chart
        fig, ax = plt.subplots(1, 1, figsize=(10, 6))
        
        metrics = ['Daily Subscriber\nGrowth', 'Daily View\nGrowth', 'Videos Added\n(Total Period)']
        values = [sub_growth, view_growth, video_growth]
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c']
        
        bars = ax.bar(metrics, values, color=colors, alpha=0.7)
        ax.set_title('📊 Recent Growth Metrics', fontsize=14, fontweight='bold')
        ax.set_ylabel('Daily Average')
        ax.grid(True, alpha=0.3, axis='y')
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            if height != 0:
                y_pos = height + (abs(height) * 0.05 if height > 0 else -abs(height) * 0.05)
                ax.text(bar.get_x() + bar.get_width()/2., y_pos,
                       f'{value:.1f}', ha='center', va='bottom' if height > 0 else 'top', 
                       fontweight='bold')
        
        plt.tight_layout()
        output_path = os.path.join(self.charts_dir, 'growth_metrics.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()


class ReadmeUpdater:
    """Updates README with latest statistics."""
    
    def __init__(self, readme_path: str):
        """
        Initialize README updater.
        
        Args:
            readme_path: Path to README file
        """
        self.readme_path = readme_path
        
    def update(self, stats: Dict[str, int], timestamp: str) -> bool:
        """
        Update README with latest statistics.
        
        Args:
            stats: Dictionary containing channel statistics
            timestamp: Timestamp string
            
        Returns:
            True if updated successfully, False otherwise
        """
        if not os.path.exists(self.readme_path):
            logger.warning(f"README file not found at {self.readme_path}")
            return False
            
        try:
            with open(self.readme_path, "r") as f:
                content = f.read()
                
            # Replace placeholders with actual values (if they exist)
            replacements = {
                "{{last_updated}}": timestamp,
                "{{subscribers}}": f"{stats['subscribers']:,}",
                "{{views}}": f"{stats['views']:,}",
                "{{videos}}": str(stats['videos']),
                "{{playlists}}": str(stats['playlists'])
            }
            
            for placeholder, value in replacements.items():
                content = content.replace(placeholder, value)
                
            with open(self.readme_path, "w") as f:
                f.write(content)
                
            logger.info("📝 README updated successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update README: {e}")
            return False


class YouTubeStatsApp:
    """Main application class."""
    
    def __init__(self, config: Config):
        """
        Initialize the application.
        
        Args:
            config: Application configuration
        """
        self.config = config
        self.api_client = YouTubeAPIClient(
            config.api_key, 
            config.request_timeout, 
            config.max_retries
        )
        self.data_manager = DataManager(
            config.csv_file, 
            config.backup_dir, 
            config.backup_retention_count
        )
        self.chart_generator = ChartGenerator(config.csv_file, config.charts_dir)
        self.readme_updater = ReadmeUpdater(config.readme_path)
        
    def run(self) -> int:
        """
        Run the main application logic.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            logger.info("🚀 Starting YouTube Stats Tracker")
            
            # Fetch channel statistics
            channel_stats = self.api_client.get_channel_statistics(self.config.channel_id)
            playlist_count = self.api_client.get_playlist_count(self.config.channel_id)
            
            # Combine all stats
            stats = {
                **channel_stats,
                "playlists": playlist_count
            }
            
            # Create backup before making changes
            self.data_manager.create_backup()
            
            # Save statistics
            if not self.data_manager.save_stats(stats):
                logger.error("Failed to save statistics")
                return 1
                
            # Check data integrity
            if not self.data_manager.check_data_integrity():
                logger.warning("⚠️ Data integrity check failed - proceeding with caution")
                
            # Update README
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.readme_updater.update(stats, timestamp)
            
            # Generate charts
            self.chart_generator.create_charts()
            
            logger.info("✅ YouTube Stats Tracker completed successfully")
            return 0
            
        except Exception as e:
            logger.error(f"❌ Application failed: {e}", exc_info=True)
            return 1


def main():
    """Main entry point."""
    # Load configuration
    config = Config()
    
    # Validate configuration
    if not config.validate():
        sys.exit(1)
        
    # Create and run application
    app = YouTubeStatsApp(config)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
