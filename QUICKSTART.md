# Quick Start Guide

Get up and running in 5 minutes!

## Step 1: Install Dependencies (1 min)

```bash
pip install -r requirements.txt
```

## Step 2: Set Up Gmail API (2 min)

1. Visit [Google Cloud Console](https://console.cloud.google.com/)
2. Create/select a project
3. Enable Gmail API
4. Create OAuth 2.0 credentials (Desktop app)
5. Download as `credentials.json` and place in project root

## Step 3: Configure (Optional, 1 min)

Edit `config.py` if you want to customize:
- Search query
- Headless mode (on/off)
- Parallel processing (on/off)

## Step 4: Run (1 min)

```bash
python automation.py
```

On first run, authorize the app in your browser.

## That's It! 🎉

The script will:
- ✅ Fetch all matching emails
- ✅ Extract removal links
- ✅ Process them automatically
- ✅ Generate a detailed report

## Common Configurations

### See the browser in action
```python
# In config.py
HEADLESS_MODE = False
```

### Process links faster (parallel mode)
```python
# In config.py
ENABLE_PARALLEL = True
MAX_WORKERS = 3
```

### Search different emails
```python
# In config.py
GMAIL_QUERY = "from:noreply@example.com subject:unsubscribe"
```

## Need Help?

See [README.md](README.md) for detailed documentation.