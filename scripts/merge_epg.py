import requests, gzip, xml.etree.ElementTree as ET
from datetime import datetime, timedelta

SOURCES = [
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR2.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://iptv-epg.org/epg/tr.xml.gz",
]

tv = ET.Element('tv')
channels = {}
prog_count = 0

def normalize_id(cid):
    if not cid: return None
    cid = cid.strip()
    if not cid: return None
    if "KABLO" in cid.upper(): return None
    # sadece .tr sil, gerisine dokunma
    if cid.lower().endswith(".tr"):
        cid = cid[:-3]
    cid = cid.split("@")[0]
    return cid.strip()

for url in SOURCES:
    try:
        print(f"Kaynak: {url}")
        data = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"}).content
        if url.endswith('.gz'): data = gzip.decompress(data)
        root = ET.fromstring(data)
        c=0
        p=0
        for ch in root.findall('channel'):
            nid = normalize_id(ch.get('id',''))
            if not nid: continue
            dn = ch.find('display-name')
            name = dn.text if dn is not None and dn.text else nid
            if nid not in channels:
                channels[nid]=name
                ch.set('id', nid)
                tv.append(ch)
                c+=1
        for pr in root.findall('programme'):
            nid = normalize_id(pr.get('channel',''))
            if not nid: continue
            t = pr.find('title')
            if t is None or not t.text: continue
            if "kablo" in t.text.lower(): continue
            pr.set('channel', nid)
            tv.append(pr)
            p+=1
        print(f"  -> {c} yeni kanal, {p} program")
        prog_count+=p
    except Exception as e:
        print(f"  HATA: {e}")

# EPG'si olmayanlara isim ekle
now = datetime.utcnow()
start = now.strftime("%Y%m%d%H%M%S +0000")
stop = (now + timedelta(hours=12)).strftime("%Y%m%d%H%M%S +0000")
# mevcut programı olan kanalları bul
has_prog = set([e.get('channel') for e in tv.findall('programme')])

for cid, name in channels.items():
    if cid not in has_prog:
        prog = ET.Element('programme', {'channel': cid, 'start': start, 'stop': stop})
        ET.SubElement(prog, 'title', {'lang': 'tr'}).text = name
        ET.SubElement(prog, 'desc', {'lang': 'tr'}).text = f"{name} yayını"
        tv.append(prog)

ET.ElementTree(tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"BİTTİ -> Toplam {len(channels)} kanal, {prog_count} program")
