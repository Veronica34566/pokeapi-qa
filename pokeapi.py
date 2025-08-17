import os
import time
import json
import hashlib
from typing import Any, Dict, Iterable, List, Optional, Tuple
import requests
from requests.exceptions import RequestException
from dotenv import load_dotenv

load_dotenv()

BASE = os.getenv("POKEAPI_BASE", "https://pokeapi.co/api/v2")
SLEEP = float(os.getenv("SLEEP_BETWEEN_CALLS", "0.0"))

CACHE_DIR = os.path.join(os.getcwd(), ".cache")
os.makedirs(CACHE_DIR, exist_ok=True)

def _cache_path(url: str) -> str:
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()
    return os.path.join(CACHE_DIR, f"{h}.json")

def get_json(url: str, retries: int = 4, backoff: float = 0.8) -> Dict[str, Any]:
    """GET con reintentos, backoff y cache en disco (simple)."""
    # cache
    cp = _cache_path(url)
    if os.path.exists(cp):
        try:
            with open(cp, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass  # si el cache está corrupto, se ignora

    attempt = 0
    last_err: Optional[Exception] = None
    while attempt <= retries:
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                # guardar cache
                try:
                    with open(cp, "w", encoding="utf-8") as f:
                        json.dump(data, f)
                except Exception:
                    pass
                if SLEEP:
                    time.sleep(SLEEP)
                return data
            elif resp.status_code in (429, 500, 502, 503, 504):
                # backoff y reintento
                time.sleep((backoff ** attempt) + 0.2)
            else:
                resp.raise_for_status()
        except RequestException as e:
            last_err = e
            time.sleep((backoff ** attempt) + 0.2)
        attempt += 1
    raise RuntimeError(f"Fallo al obtener {url}: {last_err}")

def api(*parts: str) -> str:
    return "/".join([BASE.strip("/")] + [p.strip("/") for p in parts])

def fetch_all(url: str) -> List[Dict[str, Any]]:
    """Sigue paginación (propiedad next) y concatena resultados (key 'results')."""
    results: List[Dict[str, Any]] = []
    while url:
        data = get_json(url)
        chunk = data.get("results", [])
        if chunk:
            results.extend(chunk)
        url = data.get("next")
    return results

def pokemon_detail(name_or_url: str) -> Dict[str, Any]:
    if name_or_url.startswith("http"):
        return get_json(name_or_url)
    return get_json(api("pokemon", name_or_url))

def species_detail(name_or_url: str) -> Dict[str, Any]:
    if name_or_url.startswith("http"):
        return get_json(name_or_url)
    return get_json(api("pokemon-species", name_or_url))

def type_detail(type_name: str) -> Dict[str, Any]:
    return get_json(api("type", type_name))

def pokedex(detail: str) -> Dict[str, Any]:
    return get_json(api("pokedex", detail))

def generation(idx: int) -> Dict[str, Any]:
    return get_json(api("generation", str(idx)))

def evolution_chain_by_species(species_name: str) -> Dict[str, Any]:
    sp = species_detail(species_name)
    evo_url = sp.get("evolution_chain", {}).get("url")
    if not evo_url:
        raise RuntimeError(f"Species {species_name} sin evolution_chain")
    return get_json(evo_url)

def default_pokemon_from_species(species_name: str) -> Dict[str, Any]:
    sp = species_detail(species_name)
    for v in sp.get("varieties", []):
        if v.get("is_default"):
            return pokemon_detail(v["pokemon"]["url"])
    # fallback: usar el nombre de la especie
    return pokemon_detail(species_name)

def stat_from_pokemon(p: Dict[str, Any], stat_name: str) -> Optional[int]:
    for s in p.get("stats", []):
        if s.get("stat", {}).get("name") == stat_name:
            return int(s.get("base_stat", 0))
    return None

def list_species_from_pokedex(pokedex_name: str) -> List[str]:
    px = pokedex(pokedex_name)
    species = [e["pokemon_species"]["name"] for e in px.get("pokemon_entries", []) if e.get("pokemon_species")]
    return species

def list_species_from_generation(gen_idx: int) -> List[str]:
    g = generation(gen_idx)
    species = [s["name"] for s in g.get("pokemon_species", [])]
    return species

def chain_to_paths(chain: Dict[str, Any]) -> List[List[Tuple[str, Dict[str, Any]]]]:
    """Convierte un evolution_chain en caminos desde la raíz a hojas.
    Devuelve lista de caminos; cada paso es (species_name, evolution_details_dict)."""
    paths: List[List[Tuple[str, Dict[str, Any]]]] = []

    def dfs(node, path):
        species_name = node["species"]["name"]
        if not node.get("evolves_to"):
            paths.append(path + [(species_name, {})])
            return
        if not path:
            # raíz no tiene details
            path = [(species_name, {})]
        for edge in node["evolves_to"]:
            details_list = edge.get("evolution_details", []) or [{}]
            for det in details_list:
                dfs(edge, path + [(edge["species"]["name"], det)])

    dfs(chain["chain"], [])
    return paths

def find_node_for_species(chain: Dict[str, Any], target: str) -> Optional[Dict[str, Any]]:
    """Busca el nodo en el árbol de evoluciones por species.name"""
    stack = [chain.get("chain")]
    while stack:
        n = stack.pop()
        if not n:
            continue
        if n.get("species", {}).get("name") == target:
            return n
        stack.extend(n.get("evolves_to", []))
    return None
