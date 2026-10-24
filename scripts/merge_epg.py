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
    "https://raw.githubusercontent.com/iptv-org/epg/master/sites/dsmart.com.tr/dsmart.com.tr.channels.xml",
]

tv = ET.Element('tv')
channels = {}
prog_channels = set()

def normalize_id(cid):
    if not cid: return None
    cid = cid.strip()
    if "KABLO" in cid.upper(): return None
    if cid.lower().endswith(".tr"): cid = cid[:-3]
    return cid.split("@")[0].strip()

def clean_name(name):
    if not name: return name
    name = name.strip()
    if name.lower().endswith(".tr"):
        name = name[:-3].strip()
    return name

for url in SOURCES:
    try:
        data = requests.get(url, timeout=60, headers={"User-Agent":"Mozilla/5.0"}).content
        if url.endswith('.gz'): 
            try: data = gzip.decompress(data)
            except: pass
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            nid = normalize_id(ch.get('id',''))
            if not nid or nid in channels: continue
            dn = ch.find('display-name')
            name = clean_name(dn.text if dn is not None and dn.text else nid)
            channels[nid]=name
            ch.set('id', nid)
            if dn is not None: dn.text = name
            tv.append(ch)
        for pr in root.findall('programme'):
            nid = normalize_id(pr.get('channel',''))
            if not nid: continue
            t = pr.find('title')
            if t is None or not t.text: continue
            if "kablo" in t.text.lower(): continue
            pr.set('channel', nid)
            prog_channels.add(nid)
            tv.append(pr)
    except Exception as e:
        print(f"{url} hata: {e}")

# MANUEL OLARAK BEIN 5 ve D-SMART kanalları yoksa ekle
MANUEL_KANALLAR = ["beIN Sports 5", "beIN Sports Max 1", "beIN Sports Max 2", "D-Smart Spor", "D-Smart Go", "Smart Çocuk", "D-Smart Sinema", "Tivibu Spor", "Tivibu Spor 1", "Tivibu Spor 2", "Tivibu Spor 3", "Tivibu Spor 4"]



for mk in MANUEL_KANALLAR:
    if mk not in channels:
        ch = ET.Element('channel', {'id': mk})
        ET.SubElement(ch, 'display-name').text = mk
        tv.append(ch)
        channels[mk]=mk

now = datetime.utcnow()
s = now.strftime("%Y%m%d%H%M%S +0000")
e = (now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000")

eksik = 0
for cid, name in channels.items():
    if cid not in prog_channels:
        prog = ET.Element('programme', {'channel': cid, 'start': s, 'stop': e})
        ET.SubElement(prog, 'title', {'lang': 'tr'}).text = name
        tv.append(prog)
        eksik+=1

ET.ElementTree(tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"TOPLAM KANAL: {len(channels)} | PROGRAMI OLAN: {len(prog_channels)} | İSMİ EKLENEN: {eksik}")
