import pygame
import time
import random
import sys
import json
import os

# ------------------------------
# CONFIGURACIÓN INICIAL
# ------------------------------
pygame.init()
WIDTH, HEIGHT = 1000, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("ReactionTimeLab")

# Cargar fuente externa con fallback
FONT_PATH = "./S10/ProFontIIxNerdFont-Regular.ttf"
try:
    font = pygame.font.Font(FONT_PATH, 32)
except Exception:
    font = pygame.font.SysFont("Arial", 32)
    print("⚠ No se encontró la fuente, usando Arial por defecto")

clock = pygame.time.Clock()

# ------------------------------
# Rutas y nombre de usuario
# ------------------------------
DB_PATH = "./S10/scores.json"

def ask_username_console():
    """Pide el nombre de usuario por la consola antes de iniciar el bucle."""
    try:
        username = input("Introduce tu nombre de usuario: ").strip()
    except Exception:
        username = ""
    if not username:
        username = "guest"
    return username.lower()

username = ask_username_console()

# ------------------------------
# FUNCIONES: JSON SCOREBOARD
# ------------------------------

def load_scores():
    """Carga o crea el archivo JSON de puntuaciones."""
    if not os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, "w") as f:
                json.dump({"players": {}}, f, indent=4)
        except Exception as e:
            print(f"Error creando {DB_PATH}: {e}")
            return {"players": {}}
    try:
        with open(DB_PATH, "r") as f:
            data = json.load(f)
            if "players" not in data or not isinstance(data["players"], dict):
                return {"players": {}}
            return data
    except (json.JSONDecodeError, IOError):
        # Si hay algún problema, re-inicializamos el archivo
        try:
            with open(DB_PATH, "w") as f:
                json.dump({"players": {}}, f, indent=4)
        except Exception as e:
            print(f"Error reseteando {DB_PATH}: {e}")
        return {"players": {}}

def save_scores(data):
    """Guarda el diccionario de puntuaciones en JSON."""
    try:
        with open(DB_PATH, "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error guardando puntuaciones: {e}")

def register_or_get_user(name):
    """Si el usuario no existe lo crea con puntuación alta (para poder mejorar)."""
    db = load_scores()
    if name not in db["players"]:
        db["players"][name] = float("inf")  # puntuación grande (peor)
        save_scores(db)
    return db["players"][name]

def update_score(name, new_score):
    """
    Actualiza la puntuación si la nueva es mejor (menor tiempo).
    Devuelve True si se actualizó, False si no.
    """
    db = load_scores()
    old = db["players"].get(name, float("inf"))
    try:
        # Si new_score es menor (mejor), actualizamos
        if new_score < old:
            db["players"][name] = new_score
            save_scores(db)
            return True
    except Exception as e:
        print(f"Error al actualizar score: {e}")
    return False

def get_top5():
    """
    Devuelve lista de 5 tuplas (usuario, score) ordenadas por mejor (menor tiempo).
    Rellena con placeholders si hay menos de 5 jugadores.
    """
    db = load_scores()
    players = db.get("players", {})
    # Convertimos inf a un valor alto para ordenar si hay usuarios sin score definido
    normalized = [(u, players[u] if players[u] != float("inf") else 9999.0) for u in players]
    sorted_players = sorted(normalized, key=lambda x: x[1])
    # Rellenar placeholders si hacen falta
    while len(sorted_players) < 5:
        sorted_players.append((f"user{len(sorted_players)+1}", 0.0))
    return sorted_players[:5]

# Registrar (o crear) el usuario al inicio
register_or_get_user(username)

# ------------------------------
# UTILIDADES GRAFICAS
# ------------------------------

def dibujar_gradiente(surface, color_top, color_bottom):
    """Dibuja un gradiente vertical suave en la superficie."""
    h = surface.get_height()
    for y in range(h):
        ratio = y / max(1, h - 1)
        r = color_top[0] * (1 - ratio) + color_bottom[0] * ratio
        g = color_top[1] * (1 - ratio) + color_bottom[1] * ratio
        b = color_top[2] * (1 - ratio) + color_bottom[2] * ratio
        pygame.draw.line(surface, (int(r), int(g), int(b)), (0, y), (surface.get_width(), y))

def renderizar_texto_centrado(text, y, color=(255,255,255), size=32):
    """Renderiza texto centrado en X en la posición Y dada."""
    try:
        f = pygame.font.Font(FONT_PATH, size) if size != 32 else font
    except Exception:
        f = pygame.font.SysFont("Arial", size)
    t = f.render(text, True, color)
    rect = t.get_rect(center=(WIDTH // 2, y))
    screen.blit(t, rect)

def dibujar_boton(rect, texto, hover=False):
    """Dibuja un botón rectangular con texto, resaltado si hover=True."""
    color_bg = (255, 255, 255) if hover else (200, 200, 200)
    color_text = (20, 20, 20) if hover else (10, 10, 10)
    # fondo redondeado (simulación)
    pygame.draw.rect(screen, color_bg, rect, border_radius=10)
    # borde
    pygame.draw.rect(screen, (0,0,0), rect, width=2, border_radius=10)
    # texto centrado
    try:
        f = pygame.font.Font(FONT_PATH, 22)
    except Exception:
        f = pygame.font.SysFont("Arial", 22)
    t = f.render(texto, True, color_text)
    tr = t.get_rect(center=rect.center)
    screen.blit(t, tr)

# Coordenadas del botón Puntuaciones
scores_button_rect = pygame.Rect(WIDTH - 220, 20, 200, 50)

# ------------------------------
# VARIABLES DEL JUEGO
# ------------------------------
game_state = "start"   # start, waiting, click, result, scores
start_time = None
end_time = None
waiting_delay = None
delay_start = None
last_update_message = ""  # mensaje breve tras actualizar score

# ------------------------------
# BUCLE PRINCIPAL
# ------------------------------
running = True
while running:
    mouse_pos = pygame.mouse.get_pos()
    mouse_pressed = pygame.mouse.get_pressed()[0]

    # ------------------------
    # GESTIONAR EVENTOS
    # ------------------------
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            # Salvar y salir
            pygame.quit()
            sys.exit()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Clic según estado
            if game_state == "start":
                # Si el usuario clic en el botón puntuaciones -> ir a pantalla scores
                if scores_button_rect.collidepoint(mouse_pos):
                    game_state = "scores"
                else:
                    # Comenzamos la secuencia normal
                    waiting_delay = random.uniform(3, 7)
                    delay_start = time.time()
                    game_state = "waiting"

            elif game_state == "click":
                # Usuario respondió, registramos tiempo y mostramos resultado
                end_time = time.time()
                reaction = round(end_time - start_time, 3)
                # Actualizamos scoreboard (si mejora)
                try:
                    mejoro = update_score(username, reaction)
                    if mejoro:
                        last_update_message = f"🎉 Nueva mejor puntuación: {reaction} s"
                    else:
                        last_update_message = f"Tu tiempo: {reaction} s (no superaste tu mejor marca)"
                except Exception as e:
                    last_update_message = f"Error al actualizar scoreboard: {e}"
                game_state = "result"

            elif game_state == "result":
                # Volver al inicio
                game_state = "start"

            elif game_state == "scores":
                # En scores, clic vuelve al inicio
                game_state = "start"

    # ------------------------
    # LÓGICA DE ESTADOS
    # ------------------------
    if game_state == "waiting":
        # Si ha pasado el delay, cambiamos a click y guardamos start_time
        if delay_start is None:
            delay_start = time.time()
        if time.time() - delay_start >= waiting_delay:
            game_state = "click"
            start_time = time.time()

    # ------------------------
    # DIBUJAR SEGÚN ESTADO
    # ------------------------
    # Estado: start
    if game_state == "start":
        dibujar_gradiente(screen, (0, 80, 200), (0, 0, 50))
        renderizar_texto_centrado("Demuestra tus reflejos", 120)
        renderizar_texto_centrado("Haz click (fuera del botón) para comenzar", 300, size=24)
        # Dibujamos círculo decorativo
        pygame.draw.circle(screen, (255, 255, 255), (500, 420), 70, 6)

        # Dibujamos botón Puntuaciones (hover si el ratón está encima)
        hover = scores_button_rect.collidepoint(mouse_pos)
        dibujar_boton(scores_button_rect, "Puntuaciones", hover=hover)

        # Mostramos último mensaje de actualización
        if last_update_message:
            renderizar_texto_centrado(last_update_message, 540, size=22)

        # Mostramos nombre de usuario actual arriba a la izquierda
        try:
            fsmall = pygame.font.Font(FONT_PATH, 18)
        except:
            fsmall = pygame.font.SysFont("Arial", 18)
        user_text = f"User: {username}"
        tuser = fsmall.render(user_text, True, (255,255,255))
        screen.blit(tuser, (20, 25))

    # Estado: waiting
    elif game_state == "waiting":
        dibujar_gradiente(screen, (20, 20, 20), (60, 60, 60))
        renderizar_texto_centrado("¿PREPARADO?", 300)
        # Indicador de espera (texto dinámico)


    # Estado: click
    elif game_state == "click":
        dibujar_gradiente(screen, (150, 0, 0), (80, 0, 0))
        renderizar_texto_centrado("¡YA!", 300, size=64)
        renderizar_texto_centrado("Pulsa rápido", 380, size=22)

    # Estado: result
    elif game_state == "result":
        # reaction = round(end_time - start_time, 3)  <-- ya calculado antes
        try:
            reaction = round(end_time - start_time, 3)
        except Exception:
            reaction = 0.0
        dibujar_gradiente(screen, (0, 160, 100), (0, 60, 20))
        renderizar_texto_centrado("Tiempo de reacción:", 220)
        renderizar_texto_centrado(f"{reaction} segundos", 320, size=40)
        renderizar_texto_centrado("Clic para volver a empezar", 500, size=22)
        # Mostrar info de si mejoró o no
        renderizar_texto_centrado(last_update_message, 420, size=22)

    # Estado: scores (pantalla Top 5)
    elif game_state == "scores":
        dibujar_gradiente(screen, (10, 10, 40), (0, 0, 0))
        renderizar_texto_centrado("TOP 5 JUGADORES", 80, size=36)

        top = get_top5()
        y = 160
        try:
            # Mostrar cada entrada del top
            for user, score in top:
                # Si score == 0 (placeholder), mostramos "0 s" tal como pediste
                score_display = f"{round(score,3)} s" if score != 0.0 else "0 s"
                renderizar_texto_centrado(f"{user} - {score_display}", y, size=28)
                y += 60
        except Exception as e:
            renderizar_texto_centrado(f"Error mostrando top: {e}", 300)

        renderizar_texto_centrado("Clic para volver", 540, size=22)

    # Actualizar pantalla
    pygame.display.update()
    clock.tick(60)
