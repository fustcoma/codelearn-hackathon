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

# ─── COLORS (accessibles per a daltònics: paleta blau/taronja/gris) ───────────
WHITE        = (255, 255, 255)
CANVAS_MUTED = (240, 242, 245)
GRAY_900     = ( 20,  24,  35)
GRAY_700     = ( 55,  65,  85)
GRAY_500     = (100, 110, 128)
GRAY_400     = (150, 158, 175)
GRAY_200     = (220, 224, 232)
GRAY_100     = (240, 242, 246)
# Blau principal (accessible)
BLUE_700     = ( 25,  75, 200)
BLUE_600     = ( 37,  99, 235)
BLUE_50      = (235, 245, 255)
# Taronja per a "correcte" (llegible per daltònics protanopia/deuteranopia)
ORANGE_500   = (234, 132,   0)
# Vermell per a "incorrecte"
RED_600      = (200,  35,  35)
# Verd alternatiu (cian fosc, llegible per tots)
CORRECT_COL  = ( 10, 140, 180)   # Cian fort — bon contrast blanc i negre
BLACK        = (  0,   0,   0)

# ─── SERVIDOR ─────────────────────────────────────────────────────────────────
BASE_URL = "http://fun.codelearn.cat/hackathon/game"

def inicialitzar():
    try:
        r = requests.get(f"{BASE_URL}/new", timeout=5)
        data = r.json()
        return data["game_id"], data["seed"]
    except Exception as e:
        print(f"[Servidor] Error inicialitzar: {e}")
        return "local_game", random.randint(0, 999999)

def progres(game_id, invent_actual, score):
    try:
        send = {"game_id": game_id, "data": invent_actual, "score": score}
        requests.post(f"{BASE_URL}/store_progress", json=send, timeout=5)
    except Exception as e:
        print(f"[Servidor] Error progres: {e}")

def fijoc(game_id, score):
    try:
        send = {"game_id": game_id, "data": "ha fallat", "score": score}
        requests.post(f"{BASE_URL}/finalize", json=send, timeout=5)
    except Exception as e:
        print(f"[Servidor] Error fijoc: {e}")

# ─── UTILITATS ────────────────────────────────────────────────────────────────
def format_any(any_num):
    if any_num < 0:
        return f"{abs(any_num)} aC"
    return str(any_num)

def load_image(nom_fitxer, mida=None):
    ruta = os.path.join(IMG_DIR, nom_fitxer)
    if not os.path.isfile(ruta):
        return None
    try:
        img = pygame.image.load(ruta).convert()
        if mida:
            tw, th = mida
            iw, ih = img.get_size()
            # Escala mantenint aspecte fins que cobreix tota la mida (crop)
            scale = max(tw / iw, th / ih)
            new_w = int(iw * scale)
            new_h = int(ih * scale)
            img = pygame.transform.scale(img, (new_w, new_h))
            # Retalla el centre
            cx = (new_w - tw) // 2
            cy = (new_h - th) // 2
            img = img.subsurface(pygame.Rect(cx, cy, tw, th)).copy()
        return img
    except Exception:
        return None

def wrap_text(text, font, max_width):
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
    if alpha is not None:
        s = pygame.Surface((rect[2], rect[3]), pygame.SRCALPHA)
        pygame.draw.rect(s, (*color, alpha), (0, 0, rect[2], rect[3]), border_radius=radius)
        surface.blit(s, (rect[0], rect[1]))
    else:
        pygame.draw.rect(surface, color, rect, border_radius=radius)

def draw_text_lines(surface, lines, font, color, x, y, line_height):
    for i, line in enumerate(lines):
        surf = font.render(line, True, color)
        surface.blit(surf, (x, y + i * line_height))

def draw_text_lines_centered(surface, lines, font, color, cx, y, line_height):
    for i, line in enumerate(lines):
        surf = font.render(line, True, color)
        surface.blit(surf, (cx - surf.get_width() // 2, y + i * line_height))

# ─── BOTONS ───────────────────────────────────────────────────────────────────
class Button:
    def __init__(self, x, y, w, h, text, font,
                 bg=BLUE_600, fg=WHITE, border=None,
                 radius=10, hover_bg=None):
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
        hovering = self.rect.collidepoint(mouse)
        color = self.hover_bg if hovering else self.bg

        # Ombra lleugera
        shadow = pygame.Rect(self.rect.x + 2, self.rect.y + 3,
                             self.rect.w, self.rect.h)
        draw_rounded_rect(surface, (180, 185, 200), shadow, self.radius, alpha=80)

        draw_rounded_rect(surface, color, self.rect, self.radius)
        if self.border:
            pygame.draw.rect(surface, self.border, self.rect,
                             width=2, border_radius=self.radius)
        txt = self.font.render(self.text, True, self.fg)
        r   = txt.get_rect(center=self.rect.center)
        surface.blit(txt, r)

    def is_clicked(self, event):
        return (event.type == pygame.MOUSEBUTTONDOWN and
                event.button == 1 and
                self.rect.collidepoint(event.pos))

# ─── PANELL D'INVENT (joc) ────────────────────────────────────────────────────
class PanellInvent:
    def __init__(self, rect, nom, invent, mostrar_any=True):
        self.rect        = rect
        self.nom         = nom
        self.invent      = invent
        self.mostrar_any = mostrar_any
        self.img         = load_image(invent["imatge"], (rect[2], rect[3]))

    def draw(self, surface, fonts):
        x, y, w, h = self.rect

        # Ombra del panell
        shadow_rect = (x + 4, y + 5, w, h)
        draw_rounded_rect(surface, (160, 165, 180), shadow_rect, radius=18, alpha=70)

        # Fons: imatge amb cantons arrodonits o rectangle negre
        if self.img:
            # Superfície RGBA per poder aplicar màscara d'arrodoniment
            rounded_img = pygame.Surface((w, h), pygame.SRCALPHA)
            rounded_img.fill((0, 0, 0, 0))
            # Convertim la imatge a RGBA i la bliuem
            img_rgba = self.img.convert_alpha() if hasattr(self.img, 'convert_alpha') else self.img
            rounded_img.blit(img_rgba, (0, 0))
            # Màscara arrodonida: retalla els cantons
            mask = pygame.Surface((w, h), pygame.SRCALPHA)
            mask.fill((0, 0, 0, 0))
            pygame.draw.rect(mask, (255, 255, 255, 255), (0, 0, w, h), border_radius=18)
            rounded_img.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surface.blit(rounded_img, (x, y))
        else:
            pygame.draw.rect(surface, BLACK, self.rect, border_radius=18)

        # Overlay fosc suau però suficient per a contrast
        draw_rounded_rect(surface, (0, 0, 0), self.rect, radius=18, alpha=185)

        # Bora arrodonida (decorativa)
        pygame.draw.rect(surface, (255, 255, 255), self.rect,
                         width=2, border_radius=18)

        padding = 28

        # ── Nom de l'invent — majúscules i centrat horitzontalment ──
        nom_lines = wrap_text(self.nom.upper(), fonts["nom_panell"], w - padding * 2)
        nom_y = y + padding
        cx = x + w // 2
        for i, line in enumerate(nom_lines):
            line_surf = fonts["nom_panell"].render(line, True, WHITE)
            surface.blit(line_surf, (cx - line_surf.get_width() // 2, nom_y + i * 40))

        # ── Descripció ──
        desc  = self.invent["descripcio"]
        dy    = nom_y + len(nom_lines) * 40 + 14
        d_lines = wrap_text(desc, fonts["desc_panell"], w - padding * 2)
        draw_text_lines(surface, d_lines, fonts["desc_panell"], GRAY_200,
                        x + padding, dy, 26)

        # ── Any — centrat horitzontalment ──
        if self.mostrar_any:
            any_str = format_any(self.invent["any"])
            any_surf = fonts["any_panell"].render(any_str, True, WHITE)
            aw = any_surf.get_width()
            ah = any_surf.get_height()
            pill_pad = 14
            pill_w = aw + pill_pad * 2
            pill_x = x + (w - pill_w) // 2          # centrat horitzontalment
            pill_y = y + h - ah - 24 - pill_pad
            pill_rect = (pill_x, pill_y, pill_w, ah + pill_pad)
            draw_rounded_rect(surface, BLUE_700, pill_rect, radius=12, alpha=220)
            surface.blit(any_surf, (pill_x + pill_pad, pill_y + pill_pad // 2))

# ─── PANTALLA MENÚ ────────────────────────────────────────────────────────────
class MenuScreen:
    def __init__(self, fonts):
        self.fonts = fonts
        cx = WIDTH // 2
        self.btn_joc = Button(cx - 170, 360, 340, 62,
                              "Jugar", fonts["btn_menu"],
                              BLUE_600, WHITE, hover_bg=BLUE_700, radius=12)
        self.btn_cro = Button(cx - 170, 442, 340, 62,
                              "Cronologia", fonts["btn_menu"],
                              WHITE, GRAY_700, border=GRAY_400,
                              hover_bg=GRAY_100, radius=12)

    def handle(self, event):
        if self.btn_joc.is_clicked(event):
            return "joc"
        if self.btn_cro.is_clicked(event):
            return "cronologia"
        return None

    def draw(self, surface):
        surface.fill(WHITE)
        pygame.draw.line(surface, GRAY_200, (0, 64), (WIDTH, 64), 2)

        # Títol gran
        t1 = self.fonts["menu_title"].render("Higher or Lower", True, GRAY_900)
        surface.blit(t1, t1.get_rect(center=(WIDTH // 2, 200)))

        # Subtítol
        t2 = self.fonts["menu_sub"].render(
            "Endevina si l'invent és anterior o posterior.", True, GRAY_500)
        surface.blit(t2, t2.get_rect(center=(WIDTH // 2, 278)))

        # Línia decorativa sota subtítol
        lw = 80
        lx = WIDTH // 2
        pygame.draw.line(surface, BLUE_600, (lx - lw, 308), (lx + lw, 308), 3)

        self.btn_joc.draw(surface)
        self.btn_cro.draw(surface)

        peu = self.fonts["peu"].render(
            "Higher or Lower · Invents per a la Discapacitat", True, GRAY_400)
        surface.blit(peu, peu.get_rect(center=(WIDTH // 2, HEIGHT - 30)))

        # Crèdits baix a la dreta
        credits = self.fonts["peu"].render(
            "Fet per = {\u0022\u03A3 duo\u0022: [\u0022Dídac Fustero\u0022, \u0022Oriol Milà\u0022]}", True, GRAY_400)
        surface.blit(credits, (WIDTH - credits.get_width() - 16, HEIGHT - 26))

# ─── PANTALLA CRONOLOGIA ──────────────────────────────────────────────────────
class CronologiaScreen:
    ITEM_W   = 160
    ITEM_H   = 80
    NODE_R   = 9
    LINE_Y_R = 0.5

    def __init__(self, fonts):
        self.fonts     = fonts
        self.scroll_x  = 0
        self.selected  = None
        self.popup_img = {}
        self.items     = sorted(invents.items(), key=lambda x: x[1]["any"])
        self.total_w   = len(self.items) * self.ITEM_W + 200
        self.btn_back  = Button(24, 16, 130, 44, "← Enrere", fonts["btn_small"],
                                WHITE, GRAY_700, border=GRAY_400,
                                hover_bg=GRAY_100, radius=10)
        self.dragging      = False
        self.drag_x        = 0
        self.scrollbar_dragging = False
        self.scrollbar_drag_start_x   = 0
        self.scrollbar_drag_start_scroll = 0

        # Geometria de la barra corredera
        self.SB_H    = 14   # alçada de la barra
        self.SB_Y    = HEIGHT - self.SB_H - 8
        self.SB_PADX = 20  # marges laterals

    def _item_cx(self, idx):
        return 100 + idx * self.ITEM_W - self.scroll_x

    def _scrollbar_thumb_rect(self):
        """Retorna el pygame.Rect del 'thumb' de la barra corredera."""
        track_w   = WIDTH - self.SB_PADX * 2
        max_scroll = max(1, self.total_w - WIDTH)
        thumb_w   = max(40, int(track_w * WIDTH / max(self.total_w, WIDTH + 1)))
        thumb_x   = self.SB_PADX + int((track_w - thumb_w) * self.scroll_x / max_scroll)
        return pygame.Rect(thumb_x, self.SB_Y, thumb_w, self.SB_H)

    def handle(self, event):
        if self.btn_back.is_clicked(event):
            self.selected = None
            return "menu"

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.selected = None

        # ── Barra corredera ──────────────────────────────────────────────────
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            thumb = self._scrollbar_thumb_rect()
            if thumb.collidepoint(event.pos):
                self.scrollbar_dragging = True
                self.scrollbar_drag_start_x      = event.pos[0]
                self.scrollbar_drag_start_scroll = self.scroll_x
                return None

            # Clic a la track (fora del thumb) → salta a la posició
            track_rect = pygame.Rect(self.SB_PADX, self.SB_Y,
                                     WIDTH - self.SB_PADX * 2, self.SB_H)
            if track_rect.collidepoint(event.pos) and not thumb.collidepoint(event.pos):
                track_w   = WIDTH - self.SB_PADX * 2
                max_scroll = max(1, self.total_w - WIDTH)
                ratio = (event.pos[0] - self.SB_PADX) / track_w
                self.scroll_x = int(max(0, min(ratio * self.total_w - WIDTH // 2, max_scroll)))
                return None

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.scrollbar_dragging = False

        if event.type == pygame.MOUSEMOTION and self.scrollbar_dragging:
            track_w    = WIDTH - self.SB_PADX * 2
            max_scroll = max(1, self.total_w - WIDTH)
            thumb_w    = max(40, int(track_w * WIDTH / max(self.total_w, WIDTH + 1)))
            dx = event.pos[0] - self.scrollbar_drag_start_x
            scroll_per_px = max_scroll / max(1, track_w - thumb_w)
            self.scroll_x = int(max(0, min(
                self.scrollbar_drag_start_scroll + dx * scroll_per_px, max_scroll)))
            return None

        # ── Selecció d'invent ────────────────────────────────────────────────
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
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
                        if nom not in self.popup_img:
                            self.popup_img[nom] = load_image(inv["imatge"], (300, 200))
                        break

        if event.type == pygame.MOUSEWHEEL:
            self.scroll_x = max(0, min(self.scroll_x - event.x * 30 + event.y * -30,
                                       self.total_w - WIDTH))
        return None

    def draw(self, surface):
        surface.fill(CANVAS_MUTED)
        pygame.draw.line(surface, GRAY_200, (0, 64), (WIDTH, 64), 2)

        t = self.fonts["cro_title"].render("Cronologia d'Invents", True, GRAY_900)
        surface.blit(t, (WIDTH // 2 - t.get_width() // 2, 14))
        self.btn_back.draw(surface)

        line_y = int(HEIGHT * self.LINE_Y_R)
        pygame.draw.line(surface, GRAY_400, (0, line_y), (WIDTH, line_y), 3)

        for idx, (nom, inv) in enumerate(self.items):
            cx = self._item_cx(idx)
            if cx < -self.ITEM_W or cx > WIDTH + self.ITEM_W:
                continue

            mouse = pygame.mouse.get_pos()
            hover = abs(mouse[0] - cx) < 40 and abs(mouse[1] - line_y) < 40
            color = BLUE_600 if hover else GRAY_500
            pygame.draw.circle(surface, color, (cx, line_y), self.NODE_R + (3 if hover else 0))
            pygame.draw.circle(surface, WHITE,  (cx, line_y), self.NODE_R - 4)

            any_txt = self.fonts["cro_any"].render(format_any(inv["any"]), True, GRAY_500)
            surface.blit(any_txt, (cx - any_txt.get_width() // 2, line_y + 18))

            nom_c = nom.upper()
            max_c = 18
            nom_c = nom_c[:max_c] + "…" if len(nom_c) > max_c else nom_c
            nom_srf = self.fonts["cro_nom"].render(nom_c, True, GRAY_700)
            if idx % 2 == 0:
                surface.blit(nom_srf, (cx - nom_srf.get_width() // 2, line_y - 40))
            else:
                surface.blit(nom_srf, (cx - nom_srf.get_width() // 2, line_y + 40))

        if self.selected and self.selected in invents:
            self._draw_popup(surface, self.selected, invents[self.selected])

        # ── Barra corredera horitzontal ──────────────────────────────────────
        track_rect = pygame.Rect(self.SB_PADX, self.SB_Y,
                                 WIDTH - self.SB_PADX * 2, self.SB_H)
        pygame.draw.rect(surface, GRAY_200, track_rect, border_radius=7)
        thumb = self._scrollbar_thumb_rect()
        mouse = pygame.mouse.get_pos()
        thumb_col = BLUE_600 if (thumb.collidepoint(mouse) or self.scrollbar_dragging) else GRAY_400
        pygame.draw.rect(surface, thumb_col, thumb, border_radius=7)

        inst = self.fonts["peu"].render(
            "← Fes scroll o arrossega la barra · Clica un node per veure'n els detalls →",
            True, GRAY_400)
        surface.blit(inst, (WIDTH // 2 - inst.get_width() // 2, self.SB_Y - 22))

    def _draw_popup(self, surface, nom, inv):
        pw, ph = 600, 440
        px = WIDTH  // 2 - pw // 2
        py = HEIGHT // 2 - ph // 2

        draw_rounded_rect(surface, WHITE, (px, py, pw, ph), radius=18)
        pygame.draw.rect(surface, GRAY_200, (px, py, pw, ph),
                         width=1, border_radius=18)

        img = self.popup_img.get(nom)
        if img:
            iw, ih = img.get_size()
            # Crop centrat per omplir pw×200 sense deformar
            scale = max(pw / iw, 200 / ih)
            nw = int(iw * scale)
            nh = int(ih * scale)
            img_scaled = pygame.transform.scale(img, (nw, nh))
            cx_off = (nw - pw) // 2
            cy_off = (nh - 200) // 2
            img_cropped = img_scaled.subsurface(pygame.Rect(cx_off, cy_off, pw, 200)).copy()
            # Cantons arrodonits només a la part superior (coincidint amb el popup)
            rounded_top = pygame.Surface((pw, 200), pygame.SRCALPHA)
            rounded_top.fill((0, 0, 0, 0))
            rounded_top.blit(img_cropped, (0, 0))
            mask_top = pygame.Surface((pw, 200), pygame.SRCALPHA)
            mask_top.fill((0, 0, 0, 0))
            pygame.draw.rect(mask_top, (255, 255, 255, 255), (0, 0, pw, 200), border_radius=18)
            # La part inferior sense arrodonir (quadrada) per enganxar amb el text
            pygame.draw.rect(mask_top, (255, 255, 255, 255), (0, 182, pw, 18))
            rounded_top.blit(mask_top, (0, 0), special_flags=pygame.BLEND_RGBA_MIN)
            surface.blit(rounded_top, (px, py))
            text_y = py + 216
        else:
            text_y = py + 28

        padding = 24
        # Nom amb wrap per evitar que surti del requadre o tapi l'any
        any_srf  = self.fonts["popup_any"].render(format_any(inv["any"]), True, BLUE_600)
        any_w    = any_srf.get_width()
        nom_max_w = pw - padding * 2   # amplada disponible per al nom (tota, l'any va a sota)
        nom_lines = wrap_text(nom.upper(), self.fonts["popup_nom"], nom_max_w)
        nom_line_h = 34
        for i, line in enumerate(nom_lines):
            ls = self.fonts["popup_nom"].render(line, True, GRAY_900)
            surface.blit(ls, (px + padding, text_y + i * nom_line_h))
        nom_block_h = len(nom_lines) * nom_line_h

        # Any sota el nom
        surface.blit(any_srf, (px + padding, text_y + nom_block_h + 4))

        sep_y = text_y + nom_block_h + 4 + any_srf.get_height() + 8
        pygame.draw.line(surface, GRAY_200,
                         (px + padding, sep_y),
                         (px + pw - padding, sep_y))

        desc_lines = wrap_text(inv["descripcio"], self.fonts["popup_desc"],
                               pw - padding * 2)
        draw_text_lines(surface, desc_lines, self.fonts["popup_desc"], GRAY_700,
                        px + padding, sep_y + 10, 26)

        close = self.fonts["peu"].render("Clica fora per tancar", True, GRAY_400)
        surface.blit(close, (px + pw // 2 - close.get_width() // 2, py + ph - 28))

# ─── PANTALLA JOC ─────────────────────────────────────────────────────────────
class JocScreen:
    def __init__(self, fonts, game_id):
        self.fonts       = fonts
        self.game_id     = game_id
        self.score       = 0
        self.used        = set()
        self.last_prog   = time.time()
        self.result      = None
        self.result_t    = 0
        self.finished    = False
        self.panel_w     = WIDTH // 2 - 40
        self.panel_h     = HEIGHT - 150
        self.panel_y     = 85

        # ── Botons centrats dins el panell dret (vertical i horitzontal) ────
        btn_total_w = self.panel_w - 20
        btn_h       = 54
        btn_each    = (btn_total_w - 16) // 2
        panel_dret_x = WIDTH // 2 + 20
        # Centrats verticalment: mig del panell
        panel_center_y = self.panel_y + self.panel_h // 2
        btn_y        = panel_center_y - btn_h // 2
        btn_start_x  = panel_dret_x + (self.panel_w - btn_total_w) // 2

        self.btn_abans   = Button(btn_start_x, btn_y,
                                  btn_each, btn_h,
                                  "← Abans", fonts["btn_joc"],
                                  WHITE, GRAY_900, border=GRAY_400,
                                  hover_bg=GRAY_100, radius=12)
        self.btn_despres = Button(btn_start_x + btn_each + 16, btn_y,
                                  btn_each, btn_h,
                                  "Després →", fonts["btn_joc"],
                                  BLUE_600, WHITE,
                                  hover_bg=BLUE_700, radius=12)

        # Botó "Menú" a la capçalera (esquerra)
        self.btn_menu_back = Button(14, 16, 130, 44, "← Menú", fonts["btn_small"],
                                    WHITE, GRAY_700, border=GRAY_400,
                                    hover_bg=GRAY_100, radius=10)

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
            nom_e, inv_e = self._invent_aleatori()
            if nom_e is None:
                self.finished = True
                return
            self.nom_esq = nom_e
            self.inv_esq = inv_e
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
        any_esq  = self.inv_esq["any"]
        any_dret = self.inv_dret["any"]
        if opcio == "abans":
            correcte = any_dret <= any_esq
        else:
            correcte = any_dret >= any_esq

        if correcte:
            self.score   += 1
            self.result   = "correcte"
            self.result_t = time.time()
            self.nom_esq  = self.nom_dret
            self.inv_esq  = self.inv_dret
            self._nou_torn()
        else:
            self.result   = "incorrecte"
            self.result_t = time.time()
            self.finished = True
            threading.Thread(
                target=fijoc, args=(self.game_id, self.score), daemon=True
            ).start()

    def handle(self, event):
        if self.finished:
            return None

        if self.btn_menu_back.is_clicked(event):
            return "menu"
        if self.btn_abans.is_clicked(event):
            self._comprova("abans")
        if self.btn_despres.is_clicked(event):
            self._comprova("despres")

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

        # ── Capçalera ──
        pygame.draw.line(surface, GRAY_200, (0, 74), (WIDTH, 74), 2)

        # Botó menú
        self.btn_menu_back.draw(surface)

        # Puntuació centrada
        score_txt = self.fonts["score"].render(f"Puntuació: {self.score}", True, GRAY_900)
        surface.blit(score_txt, (WIDTH // 2 - score_txt.get_width() // 2, 14))

        # Instrucció
        instr = self.fonts["instruccio"].render(
            "L'invent de la dreta és anterior o posterior al de l'esquerra?",
            True, GRAY_500)
        surface.blit(instr, (WIDTH // 2 - instr.get_width() // 2, 50))

        # ── Panells ──
        self.panell_esq.draw(surface,  self.fonts)
        self.panell_dret.draw(surface, self.fonts)

        # "?" sobre l'any dret
        q = self.fonts["interrogant"].render("?", True, WHITE)
        rx = WIDTH // 2 + 20
        surface.blit(q, (rx + self.panel_w // 2 - q.get_width() // 2,
                         self.panel_y + self.panel_h - 86))

        # ── Botons ──
        self.btn_abans.draw(surface)
        self.btn_despres.draw(surface)

        # ── Feedback gran ──
        if self.result and time.time() - self.result_t < 1.4:
            if self.result == "correcte":
                text  = "Correcte!"
                color = CORRECT_COL
            else:
                text  = "Incorrecte!"
                color = RED_600

            fb_surf = self.fonts["feedback"].render(text, True, color)
            fw = fb_surf.get_width()
            fh = fb_surf.get_height()

            # Fons blanc sòlid, sense transparència ni vores arrodonides
            bg_rect = pygame.Rect(WIDTH // 2 - fw // 2 - 30,
                                  HEIGHT // 2 - fh // 2 - 14,
                                  fw + 60, fh + 28)
            pygame.draw.rect(surface, WHITE, bg_rect)
            pygame.draw.rect(surface, color, bg_rect, width=3)
            surface.blit(fb_surf, (WIDTH // 2 - fw // 2,
                                   HEIGHT // 2 - fh // 2 + 4))

# ─── PANTALLA GAME OVER ───────────────────────────────────────────────────────
class GameOverScreen:
    def __init__(self, fonts, score, nom_esq, inv_esq, nom_dret, inv_dret):
        self.fonts    = fonts
        self.score    = score
        self.nom_esq  = nom_esq
        self.inv_esq  = inv_esq
        self.nom_dret = nom_dret
        self.inv_dret = inv_dret
        cx = WIDTH // 2
        gap = 20
        bw  = 240
        bh  = 64
        self.btn_restart = Button(cx - gap // 2 - bw, 510, bw, bh,
                                  "Tornar a jugar", fonts["btn_menu"],
                                  BLUE_600, WHITE, hover_bg=BLUE_700, radius=12)
        self.btn_menu    = Button(cx + gap // 2,      510, bw, bh,
                                  "Menú principal", fonts["btn_menu"],
                                  WHITE, GRAY_700, border=GRAY_400,
                                  hover_bg=GRAY_100, radius=12)

    def handle(self, event):
        if self.btn_restart.is_clicked(event):
            return "restart"
        if self.btn_menu.is_clicked(event):
            return "menu"
        return None

    def draw(self, surface):
        surface.fill(WHITE)
        pygame.draw.line(surface, GRAY_200, (0, 64), (WIDTH, 64), 2)

        t1 = self.fonts["go_title"].render("Joc acabat!", True, GRAY_900)
        surface.blit(t1, t1.get_rect(center=(WIDTH // 2, 128)))

        sc = self.fonts["go_score"].render(f"Puntuació final: {self.score}", True, BLUE_600)
        surface.blit(sc, sc.get_rect(center=(WIDTH // 2, 202)))

        pygame.draw.line(surface, GRAY_200, (WIDTH // 2 - 220, 234),
                         (WIDTH // 2 + 220, 234), 2)

        info = self.fonts["go_info"].render("La comparació que ha fallat:", True, GRAY_500)
        surface.blit(info, info.get_rect(center=(WIDTH // 2, 262)))

        esq_any = self.fonts["go_detall"].render(
            f"{self.nom_esq.title()} → {format_any(self.inv_esq['any'])}", True, GRAY_700)
        surface.blit(esq_any, esq_any.get_rect(center=(WIDTH // 2, 308)))

        vs = self.fonts["go_vs"].render("VS", True, GRAY_400)
        surface.blit(vs, vs.get_rect(center=(WIDTH // 2, 352)))

        dret_any = self.fonts["go_detall"].render(
            f"{self.nom_dret.title()} → {format_any(self.inv_dret['any'])}", True, GRAY_700)
        surface.blit(dret_any, dret_any.get_rect(center=(WIDTH // 2, 396)))

        self.btn_restart.draw(surface)
        self.btn_menu.draw(surface)

# ─── CONSTRUCCIÓ DE FONTS ─────────────────────────────────────────────────────
def build_fonts():
    # Prioritzem fonts sense serifa amb bona llegibilitat
    candidates = ["Verdana", "Trebuchet MS", "Inter", "Arial", "Helvetica",
                  "DejaVu Sans", "FreeSans"]
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
        # ── Menú ──
        "menu_title":   f(72),
        "menu_sub":     f(26),
        "btn_menu":     f(26),
        "peu":          f(17),

        # ── Panells de joc ──
        "nom_panell":   f(34),
        "desc_panell":  f(20),
        "any_panell":   f(46),     # any gran dins el panell

        # ── HUD joc ──
        "score":        f(30),
        "instruccio":   f(18),
        "interrogant":  f(58),
        "btn_joc":      f(26),

        # ── Feedback ──
        "feedback":     f(62),     # "Correcte!" molt gran

        # ── Game Over ──
        "go_title":     f(64),
        "go_score":     f(36),
        "go_info":      f(22),
        "go_detall":    f(26),
        "go_vs":        f(32),
        "btn_small":    f(20),

        # ── Cronologia ──
        "cro_title":    f(30),
        "cro_any":      f(17),
        "cro_nom":      f(16),
        "popup_nom":    f(28),
        "popup_any":    f(24),
        "popup_desc":   f(20),
    }

# ─── BUCLE PRINCIPAL ──────────────────────────────────────────────────────────
def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Higher or Lower · Invents")
    clock  = pygame.time.Clock()
    fonts  = build_fonts()

    game_id, seed = inicialitzar()
    random.seed(seed)

    state      = "menu"
    menu       = MenuScreen(fonts)
    cronologia = CronologiaScreen(fonts)
    joc        = None
    gameover   = None

    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

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

            elif state == "cronologia":
                dest = cronologia.handle(event)
                if dest == "menu":
                    state = "menu"

            elif state == "joc":
                dest = joc.handle(event)
                if dest == "gameover":
                    gameover = GameOverScreen(
                        fonts, joc.score,
                        joc.nom_esq, joc.inv_esq,
                        joc.nom_dret, joc.inv_dret)
                    state = "gameover"
                elif dest == "menu":
                    state = "menu"

            elif state == "gameover":
                dest = gameover.handle(event)
                if dest == "restart":
                    game_id, seed = inicialitzar()
                    random.seed(seed)
                    joc   = JocScreen(fonts, game_id)
                    state = "joc"
                elif dest == "menu":
                    state = "menu"

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
