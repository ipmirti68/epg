import requests, gzip, xml.etree.ElementTree as ET
SOURCES = [
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://raw.githubusercontent.com/ahmethascelik/epghost/main/xmltv.xml",
]
tv = ET.Element('tv')
seen=set()
for url in SOURCES:
    try:
        d=requests.get(url,timeout=90,headers={"User-Agent":"Mozilla/5.0"}).content
        if url.endswith('.gz'): d=gzip.decompress(d)
        r=ET.fromstring(d)
        for ch in r.findall('channel'):
            cid=ch.get('id','')
            if "KABLO" in cid.upper(): continue
            if cid not in seen:
                seen.add(cid); tv.append(ch)
        for p in r.findall('programme'):
            cid=p.get('channel','')
            if "KABLO" in cid.upper(): continue
            t=p.find('title')
            if t is None or not t.text: continue
            if t.text.strip().lower()=="kablo info": continue
            if t.text.strip()=="": continue
            tv.append(p)
    except Exception as e: print(e)
ET.ElementTree(tv).write('epg.xml',encoding='utf-8',xml_declaration=True)
print("TEMIZ")
