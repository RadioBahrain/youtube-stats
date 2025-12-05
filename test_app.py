#!/usr/bin/env python3
"""
Unit tests for YouTube Stats Tracker application.
"""

import os
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock
import csv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import app


class TestConfig(unittest.TestCase):
    """Test Config class."""
    
    def test_config_with_api_key(self):
        """Test configuration with API key set."""
        with patch.dict(os.environ, {'YOUTUBE_API_KEY': 'test_key'}):
            config = app.Config()
            self.assertTrue(config.validate())
            self.assertEqual(config.api_key, 'test_key')
    
    def test_config_without_api_key(self):
        """Test configuration without API key."""
        with patch.dict(os.environ, {}, clear=True):
            config = app.Config()
            self.assertFalse(config.validate())


class TestYouTubeAPIClient(unittest.TestCase):
    """Test YouTubeAPIClient class."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Use default values matching production (timeout=10, max_retries=3)
        self.client = app.YouTubeAPIClient(api_key='test_key', timeout=10, max_retries=3)
    
    @patch('app.requests.get')
    def test_successful_api_request(self, mock_get):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = {'items': [{'statistics': {'subscriberCount': '100'}}]}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = self.client._make_request('https://test.com')
        self.assertIn('items', result)
    
    @patch('app.requests.get')
    def test_api_request_with_error_response(self, mock_get):
        """Test API request that returns an error in JSON."""
        mock_response = Mock()
        mock_response.json.return_value = {'error': {'message': 'Invalid API key'}}
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        with self.assertRaises(Exception):
            self.client._make_request('https://test.com')
    
    @patch('app.requests.get')
    def test_get_channel_statistics(self, mock_get):
        """Test fetching channel statistics."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'items': [{
                'statistics': {
                    'subscriberCount': '1000',
                    'viewCount': '50000',
                    'videoCount': '100'
                }
            }]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        stats = self.client.get_channel_statistics('test_channel_id')
        
        self.assertEqual(stats['subscribers'], 1000)
        self.assertEqual(stats['views'], 50000)
        self.assertEqual(stats['videos'], 100)
    
    @patch('app.requests.get')
    def test_get_playlist_count(self, mock_get):
        """Test fetching playlist count."""
        mock_response = Mock()
        mock_response.json.return_value = {
            'items': [{'id': '1'}, {'id': '2'}, {'id': '3'}]
        }
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        count = self.client.get_playlist_count('test_channel_id')
        self.assertEqual(count, 3)


class TestDataManager(unittest.TestCase):
    """Test DataManager class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.csv_file = os.path.join(self.temp_dir, 'test_stats.csv')
        self.backup_dir = os.path.join(self.temp_dir, 'backups')
        self.manager = app.DataManager(self.csv_file, self.backup_dir, backup_retention=5)
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_save_stats_creates_file(self):
        """Test that save_stats creates CSV file with headers."""
        stats = {
            'subscribers': 1000,
            'views': 50000,
            'videos': 100,
            'playlists': 10
        }
        
        result = self.manager.save_stats(stats)
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.csv_file))
        
        # Check file contents
        with open(self.csv_file, 'r') as f:
            reader = csv.reader(f)
            headers = next(reader)
            self.assertEqual(headers, ['Date', 'Subscribers', 'Views', 'Videos', 'Playlists'])
    
    def test_save_stats_appends_data(self):
        """Test that save_stats appends to existing file."""
        stats1 = {'subscribers': 1000, 'views': 50000, 'videos': 100, 'playlists': 10}
        stats2 = {'subscribers': 1001, 'views': 50100, 'videos': 101, 'playlists': 10}
        
        self.manager.save_stats(stats1)
        self.manager.save_stats(stats2)
        
        with open(self.csv_file, 'r') as f:
            lines = f.readlines()
            self.assertEqual(len(lines), 3)  # Header + 2 data rows
    
    def test_create_backup(self):
        """Test backup creation."""
        # Create initial data
        stats = {'subscribers': 1000, 'views': 50000, 'videos': 100, 'playlists': 10}
        self.manager.save_stats(stats)
        
        # Create backup
        backup_file = self.manager.create_backup()
        
        self.assertIsNotNone(backup_file)
        self.assertTrue(os.path.exists(backup_file))
        self.assertTrue(os.path.exists(self.backup_dir))


class TestChartGenerator(unittest.TestCase):
    """Test ChartGenerator class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.csv_file = os.path.join(self.temp_dir, 'test_stats.csv')
        self.charts_dir = os.path.join(self.temp_dir, 'charts')
        self.generator = app.ChartGenerator(self.csv_file, self.charts_dir)
        
        # Create sample data
        with open(self.csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Date', 'Subscribers', 'Views', 'Videos', 'Playlists'])
            writer.writerow(['2025-01-01 00:00:00', '1000', '50000', '100', '10'])
            writer.writerow(['2025-01-02 00:00:00', '1010', '51000', '101', '10'])
            writer.writerow(['2025-01-03 00:00:00', '1020', '52000', '102', '10'])
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_create_charts_with_data(self):
        """Test chart creation with valid data."""
        result = self.generator.create_charts()
        
        self.assertTrue(result)
        self.assertTrue(os.path.exists(self.charts_dir))
        self.assertTrue(os.path.exists(os.path.join(self.charts_dir, 'youtube_analytics.png')))


class TestReadmeUpdater(unittest.TestCase):
    """Test ReadmeUpdater class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.readme_path = os.path.join(self.temp_dir, 'README.md')
        self.updater = app.ReadmeUpdater(self.readme_path)
        
        # Create sample README
        with open(self.readme_path, 'w') as f:
            f.write('Last updated: {{last_updated}}\n')
            f.write('Subscribers: {{subscribers}}\n')
            f.write('Views: {{views}}\n')
    
    def tearDown(self):
        """Clean up test fixtures."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_update_readme(self):
        """Test README update with stats."""
        stats = {
            'subscribers': 1000,
            'views': 50000,
            'videos': 100,
            'playlists': 10
        }
        timestamp = '2025-01-01 00:00:00'
        
        result = self.updater.update(stats, timestamp)
        
        self.assertTrue(result)
        
        with open(self.readme_path, 'r') as f:
            content = f.read()
            self.assertIn('2025-01-01 00:00:00', content)
            self.assertIn('1,000', content)
            self.assertIn('50,000', content)


if __name__ == '__main__':
    unittest.main()
