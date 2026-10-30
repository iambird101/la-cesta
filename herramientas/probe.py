import json, urllib.request, urllib.parse
B = "https://prices.openfoodfacts.org/api/v1/"
def get(ruta, **p):
    u = B + ruta + "?" + urllib.parse.urlencode(p)
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "la-cesta/1.0", "Accept": "application/json"}), timeout=40) as r:
            return json.load(r)
    except Exception as e:
        return {"error": str(e)}
base = get("prices", size=1)
print("prices total sin filtro:", base.get("total"), base.get("error", ""))
for k, v in [("location__osm_address_country_code", "ES"), ("location__osm_address_country_code", "es"), ("location_osm_address_country_code", "ES"),
             ("osm_address_country_code", "ES"), ("location__osm_address_city", "Madrid"), ("location__osm_address_postcode", "28025"),
             ("location__osm_address_postcode__startswith", "280")]:
    d = get("prices", size=1, **{k: v})
    print("prices", k, v, "->", d.get("total"), d.get("error", ""))
b2 = get("locations", size=1)
print("locations total sin filtro:", b2.get("total"), b2.get("error", ""))
for k, v in [("osm_address_country_code", "ES"), ("osm_address_city", "Madrid"), ("osm_address_postcode", "28025")]:
    d = get("locations", size=3, **{k: v})
    print("locations", k, v, "->", d.get("total"), d.get("error", ""), [(i.get("id"), i.get("osm_name"), i.get("osm_address_city")) for i in d.get("items", [])])
