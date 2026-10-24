name: Turkiye EPG

on:
  push:
    branches: [main]
  workflow_dispatch:
  schedule:
    - cron: "30 22 * * *"

permissions:
  contents: write

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install
        run: pip install requests
      - name: Merge EPG
        run: python scripts/merge_epg.py
      - name: Push
        run: |
          git config user.name "bot"
          git config user.email "bot@bot.com"
          git add epg.xml
          git commit -m "epg temizlendi" || echo "yok"
          git push
