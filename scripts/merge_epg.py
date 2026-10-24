import requests, gzip, xml.etree.ElementTree as ET
from datetime import datetime, timedelta

SOURCES = [
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR2.xml.gz",
    "https://iptv-epg.org/epg/tr.xml.gz",
    "https://raw.githubusercontent.com/iptv-org/epg/master/sites/tvplus.com.tr/tvplus.com.tr.xml.gz",

]

tv = ET.Element('tv')
channels = {} # id -> display-name
prog_channels = set()

def normalize_id(cid):
    if not cid: return ""
    cid = cid.strip()
    if "KABLO" in cid.upper(): return None
    if cid.lower().endswith(".tr"): cid = cid[:-3]
    cid = cid.split("@")[0].strip(".")
    return cid

for url in SOURCES:
    try:
        data = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"}).content
        if url.endswith('.gz'): data = gzip.decompress(data)
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            nid = normalize_id(ch.get('id',''))
            if not nid: continue
            dn = ch.find('display-name')
            name = dn.text if dn is not None and dn.text else nid
            if nid not in channels:
                channels[nid] = name
                ch.set('id', nid)
                tv.append(ch)
        for p in root.findall('programme'):
            nid = normalize_id(p.get('channel',''))
            if not nid: continue
            t = p.find('title')
            if t is None or not t.text: continue
            if "kablo" in t.text.lower(): continue
            p.set('channel', nid)
            prog_channels.add(nid)
            tv.append(p)
    except Exception as e:
        print(e)

# EPG'si olmayanlara kendi ismini yaz
now = datetime.utcnow()
start = now.strftime("%Y%m%d%H%M%S +0000")
stop = (now + timedelta(hours=12)).strftime("%Y%m%d%H%M%S +0000")

for cid, name in channels.items():
    if cid not in prog_channels:
        prog = ET.Element('programme', {'channel': cid, 'start': start, 'stop': stop})
        title = ET.SubElement(prog, 'title', {'lang': 'tr'})
        title.text = name  # Kanal ismi
        desc = ET.SubElement(prog, 'desc', {'lang': 'tr'})
        desc.text = f"{name} yayını"
        tv.append(prog)

ET.ElementTree(tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"Bitti -> {len(channels)} kanal, {len(channels)-len(prog_channels)} tanesine isim eklendi")
