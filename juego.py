import random
import time
from functools import reduce
from typing import Dict, List, Iterator, Tuple
from colorama import init as colorama_init, Fore, Style

colorama_init(autoreset=True)


# Constantes
NUM_CASILLAS = 30
MONEDAS_INICIALES = 2


# Utilidades funcionales
def agregar_efecto(tablero: Dict[int, Dict[str, int]], pos: int, efecto: Dict[str, int]) -> Dict[int, Dict[str, int]]:
    """
    Combina efectos si coinciden en la misma casilla (sin mutar el original).
    - Si ya hay mov/mon, suma.
    """
    actual = tablero.get(pos, {})
    combinado = {**actual, **{k: actual.get(k, 0) + v for k, v in efecto.items()}}
    nuevo = {**tablero, pos: combinado}
    return nuevo

def generar_tablero() -> Dict[int, Dict[str, int]]:
    """
    Genera posiciones random de casillas especiales:
      mov: +1, +2, +3, -5, -999 (volver a inicio)
      mon: +2, +1, +1, -1, -1
    """
    tablero: Dict[int, Dict[str, int]] = {}
    r = lambda: random.randint(1, NUM_CASILLAS - 1)  # 30 es meta, no se usa

    for mov in (1, 2, 3):
        tablero = agregar_efecto(tablero, r(), {"mov": mov})

    tablero = agregar_efecto(tablero, r(), {"mov": -999})  # volver al inicio
    tablero = agregar_efecto(tablero, r(), {"mov": -5})

    for mon in (2, 1, 1):
        tablero = agregar_efecto(tablero, r(), {"mon": mon})

    tablero = agregar_efecto(tablero, r(), {"mon": -1})
    tablero = agregar_efecto(tablero, r(), {"mon": -1})

    return tablero


# Jugadores
def crear_jugador(nombre: str) -> Dict:
    # dict inmutable por copia cuando se actualiza
    return {"nombre": nombre, "pos": 0, "mon": MONEDAS_INICIALES}


# Decorador de logging

def log_turno(func):
    def wrapper(*args, **kwargs):
        antes = args[0]  # jugador original
        resultado = func(*args, **kwargs)
        print(f"[LOG] {antes['nombre']}: pos {antes['pos']}→{resultado['pos']} | mon {antes['mon']}→{resultado['mon']}")
        return resultado
    return wrapper


# Dado (generador y helper)
def tirar_dado() -> int:
    return random.randint(1, 6)

def generador_dados() -> Iterator[int]:
    """Generador infinito de tiradas de dado (cumple con 'yield')."""
    while True:
        yield tirar_dado()


# Lógica de movimiento
def mover(jugador: Dict, dado: int) -> Dict:
    nueva_pos = jugador["pos"] + dado
    if nueva_pos > NUM_CASILLAS:
        nueva_pos = NUM_CASILLAS
    return {**jugador, "pos": nueva_pos}

def aplicar_efectos(jugador: Dict, tablero: Dict) -> Dict:
    pos = jugador["pos"]
    if pos not in tablero:
        return jugador

    efectos = tablero[pos]
    # empezar por copia para inmutabilidad
    nuevo = {**jugador}

    # Movimiento extra
    if "mov" in efectos:
        mov = efectos["mov"]
        if mov == -999:
            nuevo["pos"] = 0
        else:
            nuevo["pos"] = max(0, min(NUM_CASILLAS, nuevo["pos"] + mov))

    # Monedas (no bajar de 0)
    if "mon" in efectos:
        nuevo["mon"] = max(0, nuevo["mon"] + efectos["mon"])

    return nuevo

@log_turno
def aplicar_movimiento(jugador: Dict, dado: int, tablero: Dict) -> Dict:
    """
    Función pura por composición: mover -> aplicar_efectos
    """
    return aplicar_efectos(mover(jugador, dado), tablero)


# Visualización del tablero
def color_de_casilla(tablero: Dict[int, Dict[str, int]], pos: int) -> str:
    """
    Prioridad de color: mov castigo (rojo) > mov premio (verde) > mon castigo (amarillo) > mon premio (cian)
    """
    efectos = tablero.get(pos, {})
    mov = efectos.get("mov", 0)
    mon = efectos.get("mon", 0)
    if mov < 0:
        return Fore.RED
    if mov > 0:
        return Fore.GREEN
    if mon < 0:
        return Fore.YELLOW
    if mon > 0:
        return Fore.CYAN
    return Style.RESET_ALL

def token_casilla(pos: int, jpos: Dict[str, int], color: str) -> str:
    j1 = "J1" if jpos["J1"] == pos else ""
    j2 = "J2" if jpos["J2"] == pos else ""
    contenido = (j1 + ("&" if j1 and j2 else "") + j2) if (j1 or j2) else str(pos)
    contenido = contenido.center(4)
    return f"{color}[{contenido}]{Style.RESET_ALL}"

def mostrar_tablero(jugadores: List[Dict], tablero: Dict[int, Dict[str, int]]) -> None:
    jpos = {"J1": jugadores[0]["pos"], "J2": jugadores[1]["pos"]}
    # comprensión de lista
    fila = [token_casilla(pos, jpos, color_de_casilla(tablero, pos)) for pos in range(1, NUM_CASILLAS + 1)]
    print(" ".join(fila))
    print()
    print(f"{Fore.RED}Rojo{Style.RESET_ALL}=Castigo mov   "
          f"{Fore.GREEN}Verde{Style.RESET_ALL}=Premio mov   "
          f"{Fore.YELLOW}Amarillo{Style.RESET_ALL}=Castigo mon   "
          f"{Fore.CYAN}Cian{Style.RESET_ALL}=Premio mon")
    # reduce para total de monedas (demostrativo de uso funcional)
    total_mon = reduce(lambda acc, j: acc + j["mon"], jugadores, 0)
    print(f"J1={jugadores[0]['nombre']} pos={jugadores[0]['pos']} mon={jugadores[0]['mon']} | "
          f"J2={jugadores[1]['nombre']} pos={jugadores[1]['pos']} mon={jugadores[1]['mon']} | "
          f"Total monedas={total_mon}")
    print("-" * 100)


# Reglas de fin
def hay_ganador(j: Dict) -> bool:
    return j["pos"] >= NUM_CASILLAS and j["mon"] > 0

def perdio_por_monedas(j: Dict) -> bool:
    return j["mon"] <= 0

# Bucle recursivo del juego
def jugar_rec(jugadores: List[Dict], turno: int, tablero: Dict[int, Dict[str, int]],
              modo: str, dados: Iterator[int]) -> None:
    idx = turno % 2
    jugador = jugadores[idx]

    # Interacción según modo
    if modo == "interactivo":
        input(f"{jugador['nombre']}, presiona Enter para tirar el dado...")

    dado = next(dados)
    print(f"{jugador['nombre']} tiró un {dado}")

    nuevo = aplicar_movimiento(jugador, dado, tablero)
    # inmutabilidad: lista nueva con un solo elemento reemplazado
    jugadores_nuevos = [nuevo if i == idx else jugadores[i] for i in range(2)]

    mostrar_tablero(jugadores_nuevos, tablero)

    # condiciones de fin
    if hay_ganador(nuevo):
        print(f"🏆 {nuevo['nombre']} ganó el juego!")
        return
    if perdio_por_monedas(nuevo):
        print(f"💀 {nuevo['nombre']} perdió por quedarse sin monedas.")
        return

    if modo == "simulacion":
        time.sleep(1)

    # Recursión al siguiente turno
    return jugar_rec(jugadores_nuevos, turno + 1, tablero, modo, dados)


# Setup y entrada
def jugar(modo: str):
    # nombres en interactivo
    if modo == "interactivo":
        n1 = input("Nombre del Jugador 1: ").strip() or "Jugador 1"
        n2 = input("Nombre del Jugador 2: ").strip() or "Jugador 2"
    else:
        n1, n2 = "Jugador 1", "Jugador 2"

    tablero = generar_tablero()
    jugadores = [crear_jugador(n1), crear_jugador(n2)]
    print("🎲 ¡Comienza el juego!")
    mostrar_tablero(jugadores, tablero)

    # generador de dados
    dados = generador_dados()

    # arranca turno 0 (J1)
    jugar_rec(jugadores, 0, tablero, modo, dados)

if __name__ == "__main__":
    modo = input("Seleccione modo (simulacion/interactivo): ").strip().lower()
    if modo not in {"simulacion", "interactivo"}:
        print("Modo inválido. Usando 'simulacion' por defecto.")
        modo = "simulacion"
    jugar(modo)
