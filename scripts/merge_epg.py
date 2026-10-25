import requests, gzip, xml.etree.ElementTree as ET, re
from datetime import datetime, timedelta, timezone
from collections import defaultdict

SOURCES = [
    "https://epgshare01.online/epgshare01/epg_ripper_TR1.xml.gz",
    "https://epgshare01.online/epgshare01/epg_ripper_TR3.xml.gz",
    "https://www.open-epg.com/files/turkey1.xml.gz",
    "https://www.open-epg.com/files/turkey2.xml.gz",
    "https://www.open-epg.com/files/turkey3.xml.gz",
    # TABII VE TRT ICIN EK KAYNAKLAR - SPOR ICIN EN DOLU
    "https://iptv-org.github.io/epg/guides/tr/tabii.com.tr.epg.xml.gz",
    "https://iptv-org.github.io/epg/guides/tr/trt.com.tr.epg.xml.gz",
    "https://iptv-org.github.io/epg/guides/tr/tvplus.com.tr.epg.xml.gz",
]

EXTRA_RADIOS = [
    "AKSARAY NIN SESI 95.1", "AKSARAY FM 99.5", "AKSARAY RADYO 68", "MAVI RADYO",
    "TURKULERLE TURKIYE", "RADYO TURKU", "TRT TURKU", "RADYO 7 TURKU", 
    "RADYO 7 MUHTESEM 4", "RADYO 7 NOSTALJI", "RADYO ANKARA",
    "KRAL FM", "KRAL POP", "POWER FM", "POWER TURK",
]

# TABII SPOR ICIN SENIN LISTENDEKI IDLER
EXTRA_SPORTS_ALIAS = {
    "tabii spor": ["TABII SPOR", "tabii.spor", "tabii spor", "TABII.SPOR"],
    "tabii spor 1": ["TABII SPOR 1", "tabii spor 1", "TABII SPOR1", "tabii.spor 1"],
    "tabii spor 2": ["TABII SPOR 2", "tabii spor 2"],
    "tabii spor 3": ["TABII SPOR 3", "tabii spor 3"],
    "tabii spor 4": ["TABII SPOR 4", "tabii spor 4"],
    "tabii spor 5": ["TABII SPOR 5", "tabii spor 5"],
    "tabii spor 6": ["TABII SPOR 6", "tabii spor 6"],
    "beinsports": ["beinsports", "beIN SPORTS 1", "BEIN SPORTS 1"],
    "beinsports 2": ["beinsports 2", "beIN SPORTS 2"],
    "beinsports 3": ["beinsports 3", "beIN SPORTS 3"],
    "beinsports 4": ["beinsports 4", "beIN SPORTS 4"],
    "beinsports 5": ["beinsports 5", "beIN SPORTS 5"],
}

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
    n = name.lower()
    n = n.replace(".tv","").replace(".hd","").replace("fhd","")
    n = re.sub(r'[^a-z0-9 ]',' ', n)
    n = re.sub(r'\s+',' ', n).strip()
    return n

tv_channels = {}
channel_by_base = defaultdict(list)
tv_progs = []
seen_prog = set()
has_epg = set()

for url in SOURCES:
    try:
        r = requests.get(url, timeout=90, headers={"User-Agent":"Mozilla/5.0"})
        if r.status_code != 200: 
            print(f"❌ {url.split('/')[-1]} {r.status_code}")
            continue
        data = gzip.decompress(r.content) if url.endswith('.gz') else r.content
        root = ET.fromstring(data)
        ch_c = pr_c = 0
        for ch in root.findall('channel'):
            cid = clean_id(ch.get('id',''))
            if not cid or cid.lower() in tv_channels: continue
            dn = ch.find('display-name')
            dname = dn.text if dn is not None and dn.text else cid
            ch.set('id', cid)
            tv_channels[cid.lower()] = ch
            channel_by_base[base_name(dname)].append(cid)
            ch_c += 1
        for pr in root.findall('programme'):
            cid = clean_id(pr.get('channel',''))
            if not cid: continue
            s = fix_time(pr.get('start','')); e = fix_time(pr.get('stop',''))
            if not s: continue
            key = (cid.lower(), s)
            if key in seen_prog: continue
            pr.set('start', s); pr.set('stop', e); pr.set('channel', cid)
            tv_progs.append(pr); seen_prog.add(key); has_epg.add(cid.lower())
            pr_c += 1
        print(f"✓ {url.split('/')[-1][:35]} -> {ch_c} kanal, {pr_c} program")
    except Exception as e:
        print(f"HATA {url}: {e}")

# Varyant birleştir (24, 24 HD vs)
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

# EXTRA RADYO EKLE
for rad in EXTRA_RADIOS:
    if rad.lower() not in tv_channels:
        ch = ET.Element('channel', {'id': rad}); ET.SubElement(ch, 'display-name').text = rad
        tv_channels[rad.lower()] = ch

# SPOR ALIASLARI EKLE - tabii spor 1-5 ve beinsports
for base_target, aliases in EXTRA_SPORTS_ALIAS.items():
    # kaynakta bu base var mi ara
    src_ids = channel_by_base.get(base_target, [])
    if not src_ids:
        # tabii spor 1 -> tabii spor + 1 icerenleri bul
        src_ids = [cid for b,cids in channel_by_base.items() if base_target in b for cid in cids]
    if not src_ids: continue
    src_progs = []
    for sid in src_ids: src_progs.extend([p for p in tv_progs if p.get('channel','').lower()==sid.lower()])
    if not src_progs: continue
    for alias in aliases:
        alow = alias.lower()
        if alow not in tv_channels:
            ch = ET.Element('channel', {'id': alias}); ET.SubElement(ch, 'display-name').text = alias
            tv_channels[alow] = ch
            channel_by_base[base_target].append(alias)
        for pr in src_progs:
            key = (alow, pr.get('start'))
            if key in seen_prog: continue
            np = ET.Element('programme', {'channel': alias, 'start': pr.get('start'), 'stop': pr.get('stop')})
            for c in pr: nc = ET.Element(c.tag, c.attrib); nc.text = c.text; np.append(nc)
            tv_progs.append(np); seen_prog.add(key)
        print(f"✓ ALIAS: {base_target} -> {alias} ({len(src_progs)} prog)")

# FINAL
final_tv = ET.Element('tv')
sorted_channels = sorted(tv_channels.values(), key=lambda x: x.get('id','').lower())
for ch in sorted_channels: final_tv.append(ch)
for pr in tv_progs: final_tv.append(pr)

# EPG olmayanlara ID yaz
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

ET.ElementTree(final_tv).write('epg.xml', encoding='utf-8', xml_declaration=True)
print(f"\nBITTI: {len(tv_channels)} kanal")
print("TABII KONTROL:")
for ch in sorted_channels:
    if "tabii" in ch.get('id','').lower():
        cnt = len([p for p in tv_progs if p.get('channel','').lower()==ch.get('id','').lower()])
        print(f" - {ch.get('id'):20} : {cnt} program")
