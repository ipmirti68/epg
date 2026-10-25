import requests, gzip, xml.etree.ElementTree as ET, re
from datetime import datetime, timedelta, timezone
from collections import defaultdict

SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR2.xml.gz",
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    "https://www.open-epg.com/files/turkey4.xml.gz",
    "https://www.open-epg.com/files/turkey5.xml.gz",
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
    # 24 HD, 24.TV, 24 TV HD, 24.TV.HD -> hepsi "24"
    # A HABER HD, A.HABER.HD -> "a haber"
    # beIN SPORTS 1 HD -> "bein sports 1"
    n = name.lower()
    n = n.replace(".tv","").replace(".hd","").replace(".fhd","")
    n = n.replace(" tv hd","").replace(" hd","").replace(" fhd","")
    n = re.sub(r'[^a-z0-9 ]',' ', n)
    n = re.sub(r'\s+',' ', n).strip()
    return n

tv_channels = {} # low_id -> Element
channel_by_base = defaultdict(list) # base_name -> [ids]
tv_progs = []
seen_prog = set()

for url in SOURCES:
    try:
        r = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200: continue
        data = r.content
        if url.endswith('.gz'):
            try: data = gzip.decompress(data)
            except: pass
        root = ET.fromstring(data)
        for ch in root.findall('channel'):
            cid = clean_id(ch.get('id',''))
            if not cid: continue
            low = cid.lower()
            if low not in tv_channels:
                # display-name al
                dn = ch.find('display-name')
                dname = dn.text if dn is not None and dn.text else cid
                dname = clean_id(dname)
                if dn is not None: dn.text = dname
                ch.set('id', cid)
                tv_channels[low] = ch
                b = base_name(dname)
                channel_by_base[b].append(cid)
        for pr in root.findall('programme'):
            cid = clean_id(pr.get('channel',''))
            if not cid: continue
            low = cid.lower()
            s = fix_time(pr.get('start',''))
            e = fix_time(pr.get('stop',''))
            if not s: continue
            key = (low, s)
            if key in seen_prog: continue
            pr.set('start', s); pr.set('stop', e)
            pr.set('channel', cid)
            tv_progs.append(pr)
            seen_prog.add(key)
    except Exception as e:
        print(f"HATA {url}: {e}")

# === VARYANTLARI BIRLESTIR ===
# Ayni base'e sahip kanallarin EPG'sini birbirine kopyala
print("=== VARYANTLAR BIRLESTIRILIYOR ===")
for base, ids in channel_by_base.items():
    if len(ids) <= 1: continue
    # Bu base'e ait tum programlari topla
    all_progs = []
    for cid in ids:
        all_progs.extend([p for p in tv_progs if p.get('channel','').lower() == cid.lower()])
    # Her varyanta hepsini kopyala
    for cid in ids:
        clow = cid.lower()
        for pr in all_progs:
            s = pr.get('start'); e = pr.get('stop')
            key = (clow, s)
            if key in seen_prog: continue
            new_pr = ET.Element('programme', {'channel': cid, 'start': s, 'stop': e})
            for child in pr:
                nc = ET.Element(child.tag, child.attrib)
                nc.text = child.text
                new_pr.append(nc)
            tv_progs.append(new_pr)
            seen_prog.add(key)

# === SENIN LISTEN ICIN BEIN MAPPING ===
# Sende: beinsports, beinsports 2, 3, 4, 5...
bein_map = {
    "bein sports 1": ["beinsports", "beinsports 1"],
    "bein sports 2": ["beinsports 2"],
    "bein sports 3": ["beinsports 3"],
    "bein sports 4": ["beinsports 4"],
    "bein sports 5": ["beinsports 5"],
    "bein sports haber": ["beinsports haber"],
    "bein sports max 1": ["beinsports max 1"],
    "bein sports max 2": ["beinsports max 2"],
}

for base_target, aliases in bein_map.items():
    # kaynakta bu base var mi?
    if base_target not in channel_by_base: continue
    source_ids = channel_by_base[base_target]
    source_progs = []
    for sid in source_ids:
        source_progs.extend([p for p in tv_progs if p.get('channel','').lower() == sid.lower()])
    if not source_progs: continue
    
    for alias in aliases:
        alow = alias.lower()
        if alow not in tv_channels:
            ch = ET.Element('channel', {'id': alias})
            ET.SubElement(ch, 'display-name').text = alias
            tv_channels[alow] = ch
            print(f"Alias olustu: {alias}")
        for pr in source_progs:
            s = pr.get('start'); e = pr.get('stop')
            key = (alow, s)
            if key in seen_prog: continue
            new_pr = ET.Element('programme', {'channel': alias, 'start': s, 'stop': e})
            for child in pr:
                nc = ET.Element(child.tag, child.attrib)
                nc.text = child.text
                new_pr.append(nc)
            tv_progs.append(new_pr)
            seen_prog.add(key)

# Final
final_tv = ET.Element('tv')
# Kablo net ve beinsports ayri kalsin diye sirala, bein en alta degil kendi yerinde
sorted_channels = sorted(tv_channels.values(), key=lambda x: x.get('id','').lower())
for ch in sorted_channels: final_tv.append(ch)
for pr in tv_progs: final_tv.append(pr)

ET.ElementTree(final_tv).write('epg.xml', encoding='utf-8', xml_declaration=True)

print(f"BITTI: {len(sorted_channels)} kanal, {len(tv_progs)} program")
print("Ornek gruplar:")
for b, ids in list(channel_by_base.items())[:10]:
    if len(ids)>1:
        print(f" {b} -> {ids}")
