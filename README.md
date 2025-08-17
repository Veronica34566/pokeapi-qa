# PokeAPI Q&A — Python + requests

Script en Python que consulta **PokeAPI** para responder preguntas sobre **tipos**, **evoluciones**, **estadísticas** y **hábitats**.

## Requisitos
- Python 3.10+
- Internet
- `pip install -r requirements.txt`

## Configuración opcional
Crea un archivo `.env` (o usa variables de entorno) para ajustar el comportamiento:

```env
POKEAPI_BASE=https://pokeapi.co/api/v2
# Si vas a usar KeyDB/Redis para caching HTTP, este ejemplo no lo incluye.
# Control de rendimiento
SLEEP_BETWEEN_CALLS=0.0   # segundos opcionales entre requests
MAX_WORKERS=1             # este script usa peticiones secuenciales por simplicidad
```

## Ejecutar
```bash
python main.py
```

### Flags útiles
- `--fast` : usa un camino más rápido para tareas pesadas (sigue siendo correcto, pero hace menos llamadas cuando es posible).
- `--limit N` : límite máximo de especies a recorrer en operaciones globales (debug).
- `--sleep 0.05` : pausa (seg) entre requests para ser amable con la API.

## Qué responde
1. **Tipos**
   - (a) ¿Cuántos Pokémon de tipo fuego existen en Kanto?
   - (b) ¿Nombres de Pokémon tipo agua con altura > 10 (decímetros)?
2. **Evoluciones**
   - (a) Cadena evolutiva completa de un inicial (Charmander por defecto).
   - (b) Pokémon eléctricos que **no** tienen evoluciones.
3. **Batalla**
   - (a) Pokémon con mayor **ataque** base en **Johto** (Generación II).
   - (b) Pokémon con mayor **velocidad** que **no sea legendario**.
4. **Extras**
   - (a) Hábitat más común entre los Pokémon de tipo planta.
   - (b) Pokémon con **menor peso** registrado en toda la API.

## Notas técnicas
- Manejo de errores con reintentos y backoff exponencial.
- Soporta paginación de PokeAPI (propiedad `next`).
- Filtrado por especie para evitar duplicados por *forms*.
- Conversión de unidades:
  - `height` en decímetros (dm).
  - `weight` en hectogramos (hg) → kg = hg / 10.

> La primera ejecución puede tardar varios minutos por el volumen de consultas (sobre todo 3b y 4b). Usa `--fast` si necesitas resultados más rápidos.
