p='scene.glsl'; s=open(p,encoding='utf8').read()
def rep(a,b):
    global s
    assert a in s, a[:60]
    s=s.replace(a,b,1)
rep('*smoothstep(60.,30.,tt)*smoothstep(.25,.6,q.y)*smoothstep(5.,3.,q.y);','*smoothstep(60.,30.,tt)*smoothstep(2.5,6.,tt)*smoothstep(.25,.6,q.y)*smoothstep(5.,3.,q.y);')
rep('b+=.006*sin(q.y*52.+3.*sin(q.x*15.+q.z*9.))','b+=.0022*sin(q.y*40.+2.*sin(q.x*12.+q.z*7.))')
open(p,'w',encoding='utf8').write(s)
p='render.py'; s=open(p,encoding='utf8').read()
i0=s.index('CH_SPLIT = {'); i1=s.index('# ---------------------------------------------------------------- renderer')
new=r'''HERO = {'踩着巨人肩膀把你送到山脚': '山脚', '走了半天都还没走到半腰': '半腰', '如果爬山就是一直在走弯道': '弯道', '有云雾环绕': '云雾', '但就算登上山顶其实也不算高': '不算高',
 '过了旧的关会有新的烦恼': '新的烦恼', '当你跨过下个台阶下个转角': '转角', '会发现一山比一山高': '一山比一山高', '越过后才能看到': '越过',
 '想要登上高山欲穷千里目': '千里目', '回头看看赶了不止千里路': '千里路', '怎么越走越高越云里雾里': '云里雾里', '不如问问自己为何全力以赴': '为何',
 '也许因为甜头刚入口': '甜头', '也许因为野心像是高度酒': '野心', '也许因为人总要往高处走': '高处', '也许最想要的东西不是到处有': '最想要',
 '什么才是成功还不懂': '成功', '人是一个永远不会觉得满足的物种': '满足', '就像那句「只有天空才是极限」': '天空才是极限', '上山的路可能永远没有尽头': '没有尽头',
 '动力来自于山顶上的一切': '山顶', '和被踩在了脚底下那一片': '脚底下', '等到爬的越来越高': '越来越高', '脚底下的步伐越来越飘': '飘', '以为只要站的高一点才能看得远': '看得远',
 '于是都绷起勒紧裤腰': '勒紧', '把山顶当成最终目标': '最终目标', '为了可以拿到完美人生入场券': '入场券', '同时拥有诗和面包': '诗和面包',
 '曾经仰望的尖': '尖', '是你以为伸手就能摸到的天': '天', '结果发现登顶不过只是跨过了边': '边', '重新来到下个山脚翻掉过去的篇': '下个山脚', '不必留恋 曾经堆满筹码的桌上': '不必留恋',
 '但我需要继续前进继续盲人摸象': '继续', '继续高低来回像是海上的波浪': '波浪', '继续用力碰撞': '碰撞', '继续走在我的路上不管外面多么动荡': '我的路', '练出更大颗的心脏可以承受更多的重量': '心脏',
 '我羡慕的故事由我自己来奉上': '自己', '当我站在巨人肩膀上能看到更加辽阔以后': '巨人肩膀', '谁还不是一粒微小尘埃活在这个茫茫宇宙': '尘埃', '奋力冲向山顶上的过程我更钟爱': '过程',
 '那种后来居上弯道超车': '弯道超车', '比起独孤求败更加热血澎湃': '热血澎湃', '现在可以笑着当作花絮看': '花絮', '用来庆祝的香槟带着路上喝': '香槟', '新的游戏继续到了下一关': '下一关'}
def section(a):
    if a < 33.9 or 80.6 <= a < 112. or a >= 160.: return 'chorus'
    if a < 80.6: return 'verse'
    return 'rap'
def hero_spec(i):
    a, b, txt, fo = LYR[i]; ph = HERO.get(txt)
    if not ph: return None
    n = len(ph); vert = section(a) == 'chorus' and ph != '一山比一山高'
    size = {1: 300, 2: 215, 3: 175, 4: 150}.get(n, 118)
    if ph == '尘埃': size = 46
    if ph == '一山比一山高': return dict(ph=ph, vert=False, size=96, w=760, h=420)
    if vert: return dict(ph=ph, vert=True, size=size, w=size * 1.05, h=n * size * 1.02)
    return dict(ph=ph, vert=False, size=size, w=n * size * 1.04, h=size * 1.1)
def hero_end(i):
    a, b = LYR[i][0], LYR[i][1]; end = max(b, a + 1.2)
    for j in range(i + 1, len(LYR)):
        if HERO.get(LYR[j][2]): return min(end, LYR[j][0] - .12)
    return end
LAYOUT = {}
_lp = os.path.join(HERE, 'layout.json')
if os.path.exists(_lp):
    import json; LAYOUT = {int(k): v for k, v in json.load(open(_lp)).items()}

class Text:
    def __init__(s, W_, H):
        s.W, s.H, s.k = W_, H, H / 1080.
        mk = lambda: skia.Surface.MakeRaster(skia.ImageInfo.Make(W_, H, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType))
        s.surf = mk(); s.hsurf = mk()
        s.blank = np.zeros((H, W_, 4), np.uint8)
        rng = np.random.default_rng(7)
        def streak(horizontal):
            lo = rng.random((H // 5 + 2, W_ // 90 + 2)) if horizontal else rng.random((H // 90 + 2, W_ // 5 + 2))
            im = np.asarray(Image.fromarray((lo * 255).astype('u1')).resize((W_, H), Image.BICUBIC), np.float32) / 255
            fine = rng.random((H, W_)).astype(np.float32)
            return np.clip(1.5 - 1.25 * im ** 1.6 - .25 * fine, 0, 1) ** .8
        s.brH = streak(True); s.brV = streak(False)
    def spaced(s, c, txt, font, cx, y, sp, alphas, col=(255, 255, 255), blur=0):
        ws = [font.measureText(ch_) for ch_ in txt]
        tot = sum(ws) + sp * (len(txt) - 1); x = cx - tot / 2
        for ch_, w, al in zip(txt, ws, alphas):
            if al > 0.003 and ch_ != ' ':
                p = skia.Paint(AntiAlias=True, Color=skia.Color(col[0], col[1], col[2], int(255 * min(al, 1))))
                if blur: p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
                c.drawString(ch_, x, y, font, p)
            x += w + sp
    def hero(s, i, t):
        # large calligraphic key phrase composed into the picture; premultiplied RGBA float array or None
        sp = hero_spec(i); lay = LAYOUT.get(i)
        if not sp or not lay: return None
        a, b, txt, fo = LYR[i]; k = s.k
        end = hero_end(i)
        if t < a - .05 or t > end + .4: return None
        vis = sm(a - .05, a + .12, t) * (1 - sm(end, end + .4, t))
        if vis <= 0: return None
        c = s.hsurf.getCanvas(); c.clear(0)
        ph = sp['ph']; size = sp['size'] * k; cx, cy = lay['x'] * s.W, lay['y'] * s.H; dark = lay['dark']
        grow = 1. + .035 * (t - a) / max(end - a, .5)
        font = skia.Font(TF_TITLE, size * grow)
        ink = (24, 20, 26) if dark else (255, 250, 238)
        halo = (255, 245, 225) if dark else (0, 0, 0)
        pos = []
        if ph == '一山比一山高':
            x = cx - sp['w'] * k * .5; y = cy + sp['h'] * k * .42
            for j, ch_ in enumerate(ph):
                f = skia.Font(TF_TITLE, (70 + j * 17) * k * grow); pos.append((ch_, x, y, f)); x += f.measureText(ch_) + 6 * k; y -= (34 + j * 5) * k
        elif sp['vert']:
            step = size * 1.02 * grow; y = cy - (len(ph) - 1) * step / 2 + size * .36
            for ch_ in ph: pos.append((ch_, cx - font.measureText(ch_) / 2, y, font)); y += step
        else:
            ws = [font.measureText(ch_) for ch_ in ph]; x = cx - sum(ws) / 2
            for ch_, w in zip(ph, ws): pos.append((ch_, x, cy + size * .36, font)); x += w
        dur = min(.5, (end - a) * .5)
        for j, (ch_, x, y, f) in enumerate(pos):
            al = sm(0, .22, (t - a) - dur * j / max(len(pos), 1))
            dy = (1 - al) * 14 * k
            if ph == '飘': dy -= 60 * k * sm(.2, 2.2, t - a)
            if ph == '波浪': dy += 12 * k * math.sin(t * 5 + j * 1.7)
            if ph == '碰撞': x += 9 * k * math.sin(t * 46 + j * 3) * math.exp(-(t - a) * 3.5)
            p = skia.Paint(AntiAlias=True, Color=skia.Color(halo[0], halo[1], halo[2], int(70 * al)))
            p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, 16 * k)); c.drawString(ch_, x, y + dy + 3 * k, f, p)
            c.drawString(ch_, x, y + dy, f, skia.Paint(AntiAlias=True, Color=skia.Color(ink[0], ink[1], ink[2], int(255 * al))))
        arr = s.hsurf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType).astype(np.float32)
        op = (.8 if dark else .74) * vis
        if ph == '尘埃': arr *= .95 * vis
        else: arr *= ((s.brV if sp['vert'] else s.brH) * op)[..., None]
        return arr
    def render(s, t):
        k = s.k; items = []; heroes = []
        for i, (a, b, txt, fo) in enumerate(LYR):
            if a - .05 <= t <= b + fo: items.append((a, b, txt, fo))
            if a - .1 <= t <= b + 3.:
                h = s.hero(i, t)
                if h is not None: heroes.append(h)
        title_a = sm(.5, 1.5, t) * (1 - sm(2.2, 3.0, t))
        end_a = sm(192.3, 193.6, t)
        if not items and not heroes and title_a <= 0 and end_a <= 0: return None
        c = s.surf.getCanvas(); c.clear(0)
        for a, b, txt, fo in items:
            # the full line: small, widely spaced, sitting in the lower letterbox bar
            txt2 = txt.replace('「', ' ').replace('」', ' ').strip(); n = len(txt2)
            rev = min((b - a) * .35, .8); out = 1 - sm(b, b + fo, t)
            al = [sm(0, .22, (t - a) - rev * i / n) * out for i in range(n)]
            size = 35 if n <= 16 else 32
            f = skia.Font(TF_LYR, size * k); y = s.H - 52 * k; sp = (13 if n <= 16 else 9) * k
            s.spaced(c, txt2, f, s.W / 2, y, sp, [x * .92 for x in al], (236, 229, 214))
        for al, big in ((title_a, True), (end_a, False)):
            if al <= 0: continue
            f = skia.Font(TF_TITLE, (230 if big else 170) * k)
            cx, cy = (s.W * .5, s.H / 2 - 20 * k) if big else (s.W * .74, s.H / 2 - 30 * k)
            dr = (1 - al) * 18 * k
            s.spaced(c, '山脚', f, cx, cy + 70 * k, 30 * k, [al * .5] * 2, (0, 0, 0), blur=22 * k)
            s.spaced(c, '山脚', f, cx, cy + 70 * k - dr, 30 * k, [al * .55] * 2, (255, 215, 150), blur=14 * k)
            s.spaced(c, '山脚', f, cx, cy + 70 * k - dr, 30 * k, [al] * 2, (255, 252, 245))
            sx, sy, sz = cx + 265 * k * (1 if big else .76), cy + 40 * k, 46 * k * (1 if big else .8)
            p = skia.Paint(AntiAlias=True, Color=skia.Color(196, 48, 38, int(235 * al)))
            c.drawRoundRect(skia.Rect.MakeXYWH(sx, sy, sz, sz), 6 * k, 6 * k, p)
            c.drawString('山', sx + sz * .14, sy + sz * .78, skia.Font(TF_KAI, sz * .74), skia.Paint(AntiAlias=True, Color=skia.Color(255, 245, 235, int(255 * al))))
            fe = skia.Font(TF_EN, 21 * k)
            s.spaced(c, 'AT THE FOOT OF THE MOUNTAIN', fe, cx, cy + 135 * k, 9 * k, [al * .85] * 27, (255, 245, 230))
            if not big:
                al2 = sm(193.2, 194.4, t)
                fk = skia.Font(TF_LYR, 30 * k)
                tag = '每一座山顶 都是下一座山的山脚'
                s.spaced(c, tag, fk, cx, cy + 195 * k, 6 * k, [al2 * .7] * len(tag), (0, 0, 0), blur=5 * k)
                s.spaced(c, tag, fk, cx, cy + 195 * k, 6 * k, [al2 * .95] * len(tag), (255, 245, 230))
        arr = s.surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)
        if heroes:
            out = arr.astype(np.float32)
            for h in heroes: out = out + h * (1 - out[..., 3:4] / 255.)
            arr = np.clip(out, 0, 255).astype(np.uint8)
        return arr

def build_layout():
    import json
    Wd, Hd = 480, 270; r = Renderer(Wd, Hd, 1.0, text=False); lay = {}
    y0, y1 = int(Hd * 131 / 1080) + 6, int(Hd * 949 / 1080) - 6
    for i in range(len(LYR)):
        sp = hero_spec(i)
        if not sp: continue
        a = LYR[i][0]; end = hero_end(i)
        E = np.zeros((Hd, Wd), np.float32); L = np.zeros((Hd, Wd), np.float32)
        for tt in (a + .15, (a + end) / 2, end - .05):
            f = np.frombuffer(r.frame(tt), 'u1').reshape(Hd, Wd, 3).astype(np.float32) / 255.
            lum = f @ np.array([.3, .59, .11], np.float32)
            gx = np.abs(np.diff(lum, axis=1, prepend=lum[:, :1])); gy = np.abs(np.diff(lum, axis=0, prepend=lum[:1]))
            E += gx + gy; L += lum
        E /= 3; L /= 3
        ii = lambda A: np.pad(A.astype(np.float64).cumsum(0).cumsum(1), ((1, 0), (1, 0)))
        IE, IL, IL2 = ii(E), ii(L), ii(L * L)
        def box(I, x0, y0_, x1, y1_): return (I[y1_, x1] - I[y0_, x1] - I[y1_, x0] + I[y0_, x0]) / max((x1 - x0) * (y1_ - y0_), 1)
        bw, bh = int(sp['w'] * Wd / 1920), int(sp['h'] * Hd / 1080)
        bw = min(bw, Wd - 34); bh = min(bh, y1 - y0 - 6)
        gE = E[y0:y1].mean() + 1e-4; best = None
        for cy in range(y0 + bh // 2 + 2, y1 - bh // 2 - 1, 4):
            for cx in range(16 + bw // 2, Wd - 16 - bw // 2, 6):
                x0, x1, ya, yb = cx - bw // 2, cx + bw // 2, cy - bh // 2, cy + bh // 2
                e = box(IE, x0, ya, x1, yb) / gE; m = box(IL, x0, ya, x1, yb); var = max(box(IL2, x0, ya, x1, yb) - m * m, 0)
                # keep clear of the middle, where the subject usually is
                ox = max(0, min(x1, Wd * .64) - max(x0, Wd * .36)) / bw; oy = max(0, min(yb, Hd * .8) - max(ya, Hd * .3)) / bh
                sc = e + 6. * var ** .5 + 1.1 * ox * oy
                if best is None or sc < best[0]: best = (sc, cx, cy, m)
        sc, cx, cy, m = best
        lay[i] = dict(x=cx / Wd, y=cy / Hd, dark=bool(m > .56))
        print(i, LYR[i][2], sp['ph'], lay[i], round(float(sc), 2), flush=True)
    json.dump(lay, open(_lp, 'w'))

'''
s=s[:i0]+new+s[i1:]
a='''    mode = sys.argv[1]
    if mode == 'sheet':'''
assert a in s
s=s.replace(a,'''    mode = sys.argv[1]
    if mode == 'layout': build_layout()
    elif mode == 'sheet':''')
open(p,'w',encoding='utf8').write(s)
print('ok')
