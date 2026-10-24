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
            pr.set('channel', nid)
            tv.append(pr)
    except Exception as e:
        print(f"{url} hata: {e}")

# Eksik meşhur kanalları garanti ekle
MANUEL = ["Beyaz TV", "beIN Sports 5", "beIN Sports Max 1", "beIN Sports Max 2", "D-Smart Spor", "Smart Çocuk", "Tivibu Spor", "Tivibu Spor 1", "Tivibu Spor 2", "Tivibu Spor 3", "Tivibu Spor 4"]
for mk in MANUEL:
    if mk.lower() not in [k.lower() for k in channels]:
        ch = ET.Element('channel', {'id': mk})
        ET.SubElement(ch, 'display-name').text = mk
        tv.append(ch)
        channels[mk]=mk
        # Sahte program ekle ki listede gözüksün
        now = datetime.utcnow()
        s = now.strftime("%Y%m%d%H%M%S +0000")
        e = (now + timedelta(hours=24)).strftime("%Y%m%d%H%M%S +0000")
        prog = ET.Element('programme', {'channel': mk, 'start': s, 'stop': e})
        ET.SubElement(prog, 'title', {'lang': 'tr'}).text = mk
        tv.append(prog)

ET.ElementTree(tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"TOPLAM KANAL: {len(channels)}")
