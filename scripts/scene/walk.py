# Night walk: a low-poly me walking past billboards of my projects.
#   blender -b --factory-startup -P walk.py -- <still|anim> <walk dir>
# The character walks in place; the street scrolls under him and repeats
# every L metres, so frame N+1 == frame 1 and the loop is seamless.
# All motion is driver expressions on `frame` (no keyframes, no python).
import math, random, sys
import bpy, bmesh

MODE, HERE = sys.argv[sys.argv.index("--") + 1:][:2]
FPS, N = 20, 720            # 36 s loop: day, dusk, night, dawn
STEP = 16                   # frames per walk cycle (N % STEP == 0)
D, CARDS = 4.0, 9           # billboard spacing, card count
L = D * CARDS               # street repeat length (36 m)
V = L / N                   # metres per frame
PHI = f"((frame-1)*{2 * math.pi / STEP:.7f})"
random.seed(7)


def lin(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1]


MATS = {}


def mat(name, color, rough=0.7, emit=None, strength=0.0, metal=0.0):
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = lin(color)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    if emit:
        b.inputs["Emission Color"].default_value = lin(emit)
        b.inputs["Emission Strength"].default_value = strength
    MATS[name] = m
    return m


def screen(i):
    m = bpy.data.materials.new(f"card{i}")
    m.use_nodes = True
    nt = m.node_tree
    b = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(f"{HERE}/cards/card{i}.png")
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Roughness"].default_value = 0.5
    b.inputs["Specular IOR Level"].default_value = 0.12  # screens, not mirrors
    nt.links.new(t.outputs["Color"], b.inputs["Emission Color"])
    b.inputs["Emission Strength"].default_value = 1.3
    return m


def box(name, size, offset=(0, 0, 0), m=None, parent=None, loc=(0, 0, 0), bevel=0.0):
    """Box whose origin is the joint: geometry shifted by `offset`."""
    bm = bmesh.new()
    v = bmesh.ops.create_cube(bm, size=1)["verts"]
    bmesh.ops.scale(bm, vec=size, verts=v)
    bmesh.ops.translate(bm, vec=offset, verts=v)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    if m:
        me.materials.append(m)
    if bevel:
        mod = o.modifiers.new("bev", "BEVEL")
        mod.width, mod.segments = bevel, 2
    o.parent, o.location = parent, loc
    return o


def ball(name, r, m, parent=None, loc=(0, 0, 0), scale=(1, 1, 1), sub=2):
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    me.materials.append(m)
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    o.parent, o.location, o.scale = parent, loc, scale
    return o


def empty(name, parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o)
    o.parent, o.location = parent, loc
    return o


def drive(o, path, idx, expr):
    """Driver on o.path[idx]; every control keyed on `ctrl` below (night,
    arm poses, coat stages) is available by name in the expression."""
    fc = o.driver_add(path, idx) if idx is not None else o.driver_add(path)
    d = fc.driver
    d.type = "SCRIPTED"
    for name in PROPS:
        v = d.variables.new()
        v.name, v.type = name, "SINGLE_PROP"
        v.targets[0].id_type, v.targets[0].id, v.targets[0].data_path = "OBJECT", ctrl, f'["{name}"]'
    d.expression = expr


def array(o, count, dx):
    a = o.modifiers.new("arr", "ARRAY")
    a.count, a.use_relative_offset, a.use_constant_offset = count, False, True
    a.constant_offset_displace = (dx, 0, 0)


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.frame_start, sc.frame_end, sc.render.fps = 1, N, FPS

# controls keyed on one empty. night: 0 noon, 1 midnight. wR/wL: 0 = arm
# swings with the walk, 1 = arm follows the posed angles shR/elR, shL/elL
# (radians; shoulder +y = arm behind, elbow more negative = more bent).
# drape: coat folded over the right forearm. body/bodyz: worn coat body and
# its drop height. sleeve, lapel: 0..1 as he gets into it.
#   dusk 250-320: lift coat over shoulder, it lands on the back, both arms
#   go behind and into the sleeves, arms return to the walk, lapels settle.
#   dawn 600-684: the same in reverse.
HOLD_SH, HOLD_EL = -0.3, -1.57          # L-shaped right arm carrying the coat
KEYS = {
    "night": [(1, 0), (240, 0), (310, 1), (600, 1), (670, 0), (720, 0)],
    "wR": [(1, 1), (300, 1), (320, 0), (600, 0), (608, 1), (720, 1)],
    "wL": [(1, 0), (268, 0), (276, 1), (300, 1), (320, 0), (600, 0), (608, 1), (676, 1), (684, 0), (720, 0)],
    "shR": [(1, HOLD_SH), (250, HOLD_SH), (268, 2.4), (288, 0.9), (300, 0.9), (320, 0.0),
            (600, 0.0), (608, 0.9), (626, 0.9), (640, 2.4), (660, HOLD_SH), (720, HOLD_SH)],
    "elR": [(1, HOLD_EL), (250, HOLD_EL), (268, -0.6), (288, -0.1), (300, -0.1), (320, -0.45),
            (600, -0.45), (608, -0.1), (626, -0.1), (640, -0.6), (660, HOLD_EL), (720, HOLD_EL)],
    "shL": [(1, 0), (268, 0), (288, 0.9), (300, 0.9), (320, 0), (600, 0), (608, 0.9), (676, 0.9), (684, 0), (720, 0)],
    "elL": [(1, -0.45), (268, -0.45), (288, -0.1), (300, -0.1), (320, -0.45),
            (600, -0.45), (608, -0.1), (676, -0.1), (684, -0.45), (720, -0.45)],
    "drape": [(1, 1), (260, 1), (266, 0), (636, 0), (642, 1), (720, 1)],
    "body": [(1, 0), (262, 0), (266, 1), (640, 1), (644, 0), (720, 0)],
    "bodyz": [(1, 0.35), (264, 0.35), (282, 0), (626, 0), (642, 0.35), (720, 0.35)],
    "sleeve": [(1, 0), (284, 0), (300, 1), (610, 1), (626, 0), (720, 0)],
    "lapel": [(1, 0), (296, 0), (306, 1), (600, 1), (610, 0), (720, 0)],
}
PROPS = list(KEYS)
ctrl = bpy.data.objects.new("ctrl", None)
sc.collection.objects.link(ctrl)
for prop, keys in KEYS.items():
    for f, v in keys:
        ctrl[prop] = float(v)
        ctrl.keyframe_insert(f'["{prop}"]', frame=f)

# ---------------------------------------------------------------- palette
ASPH = mat("asphalt", "#16130f", 0.85)
WALK = mat("sidewalk", "#2b2722", 0.9)
CURB = mat("curb", "#4a443b", 0.8)
LINE = mat("line", "#8a8172", 0.7)
JOINT = mat("joint", "#1b1814", 0.9)
METAL = mat("metal", "#1d1a16", 0.45, metal=0.6)
BULB = mat("bulb", "#ffd2a8", 0.4, emit="#ffb070", strength=12)
BLDG = mat("bldg", "#2a2520", 0.9)
FAR = mat("far", "#1d1a16", 0.95)
WIN = mat("win", "#ffb070", 0.6, emit="#ffb070", strength=2.2)
SHIRT = mat("shirt", "#f2ede2", 0.75)
COAT = mat("coat", "#c8a46a", 0.85)   # camel: sits with the brown pants
PANTS = mat("pants", "#6b4a2e", 0.85)
FRAME = mat("specs", "#1a1512", 0.35)
SKIN = mat("skin", "#e9b48f", 0.6)
HAIR = mat("hair", "#f1cf7c", 0.55)
SHOE = mat("shoe", "#3a2a1c", 0.5)
DARK = mat("dark", "#120f0c", 0.3)
CAR = mat("car", "#f2ede2", 0.35)
GLASS = mat("glass", "#0f0d0b", 0.08)
HEAD = mat("headl", "#fff3e0", 0.3, emit="#fff1dc", strength=8)
TAIL = mat("taill", "#ff5a24", 0.3, emit="#ff5a24", strength=6)
MOON = mat("moon", "#f2ede2", 0.5, emit="#f2ede2", strength=1.4)
CARDM = [screen(i) for i in range(CARDS)]

# ---------------------------------------------------------------- street (scrolls at V)
street = empty("street")
drive(street, "location", 0, f"-(frame-1)*{V:.7f}")
X0, X1 = -16.0, 64.0
LEN, MID = X1 - X0, (X0 + X1) / 2
box("road", (LEN, 5.0, 0.02), m=ASPH, parent=street, loc=(MID, -3.5, -0.01))
box("backroad", (LEN, 5.0, 0.02), m=ASPH, parent=street, loc=(MID, 4.5, -0.01))
box("ground", (LEN, 60, 0.02), m=FAR, parent=street, loc=(MID, 30, -0.03))
box("sidewalk", (LEN, 2.9, 0.15), m=WALK, parent=street, loc=(MID, 0.45, 0.075))
box("curb", (LEN, 0.18, 0.17), m=CURB, parent=street, loc=(MID, -1.0, 0.085))
j = box("joint", (0.03, 2.9, 0.152), m=JOINT, parent=street, loc=(X0, 0.45, 0.076))
array(j, int(LEN / 1.5), 1.5)
for y in (-3.5, 4.5):
    dash = box("dash", (1.2, 0.12, 0.022), m=LINE, parent=street, loc=(X0, y, 0))
    array(dash, int(LEN / 3), 3.0)

for i in range(-3, 13):          # billboards + lamps, repeating every L
    x = i * D
    card = CARDM[i % CARDS]
    box(f"frame{i}", (3.4, 0.12, 2.0), m=METAL, parent=street, loc=(x, 1.42, 2.85), bevel=0.02)
    for px in (-1.0, 1.0):
        box(f"post{i}{px}", (0.1, 0.1, 1.85), m=METAL, parent=street, loc=(x + px, 1.45, 1.0))
    bpy.ops.mesh.primitive_plane_add(size=1)
    s = bpy.context.object
    s.name = f"screen{i}"
    s.scale = (3.2, 1.8, 1)
    s.rotation_euler = (math.radians(90), 0, 0)
    s.location = (x, 1.355, 2.85)
    s.data.materials.append(card)
    s.parent = street
    lx = x + D / 2           # lamp between boards
    box(f"pole{i}", (0.07, 0.07, 3.3), m=METAL, parent=street, loc=(lx, 0.95, 1.8))
    box(f"arm{i}", (0.07, 0.75, 0.06), m=METAL, parent=street, loc=(lx, 0.6, 3.42))
    box(f"lamp{i}", (0.34, 0.24, 0.1), m=METAL, parent=street, loc=(lx, 0.28, 3.4), bevel=0.02)
    box(f"bulb{i}", (0.26, 0.17, 0.02), m=BULB, parent=street, loc=(lx, 0.28, 3.345))
    ld = bpy.data.lights.new(f"lampl{i}", "POINT")
    ld.color, ld.energy, ld.shadow_soft_size = lin("#ffb070")[:3], 170, 0.15
    drive(ld, "energy", None, "170*night")
    lo = bpy.data.objects.new(f"lampl{i}", ld)
    sc.collection.objects.link(lo)
    lo.parent, lo.location = street, (lx, 0.28, 3.25)


def skyline(name, speed, period, y, hmin, hmax, m, windows, tiles):
    """Building strip moving at `speed`*V; pattern repeats every `period` m."""
    layer = empty(name)
    drive(layer, "location", 0, f"-(frame-1)*{V * speed:.7f}")
    blocks, x = [], 0.0
    while x < period - 0.8:
        w = min(random.uniform(1.6, 3.4), period - x)
        blocks.append((x, w, random.uniform(hmin, hmax), random.uniform(-0.6, 0.6)))
        x += w + random.uniform(0.0, 0.4)
    for t in tiles:
        for k, (bx, w, h, dy) in enumerate(blocks):
            cx = t * period + bx + w / 2
            box(f"{name}{t}_{k}", (w, 2.0, h), m=m, parent=layer, loc=(cx, y + dy, h / 2))
            if windows:
                for wz in [z / 10 for z in range(12, int(h * 10) - 6, 9)]:
                    for wx in [cx - w / 2 + 0.35 + q * 0.55 for q in range(int((w - 0.4) / 0.55))]:
                        if random.random() < 0.22:
                            box("w", (0.24, 0.02, 0.34), m=WIN, parent=layer, loc=(wx, y + dy - 1.01, wz))


skyline("near", 0.5, L * 0.5, 9.0, 1.6, 4.6, BLDG, True, range(-1, 4))
skyline("far", 0.25, L * 0.25, 18.0, 3.0, 7.0, FAR, True, range(-2, 6))
moon = ball("moon", 1.3, MOON, loc=(22, 70, 13.0), sub=3)
for i in range(3):
    drive(moon, "scale", i, "max(night,0.001)")
# night-only glow: street-lamp bulbs and apartment windows
for m_, k in ((BULB, 12), (WIN, 2.2)):
    sock = next(n for n in m_.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Emission Strength"]
    drive(sock, "default_value", None, f"{k}*night")

# ---------------------------------------------------------------- car on the back road
car = empty("car", loc=(0, 4.4, 0))
CARX = "(-13+min(max((frame-400)/70,0),1)*26)"   # offscreen at both loop ends
drive(car, "location", 0, CARX)
body = box("body", (2.3, 1.05, 0.48), m=CAR, parent=car, loc=(0, 0, 0.5), bevel=0.08)
box("cabin", (1.25, 0.95, 0.45), m=CAR, parent=car, loc=(-0.15, 0, 0.95), bevel=0.08)
box("glass", (1.29, 0.9, 0.3), m=GLASS, parent=car, loc=(-0.15, 0, 0.98))
for sy in (-0.36, 0.36):
    box("hl", (0.04, 0.2, 0.1), m=HEAD, parent=car, loc=(1.16, sy, 0.55))
    box("tl", (0.04, 0.2, 0.09), m=TAIL, parent=car, loc=(-1.16, sy, 0.6))
for wx in (-0.75, 0.75):
    for wy in (-0.55, 0.55):
        bpy.ops.mesh.primitive_cylinder_add(vertices=10, radius=0.3, depth=0.2)
        w = bpy.context.object
        w.data.materials.append(DARK)
        w.rotation_mode = "ZXY"  # spin about the axle first, then stand it up
        w.rotation_euler = (math.radians(90), 0, 0)
        w.parent, w.location = car, (wx, wy, 0.3)
        drive(w, "rotation_euler", 2, f"-{CARX}/0.3")
hl = bpy.data.lights.new("beam", "SPOT")
hl.color, hl.energy, hl.spot_size = lin("#fff1dc")[:3], 300, math.radians(50)
ho = bpy.data.objects.new("beam", hl)
sc.collection.objects.link(ho)
ho.parent, ho.location, ho.rotation_euler = car, (1.25, 0, 0.6), (0, math.radians(-85), 0)

# ---------------------------------------------------------------- the walker
root = empty("me", loc=(-2.6, 0.0, 0.12))
root.rotation_euler[2] = math.radians(-28)   # three-quarter view: open coat and specs read
# lowest at double support so the planted foot stays on the 0.15 m sidewalk
drive(root, "location", 2, f"0.12+0.03*cos(2*{PHI})")
hips = empty("hips", root, (0, 0, 0.99))
drive(hips, "rotation_euler", 2, f"-0.07*sin({PHI})")
box("pelvis", (0.22, 0.36, 0.17), (0, 0, -0.03), PANTS, hips, bevel=0.03)
torso = empty("torso", hips, (0, 0, 0))
torso.rotation_euler[1] = math.radians(5)
drive(torso, "rotation_euler", 2, f"0.09*sin({PHI})")
box("chest", (0.25, 0.42, 0.5), (0, 0, 0.27), SHIRT, torso, bevel=0.06)
box("collar", (0.2, 0.3, 0.05), (0.0, 0, 0.5), SHIRT, torso, bevel=0.02)


def coat_part(name, size, offset, parent, loc=(0, 0, 0), rz=0.0, prop="body", unroll=False, drop=False):
    """Worn-coat piece. Visible while `prop` is 1; `unroll` grows it down
    from its top edge (sleeves sliding on), `drop` lets it fall onto the
    shoulders from bodyz above."""
    o = box(name, size, offset, COAT, parent, loc=loc, bevel=0.03)
    o.rotation_euler[2] = rz
    if unroll:
        drive(o, "scale", 2, f"max({prop},0.001)")
        for i in range(2):
            drive(o, "scale", i, f"max(min({prop}*4,1),0.001)")
    else:
        for i in range(3):
            drive(o, "scale", i, f"max({prop},0.001)")
    if drop:
        drive(o, "location", 2, f"{loc[2]}+bodyz")
    return o


# knee-length coat, open at the front: back panel, two side panels, and two
# lapels swung 30 degrees outward from the side seams so the shirt shows
CL = 1.05
coat_part("coatback", (0.08, 0.5, CL), (-0.14, 0, -CL / 2), torso, loc=(0, 0, 0.52), drop=True)
for sgn in (1, -1):
    coat_part(f"coatside{sgn}", (0.27, 0.05, CL), (0, sgn * 0.245, -CL / 2), torso, loc=(0, 0, 0.52), drop=True)
    coat_part(f"lapel{sgn}", (0.05, 0.17, CL), (0.03, -sgn * 0.085, -CL / 2), torso,
              loc=(0.13, sgn * 0.245, 0.52), rz=sgn * math.radians(30), prop="lapel", unroll=True)
coat_part("coatcollar", (0.22, 0.36, 0.09), (-0.03, 0, -0.045), torso, loc=(0, 0, 0.565), drop=True)
head = empty("head", torso, (0.02, 0, 0.56))
ball("skull", 0.15, SKIN, head, (0.0, 0, 0.13), (1.0, 0.95, 1.05))
ball("nose", 0.03, SKIN, head, (0.15, 0, 0.11))
ball("eye", 0.018, DARK, head, (0.135, -0.07, 0.15), sub=1)
ball("hair", 0.165, HAIR, head, (-0.03, 0, 0.225), (1.02, 1.04, 0.72))
for gy in (-0.058, 0.058):                                   # specs
    box("rim", (0.03, 0.095, 0.08), m=FRAME, parent=head, loc=(0.165, gy, 0.15))
    box("lens", (0.02, 0.075, 0.06), m=GLASS, parent=head, loc=(0.175, gy, 0.15))
    box("temple", (0.19, 0.014, 0.016), m=FRAME, parent=head, loc=(0.07, gy * 1.8, 0.155))
box("bridge", (0.02, 0.03, 0.016), m=FRAME, parent=head, loc=(0.165, 0, 0.155))
for k, (hx, hz, ry) in enumerate([(0.08, 0.27, -35), (0.0, 0.31, -10), (-0.09, 0.28, 20),
                                  (-0.15, 0.2, 55), (0.13, 0.22, -60)]):
    bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=0.07, depth=0.16)
    sp = bpy.context.object
    sp.data.materials.append(HAIR)
    sp.parent, sp.location = head, (hx, random.uniform(-0.05, 0.05), hz)
    sp.rotation_euler = (random.uniform(-0.3, 0.3), math.radians(ry), 0)

for side, sy in (("L", 0.25), ("R", -0.25)):
    sign = 1 if side == "L" else -1
    sh = empty(f"sh{side}", torso, (0, sy, 0.46))
    # walk swing while w=0, posed angle while w=1 (coat choreography)
    drive(sh, "rotation_euler", 1, f"(1-w{side})*{0.34 * sign}*sin({PHI})+w{side}*sh{side}")
    box(f"upper{side}", (0.12, 0.12, 0.31), (0, 0, -0.14), SHIRT, sh, bevel=0.03)
    coat_part(f"cupper{side}", (0.16, 0.16, 0.33), (0, 0, -0.145), sh, prop="sleeve", unroll=True)
    el = empty(f"el{side}", sh, (0, 0, -0.29))
    drive(el, "rotation_euler", 1, f"(1-w{side})*-0.45+w{side}*el{side}")
    box(f"fore{side}", (0.11, 0.11, 0.25), (0, 0, -0.12), SHIRT, el, bevel=0.03)
    coat_part(f"cfore{side}", (0.15, 0.15, 0.26), (0, 0, -0.12), el, prop="sleeve", unroll=True)
    ball(f"hand{side}", 0.055, SKIN, el, (0, 0, -0.28))
    if side == "R":
        # the coat folded over the forearm by day: a bridge across the arm
        # and a half hanging down each side (world down = local -x when the
        # forearm points forward)
        coat_part("drapeTop", (0.08, 0.24, 0.3), (0.07, 0, -0.14), el, prop="drape")
        for dy in (-0.1, 0.1):
            coat_part(f"drape{dy}", (0.48, 0.05, 0.3), (-0.17, dy, -0.14), el, prop="drape")

    th = empty(f"th{side}", hips, (0, sy * 0.42, -0.04))
    drive(th, "rotation_euler", 1, f"{-0.36 * sign}*sin({PHI})")
    box(f"thigh{side}", (0.16, 0.16, 0.46), (0, 0, -0.22), PANTS, th, bevel=0.03)
    kn = empty(f"kn{side}", th, (0, 0, -0.45))
    drive(kn, "rotation_euler", 1, f"0.65*max(0,{sign}*cos({PHI}))")
    box(f"shin{side}", (0.14, 0.14, 0.42), (0, 0, -0.2), PANTS, kn, bevel=0.03)
    box(f"shoe{side}", (0.28, 0.13, 0.1), (0.05, 0, -0.45), SHOE, kn, bevel=0.03)

# ---------------------------------------------------------------- world, light, camera
w = bpy.data.worlds.new("w")
sc.world = w
w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
DAY, NIGHT = lin("#a9bfdc"), lin("#1b1713")
for i in range(3):
    drive(bg.inputs["Color"], "default_value", i, f"{DAY[i]:.4f}+({NIGHT[i]:.4f}-{DAY[i]:.4f})*night")
bg.inputs["Strength"].default_value = 1.0
drive(bg.inputs["Strength"], "default_value", None, "1.0+0.4*(1-night)")
sun = bpy.data.lights.new("moonlight", "SUN")
sun.color, sun.energy, sun.angle = lin("#ffd9a8")[:3], 3.0, math.radians(2)
drive(sun, "energy", None, "0.8+2.4*(1-night)")           # daylight → faint moonlight
for i, (dc, nc) in enumerate(zip(lin("#ffd9a8")[:3], lin("#9fb4ff")[:3])):
    drive(sun, "color", i, f"{dc:.4f}+({nc:.4f}-{dc:.4f})*night")
so = bpy.data.objects.new("moonlight", sun)
sc.collection.objects.link(so)
so.rotation_euler = (math.radians(-55), math.radians(20), 0)

# soft warm key that rides with the walker so he never drops into shadow
kd = bpy.data.lights.new("follow", "AREA")
kd.color, kd.energy, kd.size = lin("#ffd9b8")[:3], 60, 1.5
ko = bpy.data.objects.new("follow", kd)
sc.collection.objects.link(ko)
ko.location, ko.rotation_euler = (-1.6, -2.5, 2.6), (math.radians(60), 0, math.radians(-25))

aim = empty("aim", loc=(0, 1.0, 2.2))
cd = bpy.data.cameras.new("cam")
cd.lens = 42
cd.dof.use_dof, cd.dof.focus_distance, cd.dof.aperture_fstop = True, 15.9, 1.1
cam = bpy.data.objects.new("cam", cd)
sc.collection.objects.link(cam)
cam.location = (0, -15.5, 2.4)
tc = cam.constraints.new("TRACK_TO")
tc.target = aim
sc.camera = cam

# ---------------------------------------------------------------- render
sc.render.engine = "CYCLES"
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "OPTIX"
prefs.get_devices()
for d in prefs.devices:
    d.use = d.type != "CPU"
sc.cycles.device = "GPU"
sc.cycles.samples = 48
sc.cycles.use_denoising = True
sc.cycles.max_bounces = 4
sc.render.resolution_x, sc.render.resolution_y = 1280, 512
vts = [i.identifier for i in bpy.types.ColorManagedViewSettings.bl_rna.properties["view_transform"].enum_items]
sc.view_settings.view_transform = next((v for v in vts if "Neutral" in v), "AgX")
sc.view_settings.exposure = 0.5
sc.render.image_settings.file_format = "PNG"

if MODE == "still":
    for f in [int(x) for x in (sys.argv[-1].split(",") if "," in sys.argv[-1] else ["100", "275", "450", "640"])]:
        sc.frame_set(f)
        print("frame", f, "street", round(street.matrix_world.translation.x, 3), "car", round(car.matrix_world.translation.x, 2),
              "thighL", round(sc.objects["thL"].rotation_euler[1], 3))
        sc.render.filepath = f"{HERE}/still_{f:03d}.png"
        bpy.ops.render.render(write_still=True)
else:
    sc.render.filepath = f"{HERE}/frames/f_"
    bpy.ops.render.render(animation=True)
