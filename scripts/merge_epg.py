import requests, gzip, xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

SOURCES = [
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://www.open-epg.com/files/turkey5.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
]

def norm(cid):
    if not cid: return None
    cid = cid.strip()
    if cid.lower().endswith(".tr"): cid = cid[:-3]
    return cid.split("@")[0].strip()

def fix_time(timestr):
    # 20241025071500 +0000 veya 20241025071500 +0300 -> Türkiye +0300'e çevir
    try:
        if len(timestr) < 14: return timestr
        dt_part = timestr[:14]
        tz_part = timestr[15:].strip() if len(timestr) > 15 else "+0000"
        dt = datetime.strptime(dt_part, "%Y%m%d%H%M%S")

        # Kaynağın time zone'u
        sign = 1 if tz_part[0] == '+' else -1
        th = int(tz_part[1:3])
        tm = int(tz_part[3:5]) if len(tz_part) >= 5 else 0
        src_tz = timezone(timedelta(hours=sign*th, minutes=sign*tm))
        dt = dt.replace(tzinfo=src_tz)

        # Türkiye +0300
        tr_tz = timezone(timedelta(hours=3))
        dt_tr = dt.astimezone(tr_tz)
        return dt_tr.strftime("%Y%m%d%H%M%S +0300")
    except:
        return timestr

tv = ET.Element('tv')
seen = set()

for url in SOURCES:
    try:
        r = requests.get(url, timeout=60, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200: continue
        data = r.content
        if url.endswith('.gz'):
            try: data = gzip.decompress(data)
            except: pass
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            nid = norm(ch.get('id',''))
            if not nid or nid.lower() in seen: continue
            seen.add(nid.lower())
            ch.set('id', nid)
            tv.append(ch)
        for pr in root.findall('programme'):
            nid = norm(pr.get('channel',''))
            if not nid: continue
            if pr.get('start'): pr.set('start', fix_time(pr.get('start')))
            if pr.get('stop'): pr.set('stop', fix_time(pr.get('stop')))
            pr.set('channel', nid)
            tv.append(pr)
    except Exception as e:
        print(f"HATA {url}: {e}")

ET.ElementTree(tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"Bitti {len(seen)} kanal")
