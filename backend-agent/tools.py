import requests
from langchain.tools import tool

OPENWEATHER_API_KEY = "ae684ea412c8d90693f38f1ba2d35c07"

@tool
def clima_destino(ciudad: str):
    """Busca información sobre el clima actual de una ciudad usando coordenadas geográficas."""

    try:
        if not ciudad or len(ciudad.strip()) < 2:
            return "❌ No se proporcionó una ciudad válida."

        ciudad = ciudad.strip()

        print(f"🌍 Buscando coordenadas para: {ciudad}")
        
        geo_url = "https://nominatim.openstreetmap.org/search"
        geo_params = {
            "q": ciudad,
            "format": "json",
            "addressdetails": 1,
            "limit": 1,
            "accept-language": "es"
        }

        geo_resp = requests.get(geo_url, params=geo_params, headers={"User-Agent": "TravelAssistant/1.0"}, timeout=10)

        if geo_resp.status_code != 200 or not geo_resp.json():
            return f"❌ No se pudo encontrar la ubicación de '{ciudad}'."

        geo_data = geo_resp.json()[0]
        lat, lon = geo_data["lat"], geo_data["lon"]
        nombre_ciudad = geo_data.get("display_name", ciudad).split(",")[0]

        print(f"✅ Coordenadas encontradas: {nombre_ciudad} → lat={lat}, lon={lon}")

        weather_url = "http://api.openweathermap.org/data/2.5/weather"
        weather_params = {
            "lat": lat,
            "lon": lon,
            "appid": OPENWEATHER_API_KEY,
            "units": "metric",
            "lang": "es"
        }

        clima_resp = requests.get(weather_url, params=weather_params, timeout=10)

        if clima_resp.status_code != 200:
            return f"❌ No se pudo obtener el clima de {nombre_ciudad}. Verifica el nombre."

        data = clima_resp.json()
        clima = data["weather"][0]["description"]
        temperatura = data["main"]["temp"]

        print(f"🌦️ Clima obtenido: {clima.capitalize()} ({temperatura}°C)")

        return f"Clima en {nombre_ciudad}: {clima.capitalize()}, {temperatura}°C."

    except Exception as e:
        print(f"❌ Error al obtener el clima: {e}")
        return f"❌ Ocurrió un error al obtener el clima de {ciudad}."


@tool
def recomendar_actividades(ciudad: str, interes: str) -> str:
    """
    Recomienda actividades usando OpenStreetMap/Nominatim según el interés.
    Intereses: 'cultura', 'aventura', 'gastronomia', 'historia', 'naturaleza'
    """
    print(f"🎯 Buscando actividades de {interes} en {ciudad}")

    categoria_map = {
        "cultura": [
            "tourism=museum", "tourism=gallery", "tourism=theatre", 
            "tourism=artwork", "tourism=library", "tourism=attraction"
        ],
        "aventura": [
            "leisure=park", "sport=climbing", "sport=hiking", "tourism=zoo",
            "leisure=sports_centre", "sport=swimming", "leisure=fitness_centre"
        ],
        "gastronomia": [
            "amenity=restaurant", "amenity=cafe", "amenity=bar", 
            "amenity=fast_food", "amenity=pub", "amenity=biergarten"
        ],
        "historia": [
            "historic=castle", "historic=monument", "historic=archaeological_site",
            "building=church", "historic=memorial", "historic=ruins"
        ],
        "naturaleza": [
            "tourism=viewpoint", "natural=peak", "natural=beach",
            "leisure=garden", "tourism=picnic_site", "landuse=forest"
        ]
    }
    
    categorias = categoria_map.get(interes.lower(), ["tourism=attraction"])
    lugares_encontrados = []

    try:
        geo_response = requests.get(
            f"https://nominatim.openstreetmap.org/search?q={ciudad}&format=json&limit=1",
            headers={"User-Agent": "TravelAssistant/1.0"},
            timeout=10
        )
        
        if geo_response.status_code == 200 and geo_response.json():
            geo_data = geo_response.json()[0]
            lat = geo_data['lat']
            lon = geo_data['lon']
            print(f"📍 Coordenadas obtenidas: {lat}, {lon}")

            for categoria in categorias[:3]: 
                print(f"🔍 Buscando: {categoria}")

                overpass_query = f"""
                [out:json][timeout:25];
                (
                  node[{categoria}](around:5000,{lat},{lon});
                  way[{categoria}](around:5000,{lat},{lon});
                  relation[{categoria}](around:5000,{lat},{lon});
                );
                out center 8;
                """
                
                overpass_response = requests.post(
                    "https://overpass-api.de/api/interpreter",
                    data=overpass_query,
                    timeout=30
                )
                
                if overpass_response.status_code == 200:
                    data = overpass_response.json()
                    elementos = data.get('elements', [])
                    
                    for elemento in elementos:
                        if 'tags' in elemento and 'name' in elemento['tags']:
                            nombre = elemento['tags']['name']
                            if (nombre not in lugares_encontrados and 
                                len(nombre) > 3 and 
                                nombre.lower() not in ['cafe', 'restaurant', 'bar', 'park']):
                                lugares_encontrados.append(nombre)

                                if len(lugares_encontrados) >= 12:
                                    break
                    
                else:
                    print(f"⚠️ Error Overpass para {categoria}: {overpass_response.status_code}")

        else:
            return f"No se pudo encontrar la ciudad '{ciudad}'"

    except Exception as e:
        print(f"❌ Error general: {e}")
        return f"Error al buscar actividades en {ciudad}: {e}"

    if lugares_encontrados:
        lugares_unicos = list(dict.fromkeys(lugares_encontrados)) 
        lugares_formateados = "\n".join([f"• {lugar}" for lugar in lugares_unicos[:10]]) 
        
        return f"""
Recomendaciones de {interes} en {ciudad}:

{lugares_formateados}

💡 Tip: Estos son lugares populares según OpenStreetMap. Verifica horarios y disponibilidad antes de visitar.
"""
    else:
        sugerencias_alternativas = {
            "cultura": "Mira si hay museos municipales, centros culturales o galerías de arte locales.",
            "aventura": "Busca parques naturales, rutas de senderismo o centros de deportes aventura.",
            "gastronomia": "Prueba restaurantes típicos de la zona o mercados locales de comida.",
            "historia": "Visita el casco histórico, iglesias antiguas o monumentos emblemáticos.",
            "naturaleza": "Explora parques urbanos, miradores o áreas naturales cercanas."
        }
        
        sugerencia = sugerencias_alternativas.get(interes.lower(), "Explora la ciudad y descubre lugares interesantes.")
        
        return f"""
No se encontraron lugares específicos de {interes} en {ciudad}

{sugerencia}

💡 Tip: Intenta con un interés diferente o explora la ciudad para descubrir lugares únicos.
"""

agente_tools = [clima_destino.func, recomendar_actividades.func]





