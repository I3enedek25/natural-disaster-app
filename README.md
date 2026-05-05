# Globális katasztrófa-gyakoriság térképes app
Ez az alkalmazás historikus természeti katasztrófa-események alapján világtérképen mutatja az előfordulási gyakoriságot színskálás hexagon-hőtérképpel.
## Támogatott típusok
- Tornádók és hurrikánok (EONET: `severeStorms`)
- Vulkánkitörések (EONET: `volcanoes`)
- Árvizek (EONET: `floods`)
- Lavinák / földcsuszamlások (EONET: `landslides`)
- Földrengések (EONET: `earthquakes`)
## Adatforrás
- NASA EONET API (`https://eonet.gsfc.nasa.gov/api/v3/events`)
- A rekordok tartalmazzák az esemény helyét (koordináta) és időpontját.
- A lokális cache fájl: `data/cache/eonet_events.csv`.
## Telepítés
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```
## Futtatás
```powershell
streamlit run app.py
```
Az alkalmazás oldalsávjában:
- szűrhetsz katasztrófatípusra,
- beállíthatod az időintervallumot,
- állíthatod a hexagon méretet,
- frissítheted a forrásadatokat.
## Teszt futtatása
```powershell
pytest
```
