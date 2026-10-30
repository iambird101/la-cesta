# La Cesta

Menús semanales y lista de la compra según supermercado, presupuesto, adultos, niños y menores de 3 años.
Este repositorio publica la web, actualiza los precios cada lunes con Open Prices y compila el APK de Android.

## Puesta en marcha (unos 10 minutos, una sola vez)

1. **Crea un repositorio en GitHub** (por ejemplo `la-cesta`) y súbele todo el contenido de esta carpeta, incluida la carpeta oculta `.github`.
   Hazlo mejor desde la terminal para que no se pierda `.github`:

       git init -b main
       git add -A
       git commit -m "La Cesta"
       git remote add origin https://github.com/TU_USUARIO/la-cesta.git
       git push -u origin main

   Hazlo **público**: no contiene datos personales, y GitHub Pages en repositorios privados exige un plan de pago.
2. **Activa la web**: en el repositorio, *Settings → Pages → Source: GitHub Actions*.
3. **Publica**: pestaña *Actions → Publicar web y precios → Run workflow*.
   Tu app quedará en `https://TU_USUARIO.github.io/la-cesta/`. Se actualiza sola cada lunes y cada vez que subas cambios.
4. **Crea el APK**: *Actions → Crear APK → Run workflow*. Tarda unos 5-8 minutos.
   Cuando termine, entra en la pestaña **Releases** del repositorio y descarga `La-Cesta.apk`.

## Instalar el APK en cada móvil
- Descarga `La-Cesta.apk` desde Releases en el navegador del móvil (con tu sesión de GitHub).
- Android pedirá permiso para «instalar apps de origen desconocido» para ese navegador: acéptalo.
- Si Play Protect avisa, es porque el APK no viene de la tienda; elige «Instalar de todos modos».
- Las actualizaciones se instalan encima de la anterior sin perder datos, porque el APK siempre se firma con la misma clave (`android-signing/debug.keystore`, de uso personal).

## Qué se actualiza solo y qué no
- **Precios**: el APK y la web leen `precios.json` desde tu página de GitHub Pages, así que se actualizan con cada ejecución semanal sin tocar el APK.
- **Recetas y cambios de la app**: hay que volver a lanzar *Crear APK* para tener la última versión en el móvil.
- **Menú compartido entre los dos móviles**: el APK guarda el menú en cada móvil. Para pasarlo, usa en la pestaña *Precios* la tarjeta «Pasar el menú a otro dispositivo» (copiar y pegar el código). La sincronización en vivo solo funciona en la versión del enlace de Claude; hacerla en el APK requiere un servidor.

## Novedades que dependen del móvil
- **Escanear etiquetas**: abre la cámara del móvil (el APK pide permiso la primera vez). Lee el código de barras si el móvil lo permite y el texto de la etiqueta con un lector OCR (Tesseract) que se descarga la primera vez, así que hace falta internet. Siempre confirmas el producto y el precio antes de guardar.
- **Importar recetas desde un enlace**: en el APK la descarga de la página se hace desde el propio móvil. En la web, si el sitio no permite leerlo directamente, se usa un servicio público intermediario; si tampoco funciona, pega el texto de la receta.
- **Apariencia**: el tema se guarda en cada dispositivo, no se comparte.

## Precios de Open Prices
`herramientas/actualizar_precios.py` descarga precios de [Open Prices](https://prices.openfoodfacts.org) (Open Food Facts, licencia ODbL: hay que citar la fuente), se queda con los de tiendas a menos de 12 km del código postal 28025 y escribe `precios.json`.
- Prueba primero `python3 herramientas/actualizar_precios.py --diagnostico`: cuenta cuántos precios hay en tu zona, de qué cadenas, y no escribe nada.
- Open Prices es colaborativo: la cobertura depende de cuánta gente suba precios cerca de ti. Lo que no tenga precio real usa el de referencia, y la app indica cuántos productos tiene reales cada súper.
- Si la API pide token, créalo en tu cuenta de Open Food Facts y guárdalo en *Settings → Secrets and variables → Actions* con el nombre `OPEN_PRICES_TOKEN`.
- El script se escribió a partir de la documentación pública y no se pudo probar contra la API real al crearlo, solo con datos de prueba. Si algún campo ha cambiado, el diagnóstico lo enseñará.

## Pasar a otro código postal
Cambia `28025` en `.github/workflows/publicar.yml` y, si quieres afinar, pasa `--lat` y `--lon` al script.

## Archivos
- `index.html`, `manifest.webmanifest`, `sw.js`, `icons/`: la app (instalable desde el navegador y con uso sin conexión).
- `precios.json`, `productos.csv`, `herramientas/`: precios y su actualización.
- `package.json`, `capacitor.config.json`, `android/`, `android-signing/`: el proyecto de Android.
- `.github/workflows/`: las dos tareas de GitHub.
