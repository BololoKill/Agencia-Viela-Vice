"""
Gera os personagens originais do escritório virtual com aparência realista.
Cada pessoa é montada sobre um esqueleto com proporção humana e recebe volume, luz e sombra por parte do corpo.

Uso: python ferramentas/gerar_personagens.py
"""
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

RAIZ = Path(__file__).resolve().parent.parent
SAIDA = RAIZ / "sprites" / "personagens"
L, A = 132, 206
S = 4
LS, AS = L * S, A * S
CONTORNO = (24, 17, 30)
OURO = (232, 186, 52)
BRANCO = (240, 238, 230)
PRETO = (30, 28, 36)
PELES = {"clara": (236, 190, 156), "media": (206, 150, 110), "morena": (158, 104, 70),
         "negra": (98, 62, 44), "oliva": (218, 170, 122)}


def hexa(texto):
    texto = texto.lstrip("#")
    return tuple(int(texto[i:i + 2], 16) for i in (0, 2, 4))


def tom(c, fator):
    return tuple(max(0, min(255, int(v * fator))) for v in c[:3])


def misturar(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def lerp(a, b, t):
    return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)


def suave(pontos, passos=7):
    """Arredonda um contorno fechado para evitar formas quadradas."""
    n = len(pontos)
    saida = []
    for i in range(n):
        p0, p1, p2, p3 = pontos[(i - 1) % n], pontos[i], pontos[(i + 1) % n], pontos[(i + 2) % n]
        for k in range(passos):
            t = k / passos
            saida.append(tuple(0.5 * (2 * p1[e] + (p2[e] - p0[e]) * t + (2 * p0[e] - 5 * p1[e] + 4 * p2[e] - p3[e]) * t * t
                                      + (3 * p1[e] - p0[e] - 3 * p2[e] + p3[e]) * t ** 3) * S for e in (0, 1)))
    return saida


def nova():
    m = Image.new("L", (LS, AS), 0)
    return m, ImageDraw.Draw(m)


def capsula(d, a, b, ra, rb, valor=255):
    ax, ay, bx, by, ra, rb = a[0] * S, a[1] * S, b[0] * S, b[1] * S, ra * S, rb * S
    ang = math.atan2(by - ay, bx - ax)
    nx, ny = -math.sin(ang), math.cos(ang)
    d.polygon([(ax + nx * ra, ay + ny * ra), (bx + nx * rb, by + ny * rb), (bx - nx * rb, by - ny * rb), (ax - nx * ra, ay - ny * ra)], fill=valor)
    d.ellipse((ax - ra, ay - ra, ax + ra, ay + ra), fill=valor)
    d.ellipse((bx - rb, by - rb, bx + rb, by + rb), fill=valor)


def oval(d, cx, cy, rx, ry, valor=255):
    d.ellipse(((cx - rx) * S, (cy - ry) * S, (cx + rx) * S, (cy + ry) * S), fill=valor)


class Tela:
    """Pinta cada parte com volume: luz vinda do alto à esquerda e sombra nas bordas."""

    def __init__(self):
        self.rgb = np.zeros((AS, LS, 3), dtype=np.float32)
        self.alfa = np.zeros((AS, LS), dtype=np.float32)

    def _aplicar(self, caixa, alfa, rgb):
        x0, y0, x1, y1 = caixa
        destino = self.alfa[y0:y1, x0:x1]
        final = alfa + destino * (1 - alfa)
        peso = np.divide(alfa, final, out=np.zeros_like(alfa), where=final > 0)[..., None]
        self.rgb[y0:y1, x0:x1] = rgb * peso + self.rgb[y0:y1, x0:x1] * (1 - peso)
        self.alfa[y0:y1, x0:x1] = final

    def pintar(self, mascara, cor, raio=2.6, borda=True, brilho=0.3):
        caixa = mascara.getbbox()
        if not caixa:
            return
        m = 14 * S
        caixa = (max(caixa[0] - m, 0), max(caixa[1] - m, 0), min(caixa[2] + m, LS), min(caixa[3] + m, AS))
        recorte = mascara.crop(caixa)
        if borda:
            grossa = np.asarray(recorte.filter(ImageFilter.MaxFilter(5)), dtype=np.float32) / 255
            self._aplicar(caixa, grossa * 0.82, np.array(CONTORNO, dtype=np.float32))
        r = raio * S
        desvio = max(1, int(r * 0.8))
        macio = recorte.filter(ImageFilter.GaussianBlur(r))
        b = np.asarray(macio, dtype=np.float32) / 255
        baixo = np.asarray(ImageChops.offset(recorte, desvio, desvio).filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255
        cima = np.asarray(ImageChops.offset(recorte, -desvio, -desvio).filter(ImageFilter.GaussianBlur(r)), dtype=np.float32) / 255
        luz = np.clip((cima - baixo) * 1.7, -1, 1)
        volume = np.clip((b - 0.5) * 2.2, 0, 1)
        fator = 0.72 + 0.28 * volume + brilho * luz
        base = np.array(cor[:3], dtype=np.float32)
        rgb = np.clip(base[None, None] * fator[..., None], 0, 255)
        rgb += (255 - rgb) * (np.clip(luz - 0.45, 0, 1)[..., None]) * 0.45
        self._aplicar(caixa, np.asarray(recorte, dtype=np.float32) / 255, rgb)

    def detalhe(self, desenhar, mascara=None):
        """Desenha sobre a parte já pintada, sem ultrapassar o contorno dela."""
        camada = Image.new("RGBA", (LS, AS), (0, 0, 0, 0))
        desenhar(ImageDraw.Draw(camada))
        arr = np.asarray(camada, dtype=np.float32)
        alfa = arr[..., 3] / 255
        if mascara is not None:
            alfa = alfa * (np.asarray(mascara, dtype=np.float32) / 255)
        self._aplicar((0, 0, LS, AS), alfa, arr[..., :3])

    def imagem(self):
        rgba = np.dstack([np.clip(self.rgb, 0, 255), np.clip(self.alfa * 255, 0, 255)]).astype(np.uint8)
        pequena = Image.fromarray(rgba).resize((L, A), Image.LANCZOS)
        r, g, b, a = pequena.split()
        nitida = Image.merge("RGB", (r, g, b)).filter(ImageFilter.UnsharpMask(radius=1.2, percent=70, threshold=2))
        return Image.merge("RGBA", (*nitida.split(), a))


def linha(d, pontos, cor, largura=1.0, alfa=255):
    d.line([(x * S, y * S) for x, y in pontos], fill=tuple(cor[:3]) + (alfa,), width=max(1, int(largura * S)), joint="curve")


def ponto(d, x, y, r, cor, alfa=255):
    d.ellipse(((x - r) * S, (y - r) * S, (x + r) * S, (y + r) * S), fill=tuple(cor[:3]) + (alfa,))


def caixa(d, x0, y0, x1, y1, cor, alfa=255):
    d.rectangle((x0 * S, y0 * S, x1 * S, y1 * S), fill=tuple(cor[:3]) + (alfa,))


# ---------- Esqueleto e poses ----------
BASE = dict(quadril=(66, 112), peito=(67, 70), pescoco=(68, 55), cabeca=(70, 35),
            ombro_l=(51, 70), cot_l=(47, 94), pul_l=(46, 117), ombro_p=(85, 70), cot_p=(90, 94), pul_p=(92, 117),
            anca_l=(58, 116), joe_l=(57, 152), tor_l=(56, 188), anca_p=(75, 116), joe_p=(76, 152), tor_p=(77, 188))
SENTADO = dict(quadril=(50, 120), peito=(53, 76), pescoco=(56, 61), cabeca=(59, 41), ombro_l=(39, 76), ombro_p=(68, 76),
               anca_l=(46, 124), joe_l=(84, 122), tor_l=(84, 176), anca_p=(58, 126), joe_p=(94, 125), tor_p=(94, 178))
POSES = {
    "andar1": {**BASE, "joe_p": (83, 150), "tor_p": (92, 187), "joe_l": (53, 151), "tor_l": (41, 186),
               "cot_p": (87, 95), "pul_p": (83, 118), "cot_l": (47, 95), "pul_l": (53, 117)},
    "andar2": {**BASE, "joe_p": (66, 151), "tor_p": (54, 187), "joe_l": (68, 150), "tor_l": (79, 187),
               "cot_p": (95, 94), "pul_p": (104, 115), "cot_l": (42, 95), "pul_l": (34, 115), "cabeca": (70, 36)},
    "sentado1": {**BASE, **SENTADO, "cot_l": (50, 100), "pul_l": (82, 100), "cot_p": (74, 102), "pul_p": (102, 102)},
    "sentado2": {**BASE, **SENTADO, "cot_l": (50, 101), "pul_l": (84, 103), "cot_p": (74, 103), "pul_p": (104, 99), "cabeca": (59, 42)},
    "sinuca1": {**BASE, "quadril": (52, 112), "peito": (80, 88), "pescoco": (93, 78), "cabeca": (105, 66), "ombro_l": (76, 84), "ombro_p": (90, 96),
                "cot_l": (100, 104), "pul_l": (118, 112), "cot_p": (74, 112), "pul_p": (60, 124), "anca_l": (44, 116), "joe_l": (40, 152), "tor_l": (30, 188),
                "anca_p": (60, 116), "joe_p": (68, 152), "tor_p": (76, 188)},
    "sinuca2": {**BASE, "quadril": (52, 112), "peito": (80, 88), "pescoco": (93, 78), "cabeca": (105, 66), "ombro_l": (76, 84), "ombro_p": (90, 96),
                "cot_l": (100, 104), "pul_l": (118, 112), "cot_p": (82, 114), "pul_p": (74, 122), "anca_l": (44, 116), "joe_l": (40, 152), "tor_l": (30, 188),
                "anca_p": (60, 116), "joe_p": (68, 152), "tor_p": (76, 188)},
    "beber1": {**BASE, "cot_p": (101, 82), "pul_p": (91, 56), "cabeca": (68, 34)},
    "beber2": {**BASE, "cot_p": (96, 96), "pul_p": (106, 78)},
    "pegar": {**BASE, "cot_p": (102, 80), "pul_p": (122, 76), "peito": (70, 70), "cabeca": (73, 36)},
    "dj1": {**BASE, "cot_p": (98, 90), "pul_p": (114, 102), "cot_l": (72, 92), "pul_l": (102, 104), "cabeca": (72, 37)},
    "dj2": {**BASE, "cot_p": (100, 62), "pul_p": (112, 36), "cot_l": (72, 92), "pul_l": (102, 104), "cabeca": (72, 34)},
    "jogar1": {**BASE, "cot_p": (98, 92), "pul_p": (116, 96), "cot_l": (70, 94), "pul_l": (104, 98)},
    "jogar2": {**BASE, "cot_p": (98, 90), "pul_p": (117, 90), "cot_l": (70, 92), "pul_l": (105, 102), "cabeca": (71, 36)},
    "servir1": {**BASE, "cot_p": (100, 88), "pul_p": (94, 62), "cot_l": (66, 92), "pul_l": (88, 66)},
    "servir2": {**BASE, "cot_p": (102, 84), "pul_p": (100, 52), "cot_l": (68, 86), "pul_l": (94, 56), "cabeca": (71, 36)},
    "deitado1": {**BASE, "cot_p": (104, 76), "pul_p": (96, 54), "cot_l": (64, 96), "pul_l": (100, 112)},
    "deitado2": {**BASE, "cot_p": (106, 62), "pul_p": (120, 44), "cot_l": (64, 96), "pul_l": (100, 112)},
    "deitado3": {**BASE, "cot_p": (106, 60), "pul_p": (121, 41), "cot_l": (64, 96), "pul_l": (100, 112)},
}


# ---------- Roupas e corpo ----------
def manga(p):
    tipo = p.get("topo", "camiseta")
    if tipo in ("regata", "top", "vestido"):
        return "nenhuma"
    return "curta" if tipo in ("camiseta", "floral", "havaiana", "polo", "listrada", "uniforme") else "longa"


def braco(t, p, g, lado):
    pele = PELES[p.get("pele", "media")]
    c1 = hexa(p.get("cor1", "#2563eb"))
    ombro, cot, pul = g["ombro_" + lado], g["cot_" + lado], g["pul_" + lado]
    fator = 0.84 if lado == "l" else 1.0
    porte = p.get("porte", 1.0)
    m, d = nova()
    capsula(d, ombro, cot, 6.6 * porte, 5.2 * porte)
    capsula(d, cot, pul, 5.2 * porte, 4.0 * porte)
    t.pintar(m, tom(pele, fator))
    ang = math.atan2(pul[1] - cot[1], pul[0] - cot[0])
    mao = (pul[0] + math.cos(ang) * 5, pul[1] + math.sin(ang) * 5)
    h, dh = nova()
    oval(dh, mao[0], mao[1], 5, 5.6)
    capsula(dh, mao, (mao[0] + math.cos(ang + 0.9) * 5, mao[1] + math.sin(ang + 0.9) * 5), 1.8, 1.5)
    t.pintar(h, tom(pele, fator), raio=1.4)
    tipo = manga(p)
    if tipo == "nenhuma":
        return
    s, ds = nova()
    if tipo == "curta":
        capsula(ds, ombro, lerp(ombro, cot, 0.62), 7.6 * porte, 6.6 * porte)
    else:
        capsula(ds, ombro, cot, 7.6 * porte, 6.2 * porte)
        capsula(ds, cot, lerp(cot, pul, 0.94), 6.2 * porte, 5.0 * porte)
    t.pintar(s, tom(c1, fator))
    if tipo == "longa":
        t.detalhe(lambda d2: linha(d2, [lerp(ombro, cot, 0.9), lerp(cot, pul, 0.15)], tom(c1, 0.55), 0.7, 150), s)
    if "relogio" in p.get("extras", ()) and lado == "p":
        t.detalhe(lambda d2: capsula_cor(d2, lerp(cot, pul, 0.96), pul, 5, OURO))


def capsula_cor(d, a, b, r, cor):
    d.line([(a[0] * S, a[1] * S), (b[0] * S, b[1] * S)], fill=tuple(cor) + (255,), width=int(r * 2 * S))


def sapato(t, p, tor, fator):
    tipo = p.get("sapato")
    c = tom(hexa(p.get("cor_sapato", "#f0eee6")), fator)
    x, y = tor
    if tipo == "chinelo":
        pele = tom(PELES[p.get("pele", "media")], fator)
        m, d = nova()
        d.polygon(suave([(x - 6, y + 1), (x + 5, y), (x + 15, y + 5), (x + 15, y + 8), (x - 6, y + 8)]), fill=255)
        t.pintar(m, pele, raio=1.5)
        s, ds = nova()
        ds.rounded_rectangle(((x - 8) * S, (y + 7) * S, (x + 17) * S, (y + 10) * S), 4, fill=255)
        t.pintar(s, c, raio=0.8)
        return
    m, d = nova()
    d.polygon(suave([(x - 7, y - 4), (x + 6, y - 4), (x + 12, y + 2), (x + 18, y + 5), (x + 18, y + 9), (x - 7, y + 9)]), fill=255)
    t.pintar(m, c, raio=1.8)
    t.detalhe(lambda d2: caixa(d2, x - 7, y + 7, x + 18, y + 10, (34, 30, 34) if tipo == "bota" else tom(BRANCO, fator)), m)
    if tipo != "bota":
        t.detalhe(lambda d2: [linha(d2, [(x + 3 + i * 3, y - 3 + i * 1.5), (x + 6 + i * 3, y + 1 + i)], BRANCO, 0.6, 210) for i in range(3)], m)


def perna(t, p, g, lado):
    tipo = p.get("baixo", "calca")
    fator = 0.82 if lado == "l" else 1.0
    pele = tom(PELES[p.get("pele", "media")], fator)
    c = tom(hexa(p.get("cor_baixo", "#1f2937")), fator)
    anca, joe, tor = g["anca_" + lado], g["joe_" + lado], g["tor_" + lado]
    porte = p.get("porte", 1.0)
    m, d = nova()
    capsula(d, anca, joe, 9.2 * porte, 6.8 * porte)
    capsula(d, joe, tor, 6.6 * porte, 4.8 * porte)
    if tipo in ("calca", "jeans"):
        t.pintar(m, c)
        t.detalhe(lambda d2: linha(d2, [lerp(anca, joe, 0.2), joe, lerp(joe, tor, 0.95)], tom(c, 1.3), 0.6, 120), m)
        if tipo == "jeans":
            t.detalhe(lambda d2: (linha(d2, [(joe[0] - 5, joe[1] - 2), (joe[0] + 5, joe[1] - 1)], (214, 226, 240), 1.0, 220),
                                  linha(d2, [(joe[0] - 4, joe[1] + 2), (joe[0] + 4, joe[1] + 3)], (214, 226, 240), 0.8, 190)), m)
    else:
        t.pintar(m, pele)
        if tipo == "bermuda":
            s, ds = nova()
            capsula(ds, anca, lerp(anca, joe, 0.92), 10 * porte, 8 * porte)
            t.pintar(s, c)
    sapato(t, p, tor, fator)


def tronco(t, p, g):
    tipo = p.get("topo", "camiseta")
    c1, c2 = hexa(p.get("cor1", "#2563eb")), hexa(p.get("cor2", "#f0eee6"))
    pele = PELES[p.get("pele", "media")]
    porte = p.get("porte", 1.0)
    fem = p.get("corpo") == "f"
    ol, op, al, ap = g["ombro_l"], g["ombro_p"], g["anca_l"], g["anca_p"]
    cintura = 4.5 if fem else 1.5
    pontos = [(ol[0] - 4 * porte, ol[1] - 3), lerp(ol, op, 0.32), lerp(ol, op, 0.68), (op[0] + 4 * porte, op[1] - 3),
              (lerp(op, ap, 0.58)[0] + 4 - cintura, lerp(op, ap, 0.58)[1]), (ap[0] + 5 + (3 if fem else 0), ap[1] + 3),
              (al[0] - 5 - (3 if fem else 0), al[1] + 3), (lerp(ol, al, 0.58)[0] - 4 + cintura, lerp(ol, al, 0.58)[1])]
    m, d = nova()
    d.polygon(suave(pontos), fill=255)
    if tipo in ("terno", "jaleco", "couro"):
        d.polygon([((al[0] - 6) * S, (al[1] - 8) * S), ((ap[0] + 6) * S, (ap[1] - 8) * S), ((ap[0] + 8) * S, (ap[1] + 13) * S), ((al[0] - 8) * S, (al[1] + 13) * S)], fill=255)
    base = pele if tipo == "top" else c1
    t.pintar(m, base, raio=4.2)
    cx = lerp(g["pescoco"], g["quadril"], 0.08)[0] + 3
    y0 = g["pescoco"][1] + 6
    y1 = g["quadril"][1] + 4

    def detalhes(dd):
        if tipo == "top":
            caixa(dd, 30, y0 - 4, 110, y0 + 22, c1)
        elif tipo == "regata":
            ponto(dd, cx, y0 - 3, 11, pele)
            caixa(dd, ol[0] - 8, y0 - 8, ol[0] + 6, y0 + 7, pele, 0)
        elif tipo in ("terno", "colete"):
            dd.polygon([((cx - 9) * S, y0 * S), ((cx + 11) * S, y0 * S), ((cx + 2) * S, (y0 + 30) * S)], fill=BRANCO + (255,))
            dd.polygon([((cx - 2) * S, (y0 + 1) * S), ((cx + 5) * S, (y0 + 1) * S), ((cx + 5) * S, (y0 + 23) * S), ((cx + 1.5) * S, (y0 + 29) * S), ((cx - 2) * S, (y0 + 23) * S)], fill=c2 + (255,))
            dd.polygon([((cx - 11) * S, (y0 - 2) * S), ((cx - 3) * S, (y0 + 2) * S), ((cx + 1) * S, (y0 + 32) * S), ((cx - 8) * S, (y0 + 14) * S)], fill=tom(c1, 1.25) + (255,))
            dd.polygon([((cx + 13) * S, (y0 - 2) * S), ((cx + 7) * S, (y0 + 2) * S), ((cx + 3) * S, (y0 + 32) * S), ((cx + 13) * S, (y0 + 14) * S)], fill=tom(c1, 1.25) + (255,))
            linha(dd, [(cx + 2, y0 + 31), (cx + 2, y1 + 8)], tom(c1, 0.55), 0.8, 230)
            ponto(dd, cx + 5, y0 + 36, 1.1, tom(c1, 0.5))
            caixa(dd, cx + 9, y0 + 12, cx + 15, y0 + 14, BRANCO, 220)
        elif tipo == "moletom":
            ponto(dd, cx + 1, y0 - 2, 13, tom(c1, 0.8))
            ponto(dd, cx + 2, y0 - 2, 8, tom(c1, 0.55))
            dd.rounded_rectangle(((cx - 12) * S, (y1 - 18) * S, (cx + 13) * S, (y1 - 3) * S), 10, fill=tom(c1, 0.82) + (255,))
            linha(dd, [(cx - 3, y0 + 3), (cx - 3, y0 + 18)], c2, 0.8)
            linha(dd, [(cx + 6, y0 + 3), (cx + 6, y0 + 16)], c2, 0.8)
        elif tipo in ("floral", "havaiana"):
            if tipo == "havaiana":
                caixa(dd, cx - 6, y0 - 3, cx + 7, y1 + 3, c2)
            else:
                dd.polygon([((cx - 7) * S, y0 * S), ((cx + 9) * S, y0 * S), ((cx + 1) * S, (y0 + 12) * S)], fill=pele + (255,))
                linha(dd, [(cx + 1, y0 + 12), (cx + 1, y1 + 3)], tom(c1, 0.6), 0.7)
            for i, (a, b) in enumerate([(-18, 12), (-11, 26), (-17, 37), (11, 9), (17, 21), (12, 34), (-6, 42), (15, 45)]):
                flor = OURO if i % 2 else c2
                for ang in range(0, 360, 72):
                    ponto(dd, cx + a + math.cos(math.radians(ang)) * 2.4, y0 + b + math.sin(math.radians(ang)) * 2.4, 1.5, flor)
                ponto(dd, cx + a, y0 + b, 1.1, tom(c1, 0.5))
        elif tipo == "jaqueta":
            linha(dd, [(cx + 1, y0), (cx + 1, y1 + 4)], c2, 1.0)
            caixa(dd, cx - 13, y0 - 5, cx + 15, y0 + 2, tom(c1, 0.8))
            caixa(dd, 30, y1 - 4, 110, y1 + 5, tom(c1, 0.68))
            for lado in (-13, 9):
                caixa(dd, cx + lado, y0 + 26, cx + lado + 6, y0 + 28, tom(c1, 0.6))
        elif tipo == "couro":
            dd.polygon([((cx - 10) * S, y0 * S), ((cx + 12) * S, y0 * S), ((cx + 1) * S, (y0 + 20) * S)], fill=c2 + (255,))
            linha(dd, [(cx + 2, y0 + 19), (cx + 8, y1 + 8)], (205, 208, 218), 1.0)
            linha(dd, [(cx - 16, y0 + 12), (cx - 4, y0 + 20)], (205, 208, 218), 0.8)
            for i in range(5):
                ponto(dd, cx - 18, y0 + 4 + i * 9, 0.9, (214, 218, 226))
        elif tipo == "listrada":
            for b in range(4, 62, 9):
                caixa(dd, 30, y0 + b, 110, y0 + b + 4, c2)
        elif tipo == "polo":
            dd.polygon([((cx - 8) * S, (y0 - 2) * S), ((cx + 10) * S, (y0 - 2) * S), ((cx + 1) * S, (y0 + 9) * S)], fill=c2 + (255,))
            linha(dd, [(cx + 1, y0 + 8), (cx + 1, y0 + 17)], tom(c1, 0.55), 0.8)
        elif tipo == "uniforme":
            linha(dd, [(cx + 1, y0), (cx + 1, y1)], tom(c1, 0.6), 1.0)
            caixa(dd, cx - 15, y0 + 9, cx - 6, y0 + 16, tom(c1, 0.7))
            ponto(dd, cx + 10, y0 + 11, 3.2, OURO)
            caixa(dd, 30, y1 - 6, 110, y1 + 1, PRETO)
            caixa(dd, cx - 3, y1 - 7, cx + 6, y1 + 2, OURO)
        elif tipo == "jaleco":
            dd.polygon([((cx - 7) * S, y0 * S), ((cx + 9) * S, y0 * S), ((cx + 1) * S, (y0 + 22) * S)], fill=c2 + (255,))
            linha(dd, [(cx + 1, y0 + 22), (cx + 1, y1 + 10)], tom(c1, 0.7), 0.8)
        elif tipo == "camiseta":
            dd.arc(((cx - 8) * S, (y0 - 8) * S, (cx + 10) * S, (y0 + 6) * S), 15, 165, fill=tom(c1, 0.6) + (255,), width=S * 2)
            dd.polygon([((cx - 9) * S, (y0 + 13) * S), ((cx + 11) * S, (y0 + 13) * S), ((cx + 1) * S, (y0 + 32) * S)], fill=c2 + (255,))
        elif tipo == "vestido":
            caixa(dd, 30, y1 - 8, 110, y1 - 5, c2)
            ponto(dd, cx + 1, y0 - 3, 8, pele)
        for f in range(3):
            linha(dd, [(cx - 18 + f * 3, y1 - 12 - f * 7), (cx - 8 + f * 3, y1 - 8 - f * 7)], tom(base, 0.62), 0.7, 90)
    t.detalhe(detalhes, m)
    extras = p.get("extras", ())
    if "corrente" in extras:
        t.detalhe(lambda dd: (dd.arc(((cx - 11) * S, (y0 - 16) * S, (cx + 13) * S, (y0 + 22) * S), 25, 155, fill=OURO + (255,), width=int(1.3 * S)), ponto(dd, cx + 1, y0 + 23, 3.4, OURO), ponto(dd, cx + 1, y0 + 23, 1.6, tom(OURO, 0.65))))
    if "cracha" in extras:
        t.detalhe(lambda dd: (linha(dd, [(cx - 5, y0), (cx + 4, y0 + 18)], (34, 211, 238), 0.9), caixa(dd, cx, y0 + 18, cx + 11, y0 + 31, BRANCO), caixa(dd, cx + 2, y0 + 20, cx + 6, y0 + 25, (120, 130, 150))))
    if "camera" in extras:
        t.detalhe(lambda dd: (caixa(dd, cx - 9, y0 + 24, cx + 11, y0 + 38, PRETO), ponto(dd, cx + 1, y0 + 31, 5.6, (88, 96, 114)), ponto(dd, cx + 1, y0 + 31, 3, (22, 26, 34))))


def saia(t, p, g):
    tipo = p.get("baixo")
    al, ap = g["anca_l"], g["anca_p"]
    if tipo != "saia" and p.get("topo") != "vestido":
        return
    c = hexa(p.get("cor_baixo", "#1f2937")) if tipo == "saia" else hexa(p.get("cor1", "#2563eb"))
    queda = 25 if tipo == "saia" else 36
    m, d = nova()
    d.polygon([((al[0] - 7) * S, (al[1] - 7) * S), ((ap[0] + 7) * S, (ap[1] - 7) * S), ((ap[0] + 12) * S, (ap[1] + queda) * S), ((al[0] - 12) * S, (al[1] + queda) * S)], fill=255)
    t.pintar(m, c, raio=4)
    t.detalhe(lambda dd: [linha(dd, [(al[0] + i * 8, al[1]), (al[0] - 4 + i * 11, al[1] + queda)], tom(c, 0.62), 0.8, 150) for i in range(4)], m)


# ---------- Cabeça ----------
def cabelo_atras(t, p, hx, hy):
    estilo = p.get("cabelo", "curto")
    c = hexa(p.get("cor_cabelo", "#2a1c14"))
    m, d = nova()
    if estilo == "longo":
        d.polygon(suave([(hx - 16, hy - 10), (hx + 7, hy - 15), (hx + 8, hy + 16), (hx + 1, hy + 42), (hx - 19, hy + 44)]), fill=255)
    elif estilo == "afro":
        oval(d, hx - 1, hy - 7, 24, 23)
    elif estilo == "rabo":
        d.polygon(suave([(hx - 13, hy - 12), (hx - 27, hy - 7), (hx - 32, hy + 18), (hx - 26, hy + 34), (hx - 17, hy + 12)]), fill=255)
    elif estilo == "chanel":
        d.polygon(suave([(hx - 16, hy - 12), (hx + 16, hy - 12), (hx + 17, hy + 15), (hx - 18, hy + 17)]), fill=255)
    elif estilo == "coque":
        oval(d, hx - 4, hy - 23, 9, 8)
    elif estilo == "dread":
        for i in range(5):
            capsula(d, (hx - 15 + i * 3, hy - 6), (hx - 19 + i * 3, hy + 32), 2.6, 2.2)
    elif estilo == "trancas":
        for x in (hx - 16, hx + 15):
            for k in range(6):
                oval(d, x, hy + 4 + k * 6.5, 3.8, 3.8)
    elif estilo == "maria":
        oval(d, hx - 19, hy - 7, 9, 10)
        oval(d, hx + 18, hy - 7, 9, 10)
    else:
        return
    t.pintar(m, tom(c, 0.88), raio=3)
    t.detalhe(lambda dd: [linha(dd, [(hx - 20 + i * 5, hy - 12), (hx - 23 + i * 5, hy + 30)], tom(c, 1.5), 0.6, 80) for i in range(9)], m)


def cabelo_frente(t, p, hx, hy):
    estilo = p.get("cabelo", "curto")
    c = hexa(p.get("cor_cabelo", "#2a1c14"))
    if estilo == "careca":
        return
    m, d = nova()
    if estilo == "raspado":
        oval(d, hx, hy - 7, 15, 13)
        d.rectangle(((hx - 9) * S, (hy - 8) * S, (hx + 18) * S, (hy + 12) * S), fill=0)
        d.rectangle(((hx - 18) * S, (hy + 1) * S, (hx + 18) * S, (hy + 12) * S), fill=0)
        t.pintar(m, misturar(c, PELES[p.get("pele", "media")], 0.28), raio=2, borda=False, brilho=0.12)
        return
    if estilo == "moicano":
        capsula(d, (hx - 12, hy - 9), (hx + 7, hy - 19), 3.5, 4)
        d.polygon([((hx - 15) * S, (hy - 12) * S), ((hx - 4) * S, (hy - 28) * S), ((hx + 11) * S, (hy - 26) * S), ((hx + 11) * S, (hy - 17) * S)], fill=255)
    elif estilo == "espetado":
        pts = [(hx - 16, hy - 5)]
        for i in range(6):
            pts += [(hx - 16 + i * 6, hy - 24 - (i % 2) * 3), (hx - 12 + i * 6, hy - 14)]
        pts += [(hx + 17, hy - 7), (hx + 3, hy - 10)]
        d.polygon([(x * S, y * S) for x, y in pts], fill=255)
    elif estilo == "cacheado":
        for i in range(7):
            oval(d, hx - 15 + i * 5, hy - 15 - (i % 2) * 3, 6.5, 6.5)
        oval(d, hx - 14, hy - 7, 5, 6)
    elif estilo == "afro":
        oval(d, hx, hy - 12, 15.5, 8)
    else:
        oval(d, hx, hy - 8, 16, 14)
        d.rectangle(((hx - 8) * S, (hy - 7) * S, (hx + 20) * S, (hy + 14) * S), fill=0)
        d.rectangle(((hx - 20) * S, (hy + 3) * S, (hx + 20) * S, (hy + 14) * S), fill=0)
        if estilo == "liso":
            d.polygon(suave([(hx - 8, hy - 16), (hx + 12, hy - 16), (hx + 17, hy - 7), (hx + 8, hy - 9), (hx - 4, hy - 7)], passos=4), fill=255)
        if estilo in ("longo", "chanel"):
            d.polygon(suave([(hx + 8, hy - 14), (hx + 17, hy - 8), (hx + 17, hy + 13), (hx + 12, hy + 6)], passos=4), fill=255)
    t.pintar(m, c, raio=2.2)
    t.detalhe(lambda dd: ([linha(dd, [(hx - 12 + i * 5, hy - 21), (hx - 15 + i * 6, hy - 6)], tom(c, 0.55), 0.6, 170) for i in range(6)],
                          [linha(dd, [(hx - 9 + i * 7, hy - 20), (hx - 11 + i * 8, hy - 11)], misturar(c, BRANCO, 0.4), 0.6, 130) for i in range(3)]), m)


def chapeu(t, p, hx, hy):
    tipo = p.get("chapeu")
    if not tipo:
        return
    c = hexa(p.get("cor_chapeu", "#dc2626"))
    m, d = nova()
    if tipo == "bone":
        oval(d, hx, hy - 12, 16.5, 10)
        t.pintar(m, c, raio=3)
        a, da = nova()
        da.polygon(suave([(hx + 4, hy - 9), (hx + 17, hy - 12), (hx + 31, hy - 7), (hx + 29, hy - 4), (hx + 8, hy - 5)], passos=4), fill=255)
        t.pintar(a, tom(c, 0.75), raio=1.4)
    elif tipo == "balde":
        d.polygon(suave([(hx - 21, hy - 7), (hx - 12, hy - 25), (hx + 12, hy - 25), (hx + 22, hy - 7)], passos=4), fill=255)
        t.pintar(m, c, raio=3)
    elif tipo == "fedora":
        oval(d, hx, hy - 10, 27, 5.5)
        t.pintar(m, tom(c, 0.85), raio=2)
        a, da = nova()
        da.polygon(suave([(hx - 15, hy - 11), (hx - 12, hy - 27), (hx, hy - 24), (hx + 12, hy - 27), (hx + 15, hy - 11)], passos=4), fill=255)
        t.pintar(a, c, raio=3)
        t.detalhe(lambda dd: caixa(dd, hx - 17, hy - 16, hx + 17, hy - 11, OURO), a)
    elif tipo == "gorro":
        oval(d, hx, hy - 12, 17, 13)
        t.pintar(m, c, raio=3)
        t.detalhe(lambda dd: [linha(dd, [(hx - 15 + i * 4, hy - 22), (hx - 15 + i * 4, hy - 5)], tom(c, 0.65), 0.7, 170) for i in range(9)], m)
    elif tipo == "bandana":
        oval(d, hx, hy - 10, 16.5, 11)
        d.rectangle(((hx - 20) * S, (hy - 5) * S, (hx + 20) * S, (hy + 10) * S), fill=0)
        d.polygon([((hx - 15) * S, (hy - 9) * S), ((hx - 29) * S, (hy - 15) * S), ((hx - 28) * S, (hy - 2) * S)], fill=255)
        t.pintar(m, c, raio=2)
        t.detalhe(lambda dd: [ponto(dd, hx - 12 + i * 5, hy - 13 + (i % 2) * 4, 0.9, BRANCO) for i in range(6)], m)
    elif tipo == "viseira":
        d.rectangle(((hx - 15) * S, (hy - 14) * S, (hx + 15) * S, (hy - 9) * S), fill=255)
        t.pintar(m, c, raio=1.2)
        a, da = nova()
        da.polygon(suave([(hx + 4, hy - 11), (hx + 30, hy - 9), (hx + 29, hy - 5), (hx + 6, hy - 7)], passos=4), fill=255)
        t.pintar(a, tom(c, 0.75), raio=1.2)
    elif tipo == "policia":
        d.polygon(suave([(hx - 20, hy - 21), (hx + 20, hy - 22), (hx + 15, hy - 9), (hx - 15, hy - 9)], passos=4), fill=255)
        t.pintar(m, c, raio=3)
        a, da = nova()
        da.polygon(suave([(hx + 2, hy - 10), (hx + 25, hy - 10), (hx + 24, hy - 6), (hx + 4, hy - 7)], passos=4), fill=255)
        t.pintar(a, PRETO, raio=1)
        t.detalhe(lambda dd: ponto(dd, hx + 3, hy - 16, 3, OURO), m)
    elif tipo == "capacete":
        oval(d, hx, hy - 4, 21, 22)
        t.pintar(m, c, raio=4)
        t.detalhe(lambda dd: dd.rounded_rectangle(((hx - 3) * S, (hy - 8) * S, (hx + 20) * S, (hy + 5) * S), 14, fill=(30, 200, 230, 235)), m)


def cabeca(t, p, g):
    hx, hy = g["cabeca"]
    pele = PELES[p.get("pele", "media")]
    extras = p.get("extras", ())
    cor_cabelo = hexa(p.get("cor_cabelo", "#2a1c14"))
    cabelo_atras(t, p, hx, hy)
    pescoco, dp = nova()
    capsula(dp, g["pescoco"], (hx - 2, hy + 12), 6.5 * p.get("porte", 1.0), 6.2)
    t.pintar(pescoco, tom(pele, 0.86))
    o, do = nova()
    oval(do, hx - 14.5, hy + 1, 3.2, 5)
    t.pintar(o, tom(pele, 0.88), raio=1.2)
    m, d = nova()
    d.polygon(suave([(hx - 14, hy - 9), (hx - 6, hy - 18), (hx + 8, hy - 18), (hx + 15, hy - 9), (hx + 15, hy + 3), (hx + 12, hy + 12),
                     (hx + 5, hy + 18), (hx - 3, hy + 17), (hx - 12, hy + 9)], passos=6), fill=255)
    t.pintar(m, pele, raio=4.2, brilho=0.34)

    def rosto(dd):
        sombra = tom(pele, 0.68)
        ponto(dd, hx + 11, hy + 6, 4.2, misturar(pele, (222, 92, 92), 0.45), 80)
        ponto(dd, hx - 3, hy + 6, 4.2, misturar(pele, (222, 92, 92), 0.45), 70)
        linha(dd, [(hx + 8.5, hy - 2), (hx + 11.5, hy + 4), (hx + 8, hy + 6)], sombra, 0.9, 230)
        labio = (176, 44, 72) if "batom" in extras else tom(pele, 0.5)
        dd.polygon([((hx + 3) * S, (hy + 10.5) * S), ((hx + 7) * S, (hy + 9.5) * S), ((hx + 12) * S, (hy + 10.5) * S), ((hx + 7.5) * S, (hy + 13) * S)], fill=labio + (255,))
        linha(dd, [(hx + 3, hy + 10.7), (hx + 12, hy + 10.7)], tom(pele, 0.34), 0.5)
        if "escuros" not in extras:
            for ex, rx in ((hx + 2, 3.4), (hx + 13, 2.6)):
                dd.ellipse(((ex - rx) * S, (hy - 3.4) * S, (ex + rx) * S, (hy + 0.8) * S), fill=BRANCO + (255,))
                ponto(dd, ex + 0.9, hy - 1.3, 1.9, hexa(p.get("cor_olho", "#3a2618")))
                ponto(dd, ex + 1, hy - 1.3, 1.0, (12, 10, 14))
                ponto(dd, ex + 0.3, hy - 2.1, 0.45, BRANCO)
                linha(dd, [(ex - rx, hy - 2.5), (ex, hy - 3.8), (ex + rx, hy - 2.4)], (34, 22, 20), 0.8)
            sobrancelha = tom(cor_cabelo, 0.8) if p.get("cabelo") != "careca" else tom(pele, 0.42)
            linha(dd, [(hx - 2, hy - 6), (hx + 2, hy - 7.6), (hx + 6, hy - 6.4)], sobrancelha, 1.3)
            linha(dd, [(hx + 10, hy - 6.4), (hx + 13, hy - 7.6), (hx + 16, hy - 6)], sobrancelha, 1.2)
        if "barba" in extras:
            dd.polygon([(c[0], c[1]) for c in suave([(hx - 12, hy + 3), (hx - 8, hy + 8), (hx + 2, hy + 8), (hx + 8, hy + 8), (hx + 14, hy + 5), (hx + 11, hy + 13), (hx + 5, hy + 19), (hx - 3, hy + 18), (hx - 12, hy + 10)], passos=3)], fill=cor_cabelo + (235,))
            linha(dd, [(hx + 3, hy + 11), (hx + 12, hy + 11)], labio, 1.3)
        if "bigode" in extras or "barba" in extras:
            linha(dd, [(hx + 1.5, hy + 8.6), (hx + 7.5, hy + 7.4), (hx + 13.5, hy + 8.4)], cor_cabelo, 1.7)
    t.detalhe(rosto, m)
    if "brinco" in extras:
        t.detalhe(lambda dd: ponto(dd, hx - 15, hy + 7, 1.7, OURO))
    cabelo_frente(t, p, hx, hy)
    chapeu(t, p, hx, hy)
    if "escuros" in extras:
        def oculos(dd):
            aro = OURO if "ouro" in extras else (16, 15, 20)
            for ex, ex2 in ((hx - 3, hx + 7), (hx + 9, hx + 16.5)):
                dd.rounded_rectangle((ex * S, (hy - 5) * S, ex2 * S, (hy + 2) * S), 8, fill=(14, 14, 20, 255), outline=aro + (255,), width=S)
                linha(dd, [(ex + 1.5, hy - 3.5), (ex + 4, hy - 3.5)], (130, 215, 240), 0.7)
            linha(dd, [(hx - 14, hy - 3), (hx - 3, hy - 3)], aro, 1.0)
            linha(dd, [(hx + 7, hy - 3.5), (hx + 9, hy - 3.5)], aro, 1.0)
        t.detalhe(oculos)
    elif "oculos" in extras:
        def oculos(dd):
            for ex, ex2 in ((hx - 3, hx + 7), (hx + 9, hx + 16.5)):
                dd.rounded_rectangle((ex * S, (hy - 5) * S, ex2 * S, (hy + 2) * S), 8, outline=(26, 26, 32, 255), width=S)
            linha(dd, [(hx - 14, hy - 3), (hx - 3, hy - 3)], (26, 26, 32), 0.9)
            linha(dd, [(hx + 7, hy - 3.5), (hx + 9, hy - 3.5)], (26, 26, 32), 0.9)
        t.detalhe(oculos)
    if "fones" in extras:
        cor_fone = hexa(p.get("cor_fone", "#ff2fa8"))
        t.detalhe(lambda dd: dd.arc(((hx - 18) * S, (hy - 24) * S, (hx + 12) * S, (hy + 10) * S), 170, 345, fill=(30, 30, 36, 255), width=int(2.2 * S)))
        f, df = nova()
        oval(df, hx - 15, hy + 1, 5.5, 7.5)
        t.pintar(f, cor_fone, raio=1.6)


# ---------- Objetos nas mãos ----------
def objetos(t, pose, g):
    pul = g["pul_p"]
    if pose.startswith("sinuca"):
        avanco = 0 if pose == "sinuca1" else 9
        m, d = nova()
        capsula(d, (44 + avanco, 132), (128 + avanco * 0.2, 110), 1.8, 0.9)
        t.pintar(m, (178, 128, 74), raio=0.8)
    elif pose in ("beber1", "beber2"):
        m, d = nova()
        capsula(d, (pul[0] + 2, pul[1] + 2), (pul[0] + 6, pul[1] - 13), 4.3, 2.0)
        t.pintar(m, (34, 104, 70), raio=1.2)
        t.detalhe(lambda dd: caixa(dd, pul[0], pul[1] - 3, pul[0] + 8, pul[1] + 4, (236, 224, 190)), m)
    elif pose.startswith("servir"):
        m, d = nova()
        d.rounded_rectangle(((pul[0] - 3) * S, (pul[1] - 15) * S, (pul[0] + 8) * S, (pul[1] + 4) * S), 12, fill=255)
        t.pintar(m, (196, 204, 216), raio=1.8, brilho=0.55)
    elif pose == "deitado1":
        t.detalhe(lambda dd: (linha(dd, [(pul[0] + 2, pul[1] - 6), (pul[0] + 11, pul[1] - 13)], BRANCO, 1.6), ponto(dd, pul[0] + 12, pul[1] - 14, 1.6, (255, 120, 30))))
    elif pose in ("deitado2", "deitado3"):
        tela = (34, 230, 255) if pose == "deitado2" else (255, 122, 217)
        m, d = nova()
        d.rounded_rectangle(((pul[0] - 1) * S, (pul[1] - 14) * S, (pul[0] + 9) * S, (pul[1] + 4) * S), 8, fill=255)
        t.pintar(m, (20, 20, 26), raio=0.8)
        t.detalhe(lambda dd: caixa(dd, pul[0] + 1, pul[1] - 12, pul[0] + 7, pul[1] + 2, tela))


def cadeira(t):
    escuro = (46, 42, 60)
    m, d = nova()
    d.polygon(suave([(24, 40), (37, 37), (39, 96), (26, 100)], passos=5), fill=255)
    t.pintar(m, (58, 42, 96), raio=3.6)
    a, da = nova()
    da.polygon(suave([(24, 122), (76, 124), (76, 134), (24, 134)], passos=4), fill=255)
    t.pintar(a, (64, 48, 104), raio=2.6)
    h, dh = nova()
    capsula(dh, (48, 134), (48, 172), 3.2, 3.2)
    t.pintar(h, escuro, raio=1.2)
    b, db = nova()
    for fim in ((22, 186), (76, 186), (40, 192), (60, 192)):
        capsula(db, (48, 172), fim, 2.4, 2.0)
        oval(db, fim[0], fim[1] + 2, 3, 3)
    t.pintar(b, escuro, raio=1)


def desenhar(p, pose):
    g = POSES[pose]
    t = Tela()
    if pose.startswith("sentado"):
        cadeira(t)
    if "mochila" in p.get("extras", ()):
        m, d = nova()
        d.polygon(suave([(g["ombro_l"][0] - 12, 66), (g["ombro_l"][0] + 8, 62), (g["ombro_l"][0] + 8, 110), (g["ombro_l"][0] - 13, 108)], passos=4), fill=255)
        t.pintar(m, hexa(p.get("cor_mochila", "#f97316")), raio=3)
    braco(t, p, g, "l")
    perna(t, p, g, "l")
    perna(t, p, g, "p")
    if p.get("baixo", "calca") in ("calca", "jeans", "bermuda"):
        m, d = nova()
        capsula(d, g["anca_l"], g["anca_p"], 10.5 * p.get("porte", 1.0), 10.5 * p.get("porte", 1.0))
        t.pintar(m, hexa(p.get("cor_baixo", "#1f2937")), raio=4)
    saia(t, p, g)
    tronco(t, p, g)
    cabeca(t, p, g)
    if pose.startswith(("sinuca", "servir", "beber")):
        objetos(t, pose, g)
    braco(t, p, g, "p")
    if not pose.startswith(("sinuca", "servir", "beber")):
        objetos(t, pose, g)
    return t.imagem()


# ---------- Elenco original ----------
F = {"corpo": "f"}
ELENCO = {
    "dr_ricardo": dict(pele="clara", cabelo="liso", cor_cabelo="#6a6e78", topo="terno", cor1="#232838", cor2="#b91c1c", baixo="calca", cor_baixo="#1d2130", cor_sapato="#2a1a10", extras=("barba", "relogio")),
    "camila": dict(F, pele="oliva", cabelo="longo", cor_cabelo="#7c2c1c", topo="terno", cor1="#0f7f7a", cor2="#e8b93a", baixo="saia", cor_baixo="#163a42", cor_sapato="#6e1b39", extras=("batom", "brinco")),
    "bruno": dict(pele="negra", cabelo="afro", cor_cabelo="#17110d", topo="moletom", cor1="#1e4fbf", cor2="#f0eee6", baixo="jeans", cor_baixo="#2c4674", cor_sapato="#ecebe2", extras=("fones",), cor_fone="#16b8d8"),
    "lucas": dict(pele="clara", cabelo="espetado", cor_cabelo="#6d4bc0", topo="camiseta", cor1="#1b1b24", cor2="#d6287f", baixo="jeans", cor_baixo="#3e4456", cor_sapato="#b91c1c", extras=("corrente",)),
    "mariana": dict(F, pele="media", cabelo="chanel", cor_cabelo="#b3202f", topo="jaqueta", cor1="#526e3e", cor2="#c9b458", baixo="calca", cor_baixo="#23232e", cor_sapato="#1a1a22", extras=("oculos", "batom")),
    "caio": dict(pele="morena", cabelo="raspado", cor_cabelo="#1b1410", topo="polo", cor1="#17406f", cor2="#d7e6f2", baixo="calca", cor_baixo="#40372a", cor_sapato="#4b3621", extras=("oculos", "barba", "cracha")),
    "beatriz": dict(F, pele="clara", cabelo="rabo", cor_cabelo="#c9973a", chapeu="bone", cor_chapeu="#d9630f", topo="moletom", cor1="#e6b71a", cor2="#7c2d12", baixo="bermuda", cor_baixo="#39465a", cor_sapato="#1e9d4c", extras=("brinco",)),
    "thiago": dict(pele="media", cabelo="cacheado", cor_cabelo="#4a2c17", topo="floral", cor1="#c93a80", cor2="#fff0dc", baixo="bermuda", cor_baixo="#b89f72", cor_sapato="#2256c9", extras=("bigode",)),
    "barista": dict(F, pele="morena", cabelo="coque", cor_cabelo="#201510", topo="colete", cor1="#3f2619", cor2="#c92c86", baixo="calca", cor_baixo="#1b1b22", cor_sapato="#1b1b22", extras=("batom",)),
    "seguranca": dict(porte=1.16, pele="negra", cabelo="careca", topo="terno", cor1="#14141a", cor2="#14141a", baixo="calca", cor_baixo="#14141a", cor_sapato="#121216", extras=("escuros", "barba")),
    "barman": dict(pele="oliva", cabelo="liso", cor_cabelo="#191512", topo="colete", cor1="#14532d", cor2="#e8b93a", baixo="calca", cor_baixo="#1a1a20", cor_sapato="#17171d", extras=("bigode", "relogio")),
    "dj": dict(pele="media", cabelo="moicano", cor_cabelo="#18aebf", topo="regata", cor1="#6d33cf", baixo="jeans", cor_baixo="#232c3b", cor_sapato="#e0b312", extras=("fones", "corrente", "escuros"), cor_fone="#2fce7f"),
    "sinuca1": dict(pele="oliva", cabelo="liso", cor_cabelo="#1b1b22", chapeu="fedora", cor_chapeu="#6e1b39", topo="colete", cor1="#561a39", cor2="#e0b312", baixo="calca", cor_baixo="#2b1b2e", cor_sapato="#e8e6dc", extras=("bigode", "relogio")),
    "sinuca2": dict(F, pele="clara", cabelo="trancas", cor_cabelo="#c9628e", topo="top", cor1="#1ba8c4", baixo="saia", cor_baixo="#312e81", cor_sapato="#ecebe2", extras=("escuros", "brinco", "batom")),
    "p1": dict(pele="clara", cabelo="curto", cor_cabelo="#b67d36", chapeu="balde", cor_chapeu="#e6d58a", topo="havaiana", cor1="#178a42", cor2="#efece0", baixo="bermuda", cor_baixo="#d9630f", sapato="chinelo", cor_sapato="#1ba8c4", extras=("camera", "escuros")),
    "p2": dict(pele="negra", cabelo="dread", cor_cabelo="#2b1a10", topo="regata", cor1="#dfb315", baixo="bermuda", cor_baixo="#b91c1c", sapato="chinelo", cor_sapato="#1b1b22", extras=("corrente",)),
    "p3": dict(F, pele="morena", cabelo="longo", cor_cabelo="#120d0a", chapeu="viseira", cor_chapeu="#d6287f", topo="vestido", cor1="#df5f76", cor2="#fff0dc", baixo="pernas", sapato="chinelo", cor_sapato="#e0a81c", extras=("escuros", "batom", "brinco")),
    "p4": dict(pele="oliva", cabelo="curto", cor_cabelo="#111016", topo="floral", cor1="#0c8fc9", cor2="#e8cf3c", baixo="calca", cor_baixo="#ece9dd", cor_sapato="#8a5f38", extras=("escuros", "relogio", "ouro")),
    "p5": dict(F, pele="clara", cabelo="maria", cor_cabelo="#c9628e", topo="listrada", cor1="#efece0", cor2="#6d33cf", baixo="saia", cor_baixo="#1ba8c4", cor_sapato="#d6287f", extras=("batom",)),
    "p6": dict(pele="media", cabelo="raspado", cor_cabelo="#1c1410", chapeu="bandana", cor_chapeu="#b91c1c", topo="colete", cor1="#1a4a2e", cor2="#e0b312", baixo="calca", cor_baixo="#2b2724", cor_sapato="#2b2724", extras=("barba",)),
    "p7": dict(F, pele="negra", cabelo="trancas", cor_cabelo="#0f0b09", topo="top", cor1="#d98a0b", baixo="bermuda", cor_baixo="#1e3a8a", cor_sapato="#ecebe2", extras=("brinco", "corrente", "batom")),
    "p8": dict(pele="clara", cabelo="curto", cor_cabelo="#4b3621", chapeu="policia", cor_chapeu="#1e3a8a", topo="uniforme", cor1="#2256c9", baixo="calca", cor_baixo="#172554", cor_sapato="#0d0d12", sapato="bota", extras=("escuros", "bigode")),
    "m1": dict(pele="oliva", cabelo="liso", cor_cabelo="#0f0f14", topo="terno", cor1="#e8e5da", cor2="#0c8fc9", baixo="calca", cor_baixo="#e8e5da", cor_sapato="#74461f", extras=("escuros", "ouro", "relogio")),
    "m2": dict(F, pele="morena", cabelo="coque", cor_cabelo="#c2951a", topo="vestido", cor1="#8f1a9c", cor2="#e0b312", baixo="pernas", cor_sapato="#e0b312", extras=("batom", "brinco", "corrente")),
    "m3": dict(porte=1.1, pele="media", cabelo="careca", chapeu="capacete", cor_chapeu="#a11a1a", topo="couro", cor1="#201c1a", cor2="#6e1a1a", baixo="jeans", cor_baixo="#232e4a", sapato="bota", cor_sapato="#201c1a", extras=("barba",)),
    "m4": dict(F, pele="clara", cabelo="chanel", cor_cabelo="#e8e5da", chapeu="gorro", cor_chapeu="#1e9d4c", topo="jaqueta", cor1="#c93a80", cor2="#1ba8c4", baixo="jeans", cor_baixo="#39465a", cor_sapato="#ecebe2", extras=("mochila", "fones"), cor_mochila="#1e9d4c", cor_fone="#e0b312"),
    "dancarina": dict(F, pele="morena", cabelo="longo", cor_cabelo="#5b1a8a", topo="top", cor1="#3dd17f", baixo="saia", cor_baixo="#14141c", cor_sapato="#d6287f", extras=("batom", "brinco", "corrente")),
    "poker1": dict(porte=1.12, pele="clara", cabelo="cacheado", cor_cabelo="#b8b8c0", topo="terno", cor1="#3f1d4f", cor2="#e0b312", baixo="calca", cor_baixo="#24152e", cor_sapato="#17171d", extras=("bigode", "relogio", "oculos")),
    "poker2": dict(F, pele="negra", cabelo="afro", cor_cabelo="#120d0a", topo="vestido", cor1="#b91c1c", cor2="#e0b312", baixo="pernas", cor_sapato="#17171d", extras=("batom", "brinco", "corrente")),
    "gordao": dict(porte=1.06, pele="morena", cabelo="raspado", cor_cabelo="#14100c", chapeu="fedora", cor_chapeu="#14702f", topo="terno", cor1="#14702f", cor2="#e0b312", baixo="calca", cor_baixo="#125c28", cor_sapato="#d9a919", extras=("escuros", "ouro", "corrente", "relogio", "barba")),
}
POSES_PADRAO = {"pose1": "sentado1", "pose2": "sentado2", "pose3": "andar1", "pose4": "andar2"}
POSES_EXTRAS = {
    "gordao": ["sinuca1", "sinuca2", "beber1", "beber2", "pegar", "dj1", "dj2", "jogar1", "jogar2"],
    "barman": ["servir1", "servir2"],
    "sinuca1": ["sinuca1", "sinuca2"],
    "sinuca2": ["beber1", "beber2"],
    "dj": ["dj1", "dj2"],
    "dancarina": ["dj1", "dj2"],
    "poker1": ["jogar1", "jogar2"],
    "poker2": ["jogar1", "jogar2"],
}


def gerar_deitado(pessoa):
    """Deita o personagem no sofá: o corpo gira e a frente fica virada para cima."""
    for numero in (1, 2, 3):
        corpo = desenhar(pessoa, f"deitado{numero}").rotate(90, expand=True)
        tela = Image.new("RGBA", (221, 181), (0, 0, 0, 0))
        tela.alpha_composite(corpo, (8, 46))
        tela.save(RAIZ / "sprites" / f"sofa_quadro{numero}.png")


def main():
    SAIDA.mkdir(parents=True, exist_ok=True)
    escolhidos = sys.argv[1:] or list(ELENCO)
    for nome in escolhidos:
        pessoa = ELENCO[nome]
        for arquivo, pose in POSES_PADRAO.items():
            desenhar(pessoa, pose).save(SAIDA / f"{nome}_{arquivo}.png")
        for pose in POSES_EXTRAS.get(nome, []):
            desenhar(pessoa, pose).save(SAIDA / f"{nome}_{pose}.png")
    if "gordao" in escolhidos:
        gerar_deitado(ELENCO["gordao"])
    print(f"{len(escolhidos)} personagens gerados em {SAIDA}")


if __name__ == "__main__":
    main()
