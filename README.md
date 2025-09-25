# YouTube Stats for Radio Bahrain

[![Daily YouTube Stats](https://github.com/RadioBahrain/youtube-stats/actions/workflows/youtube-stats.yml/badge.svg)](https://github.com/RadioBahrain/youtube-stats/actions/workflows/youtube-stats.yml)

📊 **Latest Channel Statistics** (Updated Daily)

| Metric | Value |
|--------|-------|
| 📅 Last Updated | {{last_updated}} |
| 👥 Subscribers | {{subscribers}} |
| 👀 Total Views | {{views}} |
| 🎥 Videos | {{videos}} |
| 📝 Playlists | {{playlists}} |

---

This repository automatically tracks YouTube channel statistics for Radio Bahrain and updates daily via GitHub Actions.

## 📈 Data

Historical data is stored in [`youtube_stats.csv`](youtube_stats.csv) with daily snapshots of channel metrics.

## 🔧 Technical Details

- **Automation**: GitHub Actions workflow runs daily at midnight UTC
- **API**: YouTube Data API v3
- **Language**: Python 3.9
- **Data Format**: CSV for historical tracking