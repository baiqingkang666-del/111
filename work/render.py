import sys, os, subprocess, glob, math, numpy as np, moderngl, skia
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
DUR = 196.6
pi = math.pi

# ---------------------------------------------------------------- audio
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
    if t < BEATS[0]: x = (t - BEATS[0]) / PER
    elif t >= BEATS[-1]: x = len(BEATS) - 1 + (t - BEATS[-1]) / PER
    else:
        i = np.searchsorted(BEATS, t) - 1
        x = i + (t - BEATS[i]) / (BEATS[i + 1] - BEATS[i])
    return float(x)
def kick(t): return float(np.interp(t, FT, KICK))

# ---------------------------------------------------------------- math
def V(*a): return np.array(a, float)
def N(v):
    v = np.asarray(v, float); return v / (np.linalg.norm(v) + 1e-12)
def mix(a, b, x): return a + (b - a) * x
def cl(x, a=0., b=1.): return min(max(x, a), b)
def sm(a, b, x):
    x = cl((x - a) / (b - a)); return x * x * (3 - 2 * x)
def ease(x): return sm(0, 1, x)
def spl(keys, u):
    us = [k[0] for k in keys]; vs = [np.asarray(k[1], float) for k in keys]
    u = cl(u, us[0], us[-1]); i = min(max(int(np.searchsorted(us, u, side='right')) - 1, 0), len(us) - 2)
    def tan(j):
        if j == 0: return (vs[1] - vs[0]) / (us[1] - us[0])
        if j == len(us) - 1: return (vs[-1] - vs[-2]) / (us[-1] - us[-2])
        return (vs[j + 1] - vs[j - 1]) / (us[j + 1] - us[j - 1])
    h = us[i + 1] - us[i]; x = (u - us[i]) / h
    return (2*x**3 - 3*x**2 + 1) * vs[i] + (x**3 - 2*x**2 + x) * h * tan(i) + (-2*x**3 + 3*x**2) * vs[i + 1] + (x**3 - x**2) * h * tan(i + 1)
def h11(n): return (math.sin(n * 127.1) * 43758.5453) % 1.0

# ---------------------------------------------------------------- world helpers (need GL for terrain height)
class W: pass
VS = '#version 330\nin vec2 v;void main(){gl_Position=vec4(v,0.,1.);}'
COMMON = open(os.path.join(HERE, 'common.glsl'), encoding='utf8').read()
def pX(z):
    s = (z - 9.) / 12.; a = mix(1.25, .7, sm(1., 2., s))
    return a * math.sin(s * 31.4159) * sm(0., .12, s)
def init_world(ctx, vb):
    prog = ctx.program(vertex_shader=VS, fragment_shader='#version 330\n' + COMMON +
        'uniform vec2 pts[16];uniform int oct;out vec4 O;void main(){int i=int(gl_FragCoord.x);O=vec4(terH(pts[i],oct));}')
    tex = ctx.texture((16, 1), 1, dtype='f4'); fbo = ctx.framebuffer([tex]); vao = ctx.vertex_array(prog, [(vb, '2f', 'v')])
    def ghs(P, n=9):
        out = []
        for i in range(0, len(P), 16):
            ch_ = list(P[i:i + 16]); m = len(ch_); ch_ += [(0., 0.)] * (16 - m)
            prog['pts'].write(np.array(ch_, 'f4').tobytes()); prog['oct'].value = n
            fbo.use(); vao.render(moderngl.TRIANGLES)
            out += list(np.frombuffer(fbo.read(components=1, dtype='f4'), 'f4')[:m])
        return out
    W.ghs = ghs
    W.gh = lambda x, z, n=9: float(ghs([(x, z)], n)[0])
    W.stY = W.gh(0, 0)
    # summit search
    pts = [(x, z) for x in np.arange(-8, 8.01, .5) for z in np.arange(30, 48.01, .5)]
    hs = ghs(pts); bx, bz = pts[int(np.argmax(hs))]
    pts = [(x, z) for x in np.arange(bx - .5, bx + .51, .05) for z in np.arange(bz - .5, bz + .51, .05)]
    hs = ghs(pts); bx, bz = pts[int(np.argmax(hs))]
    W.SUM = V(bx, max(hs), bz)
    # arclength table of the path
    zs = np.arange(0, 46, .01); xs = np.array([pX(z) for z in zs])
    W.pz = zs; W.ps = np.concatenate([[0], np.cumsum(np.hypot(np.diff(xs), np.diff(zs)))])
    W.shore = {}
def G(x, z, dy=0.): return V(x, W.gh(x, z) + dy, z)
def PP(z, dy=0.): return G(pX(z), z, dy)
def yawP(z): return math.atan2(pX(z + .06) - pX(z - .06), .12)
def zAt(s): return float(np.interp(s, W.ps, W.pz))
def sAt(z): return float(np.interp(z, W.pz, W.ps))
def shoreZ(x):
    k = round(x, 2)
    if k not in W.shore:
        a, b = -3.2, 0.
        for _ in range(14):
            m = (a + b) / 2
            if W.gh(x, m) > .012: b = m
            else: a = m
        W.shore[k] = b
    return W.shore[k]
def ORB(): return V(0, W.stY + 1.66, -.24)
_VP = {}
def viewpos(P, r, h, pref, th=.05):
    key = (round(P[0], 3), round(P[2], 3), r, h, pref)
    if key not in _VP:
        best = None
        for k in range(16):
            a = pref + (k + 1) // 2 * (1 if k % 2 else -1) * pi / 8
            c = G(P[0] + r * math.sin(a), P[2] + r * math.cos(a), h); tgt = P + V(0, th, 0)
            pts = [mix(c, tgt, j / 6.) for j in range(1, 6)]
            hs = W.ghs([(q[0], q[2]) for q in pts])
            if all(q[1] - hh > .025 for q, hh in zip(pts, hs)) and c[1] - P[1] < r * .5:
                best = c; break
        _VP[key] = best if best is not None else P + V(r * math.sin(pref), r * .6, r * math.cos(pref))
    return _VP[key]

# ---------------------------------------------------------------- looks
ORANGE = (.86, .40, .2); GREY = (.66, .62, .58); GREY2 = (.74, .68, .6); BLUE = (.5, .72, .95)
PALS = [(.95, .75, .35), (.55, .8, .6), (.9, .55, .65), (.6, .65, .9), (.8, .6, .9), (.5, .8, .85)]
DEF = dict(stage=0, sets=1, ro=V(0, 1, -5), ta=V(0, 1, 0), fov=40., roll=0., focus=None, ap=0., tilt=0., tiltc=.5,
           drops=0., lsnow=0., desat=0., eblur=0., pulse=0., radial=0., film=0., vig=0., expo=1., sat=1., warm=0., lift=0., flash=0.,
           fogD=.012, fogH=.35, starA=0., domeA=.5, clY=6., clA=0., rainA=0., snowA=0., wet=0., snowL=8.5, mistA=0., amb=.6,
           orb=.6, winA=0., strm=0., ntBlur=0., tmaxS=45., clCov=0.,
           ltn=(0, 0, 0, 0), glow=(0, 0, 0, 99), lone=(0, 1, 0, 0), pl0=(0, 0, 0, 1), pl0c=(0, 0, 0, 0), sp0=(0, 0, 0, 1), sp0d=(0, -1, 0, .01),
           sp0c=(0, 0, 0, 0), setA=(0, 0, 0, 0), setB=(0, 0, 0, 0), rkO=(0, 0, 0, 0), stO=(-10., 3.0, 10.), part=(0, 0, 0, 0), partC=(1, .8, .4, 0))
PRE = dict(
 dawn=dict(sunD=N((8, 1.56, 2.36)), sunC=V(1., .6, .32) * 1.5, skT=V(.14, .22, .46), skM=V(.62, .47, .52), skH=V(1., .7, .48),
           fogC=V(.9, .68, .58), fogD=.022, fogH=.45, domeA=.6, clY=3.4, clA=.55, orb=1.3, amb=1.05),
 noon=dict(sunD=N((.45, .8, -.35)), sunC=V(1., .96, .88) * 1.45, skT=V(.1, .28, .62), skM=V(.38, .6, .86), skH=V(.78, .86, .93),
           fogC=V(.72, .82, .92), fogD=.01, domeA=.5, clY=5., clA=.5, orb=.5),
 mist=dict(sunD=N((.4, .6, -.4)), sunC=V(1., .97, .92) * .8, skT=V(.55, .6, .66), skM=V(.7, .74, .78), skH=V(.84, .86, .88),
           fogC=V(.82, .85, .88), fogD=.12, fogH=.001, domeA=.8, orb=.4, amb=.8),
 snow=dict(sunD=N((.3, .6, -.4)), sunC=V(.8, .85, 1.) * .6, skT=V(.36, .4, .48), skM=V(.5, .55, .62), skH=V(.66, .7, .76),
           fogC=V(.62, .66, .73), fogD=.09, fogH=.001, snowA=1., snowL=-2., domeA=1., amb=.8, orb=.3),
 dusk=dict(sunD=N((-.9, .1, -.2)), sunC=V(1., .5, .25) * 1.0, skT=V(.06, .08, .22), skM=V(.35, .22, .36), skH=V(.95, .5, .3),
           fogC=V(.5, .34, .38), fogD=.014, clY=9.5, clA=.9, domeA=.5, amb=1.5, winA=1., orb=1.3),
 rain=dict(sunD=N((.75, .5, -.45)), sunC=V(.3, .46, .95) * 1.9, skT=V(.01, .02, .05), skM=V(.03, .055, .12), skH=V(.07, .11, .2),
           fogC=V(.05, .085, .16), fogD=.024, fogH=.2, domeA=1., rainA=1., wet=1., winA=1.3, orb=1.8, amb=1.9, clY=7., clA=1.),
 above=dict(sunD=N((.7, .32, -.55)), sunC=V(1., .8, .55) * 1.8, skT=V(.1, .26, .62), skM=V(.46, .64, .88), skH=V(1., .86, .7),
            fogC=V(.95, .88, .82), fogD=.004, fogH=.05, domeA=.15, clA=1., amb=1.1, orb=.3),
 night=dict(sunD=N((-.45, .6, -.5)), sunC=V(.38, .48, .8) * 1.5, skT=V(.0, .008, .03), skM=V(.015, .035, .11), skH=V(.07, .12, .26),
            fogC=V(.05, .08, .17), fogD=.012, starA=1., domeA=.15, winA=1., orb=1.6, amb=2.),
 predawn=dict(sunD=N((1., .03, .1)), sunC=V(1., .5, .25) * .6, skT=V(.01, .03, .12), skM=V(.1, .14, .32), skH=V(.75, .4, .3),
              fogC=V(.3, .25, .35), fogD=.012, starA=.6, domeA=.3, amb=.9, winA=1., orb=1.4),
 morning=dict(sunD=N((1., .3, -.1)), sunC=V(1., .8, .55) * 1.7, skT=V(.16, .36, .72), skM=V(.55, .7, .9), skH=V(1., .86, .66),
              fogC=V(.95, .82, .68), fogD=.012, clY=9., clA=1., domeA=.3),
 sunset=dict(sunD=N((-1., .15, -.28)), sunC=V(1., .55, .22) * 1.7, skT=V(.17, .2, .45), skM=V(.8, .48, .38), skH=V(1., .68, .34),
             fogC=V(1., .62, .36), fogD=.02, fogH=.45, domeA=.7, clY=3.4, clA=.5, orb=1.4, winA=.5),
 deskday=dict(stage=1, sets=8, sunD=N((-.5, .6, .45)), sunC=V(1., .85, .65) * .75, skT=V(.2, .16, .14), skM=V(.4, .32, .26), skH=V(.7, .56, .42),
              fogC=V(.6, .5, .4), fogD=0., starA=.7, amb=.75),
 desknight=dict(stage=1, sets=8, sunD=N((-.5, .6, .45)), sunC=V(0, 0, 0), skT=V(.008, .01, .02), skM=V(.02, .02, .035), skH=V(.03, .03, .05),
                fogC=V(.02, .02, .03), fogD=0., starA=1., amb=.6),
)
def base(pre, **kw):
    s = dict(DEF); s.update(PRE[pre]); s['chars'] = []; s['items'] = []; s['notes'] = []; s.update(kw); return s
def blend(s, pre, x):
    for k, v in PRE[pre].items():
        if k in ('stage', 'sets'): continue
        s[k] = mix(np.asarray(s[k], float), np.asarray(v, float), x) if not np.isscalar(v) else mix(s[k], v, x)
    s['sunD'] = N(s['sunD'])
def ch(p, yaw=0., ph=0., lean=0., arm=0., col=ORANGE, sc=.1, sit=0., eye=0, hat=0, med=0., heart=0.):
    return dict(p=np.asarray(p, float), yaw=yaw, ph=ph, lean=lean, arm=arm, col=col, sc=sc, sit=sit, eye=eye, hat=hat, med=med, heart=heart)
def it(p, f=(0, 0, 1), roll=0., sc=.08, col=(1, 1, 1), ty=0):
    return dict(p=np.asarray(p, float), f=N(f), roll=roll, sc=sc, col=col, ty=ty)
def note(p, n, up, w, h, front=-1, back=-1, rev=1., bend=0.):
    n = N(n); up = np.asarray(up, float); vv = N(up - n * np.dot(up, n)); uu = N(np.cross(n, vv))
    return dict(p=np.asarray(p, float), U=uu * w, V=vv * h, front=front, back=back, rev=rev, bend=bend)
def cam(s, ro, ta, fov=None, roll=None):
    s['ro'] = np.asarray(ro, float); s['ta'] = np.asarray(ta, float)
    if fov is not None: s['fov'] = fov
    if roll is not None: s['roll'] = roll
def basis(s):
    ww = N(s['ta'] - s['ro']); uu = N(np.cross(V(0, 1, 0), ww)); vv = np.cross(ww, uu)
    c, sn = math.cos(s['roll']), math.sin(s['roll'])
    return uu * c + vv * sn, vv * c - uu * sn, ww, 1. / math.tan(math.radians(s['fov']) / 2)
def C2W(s, c):
    uu, vv, ww, fl = basis(s); return s['ro'] + uu * c[0] + vv * c[1] + ww * c[2]
def proj(s, P):
    uu, vv, ww, fl = basis(s); d = np.asarray(P, float) - s['ro']; z = max(np.dot(d, ww), 1e-3)
    return np.dot(d, uu) / z * fl, np.dot(d, vv) / z * fl
def dirYP(yaw, pitch): return V(math.sin(yaw) * math.cos(pitch), math.sin(pitch), math.cos(yaw) * math.cos(pitch))
def pov(s, eye, yaw, pitch, T, amp=1., chaos=0., fov=62.):
    x = beat(T); bob = abs(math.sin(pi * x)); sw = math.sin(pi * x)
    e = np.asarray(eye, float) + V(0, .006 * amp * bob, 0)
    yaw += .02 * amp * sw + chaos * (.05 * math.sin(T * 7.3) + .03 * math.sin(T * 13.1))
    pitch += -.015 * amp * bob + chaos * .04 * math.sin(T * 9.1 + 1)
    cam(s, e, e + dirYP(yaw, pitch), fov, .02 * amp * sw + chaos * .04 * math.sin(T * 5.7))
    s['pulse'] = .008 * math.sin(T * 1.6); s['focus'] = 3.
def hands(s, col=ORANGE, y=-.03, spread=.042, z=.092, sc=.017, lift=(0., 0.), fwd=(0., 0.)):
    # two round hands with forearms reaching in from the bottom corners of the frame
    uu, vv, ww, fl = basis(s)
    for i, sx in enumerate((-1, 1)):
        s['items'].append(it(C2W(s, (sx * spread, y + lift[i], z + fwd[i])), N(ww + vv * .25 - uu * sx * .3), -sx * .5, sc, col, 12))
def walk_ph(T, rate=1.): return pi * beat(T) * rate
def walker(z, T, **kw):
    return ch(PP(z), yaw=yawP(z), ph=walk_ph(T), **kw)
def backplane(c, col=(1, 1, 1)):
    f = dirYP(c['yaw'], 0.); p = c['p'] + V(0, .82 * c['sc'], 0) - f * .34 * c['sc']
    return it(p, N(f * .35 + V(0, 1, 0)), .3, c['sc'] * .55, col, 0)
def lightning(s, T, times, seed=1.):
    v = 0.
    for i, t0 in enumerate(times):
        if T >= t0: v = max(v, math.exp(-(T - t0) * 6.) * (.6 + .4 * math.sin((T - t0) * 60.)))
        sd = seed + i
    s['ltn'] = (v * 1.2, seed + sum(1 for t0 in times if T >= t0), .0, 0)

# ---------------------------------------------------------------- shots
def sP00(t, d, T):
    s = base('dawn'); u = cl(t / 3.3)
    ro = mix(V(-13.5, .13, -3.3), V(-8., .2, -2.6), ease(u))
    cam(s, ro, V(0, W.stY + 1.2, -.2), 24.)
    s['orb'] = 2.2; s['focus'] = 9.; s['fogD'] = .03
    return s

def sGate(t, d, T, v):
    s = base(('dawn', 'rain', 'sunset')[v]); u = cl(t / d)
    y = W.stY
    ro = spl([(0, V(1.12, y + .07, -1.55)), (.3, V(1.3, y + .4, -2.0)), (.55, V(.62, y + 1.7, -1.1)), (.75, V(.3, y + 2.7, -1.2)), (1, V(0, y + 5.4, -5.))], u)
    ta = spl([(0, V(.72, y + .1, -1.0)), (.3, V(.4, y + .5, -.4)), (.55, V(0, y + 2., 6.)), (.75, V(0, y + 4., 20.)), (1, V(0, y + 5.6, 30.))], u)
    cam(s, ro, ta, 38.); s['focus'] = mix(.7, 30., sm(.2, .7, u)); s['ap'] = mix(.02, 0., sm(.3, .7, u)); s['tilt'] = sm(.7, 1., u) * .02; s['tiltc'] = .45
    # little ones
    wk = sm(.28, 1., u)
    P0 = V(.78, 0, -.95)
    pth = spl([(0, P0), (.25, V(.62, 0, -.2)), (.5, V(0, 0, 1.2)), (1, V(0, 0, 3.4))], wk)
    px = G(pth[0], pth[2]); d2 = spl([(0, P0), (.25, V(.62, 0, -.2)), (.5, V(0, 0, 1.2)), (1, V(0, 0, 3.4))], min(wk + .03, 1.)) - pth
    yaw = math.atan2(d2[0], d2[2]) if wk > 0 else pi * .9
    x = beat(T)
    if v == 0:
        c = ch(px, yaw=yaw, ph=walk_ph(T) if wk > 0 else 0., arm=0. if wk > 0 else .6 + .4 * math.sin(pi * x * 2), sc=.1 + .05 * sm(.7, 1., u))
        s['chars'] += [c, backplane(c) and c][:1]; s['items'].append(backplane(c))
        s['chars'].append(ch(G(.6, -1.12), yaw=.7, col=GREY, sc=.155, med=-1, arm=.5 * sm(.3, .45, u)))
        s['chars'].append(ch(G(.95, -1.08), yaw=-.6, col=GREY2, sc=.145, med=-1, arm=.8 * sm(.34, .5, u) * (.6 + .4 * math.sin(pi * x))))
    elif v == 1:
        z = mix(.2, 2.4, u); c = ch(G(0, z), yaw=0, ph=walk_ph(T, .5), lean=.38, med=1., sc=.1 + .05 * sm(.7, 1., u)); s['chars'].append(c)
        lightning(s, T, [84.0, 86.6], 3.)
    else:
        hop = .012 * abs(math.sin(pi * x))
        s['chars'].append(ch(G(.78, -.98, hop), yaw=pi+.6, arm=1., hat=1, eye=2, sc=.105))
        s['chars'].append(ch(G(.6, -1.0), yaw=pi + .4, col=GREY, sc=.155, med=-1))
        s['chars'].append(ch(G(.96, -.96), yaw=pi + .85, col=GREY2, sc=.145, med=-1))
    return s

def sZig(t, d, T, v):
    s = base(('dawn', 'rain', 'sunset')[v])
    s0 = sAt(11.6); z = zAt(s0 + .2 * t * (.6 if v == 1 else 1.))
    C = PP(z) * V(.6, 1, 1)
    hgt = (3.6, 3.6, 7.)[v]
    if v == 0:
        cam(s, C + V(.5 + .1 * t, hgt, -hgt * .5 + .05 * t), C + V(0, 0, .2), 30., .05 * math.sin(t * .3))
        s['focus'] = hgt * 1.1; s['tilt'] = .035; s['tiltc'] = .5
    elif v == 1:    # low, in front of the climber: rain streaming down the path, campus lights far below
        Pc = PP(z); ro = PP(z + .75, .07) + V(.16, 0, 0)
        cam(s, ro, Pc + V(0, .09, 0), 38., .03 * math.sin(t * .8)); s['focus'] = .75; s['ap'] = .014
        s['pl0'] = tuple(ro + V(-.25, .3, .1)) + (3.,); s['pl0c'] = (.5, .62, 1., 1.)
    else:           # wide oblique aerial drifting back while the bends light up one by one
        cam(s, C + V(2.6 + .12 * t, 3.2 + .3 * t, -4.2 - .45 * t), C + V(-.3, 0, 1.6), 34.); s['focus'] = 6.; s['tilt'] = .03; s['tiltc'] = .5
    s['clA'] = 0.; s['fogD'] *= .6
    c = walker(z, T, sc=.16, lean=.3 if v == 1 else 0., med=1. if v == 1 else 0., hat=1 if v == 2 else 0)
    if v == 1: c['ph'] = walk_ph(T, .5)
    s['chars'].append(c)
    if v == 0: s['items'].append(backplane(c))
    if v == 1: s['strm'] = 1.; lightning(s, T, [89.9], 5.)
    if v == 2: s['glow'] = (0, cl(.6 + t * 1.5, 0, 9.), 0, 99)
    return s

def sFog(t, d, T, v):
    s = base(('dawn', 'rain', 'sunset')[v])
    z = (14.05, 16.6, 12.4)[v] + .11 * t * (1., .7, .8)[v]
    eye = PP(z, .078); nx = PP(z + .6, .11); dd = nx - eye; yaw = math.atan2(dd[0], dd[2]); u = cl(t / d)
    if v == 0:
        pov(s, eye, yaw, .1 + .1 * u, T, 1., .25 + .9 * u)
        s['mistA'] = .25 + .75 * u; s['fogD'] = mix(.04, .3, u * u); s['fogC'] = V(.88, .8, .76); s['clA'] = 0.
    elif v == 1:
        pov(s, eye, yaw, .08 + .1 * math.sin(T * 2.1) * .5, T, 1.6, 1.3)
        s['pulse'] = .012 * math.sin(T * 5.) + .01 * kick(T)
        s['drops'] = 1.; s['vig'] = .7; s['desat'] = .35; s['eblur'] = 1.; s['mistA'] = .5; s['fogD'] = .12
        lightning(s, T, [92.6, 94.4, 95.3], 7.); s['ltn'] = (s['ltn'][0], s['ltn'][1], .3, 0)
    else:
        pov(s, eye, yaw, .12, T, .35, 0.)
        s['mistA'] = .65; s['fogD'] = .07; s['fogC'] = V(1., .7, .4); s['clA'] = 0.
    uu, vv, ww, fl = basis(s); sw = math.sin(pi * beat(T))
    if v == 0:      # holding the brand-new paper plane in both hands
        hands(s, lift=(.002 * sw, -.002 * sw))
        s['items'].append(it(C2W(s, (0., -.022 + .0015 * sw, .1)), N(ww + vv * .42 + uu * .12), .06 * sw, .05, (1, 1, 1), 0))
    elif v == 1:    # the plane is gone: empty hands pumping through the rain
        hands(s, y=-.029, spread=.046, lift=(.004 * sw, -.004 * sw), fwd=(.008 * sw, -.008 * sw))
    else:           # refolded plane, carried easily in one hand
        hands(s, y=-.033, spread=.05, lift=(-.004, .008), fwd=(0., .006))
        s['items'].append(it(C2W(s, (.047, -.014, .103)), N(ww + vv * .35 - uu * .25), -.25, .042, (1., .97, .9), 0))
    return s

def sPeak(t, d, T, v):
    s = base(('dawn', 'rain', 'sunset')[v]); u = cl(t / d)
    top = G(7., 17.); x = beat(T)
    if v == 2:
        yaw = math.atan2(-1., -.75)
        s['chars'].append(ch(top + V(0, -.004, 0), yaw=yaw, sit=1., hat=1))
        f = dirYP(yaw, 0.)
        s['chars'][0]['yaw'] = pi + .9; s['chars'][0]['eye'] = 2
        cam(s, top + V(.38 - .12 * u, .09 + .02 * u, -.6 - .08 * u), top + V(0, .08, 0), 42.)
        s['focus'] = .6; s['ap'] = .012; s['clA'] = .3
        return s
    if v == 0:      # jump for joy, then the camera swings out sideways: the "summit" is a bump on the shoulder of the range
        k = ease(u) ** 1.6
        ro = top + mix(V(.3, .1, -.55), V(-9.5, 2.6, -6.), k); ta = top + mix(V(0, .07, 0), V(2.5, 3.2, 7.), k)
        cam(s, ro, ta, 40.); s['focus'] = np.linalg.norm(ro - top); s['ap'] = .012 * (1 - k)
    else:           # no cheering: from below, the real mountain looms over the little peak in the lightning
        ro = G(top[0] - .22, top[2] - .62 + .1 * u, .035); cam(s, ro, top + V(.15, .22 + .12 * u, .6), 46.)
        s['focus'] = .66; s['ap'] = .006; s['amb'] = 3.2; s['skH'] = V(.13, .19, .34); s['skM'] = V(.06, .09, .17); s['fogD'] = .014
        s['pl0'] = tuple(top + V(-.25, .3, -.35)) + (6.,); s['pl0c'] = (.55, .68, 1.1, 1.)
    if v == 0:
        s['chars'].append(ch(top + V(0, .03 * abs(math.sin(pi * x)), 0), yaw=pi - .5, arm=1., ph=0.))
        s['items'].append(backplane(s['chars'][0]))
    else:
        s['chars'].append(ch(top, yaw=pi - .5, lean=.22, med=1.))
        lightning(s, T, [96.5, 97.7, 98.15, 99.0], 11.); s['ltn'] = (s['ltn'][0] * 1.3, s['ltn'][1], -.4, 0)
    return s

def sDeskA(t, d, T):
    s = base('deskday'); s['setA'] = (0, 1, 0, 0)
    cam(s, V(.06, .86 - .02 * t, .74 - .015 * t), V(0, 0, .03), 32.); s['ap'] = .025; s['focus'] = 1.1
    up = V(0, 0, -1)
    s['notes'].append(note(V(0, .003, 0), V(0, 1, 0), V(.08, 0, -1), .25, .125, front=2))
    for k, (tk, cell) in enumerate([(.75, 3), (1.7, 4), (2.65, 5)]):
        a = sm(tk, tk + .32, t)
        if a <= 0: continue
        off = V((h11(k + 1.) - .5) * .12, .006 * (k + 1) + (1 - a) ** 2 * .45, (h11(k + 4.) - .5) * .07)
        yw = (h11(k + 7.) - .5) * .7
        s['notes'].append(note(off, N(V((1 - a) * .3, 1, 0)), V(math.sin(yw), 0, -math.cos(yw)), .25, .125, front=cell))
    s['items'].append(it(V(-.34, .012, .12), N((.5, .02, -1.)), 0., .16, (.95, .75, .2), 8))
    return s

def sDeskC(t, d, T):
    s = base('desknight'); s['setA'] = (0, 1, 0, 0)
    cam(s, V(-.2 + .02 * t, .3, .66), V(.1, .17, 0), 34.); s['ap'] = .02; s['focus'] = .75
    s['sp0'] = (-.3, .9, 1., .6); s['sp0d'] = tuple(N(V(.12, .17, 0) - V(-.3, .9, 1.))) + (.25,); s['sp0c'] = (1.5, 1.1, .7, 1.)
    s['pl0'] = (.5, .68, -.14, 1.2); s['pl0c'] = (3., 2.1, 1.2, 1.)
    f = N((-.25, .4, 1.)); pos = V(.12, .2, .0)
    s['items'].append(it(pos, f, 0., .2, (.8, .1, .1), 11))
    x = beat(T) / 2.; k = int(math.floor(x)); fr = x - k
    up = V(0, 1, 0)
    s['notes'].append(note(pos + f * .0275 - V(0, .012, 0), f, up, .075, .058, front=16 + (k + 1) % 8))
    if fr < .75:
        a = fr / .75
        p = pos + f * (.03 + .1 * a) + V(.5 * a, .15 * a - .5 * a * a + .05, .1 * a) - V(0, .012, 0)
        n2 = N(f + V(math.sin(a * 5.), a, math.cos(a * 4.) - 1.) * a * 1.5)
        s['notes'].append(note(p, n2, up, .075, .058, front=16 + k % 8, back=-1))
    for j in range(3):
        yw = (h11(j + 2.) - .5) * .8
        s['notes'].append(note(V(-.35 + .06 * j, .003 + .004 * j, .2 - .05 * j), V(0, 1, 0), V(math.sin(yw), 0, -math.cos(yw)), .22, .11, front=3 + j))
    return s

def stair(sv):
    seg = int(math.floor(sv / 2.4)); f = sv - 2.4 * seg; k = seg // 2
    h = .96 * cl((f - .3) / 1.8)
    l = V(0, h, f) if seg % 2 == 0 else V(f, .96 + h, 2.4)
    l = l + k * V(2.4, 1.92, 2.4)
    ya, yb = (pi / 2, 0.) if seg % 2 == 0 else (0., pi / 2)
    yaw = mix(ya, yb, sm(1.8, 2.4, f))
    idx = k * 30 + (15 if seg % 2 else 0) + (f - .3) / .12
    O = V(*DEF['stO'])
    return O + V(l[2], l[1], l[0]), yaw, idx
def stair_dy(sv):
    f = sv % 2.4; i = math.floor((f - .3) / .12)
    return .064 * cl(i + 1., 0., 15.) - .96 * cl((f - .3) / 1.8)
def sStairs(t, d, T, v):
    s = base(('dawn', 'rain')[v]); s['sets'] = 2; s['clY'] = 4.2; s['clA'] = 1.; u = cl(t / d)
    if v == 0:
        # climbing a stone stair in the sky; after the corner the camera lifts and the ranges stack up ahead
        sv = .6 + 4.3 * u
        p, yaw, idx = stair(sv); p = p + V(0, stair_dy(sv), 0)
        s['chars'].append(ch(p, yaw=yaw, ph=walk_ph(T), lean=.18, sc=.11)); s['items'].append(backplane(s['chars'][0]))
        k = sm(.5, .95, u)
        ro = p + mix(V(-.6, .44, -.48), V(-1.5, 1.25, -1.9), k)
        ta = mix(p + V(.12, .1, .12), V(1., 9.5, 38.), k * .8)
        cam(s, ro, ta, mix(40., 34., k)); s['focus'] = mix(.8, 30., k); s['ap'] = .012 * (1 - k)
        s['fogD'] = .02; s['fogH'] = .2; s['clCov'] = .5
    else:
        # the same stair at night, seen from above: the lamps come on step by step behind the climber
        sv = .6 + 4.6 * u
        p, yaw, idx = stair(sv); p = p + V(0, stair_dy(sv), 0)
        s['chars'].append(ch(p, yaw=yaw, ph=walk_ph(T, .5), lean=.4, med=1., sc=.11))
        f = dirYP(yaw, 0.); a = V(1., 0, 1.) / math.sqrt(2.)
        ro = p + a * .75 + V(.3, .95, -.3) + V(0, .06 * math.sin(T * .7), 0)
        cam(s, ro, p + V(0, .1, 0) - a * .5, 40., .04 * math.sin(T * .5)); s['focus'] = float(np.linalg.norm(ro - p)); s['ap'] = .012
        s['setA'] = (0, 0, idx + 1.5, 0); s['fogD'] = .05; s['fogH'] = .05; s['vig'] = .4
        s['pl0'] = tuple(p + V(0, .14, 0)) + (25.,); s['pl0c'] = (.7, .48, .22, 1.)
        lightning(s, T, [105.9, 108.6], 21.)
    return s

def CLIFF(): return PP(20.6)
def b1path(u):
    Pc = CLIFF()
    keys = [(0, Pc + V(0, .2, -.4)), (.18, V(2.5, Pc[1] + 1.0, 14.)), (.42, V(7., 6.6, 5.)), (.6, V(8.2, 6.3, -3.)), (.76, V(4.5, 5.9, -8.6)),
            (.9, V(.3, 5.6, -8.4)), (1., V(-1.6, 5.7, -5.6)), (1.25, V(-2.6, 9.5, 1.5))]
    return spl(keys, u)
def sThrow(t, d, T):
    s = base('noon'); Pc = CLIFF(); s['clY'] = 3.; s['clA'] = .8
    thr = sm(.3, .5, t)
    c = ch(Pc, yaw=pi, arm=mix(-.2, 1., sm(.1, .4, t)), lean=-.2 * sm(.1, .3, t) + .4 * thr)
    s['chars'].append(c)
    hand = Pc + V(-.045, .1, -.02)
    pl = hand if t < .38 else mix(hand, b1path(.0) + V(0, .0, -.0) + V(0, .25, -2.2) * (t - .38) / .8, 1.) if False else hand + V(.0, .22, -2.6) * max(t - .38, 0.) ** 1.2
    s['items'].append(it(pl, N((0, .15, -1)), .1, .07, (1, 1, 1), 0))
    k = sm(.35, .9, t)
    cam(s, Pc + V(.42, .13, .5) + V(-.3, .12, -.3) * k, mix(Pc + V(0, .07, 0), pl, k), 44.)
    s['focus'] = .7; s['ap'] = .01; s['radial'] = .5 * sm(.7, 1.2, t)
    return s
def sB1(t, d, T):
    s = base('noon'); u = cl(t / d) * 1.0
    P = b1path(u); f = N(b1path(u + .01) - P); f0 = N(b1path(u - .01 + .0) - b1path(u - .02))
    bank = cl(float(np.cross(f0, f)[1]) * 14., -.45, .45)
    s['items'].append(it(P, f, -bank, .11, (1, 1, 1), 0))
    look = sm(.55, .95, u)
    ro = P - f * .5 + V(0, .24, 0) + N(np.cross(V(0, 1, 0), f)) * .14; ta = mix(P + f * 1.2, V(0, 3.2, 18.), look * .8)
    cam(s, ro, ta, 52., -bank * .5); s['focus'] = .5
    s['glow'] = (1.6 * sm(.5, .85, u), 0, 0, mix(0., 30., sm(.5, 1., u))); s['clY'] = 4.4; s['clA'] = .5; s['radial'] = .25 * (1 - look)
    return s
def sB2a(t, d, T):
    s = base('noon'); u = 1. + .25 * cl(t / 2.1)
    P = b1path(u); f = N(b1path(u + .01) - P)
    s['items'].append(it(P, f, 0., .11, (1, 1, 1), 0))
    cam(s, P - f * .5 + V(0, .24, 0) + N(np.cross(V(0, 1, 0), f)) * .14, P + f * 1.2, 52.)
    k = sm(.3, 1.9, t); s['fogD'] = mix(.01, 1.2, k * k); s['fogH'] = .001; s['fogC'] = V(.9, .93, .96); s['mistA'] = k; s['glow'] = (1.6, 0, 0, 30.)
    return s
def sB2b(t, d, T):
    s = base('mist'); s['fogD'] = .9; s['mistA'] = .8; s['sunC'] = s['sunC'] * .2; s['amb'] = 1.3
    eye = PP(24., .078)
    pov(s, eye, 0., .05, T, .5, .15)
    uu, vv, ww, fl = basis(s)
    a = sm(.0, .75, t)
    if t < .75:
        p = C2W(s, (mix(.3, 0., a), mix(.12, -.012, a), mix(1.2, .1, a)))
        s['items'].append(it(p, N(-ww + vv * .1 * (1 - a)), .5 * (1 - a), .04, (1, 1, 1), 0))
    else:
        b = sm(.75, 1.1, t)
        s['notes'].append(note(C2W(s, (0., -.012 + .004 * b, .1)), N(-ww + vv * .35), vv, .046, .023, front=0, bend=.03 * (1 - b)))
        s['ntBlur'] = 2.3
    cup = .012 * sm(.5, .9, t)
    hands(s, y=-.034 + cup, spread=.047, z=.095)
    return s

def book_pos(L):
    Li = min(int(math.floor(L)), 9); fr = L - Li; Ln = min(Li + 1, 9)
    def P(i): return V(.52 - .047 * i - .022, .07 * (i + 1), .08)
    a = sm(.35, .9, fr)
    return mix(P(Li), P(Ln), a) + V(0, .035 * math.sin(pi * a), 0)
def sB3(t, d, T):
    s = base('desknight'); k = int(cl(t / 1.93, 0, 3.99)); fr = t / 1.93 - k
    kk = k + sm(.0, .35, fr) - 1. if k > 0 else 0.
    kk = max(kk, 0.) if k == 0 else (k - 1) + sm(0., .3, fr)
    ro, ta = [(V(1.02, .2, 1.22), V(.1, .17, .1)), (V(.25, .42, 1.62), V(0, .3, 0)), (V(-1.0, .62, 1.05), V(0, .42, 0)), (V(.25, 1.75, 1.45), V(0, .62, 0))][k]
    ro = ro + N(ta - ro) * .1 * fr
    cam(s, ro, ta, 36.); s['ap'] = .02; s['focus'] = float(np.linalg.norm(ro - ta))
    nb = 7. + 3. * sm(3.86, 5.3, t)
    s['setA'] = (nb, 1, 0, 0)
    lamp = 1. + 2.6 * sm(1.93, 2.6, t)
    dim = 1. - .9 * sm(5.79, 6.3, t)
    s['pl0'] = (.9, .95, .9, .6); s['pl0c'] = tuple(mix(V(1.5, 1.1, .7), V(1.6, .8, .25), sm(1.93, 2.6, t)) * lamp * dim) + (2.,)
    s['fogC'] = mix(V(.02, .02, .03), V(.5, .28, .08), sm(1.93, 2.8, t) * dim); s['fogD'] = .07 * sm(1.93, 2.8, t) * dim
    L = cl(1. + t * .98, 0, min(nb - 1., 9.))
    P = book_pos(L)
    s['chars'].append(ch(P, yaw=-pi / 2, sc=.055, ph=walk_ph(T), arm=.9 * sm(.35, .6, L % 1) * (1 - sm(.6, .9, L % 1))))
    if t < 3.2:
        a = sm(.15, .5, t)
        s['notes'].append(note(V(.42, .004 + (1 - a) ** 2 * .5, .52), N(V(0, 1, .0)), V(-.5, 0, -1), .16, .08, front=6))
        sx, sy = proj(s, V(.42, .01, .52)); gl = sm(.45, .6, t) * (1 - sm(1.2, 1.9, t))
        s['part'] = (sx, sy, gl * (.7 + .5 * kick(T)), 3); s['partC'] = (1., .8, .4, 0)
    sp = sm(5.79, 6.2, t)
    s['sp0'] = (0., 2.4, .0, .9965); s['sp0d'] = (0, -1, 0, .002); s['sp0c'] = (3.5 * sp, 3.3 * sp, 2.8 * sp, sp)
    s['amb'] = 1.2 * dim + .2
    return s
def sB4(t, d, T):
    s = base('desknight'); s['setA'] = (10., 1, 0, 0)
    up = sm(5.0, 7.2, t) ** 2
    s['setB'] = (1., 1.9, 3. * sm(6.5, 7.3, t), 0.)
    cam(s, V(.5 - .3 * up, .56 + 1.25 * up, .78 - .5 * up), V(0, .95 + 3. * up, 0), 50.); s['focus'] = .9; s['ap'] = .008
    s['pl0'] = (0.3, 1.4, 0.5, .8); s['pl0c'] = (1., 1.4, 2.4, 1.)
    s['chars'].append(ch(V(0, .7, 0), yaw=.55, sc=.055, lean=-.45))
    s['amb'] = .3
    return s
def sB5(t, d, T):
    s = base('dusk'); u = cl(t / d)
    a = PP(27.)
    ro = mix(V(-7.5, a[1] + 1.2, 13.5), V(-6., a[1] + 1.8, 16.5), u)
    cam(s, ro, a + V(.5, .8, 0), 40.); s['glow'] = (0, 0, 1.3, 99); s['focus'] = 16.; s['tilt'] = .02
    return s
def sB6a(t, d, T):
    s = base('morning'); S = W.SUM; u = cl(t / d)
    ro = G(S[0] - 1.2, S[2] - 5.5 + .5 * u, .5)
    cam(s, ro, S + V(0, .2, 0), 42.)
    s['sunD'] = N(S + V(.25, .55, 0) - ro); s['sunC'] = V(1., .78, .4) * 2.2; s['snowL'] = 7.; s['clA'] = 0.; s['fogD'] = .02; s['fogH'] = .001
    s['fogC'] = V(1., .85, .6); s['skH'] = V(1., .85, .6)
    return s
def FEET(): return G(7., 17.)
def sB6b(t, d, T):
    s = base('noon'); P = FEET(); s['snowL'] = -2.; s['snowA'] = .25; s['fogD'] = .06; s['fogH'] = .001; s['fogC'] = V(.85, .88, .93); s['clA'] = 0.
    k = sm(-.1, .7, t)
    cam(s, P + V(.04, .46, -.56), mix(P + V(0, .5, 2.), P + V(0, .0, -.1), k), 44.); s['focus'] = .68; s['ap'] = .008
    s['chars'].append(ch(P, yaw=pi, lean=.15))
    s['items'].append(it(G(P[0] - .13, P[2] - .09, .014), N((.08, 1, .05)), .9, .11, (1, 1, 1), 5))
    s['items'].append(it(G(P[0] + .13, P[2] - .07, .03), (0, 0, 1), 0., .07, (1, 1, 1), 6))
    s['items'].append(it(G(P[0] + .01, P[2] - .17, .008), N((.05, 1, .12)), .35, .05, (1, 1, 1), 7))
    s['pl0'] = tuple(G(P[0] + .01, P[2] - .17, .05)) + (300.,); s['pl0c'] = (.5, .9, .6, 1.)
    return s
RK = V(40., 22., 40.)
def sB7(t, d, T):
    s = base('above'); s['sets'] = 4; s['clY'] = 21.5; s['clCov'] = 1.; u = cl(t / d)
    blend(s, 'mist', .35 * u); s['fogD'] = .004 + .03 * u
    st = beat(T) - beat(65.48) + .2
    n = math.floor(st); fr = st - n; a = sm(.25, .8, fr)
    def RP(i): return V(RK[0] + (h11(i * 1.7 + 2.) - .5) * .05 + ((i % 2) - .5) * .09, RK[1] + .034, RK[2] + i * .17)
    P = mix(RP(n), RP(n + 1), a) + V(0, .05 * math.sin(pi * a), 0)
    wob = (.3 + 1.2 * u)
    s['chars'].append(ch(P, yaw=.0, ph=pi * st, lean=.2 + .12 * math.sin(T * 9.) * u, arm=.5 * math.sin(pi * a) + .3 * u * math.sin(T * 11.)))
    ro = P + V(.05 + .03 * wob * math.sin(T * 7.3), .46, -.2 + .02 * wob * math.sin(T * 5.1))
    cam(s, ro, P + V(.01 * wob * math.sin(T * 9.), 0, .12), 52., .05 * wob * math.sin(T * 4.3)); s['focus'] = .5; s['ap'] = .012
    s['rkO'] = tuple(RK) + (st + a * .0,)
    s['pulse'] = .014 * math.sin(T * (4. + 5. * u)) + .02 * kick(T); s['vig'] = .5 * u; s['eblur'] = u; s['desat'] = .25 * u
    return s
def sB8(t, d, T):
    s = base('mist'); s['sets'] = 4; top = V(40., 22.6, 42.6); s['setB'] = tuple(top) + (1.,); s['rkO'] = tuple(RK) + (99.,)
    blend(s, 'above', .6); s['fogD'] = .1; s['mistA'] = .8; s['clCov'] = 1.; s['clY'] = 22.2; s['clA'] = 1.; u = cl(t / d)
    a = 2 * pi * u * .9 + .6
    c = top + V(0, .012, 0)
    s['chars'].append(ch(c, yaw=a + 2.2 + 1.2 * math.sin(T * 1.1), lean=-.1))
    cam(s, c + V(math.cos(a) * 1.05, .32, math.sin(a) * 1.05), c + V(0, .08, 0), 40.); s['focus'] = 1.05; s['ap'] = .01
    return s
def sB9(t, d, T):
    s = base('snow'); u = cl(t / d)
    for k in ('sunC', 'skT', 'skM', 'skH', 'fogC'): s[k] = s[k] * .62
    s['sunC'] = s['sunC'] * 1.6; s['amb'] = 1.1
    eye = PP(33.5, .078); S = W.SUM + V(0, 1.4, 0); dd = N(S - eye)
    yaw = math.atan2(dd[0], dd[2]); pitch = math.asin(dd[1])
    pov(s, eye, yaw, pitch - .04, T, .8, .7, 60.)
    s['lone'] = tuple(dd) + (1.2 + .4 * math.sin(T * 5.),); s['lsnow'] = .8; s['fogD'] = .035; s['vig'] = .5; s['eblur'] = .5
    pull = sm(.3, .7, t) * (1 - sm(1.1, 1.4, t)) + sm(1.9, 2.3, t)
    hands(s, y=-.036 + .01 * pull, spread=.06 - .026 * pull, z=.09)
    return s
def sB10(t, d, T):
    s = base('snow'); S = W.SUM; u = cl(t / d)
    for k in ('sunC', 'skT', 'skM', 'skH', 'fogC'): s[k] = s[k] * .5
    s['fogD'] = .07; s['snowA'] = .7 + .6 * u
    door = S + V(0, .36, 0)
    s['items'].append(it(door, (0, 0, -1), 0., .56, (1, 1, 1), 9))
    s['pl0'] = tuple(door + V(0, 0, -.25)) + (2.5,); s['pl0c'] = (2.6, 1.9, .9, 2.)
    x = beat(T)
    c = ch(G(S[0] + .02, S[2] - .5, .02 * abs(math.sin(pi * x))), yaw=0., arm=1.)
    s['chars'].append(c)
    bp = backplane(c)
    tau = t - 2.3
    if tau > 0:
        bp['p'] = bp['p'] + V(1.4 * tau, .5 * tau + .6 * tau * tau, -.5 * tau); bp['roll'] = tau * 9.; bp['f'] = N(V(1, .4 * math.sin(tau * 7.), math.cos(tau * 5.)))
    s['items'].append(bp)
    ro = G(S[0] + .3, S[2] - 1.5, .28)
    cam(s, ro + V(-.1 * u, 0, .15 * u), mix(door + V(0, -.1, 0), bp['p'], .5 * sm(2.3, 3.2, t)), 44.); s['focus'] = 1.2
    s['part'] = (0, 0, 1., 2); s['partC'] = (1., .78, .32, 0)
    return s

def sC7(t, d, T):
    s = base('rain'); x0 = -1.3; zs = shoreZ(x0)
    P = G(x0, zs + .13)
    reach = sm(.7, 1.1, t)
    s['chars'].append(ch(P, yaw=pi + .45, sit=1., med=1., lean=.25 * reach, arm=-reach, eye=1 if t < 1.25 else 0))
    pw = V(x0 + .03, .006 + .003 * math.sin(T * 3.), zs - .09)
    lift = sm(1.1, 1.7, t)
    pp = mix(pw, P + V(.0, .085, -.07), lift)
    s['items'].append(it(pp, N((.6, .05 + .5 * lift, -1.)), .1 * math.sin(T * 2.) * (1 - lift), .06, (.62, .66, .74), 0))
    ro = P + mix(V(.36, .12, -.46), V(.3, .1, -.38), sm(0., 1.9, t))
    cam(s, ro, P + V(.02, .05, -.07), 40.); s['focus'] = float(np.linalg.norm(ro - P)); s['ap'] = .014
    s['pl0'] = tuple(ro + V(-.2, .25, .1)) + (5.,); s['pl0c'] = (.5, .62, 1., 1.)
    lightning(s, T, [110.9], 13.)
    return s

def sD1(t, d, T):
    s = base('dawn'); s['film'] = 1.; s['clA'] = .3
    P = G(0., 8.3)
    s['chars'].append(ch(P, yaw=0., sc=.075, arm=sm(.9, 1.6, t), lean=-.3 * sm(.9, 1.6, t)))
    cam(s, P + V(.1, .035, -.32 - .03 * t), V(0, 9. + .3 * t, 36.), 46.); s['focus'] = .4; s['ap'] = .006
    return s
def sD2(t, d, T):
    # third person: cresting the ridge line - and on the far side there is just another foot of another mountain
    s = base('night'); u = cl(t / d); s['sunC'] = s['sunC'] * 1.5; s['amb'] = 1.4; s['starA'] = 1.3; s['fogD'] = .008
    z = mix(16.35, 17.0, u); P = G(7., z); k = sm(.3, .9, u)
    s['chars'].append(ch(P, yaw=0., ph=walk_ph(T) * (1 - sm(.85, 1., u)), lean=.22 * (1 - k)))
    ro = mix(G(6.82, z - .5, .1), V(6.85, G(7., 17.)[1] + .3, 16.55), k)
    cam(s, ro, mix(P + V(0, .12, 0), P + V(.3, .3, 6.), k), 44.); s['focus'] = mix(.55, 5., sm(.75, 1., u)); s['ap'] = .012 * (1 - sm(.75, 1., u))
    s['pl0'] = tuple(ro + V(.2, .15, 0)) + (5.,); s['pl0c'] = (.5, .6, 1., 1.)
    return s
def sD3(t, d, T):
    s = base('night'); P = G(7., 17.); u = cl(t / d)
    off = sm(.9, 1.5, t)
    c = ch(P, yaw=pi + .35, med=1. - off if off < 1 else 0., arm=sm(1.3, 1.9, t), lean=-.25 * sm(1.3, 2.2, t), eye=1 if t < .9 else (2 if t > 1.9 else 0))
    s['chars'].append(c)
    ro = P + V(.3, .08, -.62); dd = ro - P; c['yaw'] = math.atan2(dd[0], dd[2])
    s['pl0'] = tuple(ro + V(.1, .12, 0)) + (4.,); s['pl0c'] = (1.3, .95, .6, 1.)
    cam(s, ro, P + V(0, .07 + .5 * sm(1.8, 4.2, t), 0), 42.); s['focus'] = .68; s['ap'] = .008
    sx, sy = proj(s, P + V(0, .07, 0))
    s['part'] = (sx, sy, sm(.9, 1.4, t), 1); s['partC'] = (1., .8, .35, 0)
    return s
def sD4(t, d, T):
    s = base('night'); s['amb'] = 1.1
    x = -3.3 + .85 * t; zs = shoreZ(x)
    P = G(x, zs + .1)
    bx = beat(T)
    s['chars'].append(ch(P, yaw=pi / 2, ph=walk_ph(T, 2.), lean=.3))
    wave = .035 * math.sin(pi * bx)
    cam(s, P + V(.45, .1 + wave, -1.35), P + V(.35, .09 + wave * .4, .3), 42., .03 * math.sin(pi * bx * .5)); s['focus'] = 1.4; s['ap'] = .012
    return s
def sD5a(t, d, T):
    s = base('night'); P = PP(19.2); s['domeA'] = .8; s['rainA'] = .35; s['wet'] = .6
    k = sm(.9, 1.3, t)
    c = ch(P, yaw=pi + .3, arm=-1., lean=.1, eye=2 if t > 1.3 else 0); s['chars'].append(c)
    f = dirYP(c['yaw'], 0.)
    hp = P + f * .062 + V(0, .055, 0)
    if k < .5: s['notes'].append(note(hp, N(V(0, 1, 0) + f * .5), f, .05, .028, front=0, bend=.25 * (1 - sm(0, .8, t))))
    else: s['items'].append(it(hp + V(0, .01, 0), N(f + V(0, .3, 0)), 0., .06, (.9, .92, .96), 0))
    cam(s, P + f * .4 + V(.1, .09, 0), P + V(0, .06, 0), 40.); s['focus'] = .41; s['ap'] = .02
    s['pl0'] = tuple(P + f * .4 + V(-.15, .25, 0)) + (5.,); s['pl0c'] = (.6, .68, 1., 1.)
    s['part'] = proj(s, hp) + (sm(1.0, 1.2, t) * (1 - sm(1.3, 1.9, t)) * .7, 3)
    return s
def sD5b(t, d, T):
    s = base('night'); s['domeA'] = 1.; s['rainA'] = .3 * (1 - sm(0, 2., t)); s['wet'] = .5
    z = 19.3 + .14 * t; P = PP(z)
    c = ch(P, yaw=yawP(z), ph=walk_ph(T), lean=.32, heart=.7 + 1.3 * kick(T)); s['chars'].append(c)
    s['items'].append(backplane(c))
    f = N(PP(z + .5) - P)
    cam(s, P + f * (.75 + .05 * t) + V(.12, .16, 0), P + V(0, .06, 0), 40.); s['focus'] = .8; s['ap'] = .012
    lightning(s, T, [131.4, 132.6], 17.); s['ltn'] = (s['ltn'][0] * .5, s['ltn'][1], .5, 0)
    s['skH'] = V(.1, .12, .2)
    return s
def sD6(t, d, T):
    s = base('desknight'); s['setA'] = (0, 1, 0, 0); u = cl(t / d)
    cam(s, V(.12, .3 - .02 * u, .34), V(.0, 0, .01), 30.); s['ap'] = .05; s['focus'] = .46
    s['pl0'] = (.5, .68, -.14, 1.2); s['pl0c'] = (1.9, 1.3, .7, 1.)
    rev = mix(.1, .58, u)
    up = N(V(.12, 0, -1)); n0 = note(V(0, .003, 0), V(0, 1, 0), up, .2, .1, front=1, rev=rev)
    s['notes'].append(n0)
    tip = n0['p'] + n0['U'] * (2 * rev - 1.) + n0['V'] * (.1 * math.sin(T * 14.)) + V(0, .004, 0)
    pf = N(V(-.35, .75, .5))
    s['items'].append(it(tip + pf * .085, -pf, 0., .17, (.95, .75, .2), 8))
    s['items'].append(it(tip + pf * .1 + V(.02, .0, .03), (0, 0, 1), .3, .06, ORANGE, 10))
    return s
def sD7(t, d, T):
    s = base('night'); u = cl(t / d); y = W.stY
    s['chars'].append(ch(V(.21, y + 1.065, -.03), yaw=pi, sit=1.))
    cam(s, mix(V(.5, y + 1.2, .62), V(.95, y + 1.7, 2.1), ease(u)), mix(V(.18, y + 1.13, -.4), V(0, y + 2.9, -6.), ease(u)), 40.); s['focus'] = mix(.7, 1.9, ease(u)); s['ap'] = .008
    s['starA'] = 1.4
    s['pl0'] = tuple(ORB() + V(0, -.02, .12)) + (2.2,); s['pl0c'] = (2.6, 1.6, .7, 1.)
    return s
def sD8a(t, d, T):
    s = base('night'); u = cl(t / 1.5); h = 2.4 * math.exp(u * 3.9)
    cam(s, V(0, h, -.35 * h), V(0, W.stY + 1.2, 0), 40., u * .6); s['fogD'] = .003; s['tmaxS'] = 120.
    s['chars'].append(ch(V(.21, W.stY + 1.065, -.03), yaw=pi, sit=1.))
    return s
def sD8b(t, d, T):
    s = base('night'); s['stage'] = 2; s['setA'] = (cl((t + .3) / 1.8), 0, 0, 0)
    return s
def fly(T):
    tt = T - 143.0; sd = 6. * tt + .5 * tt * tt * .6
    def P(a): return V(-46. + a, 0, 23. + 2.6 * math.sin(a * .21) + 1.2 * math.sin(a * .083 + 1.))
    c = P(sd)
    hs = W.ghs([(c[0], c[2]), (P(sd + 1.3)[0], P(sd + 1.3)[2]), (P(sd + 2.8)[0], P(sd + 2.8)[2])], 3)
    c[1] = max(hs) + .62
    f = N(P(sd + 1.) - c); f[1] = 0; f = N(f)
    return c, f, sd
def sD9(t, d, T):
    s = base('predawn'); c, f, sd = fly(T); tt = T - 143.0
    blend(s, 'morning', .3 + .7 * sm(1.5, 6., tt)); s['clA'] = .6; s['clY'] = 2.3; s['amb'] = 1.3; s['mistA'] = .25; s['expo'] = 1.1 + .15 * kick(T)
    r = N(np.cross(V(0, 1, 0), f))
    wv = math.sin(tt * 1.9); bank = -.5 * math.cos(tt * 1.9)
    pl = c + f * 1.0 + r * .28 * wv + V(0, -.08 + .05 * math.sin(tt * 3.1), 0)
    s['items'].append(it(pl, N(f + r * .25 * math.cos(tt * 1.9)), bank, .16, (1, 1, 1), 0))
    cam(s, c, c + f * 3. + V(0, -.25, 0) + r * .1 * wv, 58., .12 * math.sin(tt * .9) + bank * .15); s['focus'] = 1.; s['radial'] = .55
    if tt > 5.4:
        for i in range(6):
            a = sm(5.5 + i * .22, 6.6 + i * .22, tt)
            if a <= 0: continue
            side = 1 if i % 2 else -1
            off = r * side * (.3 + .22 * (i // 2)) * mix(3., 1., a) + f * (1.1 - .32 * (i // 2) - (1 - a) * 2.) + V(0, .1 * math.sin(tt * 2.5 + i) + .05 * (i // 2), 0)
            s['items'].append(it(c + off + V(0, -.05, 0), N(f + r * .1 * math.sin(tt * 2. + i)), .3 * math.sin(tt * 2.2 + i * 1.3), .1, PALS[i], 0))
    return s
STRIP = None
def sD11(t, d, T):
    s = base('night'); s['strip'] = dict(off=-.2 + t * 1.05, warm=sm(.3, 3.6, t))
    return s
def sD12(t, d, T):
    s = base('morning'); S = G(7., 17.); u = cl(t / d); x = beat(T)
    s['clY'] = S[1] - .35; s['clA'] = 1.; s['fogD'] = .006
    ppl = [(0., -.02, ORANGE)] + [(.2 * (i - 2.5) + .08, .12 * math.cos(i * 2.1) + .08 * ((i % 2) * 2 - 1), PALS[i]) for i in range(5)]
    thr = sm(.45, .7, t)
    for i, (dx, dz, col) in enumerate(ppl):
        hop = .03 * abs(math.sin(pi * (x + i * .37)))
        p = G(S[0] + dx * .75, S[2] - .04 + dz * .5, hop)
        c = ch(p, yaw=pi + (dx * 1.2), arm=1., col=col, hat=1 if t < .55 else 0, eye=2, med=0 if i == 0 else -1)
        s['chars'].append(c)
        if t >= .55:
            tau = t - .55; v0 = V((h11(i + 1.) - .5) * .2, .62 + .2 * h11(i + 3.), -.05 + (h11(i + 5.) - .5) * .1)
            hp = p + V(0, .1, 0) + v0 * tau + V(0, -.3, 0) * tau * tau
            if hp[1] > p[1] - .3:
                s['items'].append(it(hp, N(V(math.sin(tau * 5 + i), .3, math.cos(tau * 5 + i))), tau * 6. + i, .06, (.05, .05, .08), 1))
    tp = t - 1.2
    s['items'].append(it(S + V(-.9 + .7 * tp, .36 + .06 * math.sin(tp * 1.5), -.2 + .05 * tp), N((1, .12 * math.cos(tp * 1.5), .08)), .25 * math.sin(tp * 2.), .1, (1, 1, 1), 0))
    a = .25 * u
    ro = S + V(.3 - .25 * u, .08 + .04 * u, -.85)
    cam(s, ro, S + V(0, .03 + .06 * u, 0), 44.); s['focus'] = .85; s['ap'] = .006
    s['part'] = (0, 0, thr, 2); s['partC'] = (1., .72, .22, 1.)
    return s

def sE1b(t, d, T):
    s = base('sunset'); z = 15.2 + .05 * t; P = PP(z); s['clA'] = .3
    turn = sm(.2, .9, t)
    c = ch(P, yaw=mix(yawP(z), pi + .25, turn), hat=1, eye=2 if t > .8 else 0, arm=.9 * sm(1., 1.5, t) * (.7 + .3 * math.sin(T * 9.)))
    s['chars'].append(c)
    k = sm(0., 2.2, t); ro = G(P[0] + .2 - .05 * k, P[2] - .5 + .14 * k, .08)
    cam(s, ro, P + V(0, .09, 0), 40.); s['focus'] = float(np.linalg.norm(ro - P)); s['ap'] = .016
    return s
def sE5(t, d, T):
    s = base('sunset'); x = 10.5 + .22 * t; zz = 14.6
    P = G(x, zz); nx = G(x + .3, zz); f = N(nx - P); s['clA'] = .4
    c = ch(P, yaw=pi / 2, ph=walk_ph(T), hat=1); s['chars'].append(c)
    s['items'].append(it(P - V(.1, 0, .0) + V(0, .05, .05), N((.35, 1., 0)), 0., .07, (.25, .35, .6), 3))
    Pm = G(11., zz); ro = viewpos(Pm, .8, .1, -pi / 2 - .3, .08); g = N((Pm - ro) * V(1, 0, 1))
    cam(s, ro, Pm + g * .4 + V(0, .1, 0), 40.); s['focus'] = .8; s['ap'] = .008
    return s
def NEWP(): return G(.36, -.86)
def sE6(t, d, T):
    s = base('sunset'); u = cl(t / d); y = W.stY; P = NEWP()
    c = ch(P, yaw=.1, col=BLUE, med=-1, lean=-.35 * sm(.3, .8, u)); s['chars'].append(c)
    s['items'].append(it(P + V(.11, .045, .0), N((0, 1., .12)), 0., .075, (.85, .85, .9), 3))
    cam(s, mix(V(1.0, y + .1, -1.9), V(.85, y + .22, -2.1), u), mix(V(.2, y + .5, 1.), V(0, y + 3.8, 20.), sm(.25, .95, u)), 40.); s['focus'] = 1.2; s['ap'] = .012
    return s
def e7path(u):
    y = W.stY; P = NEWP()
    return spl([(0, V(0, y + .16, 2.1)), (.3, V(.9, y + 1.35, 1.1)), (.7, V(1.0, y + .75, -.3)), (1., P + V(.07, .012, .08))], u)
def sE7a(t, d, T):
    s = base('sunset'); u = cl(t / 2.1); y = W.stY; P = NEWP()
    c = ch(G(0, 2.2), yaw=pi - .4, hat=1, eye=2, arm=1. - .5 * sm(.3, .8, t)); s['chars'].append(c)
    s['chars'].append(ch(P, yaw=.1 + .9 * sm(1.6, 2.2, t), col=BLUE, med=-1))
    s['items'].append(it(P + V(.11, .045, .0), N((0, 1., .12)), 0., .075, (.85, .85, .9), 3))
    e = sm(0, 1, u) * .6 + u * .4
    pl = e7path(e); f = N(e7path(min(e + .02, 1.02)) - pl) if u < 1 else N((-.6, .0, -1.))
    s['items'].append(it(pl, f, .2 * math.sin(u * 5.) * (1 - u), .075, (1, 1, 1), 0))
    cam(s, mix(V(2.4, y + .55, .4), V(1.25, y + .16, -1.5), ease(u)), mix(pl, P + V(0, .05, 0), sm(.8, 1.1, u)), 38.); s['focus'] = float(np.linalg.norm(s['ro'] - pl)); s['ap'] = .012
    return s
def sE7b(t, d, T):
    s = base('sunset'); P = NEWP(); y = W.stY
    eye = P + V(0, .085, 0)
    pov(s, eye, .12, .16, T, .25, 0., 56.); s['focus'] = .11; s['ap'] = .035
    uu, vv, ww, fl = basis(s)
    a = sm(1.05, 1.6, t) * pi
    n = N(-ww + vv * .3); up = N(vv + ww * .3)
    r = N(np.cross(n, up))
    n2 = n * math.cos(a) + r * math.sin(a)
    rise = sm(-.3, .35, t)
    s['notes'].append(note(C2W(s, (0., mix(-.07, .0, rise), .115)), n2, up, .05, .025, front=0, back=1, bend=.1 * (1 - rise)))
    hands(s, BLUE, y=mix(-.08, -.02, rise), spread=.058, z=.11, sc=.016)
    return s
def sZ1(t, d, T):
    s = base('sunset'); y = W.stY; P = NEWP(); u = cl(t / 5.3)
    keys = [(0, P + V(0, .12, .05)), (.12, V(.2, y + .8, -1.6)), (.3, V(-.6, y + 1.7, -.6)), (.55, V(-.9, 3.2, 5.)), (1., V(-1.6, 7.5, 17.))]
    e = sm(0., .25, u) * .25 + .75 * max(u - .0, 0) ** 1.3 if False else u ** 1.15
    pl = spl(keys, e); f = N(spl(keys, e + .01) - pl)
    s['items'].append(it(pl, f, .25 * math.sin(t * 1.3), .09, (1, 1, 1), 0))
    s['chars'].append(ch(P, yaw=pi * (1 - sm(.4, 1.2, t)), col=BLUE, med=-1, arm=1. - sm(.5, 1.5, t) * .6))
    k = sm(.0, .25, u)
    ro = mix(P + V(.5, .12, -.7), pl - f * .55 + V(.12, .14, 0), k)
    cam(s, ro, mix(pl, pl + f * 2. + V(.6, .2, 0), k * .6), 46.); s['focus'] = .6; s['glow'] = (.5 * sm(.4, 1., u), 0, 0, 40.)
    return s

def mk(fn, *a): return lambda t, d, T: fn(t, d, T, *a)
# (start, name, fn, transition, duration)
SH = [
 (0.0, 'P00', sP00, 'cut', 0), (2.95, 'A1', mk(sGate, 0), 'dis', .8), (10.5, 'A2', mk(sZig, 0), 'dis', .6), (14.44, 'A3', mk(sFog, 0), 'dis', .6),
 (18.72, 'A4', mk(sPeak, 0), 'cut', .3), (22.1, 'A5', sDeskA, 'dis', .5), (26.2, 'A6', mk(sStairs, 0), 'dis', .5), (32.74, 'A7', sThrow, 'cut', .2),
 (33.92, 'B1', sB1, 'cut', 0), (38.42, 'B2a', sB2a, 'cut', 0), (40.5, 'B2b', sB2b, 'white', .7), (42.4, 'B3', sB3, 'dis', .4),
 (50.12, 'B4', sB4, 'cut', 0), (57.6, 'B5', sB5, 'white', .8), (61.62, 'B6a', sB6a, 'dis', .5), (63.8, 'B6b', sB6b, 'dis', .35),
 (65.48, 'B7', sB7, 'cut', .2), (69.04, 'B8', sB8, 'dis', .5), (72.94, 'B9', sB9, 'cut', .2), (76.8, 'B10', sB10, 'dis', .5),
 (80.68, 'C1', mk(sGate, 1), 'storm', 1.0), (88.5, 'C2', mk(sZig, 1), 'dis', .6), (91.88, 'C3', mk(sFog, 1), 'cut', .3), (96.14, 'C4', mk(sPeak, 1), 'cut', .2),
 (99.52, 'C5', sDeskC, 'dis', .5), (103.46, 'C6', mk(sStairs, 1), 'dis', .5), (110.2, 'C7', sC7, 'dis', .5),
 (112.5, 'D1', sD1, 'flip', .7), (115.86, 'D2', sD2, 'cut', .2), (119.6, 'D3', sD3, 'page', .7), (124.0, 'D4', sD4, 'whip', .4),
 (128.78, 'D5a', sD5a, 'whip', .35), (130.9, 'D5b', sD5b, 'dis', .4), (133.52, 'D6', sD6, 'cut', 0), (136.4, 'D7', sD7, 'whip', .4),
 (140.18, 'D8a', sD8a, 'dis', .4), (141.5, 'D8b', sD8b, 'dis', .6), (143.0, 'D9', sD9, 'white', .5), (150.58, 'D11', sD11, 'dis', .4),
 (154.56, 'D12', sD12, 'white', .5),
 (160.2, 'E1', mk(sGate, 2), 'cut', 0), (164.9, 'E1b', sE1b, 'dis', .5), (167.28, 'E2', mk(sZig, 2), 'dis', .6), (171.16, 'E3', mk(sFog, 2), 'dis', .6),
 (175.5, 'E4', mk(sPeak, 2), 'dis', .5), (178.88, 'E5', sE5, 'dis', .6), (182.86, 'E6', sE6, 'dis', .6), (186.62, 'E7a', sE7a, 'cut', 0),
 (188.9, 'E7b', sE7b, 'dis', .4), (191.3, 'Z1', sZ1, 'dis', .6),
]
SHN = {s[1]: s for s in SH}
TRK = dict(dis=1, white=2, storm=3, flip=4, page=5, whip=6)
def shot_dur(i): return (SH[i + 1][0] if i + 1 < len(SH) else DUR) - SH[i][0]
def shot_state(T):
    idx = 0
    for i, s in enumerate(SH):
        if T >= s[0] - (s[4] / 2 if s[3] != 'cut' else 0): idx = i
    s = SH[idx]; flash = 0.
    if s[3] == 'cut':
        if s[4] > 0 and T >= s[0]: flash = s[4] * math.exp(-(T - s[0]) * 7.)
        return (idx, None, 0, 0., flash)
    if idx > 0 and T < s[0] + s[4] / 2:
        x = (T - (s[0] - s[4] / 2)) / s[4]
        return (idx - 1, idx, TRK[s[3]], sm(0, 1, x) if s[3] == 'dis' else x, 0.)
    return (idx, None, 0, 0., 0.)
def eval_shot(i, T):
    s = SH[i]; return s[2](T - s[0], shot_dur(i), T)
def fade(t):
    f = sm(0, 1.4, t)
    f *= 1 - sm(158.3, 159.2, t) * (1 - sm(159.9, 160.6, t))
    f *= 1 - sm(194.6, 196.4, t)
    return f

# ---------------------------------------------------------------- text
def tf(name, *alts):
    # Windows font first; fall back to Linux fonts so previews can be rendered off the main machine
    for pth in [os.path.join(r'C:\Windows\Fonts', name)] + list(alts):
        if os.path.exists(pth):
            t = skia.Typeface.MakeFromFile(pth)
            if t: return t
    return skia.Typeface.MakeDefault()
_LF = '/usr/share/fonts/'
TF_LYR = tf('NotoSerifSC-VF.ttf', _LF + 'opentype/noto/NotoSerifCJK-Regular.ttc', _LF + 'truetype/wqy/wqy-zenhei.ttc')
TF_TITLE = tf('STXINGKA.TTF', _LF + 'truetype/arphic/ukai.ttc')
TF_KAI = tf('STKAITI.TTF', _LF + 'truetype/arphic/ukai.ttc')
TF_EN = tf('NotoSerif-Regular.ttf', _LF + 'truetype/dejavu/DejaVuSerif.ttf', _LF + 'opentype/noto/NotoSerifCJK-Regular.ttc')
LYR = []
for ln in open(os.path.join(HERE, 'lyrics_timed.tsv'), encoding='utf8').read().strip().split('\n')[1:]:
    a_, b_, tx_ = ln.split('\t'); LYR.append([float(a_), float(b_), tx_.strip()])
for i in range(len(LYR)):
    nxt = LYR[i + 1][0] if i + 1 < len(LYR) else 1e9
    LYR[i].append(min(.3, max(nxt - LYR[i][1] - .02, .06)))   # fade-out time, never overlapping the next line

def make_atlas():
    Wd, Hd = 2048, 2048; cw, chh = 512, 256
    surf = skia.Surface.MakeRaster(skia.ImageInfo.Make(Wd, Hd, skia.kRGBA_8888_ColorType, skia.kPremul_AlphaType)); c = surf.getCanvas(); c.clear(skia.Color(0, 0, 0, 255))
    def P(col, **kw): return skia.Paint(AntiAlias=True, Color=skia.Color(*col), **kw)
    def cell(i): return (i % 4) * cw, (i // 4) * chh
    def ctext(i, txt, size, col, y, face=TF_KAI, dx=0):
        f = skia.Font(face, size); x0, y0 = cell(i); w = f.measureText(txt); c.drawString(txt, x0 + cw / 2 - w / 2 + dx, y0 + y, f, P(col))
    def paper(i, col=(240, 236, 224, 255)):
        x0, y0 = cell(i); c.drawRect(skia.Rect.MakeXYWH(x0, y0, cw, chh), P(col))
    def lines(i, y0_, n, col=(120, 120, 130, 255), x1=60, x2=452, gap=26):
        x0, y0 = cell(i)
        for k in range(n): c.drawRect(skia.Rect.MakeXYWH(x0 + x1, y0 + y0_ + k * gap, (x2 - x1) * (.6 + .4 * h11(i * 7 + k)), 6), P(col))
    ink = (36, 34, 48, 255)
    paper(0); ctext(0, '我为什么出发？', 68, ink, 150)
    paper(1); ctext(1, '别忘了出发时的样子', 52, ink, 146)
    paper(2, (250, 242, 225, 255)); x0, y0 = cell(2); c.drawRect(skia.Rect.MakeXYWH(x0 + 10, y0 + 10, cw - 20, chh - 20), P((190, 40, 35, 255), Style=skia.Paint.kStroke_Style, StrokeWidth=8))
    ctext(2, '录取通知书', 72, (190, 40, 35, 255), 112); lines(2, 150, 3, (150, 110, 90, 255), 110, 400)
    paper(3); ctext(3, '课 程 表', 44, ink, 56); x0, y0 = cell(3)
    for r in range(4):
        for q in range(6):
            col = [(235, 200, 120), (150, 200, 220), (220, 160, 160), (170, 210, 160), (240, 236, 224)][int(h11(r * 7 + q * 3 + 1.) * 5)]
            c.drawRect(skia.Rect.MakeXYWH(x0 + 40 + q * 73, y0 + 78 + r * 42, 67, 36), P(col + (255,)))
    paper(4); ctext(4, '四六级报名表', 50, ink, 64); lines(4, 96, 5)
    paper(5); ctext(5, '成绩单', 46, ink, 58, dx=-120); ctext(5, 'GPA 3.92', 46, (190, 40, 35, 255), 58, face=TF_EN, dx=110); lines(5, 92, 5)
    paper(6, (252, 232, 170, 255)); x0, y0 = cell(6); c.drawRect(skia.Rect.MakeXYWH(x0 + 12, y0 + 12, cw - 24, chh - 24), P((200, 140, 30, 255), Style=skia.Paint.kStroke_Style, StrokeWidth=10))
    ctext(6, '奖  状', 86, (190, 40, 35, 255), 130); lines(6, 168, 2, (180, 140, 70, 255), 130, 380)
    x0, y0 = cell(7); c.drawRect(skia.Rect.MakeXYWH(x0, y0, cw, chh), P((14, 22, 30, 255)))
    ctext(7, '妈妈', 110, (240, 245, 250, 255), 120, face=TF_LYR); ctext(7, '来电…', 60, (120, 230, 150, 255), 215, face=TF_LYR)
    for k, txt in enumerate(['OFFER', '保研', '获奖', 'GPA 4.0', '国奖', '实习', '竞赛', '论文']):
        i = 8 + k; x0, y0 = cell(i)
        c.drawRoundRect(skia.Rect.MakeXYWH(x0 + 8, y0 + 8, cw - 16, chh - 16), 30, 30, P((70, 70, 70, 255), Style=skia.Paint.kStroke_Style, StrokeWidth=8))
        ctext(i, txt, 120 if len(txt) < 4 else 96, (255, 255, 255, 255), 168, face=TF_LYR if ord(txt[0]) > 255 else TF_EN)
    for k in range(8):
        i = 16 + k; paper(i, (245, 243, 236, 255)); ctext(i, str(12 + k), 150, ink, 160, face=TF_EN, dx=-90)
        ctext(i, ['考试', '考试', 'DDL', '考试', '答辩', '考试', 'DDL', '考试'][k], 70, (200, 40, 35, 255), 150, face=TF_LYR, dx=130)
    return surf.makeImageSnapshot().toarray(colorType=skia.kRGBA_8888_ColorType, alphaType=skia.kPremul_AlphaType)

HERO = {'踩着巨人肩膀把你送到山脚': '山脚', '会发现一山比一山高': '一山比一山高', '不如问问自己为何全力以赴': '为何',
 '就像那句「只有天空才是极限」': '天空才是极限', '脚底下的步伐越来越飘': '飘', '不必留恋 曾经堆满筹码的桌上': '不必留恋',
 '当我站在巨人肩膀上能看到更加辽阔以后': '巨人肩膀', '谁还不是一粒微小尘埃活在这个茫茫宇宙': '尘埃',
 '比起独孤求败更加热血澎湃': '热血澎湃', '新的游戏继续到了下一关': '下一关'}
HERO_SKIP = {0}   # the opening title already says it (the last '一山比一山高' is added below: it would cover the note)
HERO_SKIP.add(max(i for i, l in enumerate(LYR) if l[2] == '会发现一山比一山高'))
def section(a):
    if a < 33.9 or 80.6 <= a < 112. or a >= 160.: return 'chorus'
    if a < 80.6: return 'verse'
    return 'rap'
def hero_spec(i):
    a, b, txt, fo = LYR[i]; ph = HERO.get(txt)
    if not ph or i in HERO_SKIP: return None
    n = len(ph); vert = section(a) == 'chorus' and ph != '一山比一山高'
    size = {1: 300, 2: 215, 3: 175, 4: 150}.get(n, 118)
    if ph == '尘埃': size = 46
    if ph == '一山比一山高': return dict(ph=ph, vert=False, size=96, w=760, h=420)
    if vert: return dict(ph=ph, vert=True, size=size, w=size * 1.05, h=n * size * 1.02)
    return dict(ph=ph, vert=False, size=size, w=n * size * 1.04, h=size * 1.1)
def hero_end(i):
    a, b = LYR[i][0], LYR[i][1]; end = max(b, a + 1.6)
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
            size = 38 if n <= 16 else 34
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

# ---------------------------------------------------------------- renderer
F1 = ['fogD', 'fogH', 'starA', 'domeA', 'clY', 'clA', 'rainA', 'snowA', 'wet', 'snowL', 'mistA', 'amb', 'orb', 'winA', 'strm', 'ntBlur', 'tmaxS', 'clCov']
F3 = ['sunD', 'sunC', 'skT', 'skM', 'skH', 'fogC', 'stO']
F4 = ['ltn', 'glow', 'lone', 'pl0', 'pl0c', 'sp0', 'sp0d', 'sp0c', 'setA', 'setB', 'rkO', 'part', 'partC']
STRIP_SEQ = ['A4', 'B3', 'B7', 'C7']
STRIP_T = [.6, 1.0, 1.0, .9]
class Renderer:
    def __init__(s, W_, H, ss, text=True):
        s.W, s.H, s.ss = W_, H, ss
        try: s.ctx = moderngl.create_standalone_context()
        except Exception: s.ctx = moderngl.create_standalone_context(backend='egl')
        vb = s.ctx.buffer(np.array([-1, -1, 3, -1, -1, 3], 'f4').tobytes()); s.vb = vb
        init_world(s.ctx, vb)
        rd = lambda n: open(os.path.join(HERE, n), encoding='utf8').read()
        s.p1 = s.ctx.program(vertex_shader=VS, fragment_shader='#version 330\n' + COMMON + rd('scene.glsl'))
        s.p2 = s.ctx.program(vertex_shader=VS, fragment_shader=rd('post.glsl'))
        s.p3 = s.ctx.program(vertex_shader=VS, fragment_shader=rd('strip.glsl'))
        s.v1 = s.ctx.vertex_array(s.p1, [(vb, '2f', 'v')]); s.v2 = s.ctx.vertex_array(s.p2, [(vb, '2f', 'v')]); s.v3 = s.ctx.vertex_array(s.p3, [(vb, '2f', 'v')])
        SW, SH_ = int(W_ * ss), int(H * ss); s.SW, s.SH = SW, SH_
        def mk_(w, h):
            t = s.ctx.texture((w, h), 4, dtype='f2'); t.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR); t.repeat_x = t.repeat_y = False
            return t, s.ctx.framebuffer([t])
        s.tA, s.fA = mk_(SW, SH_); s.tB, s.fB = mk_(SW, SH_)
        s.cells = [mk_(SW // 2, SH_ // 2) for _ in range(3)]
        for t, f in s.cells: t.filter = (moderngl.LINEAR, moderngl.LINEAR)
        s.out = s.ctx.texture((W_, H), 3); s.f2 = s.ctx.framebuffer([s.out])
        s.txt = s.ctx.texture((W_, H), 4); s.txt.filter = (moderngl.LINEAR, moderngl.LINEAR)
        s.text = Text(W_, H) if text else None; s.blank = True; s.txt.write(np.zeros((H, W_, 4), np.uint8).tobytes())
        at = make_atlas(); s.at = s.ctx.texture((2048, 2048), 4, np.ascontiguousarray(at).tobytes()); s.at.build_mipmaps(); s.at.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR)
    def U(s, p, k, v):
        if k in p: p[k].value = v
    def arr(s, p, k, rows, n, w):
        if k not in p: return
        a = np.zeros((n, w), 'f4')
        for i, r in enumerate(rows[:n]): a[i] = r
        p[k].write(a.tobytes())
    def scene(s, st, fbo, size, T):
        if 'strip' in st: return s.strip(st, fbo, size, T)
        fbo.use(); p = s.p1; U = s.U
        uu, vv, ww, fl = basis(st)
        U(p, 'R', (float(size[0]), float(size[1]))); U(p, 'T', T)
        U(p, 'ro', tuple(map(float, st['ro']))); U(p, 'cu', tuple(uu)); U(p, 'cv', tuple(vv)); U(p, 'cw', tuple(ww)); U(p, 'fl', fl)
        U(p, 'stage', int(st['stage'])); U(p, 'sets', int(st['sets'])); U(p, 'stY', W.stY)
        for k in F1: U(p, k, float(st[k]))
        for k in F3: U(p, k, tuple(float(x) for x in st[k]))
        for k in F4: U(p, k, tuple(float(x) for x in st[k]))
        C = st['chars'][:8]
        s.arr(p, 'chP', [list(c['p']) + [c['sc']] for c in C], 8, 4)
        s.arr(p, 'chR', [[c['yaw'], c['ph'], c['lean'], c['arm']] for c in C], 8, 4)
        s.arr(p, 'chC', [list(c['col']) + [c['sit']] for c in C], 8, 4)
        s.arr(p, 'chF', [[c['eye'], c['hat'], c['med'], c['heart']] for c in C], 8, 4)
        U(p, 'nCh', len(C))
        I = st['items'][:12]
        s.arr(p, 'itP', [list(i['p']) + [i['sc']] for i in I], 12, 4)
        s.arr(p, 'itD', [list(i['f']) + [i['roll']] for i in I], 12, 4)
        s.arr(p, 'itC', [list(i['col']) + [i['ty']] for i in I], 12, 4)
        U(p, 'nIt', len(I))
        Nn = st['notes'][:6]
        s.arr(p, 'ntP', [n['p'] for n in Nn], 6, 3); s.arr(p, 'ntU', [n['U'] for n in Nn], 6, 3); s.arr(p, 'ntV', [n['V'] for n in Nn], 6, 3)
        s.arr(p, 'ntS', [[n['front'], n['back'], n['rev'], n['bend']] for n in Nn], 6, 4)
        U(p, 'nNt', len(Nn))
        s.at.use(3); U(p, 'AT', 3)
        U(p, 'kick', kick(T)); U(p, 'bph', beat(T) % 1.); U(p, 'beatN', math.floor(beat(T)))
        s.v1.render(moderngl.TRIANGLES)
    def strip(s, st, fbo, size, T):
        off = st['strip']['off']; lo = int(math.floor(off - .5 / .6)); csz = (s.SW // 2, s.SH // 2)
        for idx in range(lo, lo + 3):
            nm = STRIP_SEQ[idx % 4]; i = [j for j, q in enumerate(SH) if q[1] == nm][0]
            tl = STRIP_T[idx % 4] + (T - 150.58) * .8
            sub = SH[i][2](tl, shot_dur(i), SH[i][0] + tl)
            s.scene(sub, s.cells[idx % 3][1], csz, SH[i][0] + tl)
        fbo.use(); p = s.p3
        for j in range(3): s.cells[j][0].use(j); s.U(p, 'C%d' % j, j)
        s.U(p, 'R', (float(size[0]), float(size[1]))); s.U(p, 'off', off); s.U(p, 'warm', st['strip']['warm']); s.U(p, 'T', T)
        s.v3.render(moderngl.TRIANGLES)
    def frame(s, T):
        ia, ib, trk, trx, flash = shot_state(T)
        A = eval_shot(ia, T); s.scene(A, s.fA, (s.SW, s.SH), T); s.tA.build_mipmaps()
        B = A
        if ib is not None:
            B = eval_shot(ib, T); s.scene(B, s.fB, (s.SW, s.SH), T); s.tB.build_mipmaps()
        if s.text:
            arr = s.text.render(T)
            if arr is not None: s.txt.write(np.ascontiguousarray(arr).tobytes()); s.blank = False
            elif not s.blank: s.txt.write(s.text.blank.tobytes()); s.blank = True
        def dof(st):
            f = st['focus'] if st['focus'] is not None else float(np.linalg.norm(st['ta'] - st['ro']))
            return (float(f), float(st['ap']), float(st['tilt']), float(st['tiltc']))
        x = trx if trk == 1 else (1. if trx > .5 else 0.)
        if ib is None: x = 0.
        g = lambda k: float(mix(A[k], B[k], x))
        s.f2.use(); p = s.p2; U = s.U
        s.tA.use(0); s.tB.use(1); s.txt.use(2); U(p, 'S', 0); U(p, 'S2', 1); U(p, 'TX', 2)
        U(p, 'R', (float(s.W), float(s.H))); U(p, 'T', T); U(p, 'flash', flash + g('flash')); U(p, 'fade', fade(T)); U(p, 'kick', kick(T))
        U(p, 'lod0', float(np.log2(s.ss))); U(p, 'trK', int(trk)); U(p, 'trX', float(trx))
        U(p, 'dofA', dof(A)); U(p, 'dofB', dof(B))
        U(p, 'pov', (g('drops'), g('lsnow'), g('desat'), g('eblur')))
        punch = kick(T) * (.0045 if 112.5 <= T < 158.5 else .0025)
        U(p, 'fx', (g('pulse') + punch, g('radial'), g('film'), g('vig')))
        U(p, 'grade', (g('expo'), g('sat'), g('warm'), g('lift')))
        s.v2.render(moderngl.TRIANGLES)
        return s.f2.read(components=3, alignment=1)

def parse_times(args):
    ts = []
    for a_ in args:
        if a_ in SHN:
            i = [j for j, q in enumerate(SH) if q[1] == a_][0]; t0 = SH[i][0]; d = shot_dur(i)
            ts += [t0 + d * .12, t0 + d * .5, t0 + d * .9]
        else: ts.append(float(a_))
    return ts
if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'layout': build_layout()
    elif mode == 'sheet':
        ts = parse_times(sys.argv[3:])
        W_, H = (480, 270) if os.environ.get('SMALL') else (960, 540); r = Renderer(W_, H, 1.0); cols = 5 if os.environ.get('C5') else 3; rows = (len(ts) + cols - 1) // cols
        im = Image.new('RGB', (W_ * cols, H * rows))
        import time
        for i, t in enumerate(ts):
            t0 = time.time()
            im.paste(Image.frombytes('RGB', (W_, H), r.frame(t)), ((i % cols) * W_, (i // cols) * H)); im.save(sys.argv[2], quality=88)
            print(f'{t:.2f} {time.time() - t0:.2f}s', flush=True)
        im.resize((1920, 360 * rows) if cols == 3 else (1920, 216 * rows), Image.LANCZOS).save(sys.argv[2], quality=88)
    elif mode == 'still':
        r = Renderer(1920, 1080, float(sys.argv[4]) if len(sys.argv) > 4 else 1.5)
        Image.frombytes('RGB', (1920, 1080), r.frame(float(sys.argv[3]))).save(sys.argv[2])
    elif mode == 'video':
        out, t0, t1 = sys.argv[2], float(sys.argv[3]), float(sys.argv[4]); ss = float(sys.argv[5]) if len(sys.argv) > 5 else 1.5
        W_, H = (1920, 1080) if ss > 0 else (960, 540)
        ss = abs(ss); r = Renderer(W_, H, ss)
        audio = glob.glob(os.path.join(HERE, '..', '*.m4a'))[0]
        cmd = ['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W_}x{H}', '-r', str(FPS), '-i', '-',
               '-ss', str(t0), '-t', str(t1 - t0), '-i', audio, '-map', '0:v', '-map', '1:a',
               '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-colorspace', 'bt709', '-color_primaries', 'bt709', '-color_trc', 'bt709',
               '-vf', 'scale=out_color_matrix=bt709', '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', out]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        import time; T0 = time.time(); n = int(round((t1 - t0) * FPS))
        for i in range(n):
            ff.stdin.write(r.frame(t0 + i / FPS))
            if i % 150 == 0: print(f'{i}/{n} {time.time() - T0:.0f}s', flush=True)
        ff.stdin.close(); ff.wait(); print('done', time.time() - T0)
