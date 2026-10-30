#!/usr/bin/env python3
"""Genera precios.json a partir de Open Prices (Open Food Facts) para una zona.

Uso:
  python3 herramientas/actualizar_precios.py --diagnostico      # solo cuenta y enseña qué hay en tu zona
  python3 herramientas/actualizar_precios.py                    # escribe precios.json
  python3 herramientas/actualizar_precios.py --entrada pagina.json   # lee un volcado local en vez de la red

Opciones: --cp 28025 --lat 40.388 --lon -3.735 --radio 12 --dias 365 --min-obs 1 --paginas 60
Si la API pide autenticación, define OPEN_PRICES_TOKEN en el entorno.

Datos: Open Prices, proyecto de Open Food Facts, licencia ODbL (hay que citar la fuente).
Solo usa la biblioteca estándar de Python.
NOTA: escrito siguiendo la documentación pública de la API. Si algún campo no coincide,
el modo --diagnostico lo enseña y basta con ajustar la función `normaliza`.
"""
import argparse, csv, json, math, os, re, statistics, sys, time, unicodedata
import urllib.parse, urllib.request, urllib.error
from datetime import date, timedelta
from pathlib import Path

BASE = "https://prices.openfoodfacts.org/api/v1/prices"
RAIZ = Path(__file__).resolve().parent.parent
CADENAS = {
    "Mercadona": r"mercadona",
    "Lidl": r"\blidl\b",
    "Aldi": r"\baldi\b",
    "Dia": r"\bdia\b|supermercados dia|\bdia %",
    "Carrefour": r"carrefour",
    "Alcampo": r"alcampo",
    "Ahorramás": r"ahorramas|ahorra mas",
}
# id de producto -> expresión sobre el nombre/categoría. Lo que no esté aquí usa el precio de referencia.
PATRONES = {
    "tomate": r"\btomates?\b|tomatoes", "cebolla": r"\bcebollas?\b|onions", "ajo": r"\bajos?\b|garlic",
    "pimiento": r"\bpimientos?\b(?!.*piquillo)|bell-peppers", "zanahoria": r"zanahoria|carrots",
    "patata": r"\bpatatas?\b|potatoes", "calabacin": r"calabac[ií]n|zucchini|courgette",
    "espinacas": r"espinaca|spinach", "champis": r"champi[ñn]ones?|mushrooms", "platano": r"pl[aá]tano|banana",
    "manzana": r"\bmanzanas?\b|apples", "brocoli": r"br[oó]coli|broccoli", "judias": r"jud[ií]as verdes|green-beans",
    "berenjena": r"berenjena|aubergine|eggplant", "pepino": r"\bpepinos?\b|cucumber", "puerro": r"\bpuerros?\b|leeks",
    "calabaza": r"calabaza|pumpkin", "coliflor": r"coliflor|cauliflower", "naranja": r"\bnaranjas?\b|oranges",
    "pechuga": r"pechuga.*pollo|chicken-breast", "muslo": r"(muslo|contramuslo).*pollo|chicken-thigh",
    "picada": r"carne picada|minced-meat", "lomo": r"\blomo\b.*cerdo|pork-loin", "ternera": r"ternera.*(guisar|estofar)|beef-stew",
    "merluza": r"merluza|hake", "salmon": r"salm[oó]n|salmon", "bacalao": r"bacalao|cod\b",
    "sardinas": r"sardina|sardines", "boquerones": r"boquer[oó]n|anchov", "mejillones": r"mejill[oó]n|mussels",
    "leche": r"\bleche\b(?!.*(coco|avena|soja|almendra))|milk", "arroz": r"\barroz\b|\brice\b", "pasta": r"macarron|espagueti|\bpasta\b|spaghetti|pasta",
    "lentejas": r"lentejas|lentils", "garbanzos": r"garbanzos|chickpeas", "aceite": r"aceite.*oliva|olive-oil",
    "harina": r"harina|\bflour\b", "avena": r"copos.*avena|rolled-oats|oat-flakes", "cuscus": r"cusc[uú]s|couscous",
    "yogur": r"yogur natural|plain-yogurt", "huevos": r"\bhuevos?\b|\beggs?\b", "atun": r"at[uú]n.*(lata|aceite)|canned-tuna",
}
def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")

def haversine(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742 * math.asin(math.sqrt(x))

def productos():
    out = {}
    with open(RAIZ / "productos.csv", encoding="utf-8-sig") as f:
        for r in csv.DictReader(f, delimiter=";"):
            out[r["id"]] = {"nombre": r["nombre"], "tam": float(r["tamano_envase"]), "u": r["unidad"]}
    return out

def pide(params, token):
    url = BASE + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "la-cesta/1.0"})
    if token:
        req.add_header("Authorization", "Bearer " + token)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)

def descarga(args):
    token = os.environ.get("OPEN_PRICES_TOKEN")
    desde = (date.today() - timedelta(days=args.dias)).isoformat()
    params = {"size": 100, "order_by": "-date", "currency": "EUR", "date__gte": desde,
              "location__osm_address_country_code": "ES"}
    for pag in range(1, args.paginas + 1):
        params["page"] = pag
        try:
            datos = pide(params, token)
        except urllib.error.HTTPError as e:
            if e.code in (400, 422) and "location__osm_address_country_code" in params:
                del params["location__osm_address_country_code"]; print("Filtro de país no admitido; filtro en local.", file=sys.stderr); continue
            if e.code in (401, 403):
                sys.exit("La API pide autenticación: define OPEN_PRICES_TOKEN.")
            raise
        items = datos.get("items", [])
        yield from items
        if pag >= int(datos.get("pages", pag)) or not items:
            break
        time.sleep(0.4)

def normaliza(p):
    """Devuelve (cadena_texto, lat, lon, texto_producto, euros_por_base, base) o None. Base: kg, l o ud."""
    loc = p.get("location") or {}
    lat, lon = loc.get("osm_lat"), loc.get("osm_lon")
    prod = p.get("product") or {}
    texto = sin_tildes(" ".join(str(x) for x in [prod.get("product_name") or "", p.get("category_tag") or "",
                                                " ".join(prod.get("categories_tags") or [])]))
    precio = p.get("price")
    per = (p.get("price_per") or "").upper()
    if precio is None or lat is None or lon is None:
        return None
    cant = prod.get("product_quantity")
    unidad_cant = (prod.get("product_quantity_unit") or "g").lower()
    if per == "KILOGRAM":
        valor, base = float(precio), "kg"
    elif per in ("LITER", "LITRE"):
        valor, base = float(precio), "l"
    elif per == "UNIT" and cant:
        q = float(cant) / 1000.0
        valor, base = float(precio) / q, ("l" if unidad_cant == "ml" else "kg")
    elif per == "UNIT":
        valor, base = float(precio), "ud"
    else:
        return None
    nombre_loc = sin_tildes(" ".join(str(loc.get(k) or "") for k in ("osm_brand", "osm_name")))
    return nombre_loc, float(lat), float(lon), texto, valor, base

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cp", default="28025"); ap.add_argument("--lat", type=float, default=40.388)
    ap.add_argument("--lon", type=float, default=-3.735); ap.add_argument("--radio", type=float, default=12)
    ap.add_argument("--dias", type=int, default=365); ap.add_argument("--min-obs", type=int, default=1)
    ap.add_argument("--paginas", type=int, default=60); ap.add_argument("--entrada")
    ap.add_argument("--diagnostico", action="store_true"); ap.add_argument("--salida", default=str(RAIZ / "precios.json"))
    args = ap.parse_args()
    prods = productos()
    if args.entrada:
        crudo = json.load(open(args.entrada, encoding="utf-8")); fuente = crudo.get("items", crudo)
    else:
        fuente = descarga(args)
    n = cerca = 0
    validos = 0
    dmin = 1e9
    muestra = None
    ciudades = {}
    por_cadena = {c: 0 for c in CADENAS}
    obs = {c: {} for c in CADENAS}
    for p in fuente:
        n += 1
        if muestra is None:
            muestra = p
        lc = p.get("location") or {}
        ck = (lc.get("osm_address_country_code") or "?") + "/" + str(lc.get("osm_address_city") or lc.get("osm_address_state") or "?")
        ciudades[ck] = ciudades.get(ck, 0) + 1
        r = normaliza(p)
        if not r:
            continue
        validos += 1
        loc, lat, lon, texto, valor, base = r
        dmin = min(dmin, haversine(args.lat, args.lon, lat, lon))
        if haversine(args.lat, args.lon, lat, lon) > args.radio:
            continue
        cerca += 1
        cad = next((c for c, rx in CADENAS.items() if re.search(rx, loc)), None)
        if not cad:
            continue
        por_cadena[cad] += 1
        for pid, rx in PATRONES.items():
            if pid in prods and re.search(rx, texto):
                obs[cad].setdefault(pid, []).append((valor, base))
    precios, cobertura = {}, {}
    for cad in CADENAS:
        precios[cad] = {}
        for pid, lista in obs[cad].items():
            tam, u = prods[pid]["tam"], prods[pid]["u"]
            base_esp = {"g": "kg", "ml": "l", "ud": "ud"}[u]
            vals = [v for v, b in lista if b == base_esp]
            if len(vals) < args.min_obs:
                continue
            med = statistics.median(vals)
            precios[cad][pid] = round(med * (tam / 1000.0 if u in ("g", "ml") else tam), 2)
        cobertura[cad] = len(precios[cad])
    print(f"Precios leídos: {n} · a menos de {args.radio:g} km de {args.cp}: {cerca}")
    for c in CADENAS:
        print(f"  {c:10s} observaciones: {por_cadena[c]:4d} · productos con precio: {cobertura[c]:2d}/{len(prods)}")
    if args.diagnostico:
        print(f"Utilizables (con coordenadas y unidad de precio): {validos} · distancia mínima a {args.cp}: {dmin:.1f} km")
        print("Ciudades más frecuentes:", sorted(ciudades.items(), key=lambda x: -x[1])[:12])
        if muestra:
            print("Ejemplo de registro:", json.dumps(muestra, ensure_ascii=False)[:1500])
        return
    salida = {"meta": {"fecha": date.today().isoformat(), "cp": args.cp, "fuente": "Open Prices (Open Food Facts), ODbL",
                       "cobertura": cobertura, "total": len(prods)}, "precios": precios}
    Path(args.salida).write_text(json.dumps(salida, ensure_ascii=False, indent=1), encoding="utf-8")
    print("Escrito", args.salida)

if __name__ == "__main__":
    main()
