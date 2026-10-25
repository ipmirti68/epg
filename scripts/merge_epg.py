import requests, gzip, xml.etree.ElementTree as ET, re
from datetime import datetime, timedelta, timezone
from collections import defaultdict

SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://www.open-epg.com/files/turkey4.xml.gz",
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

def base_name(name):
    n = name.lower().replace(".tv","").replace(".hd","")
    n = re.sub(r'[^a-z0-9 ]',' ', n); n = re.sub(r'\s+',' ', n).strip()
    return n

tv_channels = {}
channel_by_base = defaultdict(list)
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
            dn = ch.find('display-name')
            dname = dn.text if dn is not None and dn.text else cid
            if dn is not None: dn.text = clean_id(dname)
            ch.set('id', cid)
            tv_channels[cid.lower()] = ch
            channel_by_base[base_name(dname)].append(cid)
        for pr in root.findall('programme'):
            cid = clean_id(pr.get('channel',''))
            if not cid: continue
            s = fix_time(pr.get('start','')); e = fix_time(pr.get('stop',''))
            if not s: continue
            key = (cid.lower(), s)
            if key in seen_prog: continue
            pr.set('start', s); pr.set('stop', e); pr.set('channel', cid)
            tv_progs.append(pr); seen_prog.add(key); has_epg.add(cid.lower())
    except Exception as e:
        print(e)

# Varyant birleştir
for base, ids in channel_by_base.items():
    if len(ids) <= 1: continue
    all_p = []
    for cid in ids: all_p.extend([p for p in tv_progs if p.get('channel','').lower()==cid.lower()])
    for cid in ids:
        for pr in all_p:
            key = (cid.lower(), pr.get('start'))
            if key in seen_prog: continue
            np = ET.Element('programme', {'channel': cid, 'start': pr.get('start'), 'stop': pr.get('stop')})
            for c in pr: nc = ET.Element(c.tag, c.attrib); nc.text = c.text; np.append(nc)
            tv_progs.append(np); seen_prog.add(key)

# beinsports mapping - senin liste
for base_target, aliases in {"bein sports 1":["beinsports","beinsports 1"],"bein sports 2":["beinsports 2"],"bein sports 3":["beinsports 3"],"bein sports 4":["beinsports 4"],"bein sports 5":["beinsports 5"],"bein sports haber":["beinsports haber"]}.items():
    if base_target not in channel_by_base: continue
    src = []
    for sid in channel_by_base[base_target]: src.extend([p for p in tv_progs if p.get('channel','').lower()==sid.lower()])
    for alias in aliases:
        if alias.lower() not in tv_channels:
            ch = ET.Element('channel', {'id': alias}); ET.SubElement(ch, 'display-name').text = alias; tv_channels[alias.lower()] = ch
        for pr in src:
            key = (alias.lower(), pr.get('start'))
            if key in seen_prog: continue
            np = ET.Element('programme', {'channel': alias, 'start': pr.get('start'), 'stop': pr.get('stop')})
            for c in pr: nc = ET.Element(c.tag, c.attrib); nc.text = c.text; np.append(nc)
            tv_progs.append(np); seen_prog.add(key)

# FINAL - Radyo için ID yazdır
final_tv = ET.Element('tv')
sorted_channels = sorted(tv_channels.values(), key=lambda x: x.get('id','').lower())
for ch in sorted_channels: final_tv.append(ch)
for pr in tv_progs: final_tv.append(pr)

now = datetime.now(timezone(timedelta(hours=3)))
for low,ch in tv_channels.items():
    if low in has_epg: continue
    cid = ch.get('id')
    dname = ch.find('display-name').text if ch.find('display-name') is not None else cid
    is_radio = any(x in dname.lower() for x in ["radyo","fm","radio","türkü"])
    for day in range(7): # 7 GÜN
        ds = (now + timedelta(days=day)).replace(hour=0,minute=0,second=0,microsecond=0)
        de = ds + timedelta(days=1)
        prog = ET.Element('programme', {'channel': cid, 'start': ds.strftime("%Y%m%d%H%M%S +0300"), 'stop': de.strftime("%Y%m%d%H%M%S +0300")})
        if is_radio:
            ET.SubElement(prog, 'title', {'lang':'tr'}).text = f"📻 {dname}"
            ET.SubElement(prog, 'desc', {'lang':'tr'}).text = f"{dname} canlı yayın"
        else:
            ET.SubElement(prog, 'title', {'lang':'tr'}).text = dname
            ET.SubElement(prog, 'desc', {'lang':'tr'}).text = dname
        final_tv.append(prog)

ET.ElementTree(final_tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"BITTI: {len(sorted_channels)} kanal, EPG olmayan: {len(tv_channels)-len(has_epg)} tanesine ID yazildi")
