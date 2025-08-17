from typing import List, Dict, Any, Tuple, Optional
from collections import Counter
import argparse
import math

from pokeapi import (
    api,
    get_json,
    fetch_all,
    pokemon_detail,
    species_detail,
    type_detail,
    default_pokemon_from_species,
    list_species_from_pokedex,
    list_species_from_generation,
    evolution_chain_by_species,
    chain_to_paths,
    find_node_for_species,
    stat_from_pokemon,
)

# ---------- Helpers de presentación ----------

def dm_to_m(dm: int) -> float:
    return round(dm / 10.0, 2)

def hg_to_kg(hg: int) -> float:
    return round(hg / 10.0, 2)

def pretty_evolution_detail(d: Dict[str, Any]) -> str:
    if not d:
        return "(inicio)"
    parts = [d.get("trigger", {}).get("name", "level-up")]
    if d.get("min_level") is not None:
        parts.append(f"lvl {d['min_level']}")
    if d.get("item"):
        parts.append(f"item: {d['item']['name']}")
    if d.get("held_item"):
        parts.append(f"held: {d['held_item']['name']}")
    if d.get("known_move"):
        parts.append(f"move: {d['known_move']['name']}")
    if d.get("known_move_type"):
        parts.append(f"type: {d['known_move_type']['name']}")
    if d.get("min_happiness"):
        parts.append(f"happiness≥{d['min_happiness']}")
    if d.get("min_beauty"):
        parts.append(f"beauty≥{d['min_beauty']}")
    if d.get("location"):
        parts.append(f"loc: {d['location']['name']}")
    if d.get("time_of_day"):
        parts.append(f"time: {d['time_of_day']}")
    if d.get("trade_species"):
        parts.append(f"trade:{d['trade_species']['name']}")
    return ", ".join(parts)

# ---------- Preguntas ----------

def q_tipos_fuego_kanto() -> int:
    """¿Cuántos Pokémon de tipo fuego existen en Kanto? (según Pokédex Kanto)"""
    kanto_species = set(list_species_from_pokedex("kanto"))  # especies Kanto
    fire = type_detail("fire")
    count = 0
    # La lista del tipo incluye 'pokemon' (formas). Convertimos a especie real.
    for x in fire.get("pokemon", []):
        p = pokemon_detail(x["pokemon"]["url"])
        sp_name = p.get("species", {}).get("name")
        if sp_name in kanto_species:
            count += 1
    return count

def q_agua_altura_mayor_10() -> List[str]:
    """Nombres de Pokémon agua con altura > 10 dm"""
    water = type_detail("water")
    names: List[str] = []
    seen_species = set()
    for x in water.get("pokemon", []):
        p = pokemon_detail(x["pokemon"]["url"])
        # evitar duplicados por forms usando species
        sp_name = p.get("species", {}).get("name")
        if sp_name in seen_species:
            continue
        seen_species.add(sp_name)
        if p.get("height", 0) > 10:
            names.append(p["name"])
    names.sort()
    return names

def q_cadena_evolutiva_inicial(inicial: str = "charmander") -> List[str]:
    """Cadena evolutiva completa (texto) del inicial dado."""
    chain = evolution_chain_by_species(inicial)
    paths = chain_to_paths(chain)
    # Tomamos el camino que contiene a la especie inicial
    picked = None
    for path in paths:
        species_names = [n for n, d in path]
        if inicial in species_names:
            picked = path
            break
    if not picked and paths:
        picked = paths[0]
    lines = []
    for name, det in picked:
        lines.append(f"- {name} — {pretty_evolution_detail(det)}")
    return lines

def q_electricos_sin_evoluciones() -> List[str]:
    """Pokémon de tipo eléctrico que no tienen evoluciones (como especie)."""
    electric = type_detail("electric")
    result = []
    seen_species = set()
    for x in electric.get("pokemon", []):
        p = pokemon_detail(x["pokemon"]["url"])
        sp_name = p.get("species", {}).get("name")
        if sp_name in seen_species:
            continue
        seen_species.add(sp_name)
        chain = evolution_chain_by_species(sp_name)
        node = find_node_for_species(chain, sp_name)
        if node and not node.get("evolves_to"):
            result.append(sp_name)
    result.sort()
    return result

def q_johto_mayor_ataque() -> Tuple[str, int]:
    """Pokémon con mayor ataque base en Johto (Gen II)."""
    species = list_species_from_generation(2)
    best_name, best_attack = None, -1
    for sp in species:
        p = default_pokemon_from_species(sp)
        atk = stat_from_pokemon(p, "attack") or 0
        if atk > best_attack:
            best_attack = atk
            best_name = p["name"]
    return best_name, best_attack

def q_velocidad_max_no_legendario(limit: Optional[int] = None) -> Tuple[str, int, bool]:
    """Pokémon con velocidad más alta que NO sea legendario (también excluye míticos).
       Recorre todas las especies (puede tardar)."""
    data = fetch_all(api("pokemon-species?limit=2000"))
    best = ("", -1, False)
    count = 0
    for row in data:
        sp = species_detail(row["url"])
        if sp.get("is_legendary") or sp.get("is_mythical"):
            continue
        p = default_pokemon_from_species(sp["name"])
        spd = stat_from_pokemon(p, "speed") or 0
        if spd > best[1]:
            best = (p["name"], spd, False)
        count += 1
        if limit and count >= limit:
            break
    return best

def q_habitat_mas_comun_planta() -> Tuple[str, int]:
    """Hábitat más común entre Pokémon tipo planta (por especie)."""
    grass = type_detail("grass")
    counter = Counter()
    seen_species = set()
    for x in grass.get("pokemon", []):
        p = pokemon_detail(x["pokemon"]["url"])
        sp = species_detail(p["species"]["url"])
        sp_name = sp["name"]
        if sp_name in seen_species:
            continue
        seen_species.add(sp_name)
        habitat = sp.get("habitat", {}).get("name", None)
        if habitat:
            counter[habitat] += 1
    if not counter:
        return ("desconocido", 0)
    habitat, qty = counter.most_common(1)[0]
    return habitat, qty

def q_menor_peso_global(limit: Optional[int] = None) -> Tuple[str, float]:
    """Pokémon con menor peso (usando especie → variedad por defecto)."""
    data = fetch_all(api("pokemon-species?limit=2000"))
    best = ("", math.inf)
    count = 0
    for row in data:
        sp = species_detail(row["url"])
        p = default_pokemon_from_species(sp["name"])
        w = p.get("weight", 10**9)  # hg
        if w < best[1]:
            best = (p["name"], w)
        count += 1
        if limit and count >= limit:
            break
    # convertir a kg
    return best[0], round(best[1] / 10.0, 2)

def main():
    ap = argparse.ArgumentParser(description="Responde preguntas con PokeAPI")
    ap.add_argument("--fast", action="store_true", help="Usa límites prudentes en queries globales")
    ap.add_argument("--limit", type=int, default=None, help="Límite de especies para pruebas")
    ap.add_argument("--sleep", type=float, default=None, help="Pausa entre requests (seg).")
    args = ap.parse_args()

    if args.sleep is not None:
        import os
        os.environ["SLEEP_BETWEEN_CALLS"] = str(args.sleep)

    print("\n== Tipos ==")
    print(f"(a) Fuego en Kanto: {q_tipos_fuego_kanto()} pokémon")
    agua_altos = q_agua_altura_mayor_10()
    print(f"(b) Agua con altura > 10 dm: {len(agua_altos)} encontrados")
    print(", ".join(agua_altos))

    print("\n== Evoluciones ==")
    chain_lines = q_cadena_evolutiva_inicial("charmander")
    print("(a) Cadena Charmander:")
    print("\n".join(chain_lines))
    electrics = q_electricos_sin_evoluciones()
    print(f"(b) Eléctricos sin evoluciones: {len(electrics)}")
    print(", ".join(electrics))

    print("\n== Batalla ==")
    name, atk = q_johto_mayor_ataque()
    print(f"(a) Mayor ataque en Johto: {name} ({atk})")
    lim = 200 if args.fast and not args.limit else args.limit
    spd_name, spd, _ = q_velocidad_max_no_legendario(limit=lim)
    print(f"(b) Velocidad más alta no legendario: {spd_name} ({spd}) {'[FAST MODE]' if lim else ''}")

    print("\n== Extras ==")
    habitat, qty = q_habitat_mas_comun_planta()
    print(f"(a) Hábitat más común (planta): {habitat} (n={qty})")
    lightest_name, lightest_kg = q_menor_peso_global(limit=lim)
    print(f"(b) Menor peso global: {lightest_name} ({lightest_kg} kg){' [FAST MODE]' if lim else ''}")

if __name__ == "__main__":
    main()
