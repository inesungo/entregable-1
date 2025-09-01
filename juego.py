import random
import time
from rich.panel import Panel
from rich.columns import Columns
from rich.table import Table
from rich.console import Console
from rich.text import Text
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
    
    Usa comprensión de diccionario para generar los efectos iniciales.
    """
    posiciones_usadas = set()
    def r_unico():
        while True:
            pos = random.randint(1, NUM_CASILLAS - 1)
            if pos not in posiciones_usadas:
                posiciones_usadas.add(pos)
                return pos
    
    # Definir todos los efectos usando comprensión de diccionario
    efectos = [
        {"mov": mov} for mov in (1, 2, 3)  # Verde: premios de movimiento
    ] + [
        {"mov": -999}, {"mov": -5}  # Rojo: castigos de movimiento
    ] + [
        {"mon": mon} for mon in (2, 1, 1)  # Cian: premios de monedas
    ] + [
        {"mon": -1} for _ in range(2)  # Amarillo: castigos de monedas
    ]
    
    # Generar el tablero usando reduce para combinar todos los efectos
    return reduce(lambda tab, ef: agregar_efecto(tab, r_unico(), ef), efectos, {})

    return tablero


# Jugadores
def crear_jugador(nombre: str) -> Dict:
    # dict inmutable por copia cuando se actualiza
    return {"nombre": nombre, "pos": 0, "mon": MONEDAS_INICIALES}


# Decorador de logging

def log_turno(func):
    def wrapper(*args, **kwargs):
        antes = args[0]  # jugador original
        dado = args[1]
        tablero = kwargs.get('tablero', None) or args[2]  # tablero es el tercer argumento
        # Paso 1: movimiento inicial
        pos_inicial = antes["pos"] + dado
        if pos_inicial > NUM_CASILLAS:
            pos_inicial = NUM_CASILLAS
        efectos_inicial = tablero.get(pos_inicial, {}) if tablero else {}
        mensajes_inicial = []
        if not efectos_inicial:
            print(f"La casilla {pos_inicial} no tiene efectos especiales.")
        else:
            if "mov" in efectos_inicial:
                mov = efectos_inicial["mov"]
                if mov == -999:
                    mensajes_inicial.append("Vuelve al inicio")
                elif mov < 0:
                    mensajes_inicial.append(f"Retrocede {abs(mov)} casillas")
                else:
                    mensajes_inicial.append(f"Avanza {mov} casillas")
            if "mon" in efectos_inicial:
                mon = efectos_inicial["mon"]
                if mon < 0:
                    mensajes_inicial.append(f"Pierde {abs(mon)} moneda(s)")
                else:
                    mensajes_inicial.append(f"Gana {mon} moneda(s)")
            print(f"La casilla {pos_inicial} tiene efectos: {', '.join(mensajes_inicial)}")

        resultado = func(*args, **kwargs)
        # Paso 2: movimiento extra (si lo hubo)
        pos_final = resultado["pos"]
        if pos_final != pos_inicial:
            print(f"Por efecto de la casilla, ahora está en la casilla {pos_final}.")
            efectos_final = tablero.get(pos_final, {}) if tablero else {}
            mensajes_final = []
            if efectos_final and pos_final != pos_inicial:
                if "mov" in efectos_final:
                    mov = efectos_final["mov"]
                    if mov == -999:
                        mensajes_final.append("Vuelve al inicio")
                    elif mov < 0:
                        mensajes_final.append(f"Retrocede {abs(mov)} casillas")
                    else:
                        mensajes_final.append(f"Avanza {mov} casillas")
                if "mon" in efectos_final:
                    mon = efectos_final["mon"]
                    if mon < 0:
                        mensajes_final.append(f"Pierde {abs(mon)} moneda(s)")
                    else:
                        mensajes_final.append(f"Gana {mon} moneda(s)")
                print(f"La casilla {pos_final} tiene efectos: {', '.join(mensajes_final)}")
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
            nueva_pos = nuevo["pos"] + mov
            if mov < 0:
                nuevo["pos"] = max(0, nueva_pos)
            else:
                nuevo["pos"] = min(NUM_CASILLAS, nueva_pos)

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
    # Colores distintos para cada jugador
    j1 = Fore.MAGENTA + "J1" + Style.RESET_ALL if jpos["J1"] == pos else ""
    j2 = Fore.BLUE + "J2" + Style.RESET_ALL if jpos["J2"] == pos else ""
    contenido = (j1 + ("&" if j1 and j2 else "") + j2) if (j1 or j2) else str(pos)
    contenido = contenido.center(4)
    return f"{color}[{contenido}]{Style.RESET_ALL}"

def mostrar_tablero(jugadores: List[Dict], tablero: Dict[int, Dict[str, int]]) -> None:
    jpos = {"J1": jugadores[0]["pos"], "J2": jugadores[1]["pos"]}
    console = Console()
    casillas = []
    for pos in range(0, NUM_CASILLAS + 1):
        efectos = tablero.get(pos, {})
        mov = efectos.get("mov", 0)
        mon = efectos.get("mon", 0)
        # Jugadores
        if jpos["J1"] == pos and jpos["J2"] == pos:
            contenido = f"J1&J2"
            color = "magenta"
        elif jpos["J1"] == pos:
            contenido = "J1"
            color = "magenta"
        elif jpos["J2"] == pos:
            contenido = "J2"
            color = "blue"
        else:
            contenido = "Inicio" if pos == 0 else str(pos)
            color = "white"
        # Efectos
        border = "white"
        if mov == -999 or mov < 0:
            border = "red"
        elif mov > 0:
            border = "green"
        elif mon < 0:
            border = "yellow"
        elif mon > 0:
            border = "cyan"
        panel = Panel(contenido, border_style=border, style=color, width=7)
        casillas.append(panel)
    console.print(Columns(casillas))
    # Leyenda
    legend = (
        f"[red]Rojo[/][white]=Castigo mov   "
        f"[green]Verde[/][white]=Premio mov   "
        f"[yellow]Amarillo[/][white]=Castigo mon   "
        f"[cyan]Cian[/][white]=Premio mon"
    )
    console.print(legend)
    # Estado jugadores
    console.print(f"[magenta]J1={jugadores[0]['nombre']}[/] - Posición: {jugadores[0]['pos']} - Monedas: {jugadores[0]['mon']}")
    console.print(f"[blue]J2={jugadores[1]['nombre']}[/] - Posición: {jugadores[1]['pos']} - Monedas: {jugadores[1]['mon']}")
    console.print("=" * 100)


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
    mostrar_efecto_casilla(nuevo, tablero)

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
# Reglas de fin
def mostrar_efecto_casilla(jugador: Dict, tablero: Dict[int, Dict[str, int]]) -> None:
    pos = jugador["pos"]
    efectos = tablero.get(pos, {})
    if not efectos:
        print(f"La casilla {pos} no tiene efectos especiales.")
        return
    mensajes = []
    if "mov" in efectos:
        if efectos["mov"] == -999:
            mensajes.append(f"{Fore.RED}Vuelve al inicio{Style.RESET_ALL}")
        elif efectos["mov"] < 0:
            mensajes.append(f"{Fore.RED}Retrocede {abs(efectos['mov'])} casillas{Style.RESET_ALL}")
        else:
            mensajes.append(f"{Fore.GREEN}Avanza {efectos['mov']} casillas{Style.RESET_ALL}")
    if "mon" in efectos:
        if efectos["mon"] < 0:
            mensajes.append(f"{Fore.YELLOW}Pierde {abs(efectos['mon'])} moneda(s){Style.RESET_ALL}")
        else:
            mensajes.append(f"{Fore.CYAN}Gana {efectos['mon']} moneda(s){Style.RESET_ALL}")
    print(f"Efectos en la casilla {pos}: " + ", ".join(mensajes))

def mostrar_resumen_turno(jugadores: List[Dict]) -> None:
    print(f"{Fore.MAGENTA}J1: {jugadores[0]['nombre']} - Posición: {jugadores[0]['pos']} - Monedas: {jugadores[0]['mon']}{Style.RESET_ALL}")
    print(f"{Fore.BLUE}J2: {jugadores[1]['nombre']} - Posición: {jugadores[1]['pos']} - Monedas: {jugadores[1]['mon']}{Style.RESET_ALL}")
    print("-" * 50)


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
