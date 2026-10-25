import requests, gzip, xml.etree.ElementTree as ET, re
from datetime import datetime, timedelta, timezone
from collections import defaultdict

SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
]

# SENIN RESIMDEKI + TURKIYE GENELI RADYOLAR - BURAYA KENDI RADYO ID'LERINI EKLEYEBILIRSIN
EXTRA_RADIOS = [
    "AKSARAY NIN SESI 95.1", "AKSARAY FM 99.5", "AKSARAY RADYO 68", "MAVI RADYO", "MAVI RADYO (copy)",
    "TURKULERLE TURKIYE", "RADYO TURKU", "TRT TURKU", "RADYO 7 TURKU", 
    "RADYO 7 MUHTESEM 4", "RADYO 7 NOSTALJI", "RADYO ANKARA",
    "KRAL FM", "KRAL POP", "POWER FM", "POWER TURK", "JOY FM", "JOY TURK",
    "METRO FM", "SUPER FM", "SHOW RADYO", "NUMBER ONE FM", "RADYO D", "RADYO VIVA",
    "BEST FM", "ALEM FM", "TRT FM", "TRT RADYO 1", "RADYO 7", "AKSARAYIN SESI",
]

def clean_id(cid):
    if not cid: return None
    cid = cid.strip()
    if cid.lower().endswith(".tr"): cid = cid[:-3]
    return cid.strip()

def fix_time(t):
    try:
        if len(t) < 14: return t
        return f"{t[:14]} +0300"
    except:
        return t

tv_channels = {}
tv_progs = []
seen_prog = set()
has_epg = set()

for url in SOURCES:
    try:
        r = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200: continue
        data = gzip.decompress(r.content) if url.endswith('.gz') else r.content
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            cid = clean_id(ch.get('id',''))
            if not cid or cid.lower() in tv_channels: continue
            tv_channels[cid.lower()] = ch
            ch.set('id', cid)
        for pr in root.findall('programme'):
            cid = clean_id(pr.get('channel',''))
            if not cid: continue
            s = fix_time(pr.get('start','')); e = fix_time(pr.get('stop',''))
            if not s: continue
            key = (cid.lower(), s)
            if key in seen_prog: continue
            pr.set('start', s); pr.set('stop', e); pr.set('channel', cid)
            tv_progs.append(pr); seen_prog.add(key); has_epg.add(cid.lower())
    except: pass

# EXTRA RADYOLARI EKLE
for rad in EXTRA_RADIOS:
    low = rad.lower()
    if low not in tv_channels:
        ch = ET.Element('channel', {'id': rad})
        ET.SubElement(ch, 'display-name').text = rad
        tv_channels[low] = ch

# FINAL
final_tv = ET.Element('tv')
sorted_channels = sorted(tv_channels.values(), key=lambda x: x.get('id','').lower())
for ch in sorted_channels: final_tv.append(ch)
for pr in tv_progs: final_tv.append(pr)

# EPG'SI OLMAYAN HER SEYE ID YAZDIR (7 GUN)
now = datetime.now(timezone(timedelta(hours=3)))
for low,ch in tv_channels.items():
    if low in has_epg: continue
    cid = ch.get('id')
    dname = ch.find('display-name').text if ch.find('display-name') is not None else cid
    for day in range(7):
        ds = (now + timedelta(days=day)).replace(hour=0,minute=0,second=0,microsecond=0)
        de = ds + timedelta(days=1)
        prog = ET.Element('programme', {'channel': cid, 'start': ds.strftime("%Y%m%d%H%M%S +0300"), 'stop': de.strftime("%Y%m%d%H%M%S +0300")})
        ET.SubElement(prog, 'title', {'lang':'tr'}).text = dname
        ET.SubElement(prog, 'desc', {'lang':'tr'}).text = f"{dname} Canli Yayin"
        final_tv.append(prog)
    has_epg.add(low)

ET.ElementTree(final_tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"BITTI: {len(tv_channels)} kanal, radyolar dahil ID yazildi")
for r in EXTRA_RADIOS[:15]:
    print(f" - {r}")
