CANARIAS CERCA — EXPLORE ALL ISLANDS PATCH

WHAT THIS PATCH ADDS
- Gran Canaria: 6 Explore stories
- Lanzarote: 6 Explore stories
- Fuerteventura: 6 Explore stories
- La Palma: 6 Explore stories
- La Gomera: 6 Explore stories
- El Hierro: 6 Explore stories
- La Graciosa: 6 Explore stories
- app/services/explore.py: supported_islands is detected dynamically

TENERIFE
This patch intentionally does NOT contain data/content/tenerife/explore.json.
Keep your existing working Tenerife file.

INSTALL
Copy the patch contents into the backend project root:
C:\projects\canary project\canarias-backend-starter

It will create:
data/content/<island>/explore.json

and replace:
app/services/explore.py

TEST
http://127.0.0.1:8000/api/regions/canarias/explore?island=gran-canaria
http://127.0.0.1:8000/api/regions/canarias/explore?island=lanzarote
http://127.0.0.1:8000/api/regions/canarias/explore?island=fuerteventura
http://127.0.0.1:8000/api/regions/canarias/explore?island=la-palma
http://127.0.0.1:8000/api/regions/canarias/explore?island=la-gomera
http://127.0.0.1:8000/api/regions/canarias/explore?island=el-hierro
http://127.0.0.1:8000/api/regions/canarias/explore?island=la-graciosa

IMAGES
New islands intentionally ship with image_url/image_credit/image_source_url = null.
The editorial content and source URLs are ready first. Add licensed Wikimedia
or your own photos in the next pass rather than shipping guessed/broken image URLs.
