import sys, os, subprocess, glob, numpy as np, moderngl, skia
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
DUR = 196.6
U = 3.871
# (start, shot id, transition kind, amount)
SHOTS = [
 (0.00, 64, 'cut', 0), (3.26, 10, 'dis', 1.4), (11.00, 20, 'dis', 1.0), (18.74, 30, 'dis', 1.0),
 (26.49, 40, 'dis', .8), (29.90, 70, 'dis', .8),
 (36.16, 50, 'cut', 1.), (41.97, 60, 'cut', .6), (49.71, 21, 'cut', .6), (57.45, 51, 'cut', .6),
 (65.20, 52, 'cut', .6), (72.94, 53, 'cut', .6),
 (80.68, 11, 'cut', 1.), (88.42, 22, 'dis', .6), (96.17, 31, 'cut', .9), (103.91, 41, 'dis', .6), (107.30, 71, 'dis', .6),
 (111.65, 61, 'cut', .8), (119.39, 62, 'cut', .5), (127.13, 54, 'cut', .6), (134.87, 13, 'cut', .6),
 (141.00, 80, 'dis', 1.2), (150.36, 90, 'cut', .9),
 (160.20, 12, 'cut', .5), (167.94, 55, 'cut', .6), (175.68, 32, 'cut', .7), (183.42, 72, 'dis', .8),
 (191.20, 63, 'dis', 1.6),
]
LYR = [
 (3.2, 6.7, '踩着巨人肩膀 把你送到山脚'), (7.0, 10.6, '走了半天 都还没走到半腰'), (10.8, 14.3, '如果爬山 就是一直在走弯道'),
 (14.44, 18.6, '有云雾环绕 坏天气不停干扰'), (18.72, 22.0, '但就算登上山顶 其实也不算高'), (22.3, 26.2, '过了旧的关 会有新的烦恼'),
 (26.44, 29.7, '当你跨过下个台阶 下个转角'), (29.84, 33.2, '会发现 一山比一山高'),
 (80.68, 84.3, '踩着巨人肩膀 把你送到山脚'), (84.6, 88.2, '走了半天 都还没走到半腰'), (88.52, 91.7, '如果爬山 就是一直在走弯道'),
 (91.88, 95.95, '有云雾环绕 坏天气不停干扰'), (96.14, 99.4, '但就算登上山顶 其实也不算高'), (99.6, 103.3, '过了旧的关 会有新的烦恼'),
 (103.6, 107.1, '当你跨过下个台阶 下个转角'), (107.26, 110.6, '会发现 一山比一山高'),
 (160.2, 163.3, '踩着巨人肩膀 把你送到山脚'), (163.6, 167.1, '走了半天 都还没走到半腰'), (167.4, 171.0, '如果爬山 就是一直在走弯道'),
 (171.16, 175.3, '有云雾环绕 坏天气不停干扰'), (175.5, 178.7, '但就算登上山顶 其实也不算高'), (179.0, 182.6, '过了旧的关 会有新的烦恼'),
 (183.0, 186.4, '当你跨过下个台阶 下个转角'), (186.62, 190.2, '会发现 一山比一山高'),
]
F = np.load(os.path.join(HERE, 'feat.npz'))
BEATS = F['beats']; FT = F['t']
_low = F['low'] / np.percentile(F['low'], 98)
_k = np.clip(_low, 0, 1.3) ** 2
KICK = np.zeros_like(_k); a = 0.
dt = FT[1] - FT[0]
for i, v in enumerate(_k):
    a = max(v, a * np.exp(-dt / .16)); KICK[i] = a
KICK = np.clip((KICK - .25) / .9, 0, 1)
PER = float(np.median(np.diff(BEATS)))

def beat(t):
    if t < BEATS[0]:
        x = (t - BEATS[0]) / PER
    elif t >= BEATS[-1]:
        x = len(BEATS) - 1 + (t - BEATS[-1]) / PER
    else:
        i = np.searchsorted(BEATS, t) - 1
        x = i + (t - BEATS[i]) / (BEATS[i + 1] - BEATS[i])
    return float(np.floor(x)), float(x - np.floor(x))

def sm(a, b, x):
    x = min(max((x - a) / (b - a), 0), 1); return x * x * (3 - 2 * x)

def shot_state(t):
    idx = 0
    for i, s in enumerate(SHOTS):
        if t >= s[0] - (s[3] / 2 if s[2] == 'dis' else 0): idx = i
    def win(i):
        s = SHOTS[i]
        st = s[0] - (s[3] / 2 if s[2] == 'dis' else 0)
        if i + 1 < len(SHOTS):
            n = SHOTS[i + 1]; en = n[0] + (n[3] / 2 if n[2] == 'dis' else 0)
        else: en = DUR
        return st, en
    st, en = win(idx); s = SHOTS[idx]
    A = (s[1], t - st, en - st); B = A; mx = 0.; flash = 0.
    if s[2] == 'dis' and idx > 0 and t < s[0] + s[3] / 2:
        pst, pen = win(idx - 1)
        B = A; A = (SHOTS[idx - 1][1], t - pst, pen - pst)
        mx = sm(0, 1, (t - (s[0] - s[3] / 2)) / s[3])
    if s[2] == 'cut' and s[3] > 0:
        flash = s[3] * np.exp(-(t - s[0]) * 7.) if t >= s[0] else 0.
    # anticipation flash just before hard cuts
    if idx + 1 < len(SHOTS) and SHOTS[idx + 1][2] == 'cut':
        flash += SHOTS[idx + 1][3] * .5 * np.exp(-(SHOTS[idx + 1][0] - t) * 14.)
    return A, B, mx, float(flash)

def fade(t):
    f = sm(0, 1.2, t)
    f *= 1 - sm(158.2, 159.2, t) * (1 - sm(159.9, 160.5, t))
    f *= 1 - sm(193.6, 196.2, t)
    return f

# ---------- text ----------
def tf(name): return skia.Typeface.MakeFromFile(os.path.join(r'C:\Windows\Fonts', name))
TF_LYR = tf('NotoSerifSC-VF.ttf'); TF_TITLE = tf('STXINGKA.TTF'); TF_KAI = tf('STKAITI.TTF'); TF_EN = tf('NotoSerif-Regular.ttf')

class Text:
    def __init__(s, W, H):
        s.W, s.H, s.k = W, H, H / 1080.
        s.surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(W, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
        s.blank = np.zeros((H, W, 4), np.uint8)
    def spaced(s, c, txt, font, cx, y, sp, alphas, col=(255, 255, 255), blur=0, vertical=False):
        ws = [font.measureText(ch) for ch in txt]
        if vertical:
            size = font.getSize(); tot = len(txt) * size + (len(txt) - 1) * sp; yy = y - tot / 2 + size * .85
            for ch, w, al in zip(txt, ws, alphas):
                p = skia.Paint(AntiAlias=True, Color=skia.Color(col[0], col[1], col[2], int(255 * al)))
                if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
                c.drawString(ch, cx - w / 2, yy, font, p); yy += size + sp
            return
        tot = sum(ws) + sp * (len(txt) - 1); x = cx - tot / 2
        for ch, w, al in zip(txt, ws, alphas):
            if al > 0.003 and ch != ' ':
                p = skia.Paint(AntiAlias=True, Color=skia.Color(col[0], col[1], col[2], int(255 * min(al, 1))))
                if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
                c.drawString(ch, x, y, font, p)
            x += w + sp
    def render(s, t):
        k = s.k; items = []
        for a, b, txt in LYR:
            if a - .05 <= t <= b + .5: items.append((a, b, txt))
        title_a = sm(.4, 1.6, t) * (1 - sm(3.3, 4.4, t))
        end_a = sm(192.0, 193.4, t)
        if not items and title_a <= 0 and end_a <= 0: return None
        c = s.surf.getCanvas(); c.clear(0)
        for a, b, txt in items:
            n = len(txt); rev = min((b - a) * .5, 1.6); out = 1 - sm(b, b + .45, t)
            al = [sm(0, .35, (t - a) - rev * i / n) * out for i in range(n)]
            f = skia.Font(TF_LYR, 44 * k); y = s.H - 131 * k - 62 * k
            s.spaced(c, txt, f, s.W / 2, y + 2 * k, 7 * k, [x * .85 for x in al], (0, 0, 0), blur=7 * k)
            s.spaced(c, txt, f, s.W / 2, y + 1 * k, 7 * k, [x * .6 for x in al], (0, 0, 0), blur=2 * k)
            s.spaced(c, txt, f, s.W / 2, y, 7 * k, al, (255, 250, 240))
        for al, big in ((title_a, True), (end_a, False)):
            if al <= 0: continue
            f = skia.Font(TF_TITLE, (230 if big else 170) * k)
            cx, cy = (s.W / 2, s.H / 2 - 20 * k) if big else (s.W * .74, s.H / 2 - 30 * k)
            dr = (1 - al) * 18 * k
            s.spaced(c, '山脚', f, cx, cy + 70 * k, 30 * k, [al * .5] * 2, (0, 0, 0), blur=22 * k)
            s.spaced(c, '山脚', f, cx, cy + 70 * k - dr, 30 * k, [al * .55] * 2, (255, 215, 150), blur=14 * k)
            s.spaced(c, '山脚', f, cx, cy + 70 * k - dr, 30 * k, [al] * 2, (255, 252, 245))
            # seal
            sx, sy, sz = cx + 265 * k * (1 if big else .76), cy + 40 * k, 46 * k * (1 if big else .8)
            p = skia.Paint(AntiAlias=True, Color=skia.Color(196, 48, 38, int(235 * al)))
            c.drawRoundRect(skia.Rect.MakeXYWH(sx, sy, sz, sz), 6 * k, 6 * k, p)
            c.drawString('山', sx + sz * .14, sy + sz * .78, skia.Font(TF_KAI, sz * .74), skia.Paint(AntiAlias=True, Color=skia.Color(255, 245, 235, int(255 * al))))
            fe = skia.Font(TF_EN, 21 * k)
            s.spaced(c, 'AT THE FOOT OF THE MOUNTAIN', fe, cx, cy + 135 * k, 9 * k, [al * .85] * 27, (255, 245, 230))
            if not big:
                al2 = sm(193.0, 194.4, t)
                fk = skia.Font(TF_LYR, 30 * k)
                tag = '每一座山顶 都是下一座山的山脚'
                s.spaced(c, tag, fk, cx, cy + 195 * k, 6 * k, [al2 * .7] * len(tag), (0, 0, 0), blur=5 * k)
                s.spaced(c, tag, fk, cx, cy + 195 * k, 6 * k, [al2 * .95] * len(tag), (255, 245, 230))
        return s.surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)

class Renderer:
    def __init__(s, W, H, ss):
        s.W, s.H, s.ss = W, H, ss
        s.ctx = moderngl.create_standalone_context()
        vs = '#version 330\nin vec2 v;void main(){gl_Position=vec4(v,0.,1.);}'
        s.p1 = s.ctx.program(vertex_shader=vs, fragment_shader=open(os.path.join(HERE, 'scene.glsl'), encoding='utf8').read())
        s.p2 = s.ctx.program(vertex_shader=vs, fragment_shader=open(os.path.join(HERE, 'post.glsl'), encoding='utf8').read())
        vb = s.ctx.buffer(np.array([-1, -1, 3, -1, -1, 3], 'f4').tobytes())
        s.v1 = s.ctx.vertex_array(s.p1, [(vb, '2f', 'v')]); s.v2 = s.ctx.vertex_array(s.p2, [(vb, '2f', 'v')])
        SW, SH = int(W * ss), int(H * ss)
        s.tex = s.ctx.texture((SW, SH), 4, dtype='f2'); s.tex.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
        s.tex.repeat_x = s.tex.repeat_y = False
        s.f1 = s.ctx.framebuffer([s.tex])
        s.out = s.ctx.texture((W, H), 3); s.f2 = s.ctx.framebuffer([s.out])
        s.txt = s.ctx.texture((W, H), 4); s.txt.filter = (moderngl.LINEAR, moderngl.LINEAR)
        s.text = Text(W, H); s.blank = True; s.txt.write(s.text.blank.tobytes())
        s.SW, s.SH = SW, SH
    def U(s, p, k, v):
        if k in p: p[k].value = v
    def frame(s, t):
        A, B, mx, flash = shot_state(t); bn, bp = beat(t)
        kick = float(np.interp(t, FT, KICK))
        s.f1.use(); p = s.p1
        s.U(p, 'R', (s.SW, s.SH)); s.U(p, 'T', t)
        s.U(p, 'shA', A[0]); s.U(p, 'tA', A[1]); s.U(p, 'dA', A[2])
        s.U(p, 'shB', B[0]); s.U(p, 'tB', B[1]); s.U(p, 'dB', B[2]); s.U(p, 'mx', mx)
        s.U(p, 'kick', kick); s.U(p, 'bph', bp); s.U(p, 'beatN', bn)
        s.v1.render(moderngl.TRIANGLES); s.tex.build_mipmaps()
        arr = s.text.render(t)
        if arr is not None: s.txt.write(np.ascontiguousarray(arr).tobytes()); s.blank = False
        elif not s.blank: s.txt.write(s.text.blank.tobytes()); s.blank = True
        s.f2.use(); p = s.p2
        s.tex.use(0); s.txt.use(1); s.U(p, 'S', 0); s.U(p, 'TX', 1)
        s.U(p, 'R', (s.W, s.H)); s.U(p, 'T', t); s.U(p, 'flash', flash); s.U(p, 'fade', fade(t)); s.U(p, 'kick', kick)
        s.U(p, 'lod0', float(np.log2(s.ss)))
        s.v2.render(moderngl.TRIANGLES)
        return s.f2.read(components=3, alignment=1)

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'sheet':  # contact sheet of given times
        ts = [float(x) for x in sys.argv[3:]]
        W, H = 960, 540; r = Renderer(W, H, 1.0); cols = 3; rows = (len(ts) + cols - 1) // cols
        im = Image.new('RGB', (W * cols, H * rows))
        for i, t in enumerate(ts):
            im.paste(Image.frombytes('RGB', (W, H), r.frame(t)), ((i % cols) * W, (i // cols) * H))
        im.save(sys.argv[2], quality=90)
    elif mode == 'still':
        r = Renderer(1920, 1080, float(sys.argv[4]) if len(sys.argv) > 4 else 2.0)
        Image.frombytes('RGB', (1920, 1080), r.frame(float(sys.argv[3]))).save(sys.argv[2])
    elif mode == 'video':
        out, t0, t1 = sys.argv[2], float(sys.argv[3]), float(sys.argv[4]); ss = float(sys.argv[5]) if len(sys.argv) > 5 else 2.0
        W, H = (1920, 1080) if ss > 0 else (960, 540)
        ss = abs(ss); r = Renderer(W, H, ss)
        audio = glob.glob(os.path.join(HERE, '..', '*.m4a'))[0]
        cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
               '-ss', str(t0), '-t', str(t1 - t0), '-i', audio, '-map', '0:v', '-map', '1:a',
               '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
               '-vf', 'scale=out_color_matrix=bt709', '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', out]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        import time; T0 = time.time(); n = int(round((t1 - t0) * FPS))
        for i in range(n):
            ff.stdin.write(r.frame(t0 + i / FPS))
            if i % 150 == 0: print(f'{i}/{n} {time.time() - T0:.0f}s', flush=True)
        ff.stdin.close(); ff.wait(); print('done', time.time() - T0)
