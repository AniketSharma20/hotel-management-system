import urllib.request
import os
import concurrent.futures

rooms = [
    '1611892440504-42a792e24d32', '1582719478250-c89cae4dc85b', '1522708323590-d24dbb6b0267', 
    '1590490359854-dfba196ce0cb', '1578683010236-d716f9a3f461', '1566665797739-165f69aae28e',
    '1512918728675-ed5a9ecdebfd', '1600596542815-ffad4c1539a9'
]

foods = [
    '1484723091782-4defd7cb44da', '1525351484163-7529414344d8', '1562376552-0d160a2f14b5',
    '1568901346375-23c9450c58cd', '1467003909585-2f8a72700288', '1544025162-817abedcf4ce',
    '1473093295043-cdd812d0e601', '1624353365286-3f8d62daad51', '1524351199678-941a58a3df50',
    '1571115177098-24ec42ed204d', '1514362545857-3bc16c4c7d1b', '1613478223719-2ab802602423',
    '1506377247377-2a5b3b417ebb'
]

os.makedirs('assets', exist_ok=True)

def download(item, index, prefix):
    url = f'https://images.unsplash.com/photo-{item}?w=800&q=80'
    filename = f'assets/{prefix}{index}.jpg'
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
    try:
        res = urllib.request.urlopen(req, timeout=10)
        with open(filename, 'wb') as f:
            f.write(res.read())
        print(f'Downloaded {filename}')
    except Exception as e:
        print(f'Failed {filename}: {e}')

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    for i, r in enumerate(rooms):
        executor.submit(download, r, i+1, 'room')
    for i, f in enumerate(foods):
        executor.submit(download, f, i+1, 'food')
