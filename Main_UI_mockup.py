# Versió UI inspirada en el mockup aportat per l'usuari
# main.py
import requests
import random
import pygame
import os
import sys
import time
import threading

try:
    from invents import invents
except ImportError:
    print("Error: No es troba el fitxer invents.py")
    sys.exit(1)

# ─── CONSTANTS ────────────────────────────────────────────────────────────────
WIDTH, HEIGHT   = 1280, 720
FPS             = 60
IMG_DIR         = "Imatges"
PROGRESS_INTERVAL = 30  # segons

# ─── COLORS ───────────────────────────────────────────────────────────────────
WHITE        = (255, 255, 255)
CANVAS_MUTED = (249, 250, 251)
GRAY_900     = ( 17,  24,  39)
GRAY_700     = ( 55,  65,  81)
GRAY_500     = (107, 114, 128)
GRAY_400     = (156, 163, 175)
GRAY_200     = (229, 231, 235)
GRAY_100     = (243, 244, 246)
BLUE_600     = ( 37,  99, 235)
BLUE_50      = (239, 246, 255)
BLACK        = (  0,   0,   0)
RED_600      = (220,  38,  38)
GREEN_600    = ( 22, 163,  74)
OVERLAY      = (  0,   0,   0, 160)

# ─── SERVIDOR ─────────────────────────────────────────────────────────────────
BASE_URL = "http://fun.codelearn.cat/hackathon/game"

def inicialitzar():
    """Crida al servidor per iniciar partida. Retorna (game_id, seed)."""
    try:
        r = requests.get(f"{BASE_URL}/new", timeout=5)
        data = r.json()
        return data["game_id"], data["seed"]
    except Exception as e:
        print(f"[Servidor] Error inicialitzar: {e}")
        # Fallback local perquè el joc funcioni sense servidor
        return "local_game", random.randint(0, 999999)

def progres(game_id, invent_actual, score):
    """Envia progrés al servidor (crida cada PROGRESS_INTERVAL segons)."""
    try:
        send = {"game_id": game_id, "data": invent_actual, "score": score}
        requests.post(f"{BASE_URL}/store_progress", json=send, timeout=5)
    except Exception as e:
        print(f"[Servidor] Error progres: {e}")

def fijoc(game_id, score):
    """Envia puntuació final al servidor."""
    try:
        send = {"game_id": game_id, "data": "ha fallat", "score": score}
        requests.post(f"{BASE_URL}/finalize", json=send, timeout=5)
    except Exception as e:
        print(f"[Servidor] Error fijoc: {e}")

# ─── UTILITATS ────────────────────────────────────────────────────────────────
def format_any(any_num):
    """Converteix -300 → '300 aC', 1990 → '1990'."""
    if any_num < 0:
        return f"{abs(any_num)} aC"
    return str(any_num)

def load_image(nom_fitxer, mida=None):
    """Carrega una imatge. Retorna None si no existeix."""
    ruta = os.path.join(IMG_DIR, nom_fitxer)
    if not os.path.isfile(ruta):
        return None
    try:
        img = pygame.image.load(ruta).convert()
        if mida:
            img = pygame.transform.scale(img, mida)
        return img
    except Exception:
        return None

def wrap_text(text, font, max_width):
    """Trenca text en línies que caben dins de max_width."""
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = current + (" " if current else "") + word
        if font.size(test)[0] <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

def draw_rounded_rect(surface, color, rect, radius=12, alpha=None):
    """Dibuixa un rectangle arrodonit."""
    if alpha is not None:
        s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), (0, 0, rect[2], rect[3]), border_radius=radius)
        surface.blit(s, (rect[0], rect[1]))
    else:
        pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_text_lines(surface, lines, font, color, x, y, line_height):
    """Dibuixa una llista de línies de text."""
    for i, line in enumerate(lines):
        surf = font.render(line, True, color)
        surface.blit(surf, (x, y + i * line_height))

# ─── BOTONS ───────────────────────────────────────────────────────────────────
class Button:
    def __init__(self, x, y, w, h, text, font,
                 bg=BLUE_600, fg=WHITE, border=None,
                 radius=8, hover_bg=None):
        self.rect     = pygame.Rect(x, y, w, h)
        self.text     = text
        self.font     = font
        self.bg       = bg
        self.fg       = fg
        self.border   = border
        self.radius   = radius
        self.hover_bg = hover_bg or bg

    def draw(self, surface):
        mouse = pygame.mouse.get_pos()
        color = self.hover_bg if self.rect.collidepoint(mouse) else self.bg
        draw_rounded_rect(surface, color, self.rect, self.radius)
        if self.border:
            pygame.draw.rect(surface, self.border, self.rect,
                             width=1, border_radius=self.radius)
        txt = self.font.render(self.text, True, self.fg)
        r   = txt.get_rect(center=self.rect.center)
        surface.blit(txt, r)

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and
                event.button == 1 and
                self.rect.collidepoint(event.pos))

# ─── PANELL D'INVENT (joc) ────────────────────────────────────────────────────
class PanellInvent:
    """Dibuixa un invent com a panell amb imatge de fons i text superposat."""

    def __init__(self, rect, nom, invent, mostrar_any=True):
        self.rect        = rect
        self.nom         = nom
        self.invent      = invent
        self.mostrar_any = mostrar_any
        self.img         = load_image(invent["imatge"], (rect[2], rect[3]))

    def draw(self, surface, fonts):
        x, y, w, h = self.rect

        # Fons: imatge o color gris
        if self.img:
            surface.blit(self.img, (x, y))
        else:
            pygame.draw.rect(surface, GRAY_200, self.rect)

        # Overlay fosc per llegibilitat
        draw_rounded_rect(surface, (0, 0, 0), self.rect, radius=12, alpha=170)

        # Nom
        padding = 24
        nom_lines = wrap_text(self.nom.title(), fonts["bold"], w - padding * 2)
        draw_text_lines(surface, nom_lines, fonts["bold"], WHITE,
                        x + padding, y + padding, 32)

        # Descripció
        desc     = self.invent["descripcio"]
        dy       = y + padding + len(nom_lines) * 32 + 12
        d_lines  = wrap_text(desc, fonts["small"], w - padding * 2)
        draw_text_lines(surface, d_lines, fonts["small"], GRAY_200,
                        x + padding, dy, 22)

        # Any (opcional)
        if self.mostrar_any:
            any_txt = fonts["semibold"].render(
                format_any(self.invent["any"]), True, BLUE_50)
            surface.blit(any_txt, (x + padding, y + h - 56))

# ─── PANTALLA MENÚ ────────────────────────────────────────────────────────────
class MenuScreen:
    def __init__(self, fonts):
        self.fonts = fonts
        cx = WIDTH // 2
        self.btn_joc = Button(cx - 160, 340, 320, 56,
                              "Jugar",        fonts["semibold"],
                              BLUE_600, WHITE, hover_bg=(29, 78, 216))
        self.btn_cro = Button(cx - 160, 416, 320, 56,
                              "Cronologia",   fonts["semibold"],
                              WHITE, GRAY_900, border=GRAY_200,
                              hover_bg=GRAY_100)

    def handle(self, event):
        if self.btn_joc.is_clicked(event):
            return "joc"
        if self.btn_cro.is_clicked(event):
            return "cronologia"
        return None

    def draw(self, surface):
        surface.fill(WHITE)

        # Línia separadora superior suau
        pygame.draw.line(surface, GRAY_200, (0, 60), (WIDTH, 60))

        # Títol
        t1 = self.fonts["title"].render("Higher or Lower", True, GRAY_900)
        t2 = self.fonts["body"].render(
            "Endevina si l'invent és anterior o posterior.", True, GRAY_500)
        surface.blit(t1, t1.get_rect(center=(WIDTH // 2, 200)))
        surface.blit(t2, t2.get_rect(center=(WIDTH // 2, 260)))

        self.btn_joc.draw(surface)
        self.btn_cro.draw(surface)

        # Peu
        peu = self.fonts["meta"].render(
            "Higher or Lower · Invents per a la Discapacitat", True, GRAY_400)
        surface.blit(peu, peu.get_rect(center=(WIDTH // 2, HEIGHT - 32)))

# ─── PANTALLA CRONOLOGIA ──────────────────────────────────────────────────────
class CronologiaScreen:
    ITEM_W   = 160
    ITEM_H   = 80
    NODE_R   = 8
    LINE_Y_R = 0.5   # fracció de l'alçada per a la línia

    def __init__(self, fonts):
        self.fonts     = fonts
        self.scroll_x  = 0
        self.selected  = None   # nom de l'invent seleccionat
        self.popup_img = {}     # caché d'imatges
        self.items     = sorted(invents.items(), key=lambda x: x[1]["any"])
        self.total_w   = len(self.items) * self.ITEM_W + 200
        self.btn_back  = Button(24, 24, 120, 40, "← Enrere", fonts["body"],
                                WHITE, GRAY_700, border=GRAY_200,
                                hover_bg=GRAY_100)
        self.dragging  = False
        self.drag_x    = 0

    def _item_cx(self, idx):
        return 100 + idx * self.ITEM_W - self.scroll_x

    def handle(self, event):
        if self.btn_back.is_clicked(event):
            self.selected = None
            return "menu"

        # Tancar popup
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.selected = None

        # Clic per seleccionar invent
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            # Tanca popup si ja n'hi ha un
            if self.selected:
                popup_rect = pygame.Rect(WIDTH // 2 - 300, HEIGHT // 2 - 220, 600, 440)
                if not popup_rect.collidepoint(event.pos):
                    self.selected = None
                    return None
            else:
                line_y = int(HEIGHT * self.LINE_Y_R)
                for idx, (nom, inv) in enumerate(self.items):
                    cx = self._item_cx(idx)
                    cy = line_y
                    if abs(event.pos[0] - cx) < 40 and abs(event.pos[1] - cy) < 40:
                        self.selected = nom
                        # Carrega imatge si cal
                        if nom not in self.popup_img:
                            self.popup_img[nom] = load_image(inv["imatge"], (300, 200))
                        break

        # Scroll amb roda
        if event.type == pygame.MOUSEWHEEL:
            self.scroll_x = max(0, min(self.scroll_x - event.x * 30 + event.y * -30,
                                       self.total_w - WIDTH))
        return None

    def draw(self, surface):
        surface.fill(CANVAS_MUTED)
        pygame.draw.line(surface, GRAY_200, (0, 60), (WIDTH, 60))

        # Títol
        t = self.fonts["semibold"].render("Cronologia d'Invents", True, GRAY_900)
        surface.blit(t, (WIDTH // 2 - t.get_width() // 2, 16))
        self.btn_back.draw(surface)

        line_y = int(HEIGHT * self.LINE_Y_R)

        # Línia de temps
        pygame.draw.line(surface, GRAY_400, (0, line_y), (WIDTH, line_y), 2)

        for idx, (nom, inv) in enumerate(self.items):
            cx = self._item_cx(idx)
            if cx < -self.ITEM_W or cx > WIDTH + self.ITEM_W:
                continue

            # Node
            mouse = pygame.mouse.get_pos()
            hover = abs(mouse[0] - cx) < 40 and abs(mouse[1] - line_y) < 40
            color = BLUE_600 if hover else GRAY_500
            pygame.draw.circle(surface, color, (cx, line_y), self.NODE_R + (2 if hover else 0))
            pygame.draw.circle(surface, WHITE,  (cx, line_y), self.NODE_R - 3)

            # Any
            any_txt = self.fonts["meta"].render(format_any(inv["any"]), True, GRAY_500)
            surface.blit(any_txt, (cx - any_txt.get_width() // 2, line_y + 16))

            # Nom (alternat dalt/baix)
            nom_c   = nom.title()
            max_c   = 18
            nom_c   = nom_c[:max_c] + "…" if len(nom_c) > max_c else nom_c
            nom_srf = self.fonts["meta"].render(nom_c, True, GRAY_700)
            if idx % 2 == 0:
                surface.blit(nom_srf, (cx - nom_srf.get_width() // 2, line_y - 36))
            else:
                surface.blit(nom_srf, (cx - nom_srf.get_width() // 2, line_y + 36))

        # Popup
        if self.selected and self.selected in invents:
            self._draw_popup(surface, self.selected, invents[self.selected])

        # Instrucció scroll
        inst = self.fonts["meta"].render(
            "← Fes scroll per navegar · Clica un node per veure'n els detalls →",
            True, GRAY_400)
        surface.blit(inst, (WIDTH // 2 - inst.get_width() // 2, HEIGHT - 36))

    def _draw_popup(self, surface, nom, inv):
        pw, ph = 600, 440
        px = WIDTH  // 2 - pw // 2
        py = HEIGHT // 2 - ph // 2

        # Fons popup
        draw_rounded_rect(surface, WHITE,    (px, py, pw, ph), radius=16)
        pygame.draw.rect(surface,  GRAY_200, (px, py, pw, ph),
                         width=1, border_radius=16)

        # Imatge
        img = self.popup_img.get(nom)
        if img:
            img_scaled = pygame.transform.scale(img, (pw, 200))
            # Clip arrodonit simulat (rectangle normal)
            surface.blit(img_scaled, (px, py))
            pygame.draw.rect(surface, GRAY_200, (px, py, pw, 200), width=1)
            text_y = py + 212
        else:
            text_y = py + 24

        padding = 24
        # Nom
        nom_srf = self.fonts["bold"].render(nom.title(), True, GRAY_900)
        surface.blit(nom_srf, (px + padding, text_y))

        # Any
        any_srf = self.fonts["semibold"].render(format_any(inv["any"]), True, BLUE_600)
        surface.blit(any_srf, (px + pw - any_srf.get_width() - padding, text_y))

        # Separador
        pygame.draw.line(surface, GRAY_200,
                         (px + padding, text_y + 36),
                         (px + pw - padding, text_y + 36))

        # Descripció
        desc_lines = wrap_text(inv["descripcio"], self.fonts["body"],
                               pw - padding * 2)
        draw_text_lines(surface, desc_lines, self.fonts["body"], GRAY_700,
                        px + padding, text_y + 48, 22)

        # Tanca
        close = self.fonts["meta"].render("Clica fora per tancar", True, GRAY_400)
        surface.blit(close, (px + pw // 2 - close.get_width() // 2, py + ph - 28))

# ─── PANTALLA JOC ─────────────────────────────────────────────────────────────
class JocScreen:
    def __init__(self, fonts, game_id):
        self.fonts       = fonts
        self.game_id     = game_id
        self.score       = 0
        self.used        = set()
        self.last_prog   = time.time()
        self.result      = None   # "correcte" | "incorrecte"
        self.result_t    = 0
        self.finished    = False
        self.panel_w     = WIDTH // 2 - 40
        self.panel_h     = HEIGHT - 140
        self.panel_y     = 90

        self.btn_abans   = Button(WIDTH // 2 + 20, HEIGHT - 72,
                                  (self.panel_w - 20) // 2, 48,
                                  "← Abans", fonts["semibold"],
                                  WHITE, GRAY_900, border=GRAY_200,
                                  hover_bg=GRAY_100)
        self.btn_despres = Button(WIDTH // 2 + 20 + (self.panel_w + 20) // 2, HEIGHT - 72,
                                  (self.panel_w - 20) // 2, 48,
                                  "Després →", fonts["semibold"],
                                  BLUE_600, WHITE,
                                  hover_bg=(29, 78, 216))

        self._nou_torn()

    def _invent_aleatori(self):
        claus = [k for k in invents if k not in self.used]
        if not claus:
            return None, None
        nom = random.choice(claus)
        self.used.add(nom)
        return nom, invents[nom]

    def _nou_torn(self):
        if not self.used:
            # Primer torn: tria l'esquerra
            nom_e, inv_e = self._invent_aleatori()
            if nom_e is None:
                self.finished = True
                return
            self.nom_esq = nom_e
            self.inv_esq = inv_e
        # Sempre tria nova dreta
        nom_d, inv_d = self._invent_aleatori()
        if nom_d is None:
            self.finished = True
            return
        self.nom_dret = nom_d
        self.inv_dret = inv_d

        self.panell_esq = PanellInvent(
            (20, self.panel_y, self.panel_w, self.panel_h),
            self.nom_esq, self.inv_esq, mostrar_any=True)
        self.panell_dret = PanellInvent(
            (WIDTH // 2 + 20, self.panel_y, self.panel_w, self.panel_h),
            self.nom_dret, self.inv_dret, mostrar_any=False)

    def _comprova(self, opcio):
        """opcio: 'abans' o 'despres'"""
        any_esq  = self.inv_esq["any"]
        any_dret = self.inv_dret["any"]
        if opcio == "abans":
            correcte = any_dret <= any_esq
        else:
            correcte = any_dret >= any_esq

        if correcte:
            self.score  += 1
            self.result  = "correcte"
            self.result_t = time.time()
            # El panell dret es converteix en el nou esquerre
            self.nom_esq = self.nom_dret
            self.inv_esq = self.inv_dret
            self._nou_torn()
        else:
            self.result   = "incorrecte"
            self.result_t = time.time()
            self.finished = True
            # Notifica servidor
            threading.Thread(
                target=fijoc, args=(self.game_id, self.score), daemon=True
            ).start()

    def handle(self, event):
        if self.finished:
            return None

        if self.btn_abans.is_clicked(event):
            self._comprova("abans")
        if self.btn_despres.is_clicked(event):
            self._comprova("despres")

        # Progrés periòdic
        if time.time() - self.last_prog >= PROGRESS_INTERVAL:
            threading.Thread(
                target=progres,
                args=(self.game_id, self.nom_esq, self.score),
                daemon=True
            ).start()
            self.last_prog = time.time()

        if self.finished:
            return "gameover"
        return None

    def draw(self, surface):
        surface.fill(CANVAS_MUTED)

        # Capçalera
        pygame.draw.line(surface, GRAY_200, (0, 70), (WIDTH, 70))
        score_txt = self.fonts["semibold"].render(
            f"Puntuació: {self.score}", True, GRAY_900)
        surface.blit(score_txt, (WIDTH // 2 - score_txt.get_width() // 2, 20))

        instr = self.fonts["meta"].render(
            "L'invent de la dreta és anterior o posterior al de l'esquerra?",
            True, GRAY_500)
        surface.blit(instr, (WIDTH // 2 - instr.get_width() // 2, 48))

        # Panells
        self.panell_esq.draw(surface,  self.fonts)
        self.panell_dret.draw(surface, self.fonts)

        # "?" sobre any dret
        q = self.fonts["title"].render("?", True, WHITE)
        rx = WIDTH // 2 + 20
        surface.blit(q, (rx + self.panel_w // 2 - q.get_width() // 2,
                         self.panel_y + self.panel_h - 72))

        # Botons
        self.btn_abans.draw(surface)
        self.btn_despres.draw(surface)

        # Feedback breu
        if self.result and time.time() - self.result_t < 1.2:
            color = GREEN_600 if self.result == "correcte" else RED_600
            text  = "✓ Correcte!" if self.result == "correcte" else "✗ Incorrecte!"
            fb    = self.fonts["bold"].render(text, True, color)
            surface.blit(fb, (WIDTH // 2 - fb.get_width() // 2, HEIGHT // 2 - 20))

# ─── PANTALLA GAME OVER ───────────────────────────────────────────────────────
class GameOverScreen:
    def __init__(self, fonts, score, nom_esq, inv_esq, nom_dret, inv_dret):
        self.fonts   = fonts
        self.score   = score
        self.nom_esq = nom_esq
        self.inv_esq = inv_esq
        self.nom_dret = nom_dret
        self.inv_dret = inv_dret
        cx = WIDTH // 2
        self.btn_restart = Button(cx - 260, 500, 240, 70,
                                  "Tornar a jugar", fonts["semibold"],
                                  BLUE_600, WHITE, hover_bg=(29, 78, 216))
        self.btn_menu    = Button(cx + 40, 500, 240, 70,
                                  "Menú principal", fonts["semibold"],
                                  WHITE, GRAY_900, border=GRAY_200,
                                  hover_bg=GRAY_100)

    def handle(self, event):
        if self.btn_restart.is_clicked(event):
            return "restart"
        if self.btn_menu.is_clicked(event):
            return "menu"
        return None

    def draw(self, surface):
        surface.fill(WHITE)
        pygame.draw.line(surface, GRAY_200, (0, 60), (WIDTH, 60))

        # Títol
        t1 = self.fonts["title"].render("Joc acabat!", True, GRAY_900)
        surface.blit(t1, t1.get_rect(center=(WIDTH // 2, 120)))

        # Puntuació
        sc = self.fonts["bold"].render(f"Puntuació final: {self.score}", True, BLUE_600)
        surface.blit(sc, sc.get_rect(center=(WIDTH // 2, 190)))

        # Divisori
        pygame.draw.line(surface, GRAY_200, (WIDTH // 2 - 200, 220),
                         (WIDTH // 2 + 200, 220))

        # Comparació d'invents
        info = self.fonts["body"].render("La comparació que ha fallat:", True, GRAY_500)
        surface.blit(info, info.get_rect(center=(WIDTH // 2, 250)))

        # Esquerra
        esq_any = self.fonts["semibold"].render(
            f"{self.nom_esq.title()} → {format_any(self.inv_esq['any'])}", True, GRAY_700)
        surface.blit(esq_any, esq_any.get_rect(center=(WIDTH // 2, 295)))

        vs = self.fonts["bold"].render("VS", True, GRAY_400)
        surface.blit(vs, vs.get_rect(center=(WIDTH // 2, 335)))

        dret_any = self.fonts["semibold"].render(
            f"{self.nom_dret.title()} → {format_any(self.inv_dret['any'])}", True, GRAY_700)
        surface.blit(dret_any, dret_any.get_rect(center=(WIDTH // 2, 375)))

        # Botons
        self.btn_restart.draw(surface)
        self.btn_menu.draw(surface)

# ─── INICIALITZACIÓ PYGAME ────────────────────────────────────────────────────
def build_fonts():
    """Construeix tots els fonts del joc."""
    # Intenta carregar Inter (si el sistema el té), sinó fa servir Arial
    candidates = ["Inter", "Arial", "Helvetica", "DejaVu Sans", "FreeSans"]
    base = None
    for name in candidates:
        try:
            test = pygame.font.SysFont(name, 16)
            if test:
                base = name
                break
        except Exception:
            continue

    def f(size, bold=False):
        return pygame.font.SysFont(base, size, bold=bold)

    return {
        "title":    f(64, bold=True),
        "bold":     f(36, bold=True),
        "semibold": f(28, bold=True),
        "body":     f(24),
        "small":    f(20),
        "meta":     f(18),
}

# ─── BUCLE PRINCIPAL ──────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Higher or Lower · Invents")
    clock  = pygame.time.Clock()
    fonts  = build_fonts()

    # Inicialitza el servidor
    game_id, seed = inicialitzar()
    random.seed(seed)

    # Estat inicial
    state       = "menu"
    menu        = MenuScreen(fonts)
    cronologia  = CronologiaScreen(fonts)
    joc         = None
    gameover    = None

    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

            # ── Menú ──────────────────────────────────────────────────────────
            if state == "menu":
                dest = menu.handle(event)
                if dest == "joc":
                    game_id, seed = inicialitzar()
                    random.seed(seed)
                    joc   = JocScreen(fonts, game_id)
                    state = "joc"
                elif dest == "cronologia":
                    cronologia = CronologiaScreen(fonts)
                    state = "cronologia"

            # ── Cronologia ────────────────────────────────────────────────────
            elif state == "cronologia":
                dest = cronologia.handle(event)
                if dest == "menu":
                    state = "menu"

            # ── Joc ───────────────────────────────────────────────────────────
            elif state == "joc":
                dest = joc.handle(event)
                if dest == "gameover":
                    gameover = GameOverScreen(
                        fonts, joc.score,
                        joc.nom_esq, joc.inv_esq,
                        joc.nom_dret, joc.inv_dret)
                    state = "gameover"

            # ── Game Over ─────────────────────────────────────────────────────
            elif state == "gameover":
                dest = gameover.handle(event)
                if dest == "restart":
                    game_id, seed = inicialitzar()
                    random.seed(seed)
                    joc   = JocScreen(fonts, game_id)
                    state = "joc"
                elif dest == "menu":
                    state = "menu"

        # ── Dibuix ────────────────────────────────────────────────────────────
        if state == "menu":
            menu.draw(screen)
        elif state == "cronologia":
            cronologia.draw(screen)
        elif state == "joc":
            joc.draw(screen)
        elif state == "gameover":
            gameover.draw(screen)

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()