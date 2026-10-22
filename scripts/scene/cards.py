# Render billboard screens (1600x900 PNG) via headless Chrome. Real facts only.
import html, subprocess, pathlib
OUT = pathlib.Path(__file__).parent / "cards"
CARDS = [
  dict(k="~/justutsav", name="utsav.", desc="I build the fix for my own annoyance, then I ship it.", chips=["BTech CSE '28", "freelance full-stack", "Ranchi"], intro=True),
  dict(k="01 · client · live", name="Atul Finance", desc="Investor portal. Clients log in and watch their capital and returns live.", big="₹75L+", lab="managed on it, up from ₹20L", chips=["sole dev", "since Jun 2025", "40+ daily users"]),
  dict(k="02 · client · real money", name="JustTrade", desc="One pane over many trading accounts: positions, P&L and strategy metrics.", chips=["client work", "code private"]),
  dict(k="03 · on the Play Store", name="Grit", desc="Snap a paper timetable, get a calendar. Tasks and alarms by voice.", big="23", lab="releases, shipped solo", chips=["TypeScript", "Capacitor", "Kotlin"]),
  dict(k="04 · on the Play Store", name="SplitFree", desc="Rent for a flat of five, settled with one-tap UPI and proof attached.", big="5", lab="flatmates settle on it", chips=["Flutter", "Supabase", "Riverpod"]),
  dict(k="05 · open source", name="claude-route", desc="Zero-token model router for Claude Code. Cheapest capable model, per task.", big="~46%", lab="cheaper session, worked example", chips=["Python", "hooks", "0 tokens to route"]),
  dict(k="06 · open source", name="justWhisper", desc="Hold a key, speak, text lands in the focused window. Speaks Hinglish.", big="0", lab="cloud calls, fully offline", chips=["faster-whisper", "Ollama", "X11"]),
  dict(k="07 · Avinya 2026", name="Drone twin", desc="Will a heavy-lift drone make the mountain sortie? Physics answers first.", big="1%", lab="energy error, 4.3 km / 15 kg test", chips=["ArduPilot SITL", "Gazebo", "QGC"]),
  dict(k="08 · client", name="Astro Wala", desc="Kundli generation and live chat with astrologers.", chips=["mobile", "client work"]),
]
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Geist:wght@400;500&family=Geist+Mono:wght@400;500&display=block');
*{margin:0;box-sizing:border-box} html,body{width:1600px;height:900px;background:#14120f;overflow:hidden}
.c{position:relative;width:1600px;height:900px;padding:84px 96px;display:grid;grid-template-columns:minmax(0,1fr) 440px;column-gap:56px;grid-template-rows:auto 1fr auto;
  background:radial-gradient(1200px 700px at 85% 110%,rgba(255,90,36,.20),transparent 60%),#14120f;color:#f2ede2}
.c:before{content:"";position:absolute;inset:0;background-image:linear-gradient(rgba(242,237,226,.045) 1px,transparent 1px),linear-gradient(90deg,rgba(242,237,226,.045) 1px,transparent 1px);background-size:64px 64px}
.k{grid-column:1/3;font:500 30px/1 'Geist Mono',monospace;letter-spacing:.18em;text-transform:uppercase;color:#ff5a24;display:flex;align-items:center;gap:22px;position:relative}
.k:after{content:"";height:2px;flex:1;background:rgba(242,237,226,.14)}
.main{align-self:end;position:relative;min-width:0}
.n{font:800 140px/.95 'Syne',sans-serif;letter-spacing:-.035em;word-break:keep-all}
.intro .n{font-size:240px}
.intro{grid-template-columns:minmax(0,1fr) 0}
.n i{font-style:normal;color:#ff5a24}
.d{margin-top:34px;font:400 40px/1.35 'Geist',sans-serif;color:#b8ae9c;max-width:860px}
.m{align-self:end;text-align:right;position:relative;min-width:0}
.b{font:800 190px/.9 'Syne',sans-serif;letter-spacing:-.04em;color:#ff5a24;white-space:nowrap}
.l{margin-top:18px;font:500 28px/1.3 'Geist Mono',monospace;color:#b8ae9c}
.chips{grid-column:1/3;display:flex;gap:16px;margin-top:56px;position:relative}
.chips span{font:500 26px/1 'Geist Mono',monospace;color:#f2ede2;border:2px solid rgba(242,237,226,.22);padding:14px 20px;border-radius:999px}
"""
# shrink any headline or metric that overflows its column (Syne runs wide)
FIT = """<script>document.fonts.ready.then(()=>{for(const el of document.querySelectorAll('.n,.b')){let f=parseFloat(getComputedStyle(el).fontSize);
const box=el.parentElement;while((el.scrollWidth>box.clientWidth+1)&&f>40){f-=4;el.style.fontSize=f+'px'}}})</script>"""
def card(c):
    e = html.escape
    name = e(c["name"]).replace(".", "<i>.</i>") if c.get("intro") else e(c["name"])
    metric = f'<div class="m"><div class="b">{e(c["big"])}</div><div class="l">{e(c["lab"])}</div></div>' if c.get("big") else "<div></div>"
    chips = "".join(f"<span>{e(x)}</span>" for x in c["chips"])
    cls = "c intro" if c.get("intro") else "c"
    return f'<!doctype html><meta charset="utf-8"><style>{CSS}</style><div class="{cls}"><div class="k">{e(c["k"])}</div><div class="main"><div class="n">{name}</div><div class="d">{e(c["desc"])}</div></div>{metric}<div class="chips">{chips}</div></div>{FIT}'
for i, c in enumerate(CARDS):
    h = OUT / f"card{i}.html"; h.write_text(card(c))
    subprocess.run(["google-chrome", "--headless=new", "--disable-gpu", "--hide-scrollbars", "--virtual-time-budget=5000",
                    "--window-size=1600,900", f"--screenshot={OUT}/card{i}.png", f"file://{h}"], capture_output=True)
print(len(CARDS), "cards")
