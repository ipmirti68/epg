import requests, gzip, xml.etree.ElementTree as ET
from datetime import datetime, timedelta

SOURCES = [
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
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

for url in SOURCES:
    try:
        data = requests.get(url, timeout=60, headers={"User-Agent":"Mozilla/5.0"}).content
        if url.endswith('.gz'): data = gzip.decompress(data)
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            nid = normalize_id(ch.get('id',''))
            if not nid or nid in channels: continue
            dn = ch.find('display-name')
            name = dn.text.strip() if dn is not None and dn.text else nid
            channels[nid]=name
            ch.set('id', nid)
            if dn is not None: dn.text = name
            tv.append(ch)
        for pr in root.findall('programme'):
            nid = normalize_id(pr.get('channel',''))
            if not nid: continue
            if pr.find('title') is None: continue
            if "kablo" in pr.find('title').text.lower(): continue
            pr.set('channel', nid)
            prog_channels.add(nid)
            tv.append(pr)
    except Exception as e:
        print(e)

# İŞTE BURASI - EPG'si olmayan kanala kendi ismini yaz
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
