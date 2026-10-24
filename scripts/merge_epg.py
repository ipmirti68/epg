import requests, gzip, xml.etree.ElementTree as ET
from datetime import datetime, timedelta

SOURCES = [
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://www.open-epg.com/files/turkey5.xml.gz",
    "https://www.open-epg.com/files/turkey6.xml.gz",
    "https://www.open-epg.com/files/turkey7.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR4.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR5.xml.gz",
]

# 3 SAAT GERİ AL - TÜRKİYE İÇİN DÜZELTME
SHIFT_HOURS = -3

tv = ET.Element('tv')
channels = {}

def normalize_id(cid):
    if not cid: return None
    cid = cid.strip()
    if cid.lower().endswith(".tr"): cid = cid[:-3]
    return cid.split("@")[0].strip()

def clean_name(name):
    if not name: return name
    name = name.strip()
    if name.lower().endswith(".tr"):
        name = name[:-3].strip()
    return name

def shift_time(timestr):
    # Format: 20241025033000 +0300 veya 20241025033000 +0000
    try:
        if len(timestr) < 14: return timestr
        dt_part = timestr[:14]
        tz_part = timestr[15:] if len(timestr) > 14 else "+0300"
        dt = datetime.strptime(dt_part, "%Y%m%d%H%M%S")
        dt = dt + timedelta(hours=SHIFT_HOURS)
        return dt.strftime("%Y%m%d%H%M%S") + f" {tz_part}"
    except:
        return timestr

for url in SOURCES:
    try:
        data = requests.get(url, timeout=60, headers={"User-Agent":"Mozilla/5.0"}).content
        if url.endswith('.gz'): 
            try: data = gzip.decompress(data)
            except: pass
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            nid = normalize_id(ch.get('id',''))
            if not nid: continue
            if nid.lower() in [k.lower() for k in channels]: continue
            dn = ch.find('display-name')
            name = clean_name(dn.text if dn is not None and dn.text else nid)
            channels[nid]=name
            ch.set('id', nid)
            if dn is not None: dn.text = name
            tv.append(ch)
        for pr in root.findall('programme'):
            nid = normalize_id(pr.get('channel',''))
            if not nid: continue
            # ZAMANI DÜZELT
            if pr.get('start'): pr.set('start', shift_time(pr.get('start')))
            if pr.get('stop'): pr.set('stop', shift_time(pr.get('stop')))
            pr.set('channel', nid)
            tv.append(pr)
    except Exception as e:
        print(f"{url} hata: {e}")

print(f"TOPLAM KANAL: {len(channels)}")

ET.ElementTree(tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
