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

# SENIN LISTEN - BOSLUKLARI TEMIZLEDIM
EXTRA_RADIOS_RAW = [
   "RADYO 7 TÜRKÜ", "TÜRKÜLERLE TÜRKİYE", "RADYO TÜRKÜ",
   "AKSARAY IN SESI 95.1", "AKSARAY FM 99.5", "AKSARAY RADYO 68 101.2", "AKSARAY MAVİ RADYO 98.0",
   "TRT TÜRKÜ", "RADYO 7 MUHTEŞEM 4", "RADYO 7 NOSTALJİ", "RADYO ANKARA", "RADYO 7", "RADYO 7 ARABESK",
   "KRAL POP"
]

def tr_fold(s):
    # TÜRKÇE KARAKTERI ASCII YAP - TURKU = TÜRKÜ eşleşmesi için
    m = {"Ğ":"G","Ü":"U","Ş":"S","İ":"I","Ö":"O","Ç":"C","ğ":"g","ü":"u","ş":"s","ı":"i","ö":"o","ç":"c"}
    for k,v in m.items(): s = s.replace(k,v)
    return s

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

# RADYOLARI EKLE - HEM ORIJINAL HEM ASCII VERSIYON
for raw in EXTRA_RADIOS_RAW:
    raw = raw.strip()  # baştaki boşluğu sil
    if not raw: continue
    for variant in [raw, tr_fold(raw), raw.lower(), tr_fold(raw).lower()]:
        v = variant.strip()
        if not v: continue
        low = v.lower()
        if low not in tv_channels:
            ch = ET.Element('channel', {'id': v})
            ET.SubElement(ch, 'display-name').text = raw  # ekranda orijinal isim gözüksün
            tv_channels[low] = ch

# TABII ve BEIN parent bul - SYNTAX DUZELTILDI
tabii_parent = []
bein_parent = []
for p in tv_progs:
    cname = p.get('channel','').lower()
    if 'tabii' in cname and 'spor' in cname:
        tabii_parent.append(p)
    if 'bein' in cname:
        bein_parent.append(p)

if not tabii_parent:
    tabii_parent = [p for p in tv_progs if 'trt spor' in p.get('channel','').lower()]

print(f"TABII parent: {len(tabii_parent)} | BEIN parent: {len(bein_parent)}")

# TABII/BEIN ZORLA OLUSTUR
WANTED = ["TABII SPOR 1","TABII SPOR 2","TABII SPOR 3","TABII SPOR 4","TABII SPOR 5","TABII SPOR 6",
          "tabii spor 1","tabii spor 2","tabii spor 3","tabii spor 4","tabii spor 5","tabii spor 6",
          "beinsports","beinsports 2","beinsports 3","beinsports 4","beinsports 5"]

for alias in WANTED:
    alow = alias.lower()
    if alow not in tv_channels:
        ch = ET.Element('channel', {'id': alias}); ET.SubElement(ch, 'display-name').text = alias
        tv_channels[alow] = ch
    src = tabii_parent if 'tabii' in alow else bein_parent
    for pr in src:
        key = (alow, pr.get('start'))
        if key in seen: continue
        np = ET.Element('programme', {'channel': alias, 'start': pr.get('start'), 'stop': pr.get('stop')})
        for c in pr: nc = ET.Element(c.tag, c.attrib); nc.text = c.text; np.append(nc)
        tv_progs.append(np); seen.add(key)

# FINAL
final_tv = ET.Element('tv')
for ch in sorted(tv_channels.values(), key=lambda x: x.get('id','').lower()): final_tv.append(ch)
for pr in tv_progs: final_tv.append(pr)

# EPG'SI OLMAYAN HER SEYE 7 GUN ID YAZ
now = datetime.now(timezone(timedelta(hours=3)))
for low,ch in tv_channels.items():
    if low in has_epg: continue
    if 'tabii' in low or 'bein' in low: continue  # bunlar zaten eklendi
    cid = ch.get('id')
    dname = ch.find('display-name').text if ch.find('display-name') is not None else cid
    for day in range(7):
        ds = (now + timedelta(days=day)).replace(hour=0,minute=0,second=0,microsecond=0)
        de = ds + timedelta(days=1)
        prog = ET.Element('programme', {'channel': cid, 'start': ds.strftime("%Y%m%d%H%M%S +0300"), 'stop': de.strftime("%Y%m%d%H%M%S +0300")})
        ET.SubElement(prog, 'title', {'lang':'tr'}).text = dname
        ET.SubElement(prog, 'desc', {'lang':'tr'}).text = f"{dname} Canli Yayin"
        final_tv.append(prog)

ET.ElementTree(final_tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"BITTI: {len(tv_channels)} kanal")
