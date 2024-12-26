# 🚀 Google Drive Migration Tool

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Made with Love](https://img.shields.io/badge/Made%20with-♥-red.svg)](https://github.com/yourusername)

> 🔄 Seamlessly migrate your Google Drive folders with confidence and precision!

---

## ✨ Features

🏗️ **Robust Structure Handling**
- Perfect folder hierarchy preservation
- Smart duplicate detection
- Intelligent path management

🛡️ **Data Integrity**
- Checksum validation
- Automatic retry mechanism
- Comprehensive error handling

📊 **Advanced Progress Tracking**
- Real-time progress visualization
- Accurate ETA calculation
- Detailed statistics

🎮 **Smart Controls**
- Rate limiting for API optimization
- Intelligent caching system
- Test mode for safe verification
- Source/destination comparison tools

## 🎯 Prerequisites

Before embarking on your migration journey, ensure you have:

- 🐍 Python 3.7 or higher
- ☁️ Google Cloud Project with Drive API enabled
- 📦 Required Python packages (auto-installed):
  ```
  google-auth-oauthlib
  google-api-python-client
  rich
  pathlib
  ```

## 🚀 Quick Start

### 1️⃣ Google Cloud Setup

<details>
<summary>Click to expand detailed Google Cloud setup steps</summary>

#### Create Your Project 🏗️
1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the project dropdown → "New Project"
3. Name your project → "Create"

#### Enable Drive API 🔌
1. Open side menu → "APIs & Services" → "Library"
2. Search for "Google Drive API"
3. Click "Enable" button

#### Setup OAuth 🔑
1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. Select "Desktop app"
4. Name your OAuth client
5. Download the credentials as `credentials.json`

</details>

### 2️⃣ Drive Setup

<details>
<summary>Click to expand Drive setup instructions</summary>

#### Locate Your Folders 📁
1. Navigate to your source folder in Google Drive
2. Copy the folder ID from the URL:
   ```
   drive.google.com/drive/folders/[THIS-IS-YOUR-FOLDER-ID]
   ```
3. Repeat for destination folder

</details>

### 3️⃣ Installation

```bash
# Clone the repository
git clone [repository-url]
cd google-drive-migration

# Run initial setup
python migrate.py
```

## ⚙️ Configuration

Create your `config.json`:

<details>
<summary>Click to see full config.json template</summary>

```json
{
    "credentials": {
        "client_secrets_path": "./credentials.json",
        "token_path": "./token.json"
    },
    "logging": {
        "log_directory": "./logs",
        "log_level": "DEBUG",
        "log_format": "%(asctime)s - %(levelname)s - %(message)s",
        "max_log_size_mb": 10,
        "backup_count": 5
    },
    "source": {
        "folder_id": "YOUR_SOURCE_FOLDER_ID",
        "test_folder_name": "TestPath"
    },
    "destination": {
        "folder_id": "YOUR_DESTINATION_FOLDER_ID",
        "preserve_dates": true,
        "preserve_sharing": false
    },
    "migration": {
        "max_retries": 3,
        "retry_delay_seconds": 5,
        "validate_checksums": true,
        "timeout_seconds": 300,
        "batch_size": 100,
        "auto_fix_missing": true,
        "final_validation": true
    },
    "test_settings": {
        "print_folder_structure": true,
        "max_test_files": 10,
        "size_threshold_gb": 160
    },
    "performance": {
        "user_rate_limit": 12000,
        "user_time_window": 60
    }
}
```

</details>

## 🎮 Usage

```bash
# Full migration
python migrate.py

# Test migration
python migrate.py --test

# View folder structure
python migrate.py --print-structure

# Compare folders
python migrate.py --compare

# Detailed comparison
python migrate.py --compare --detailed

# Custom config
python migrate.py --config /path/to/config.json
```

## 📊 Progress Tracking

Watch your migration progress in style:
```
┌──────────────────────────────────────┐
│        Migration Progress            │
│                                      │
│ 📊 Progress:  85.7%                  │
│ ⏱️ Elapsed: 2h 15m                   │
│ 🕒 ETA: 22m 30s                      │
│                                      │
│ 📁 Folders: 158                      │
│ 📄 Files: 1,542                      │
│                                      │
│ ✅ Successful: 1,320                 │
│ ❌ Failed: 0                         │
│ ⏭️ Skipped: 222                      │
└──────────────────────────────────────┘
```

## 🔧 Troubleshooting

<details>
<summary>🚫 Authentication Failed</summary>

- ✓ Check credentials.json location
- ✓ Verify Drive API is enabled
- ✓ Try deleting token.json and reauthenticating
</details>

<details>
<summary>⚠️ Rate Limit Exceeded</summary>

- ✓ Adjust config.json rate limits
- ✓ Increase retry delay
- ✓ Check API quotas
</details>

<details>
<summary>🚫 Permission Denied</summary>

- ✓ Verify folder access
- ✓ Check account permissions
- ✓ Confirm OAuth scopes
</details>

## 🔒 Security Best Practices

- 🔑 Secure storage of credentials
- 🚫 Never commit credentials to VCS
- 🔄 Regular credential rotation
- 👀 Monitor access logs

## 📜 License

This project is licensed under the GNU Affero General Public License v3.0 (AGPL-3.0).

The AGPL-3.0 is a strong copyleft license that requires anyone who distributes or modifies this software to make the source code available under the same terms. This includes:

- ✅ Freedom to use the software for any purpose
- ✅ Freedom to study how the program works and modify it
- ✅ Freedom to redistribute copies
- ✅ Freedom to distribute modified versions
- ⚠️ Must make source code available when distributing
- ⚠️ Modified versions must also be AGPL-3.0
- ⚠️ Network use counts as distribution
- ⚠️ Must state significant changes made

For the full license text, see [GNU AGPL-3.0](https://www.gnu.org/licenses/agpl-3.0.txt).

## 💝 Support

Found a bug? Have a feature request? We'd love to hear from you! Open an issue in the repository.

---

<p align="center">
Made with ❤️ for the Google Drive community
</p>

---

<p align="center">
⭐ Star this repository if you find it helpful! ⭐
</p>
```
