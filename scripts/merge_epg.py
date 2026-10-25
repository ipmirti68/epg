import requests, gzip, xml.etree.ElementTree as ET, re
from datetime import datetime, timedelta, timezone

SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://iptv-org.github.io/epg/guides/tr/tabii.com.tr.epg.xml.gz",
    "https://iptv-org.github.io/epg/guides/tr/trt.com.tr.epg.xml.gz",
]

EXTRA_RADIOS = [
   "RADYO 7 TÜRKÜ", " TÜRKÜLERLE TÜRKİYE","RADYO TÜRKÜ","AKSARAY IN SESI 95.1", "AKSARAY FM 99.5", "AKSARAY RADYO 68 101.2", "AKSARAY MAVİ RADYO 98.0",
]

def clean_id(cid):
    if not cid: return None
    cid = cid.strip()
    if cid.lower().endswith(".tr"): cid = cid[:-3]
    return cid.strip()

def fix_time(t):
    try: return f"{t[:14]} +0300" if len(t)>=14 else t
    except: return t

tv_channels = {}; tv_progs = []; seen = set(); has_epg = set()

for url in SOURCES:
    try:
        r = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200: continue
        data = gzip.decompress(r.content) if url.endswith('.gz') else r.content
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            cid = clean_id(ch.get('id',''))
            if not cid or cid.lower() in tv_channels: continue
            ch.set('id', cid); tv_channels[cid.lower()] = ch
        for pr in root.findall('programme'):
            cid = clean_id(pr.get('channel',''))
            if not cid: continue
            s = fix_time(pr.get('start','')); e = fix_time(pr.get('stop',''))
            if not s: continue
            key = (cid.lower(), s)
            if key in seen: continue
            pr.set('start', s); pr.set('stop', e); pr.set('channel', cid)
            tv_progs.append(pr); seen.add(key); has_epg.add(cid.lower())
    except: pass

for rad in EXTRA_RADIOS:
    if rad.lower() not in tv_channels:
        ch = ET.Element('channel', {'id': rad}); ET.SubElement(ch, 'display-name').text = rad
        tv_channels[rad.lower()] = ch

# TABII ve BEIN parent bul
tabii_parent = [p for p in tv_progs if "tabii" in p.get('channel
