# SuccubusClinic -えすえすあーる- サイトの組み立て
#   content/（管理画面で編集するデータ）と src/pages（各ページのひな形）から、公開用のサイトを _site/ に書き出します。
#   GitHub に保存されるたびに GitHub Actions が自動で実行します（.github/workflows/deploy.yml）。
#   手元で試すとき: pip install -r requirements.txt && python src/build.py  →  _site/index.html をブラウザで開く
import colorsys, hashlib, html as _html, io, json, os, re, shutil, sys, urllib.parse, urllib.request
from datetime import date

import markdown
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "src", "pages")
STATIC = os.path.join(ROOT, "src", "static")
CONTENT = os.path.join(ROOT, "content")
OUT = os.path.join(ROOT, "_site")
CACHE = os.path.join(ROOT, ".cache", "img")
OFFLINE = os.environ.get("OFFLINE") == "1"   # 1 のとき YouTube へ取りに行かない（手元の確認用）

# ---------------------------------------------------------------- イベントの基本情報（決まったら、ここだけ書き換えればサイト全体に反映されます）
EVENT = "SuccubusClinic"                         # 短く書くときの名前
EVENT_FULL = "SuccubusClinic -えすえすあーる-"     # 正式な名前（「えすえすあーる」はひらがなのまま）
PUBLIC_URL = "https://succubusclinicssr.github.io/succubusclinic.github.io"  # 公開URL（GitHub Actions では環境変数 SITE_URL が優先されます）
GROUP_URL = "#"    # VRChat グループの URL（未定のあいだは "#"）
X_URL = "#"        # 公式 X の URL（例 "https://x.com/xxxx"。未定のあいだは "#"）
X_ID = ""          # 公式 X の ID（@ は付けない。未定のあいだは空 → 「準備中」と表示、twitter:site も出さない）
HASHTAG = ""       # ハッシュタグ（# は付けない。未定のあいだは空 → 「準備中」と表示）
WORLD = ""         # 会場ワールド名（未定のあいだは空 → 「準備中」と表示）
TBD = "準備中"

# トップの縦書きのネオン管タイトル（仮の文言。ここを書き換えるだけで、表示もネオン管の書体の読み込みも自動で変わります）
KV_TATE_A = "夢魔診療所"              # 太め・大きめの列（漢字）
KV_TATE_B = "サキュバス・クリニック"    # 細く長い列（カタカナ）
KV_FLICK = 3                         # 明滅させる1文字（KV_TATE_A の何文字目か。0 から数える。-1 で明滅なし）
# 各ページの見出しの右に置く、縦書きの小さなネオン看板と、見出しの下のデータ行
PHEAD_SIGN = {
    "news": ("{{NEWSN}} ARTICLES // LATEST {{NEWSDATE}}", "告知"),
    "news-detail": ("{{NEWSN}} ARTICLES // NEWS ARCHIVE", "告知"),
    "about": ("OPEN 2026.12.07 // EVERY OTHER MON", "案内"),
    "nurses": ("{{CASTN}} NURSES ON DUTY", "看護"),
    "schedule": ('NEXT <b data-next>12.07 MON</b> // 21:50 JST', "診療"),
    "menu": ("11 Rx // PRESCRIPTION", "処方"),
    "media": ("{{PHOTON}} PHOTOS // {{MOVIEN}} MOVIES", "記録"),
    "guidelines": ("08 SECTIONS // REV.2026.11.23", "院則"),
    "faq": ("12 Q&amp;A // MEDICAL INTERVIEW", "問診"),
    "contact": ("02 CHANNELS // X・VRCHAT GROUP", "受付"),
}
COLLAGE_JP = "診夢処方"               # トップの「看板の絵」に使う日本語（ネオン管の書体で読み込む文字）

SITE_URL = os.environ.get("SITE_URL", PUBLIC_URL).rstrip("/")
X_LABEL = "@" + X_ID if X_ID else TBD
TAG_LABEL = "#" + HASHTAG if HASHTAG else TBD
TAG_URL = "https://x.com/hashtag/" + urllib.parse.quote(HASHTAG) if HASHTAG else "#"
def ext(url):
    """外部リンクの属性。未定（#）のあいだは新しいタブで開かない"""
    return f'href="{url}" target="_blank" rel="noopener"' if url and url != "#" else 'href="#" aria-disabled="true"'
WARN = []
def warn(msg):
    WARN.append(msg); print("⚠ " + msg, file=sys.stderr)
esc = lambda t: _html.escape(str(t or ""), quote=True)

# ---------------------------------------------------------------- データの読み込み
def load(folder):
    d = os.path.join(CONTENT, folder); out = []
    for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
        if not f.endswith(".json"): continue
        try: out.append((f[:-5], json.load(open(os.path.join(d, f), encoding="utf-8"))))
        except Exception as e: warn(f"content/{folder}/{f} を読めませんでした（{e}）")
    return out

def num(v, default=0):
    try: return float(v)
    except (TypeError, ValueError): return default

def source(path, folder):
    """管理画面に保存された画像のパス（/uploads/... など）を、リポジトリ内の実際のファイルにする"""
    if not path: return None
    p = urllib.parse.unquote(str(path).split("?")[0]).lstrip("/")
    for cand in (p, os.path.join("uploads", folder, os.path.basename(p))):
        full = os.path.join(ROOT, cand)
        if os.path.isfile(full): return full
    warn(f"画像が見つかりません: {path}")
    return None

# ---------------------------------------------------------------- 画像の変換（結果は .cache に保存して再利用）
def save_img(src_path, out_rel, recipe, fn, quality=84, alpha_quality=90, keep_if=None):
    dst = os.path.join(OUT, out_rel); os.makedirs(os.path.dirname(dst), exist_ok=True)
    raw = open(src_path, "rb").read()
    key = hashlib.sha1(raw + recipe.encode()).hexdigest()
    cached = os.path.join(CACHE, key + ".webp")
    if not os.path.exists(cached):
        os.makedirs(CACHE, exist_ok=True)
        im = Image.open(io.BytesIO(raw)); im.load()
        if keep_if and src_path.lower().endswith(".webp") and keep_if(im):
            open(cached, "wb").write(raw)      # すでにちょうどいい大きさの webp はそのまま使う
        else:
            res = fn(clean(im))
            res.save(cached, "WEBP", quality=quality, alpha_quality=alpha_quality, method=6)
    shutil.copyfile(cached, dst)
    return Image.open(dst).size

def clean(im):
    im = im.convert("RGBA"); r, g, b, a = im.split()
    return Image.merge("RGBA", (r, g, b, a.point(lambda v: 0 if v < 14 else v)))

def fit_top(w, h):
    """横幅を w に合わせ、縦は h に（長ければ下を切り、短ければ下に余白）"""
    def f(im):
        nh = round(im.height * w / im.width); im = im.resize((w, nh), Image.LANCZOS)
        canvas = Image.new("RGBA", (w, h), (0, 0, 0, 0)); canvas.paste(im, (0, 0)); return canvas
    return f

def max_width(w):
    def f(im):
        if im.width <= w: return im
        return im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    return f

def cover(ratio, w_max, anchor="top"):
    """縦横比 ratio（横/縦）の枠いっぱいに切り抜く。anchor=top なら上を残す"""
    def f(im):
        W, H = im.size
        if W / H > ratio: cw, ch = round(H * ratio), H
        else: cw, ch = W, round(W / ratio)
        x = (W - cw) // 2; y = 0 if anchor == "top" else (H - ch) // 2 if anchor == "center" else H - ch
        im = im.crop((x, y, x + cw, y + ch)); w = min(w_max, cw)
        return im.resize((w, round(w / ratio)), Image.LANCZOS)
    return f

def contain(w, h):
    def f(im):
        s = min(w / im.width, h / im.height); im = im.resize((round(im.width * s), round(im.height * s)), Image.LANCZOS)
        c = Image.new("RGBA", (w, h), (0, 0, 0, 0)); c.paste(im, ((w - im.width) // 2, (h - im.height) // 2), im); return c
    return f

def auto_colors(src_path):
    """立ち絵の髪・顔あたりの色から、パステルのイメージカラー2色をつくる"""
    im = clean(Image.open(src_path)); W, H = im.size
    reg = im.crop((round(W * .147), round(H * .039), round(W * .85), round(H * .364))).resize((72, 50))
    data = reg.get_flattened_data() if hasattr(reg, "get_flattened_data") else reg.getdata()
    px = [p for p in data if p[3] > 200]
    R, G, B = (sum(p[i] for p in px) / len(px) for i in range(3)) if px else (230, 230, 230)
    h, l, s = colorsys.rgb_to_hls(R / 255, G / 255, B / 255)
    s2 = max(.35, min(.75, s * 1.6)) if s > .06 else .12
    hx = lambda ll, ss: "#%02x%02x%02x" % tuple(round(v * 255) for v in colorsys.hls_to_rgb(h, ll, ss))
    return hx(.86, s2), hx(.66, min(.85, s2 + .1))

# ---------------------------------------------------------------- キャスト
RANK = ["院長", "婦長", "主任"]                 # 同じ期生のなかで前に並ぶ役職
def maid_types():
    """content/settings/maid_types.json：期生ごとのナースの種類（管理画面の「設定」で編集。ファイル名は互換のためそのまま）"""
    try: rows = json.load(open(os.path.join(CONTENT, "settings", "maid_types.json"), encoding="utf-8")).get("types") or []
    except Exception as e: warn(f"ナースの種類の設定を読めませんでした（{e}）"); rows = []
    return {int(num(r.get("gen"), 0)): str(r.get("name") or "").strip() for r in rows if r.get("name")}
TYPES = {}
def build_cast():
    TYPES.update(maid_types())
    rows = []
    for cid, d in load("cast"):
        if d.get("show") is False or not str(d.get("name", "")).strip(): continue
        src = source(d.get("image"), "cast")
        if not src: warn(f"{d.get('name')}（{cid}）は立ち絵がないため表示しません"); continue
        save_img(src, f"img/cast/{cid}.webp", "cast800", fit_top(800, 1202), 86, 92, keep_if=lambda im: im.size == (800, 1202))
        save_img(src, f"img/cast/s/{cid}.webp", "cast400", fit_top(400, 601), 84, 90)
        c, c2 = d.get("color") or "", d.get("color2") or ""
        if not (re.fullmatch(r"#[0-9a-fA-F]{6}", c) and re.fullmatch(r"#[0-9a-fA-F]{6}", c2)):
            ac, ac2 = auto_colors(src); c = c if re.fullmatch(r"#[0-9a-fA-F]{6}", c) else ac; c2 = c2 if re.fullmatch(r"#[0-9a-fA-F]{6}", c2) else ac2
        gen = int(num(d.get("gen"), 0)); roles = [r for r in (d.get("roles") or []) if r]
        p = None
        if gen > 0:
            p = {k: str(d.get(k) or "") for k in ("card", "catch", "bday", "from", "blood", "likes", "skill")}
            p.update(gen=gen, roles=roles, type=TYPES.get(gen) or "ナース")
            if not p["card"]: p["card"] = d["name"]
        rank = min([RANK.index(r) for r in roles if r in RANK] or [len(RANK)])
        rows.append(((gen or 99), rank, num(d.get("order"), 9999), d["name"], {"id": cid, "name": d["name"].strip(), "c": c.lower(), "c2": c2.lower(), "p": p}))
    rows.sort(key=lambda r: r[:4])
    return [r[4] for r in rows]

# ---------------------------------------------------------------- お知らせ
CATS = {"event", "maid", "menu", "info"}
POS = {"top": "50% 15%", "30%": "50% 30%", "center": "50% 50%", "bottom": "50% 85%"}
def build_news():
    out = []
    for nid, d in load("news"):
        if d.get("draft") or not str(d.get("title", "")).strip(): continue
        dt = str(d.get("date") or "")[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dt): warn(f"お知らせ「{d.get('title')}」の日付がありません"); dt = date.today().isoformat()
        th = {"logo": True}
        src = source(d.get("image"), "news") if d.get("thumbnail") == "image" else None
        if src:
            save_img(src, f"img/news/{nid}.webp", "news1200", max_width(1200), 84, 90)
            th = {"img": f"img/news/{nid}.webp", "pos": POS.get(d.get("image_pos"), "50% 30%")}
        body = markdown.markdown(str(d.get("body") or ""), extensions=["nl2br", "sane_lists"])
        out.append({"id": nid, "date": dt.replace("-", "."), "cat": d.get("category") if d.get("category") in CATS else "info", "title": d["title"].strip(), "th": th, "body": body})
    out.sort(key=lambda n: (n["date"], n["id"]), reverse=True)
    return out

# ---------------------------------------------------------------- スケジュール（特別診療・休診）
def hm_min(v):
    m = re.fullmatch(r"\s*(\d{1,2})\s*[:：時]\s*(\d{1,2})?\s*分?\s*", str(v or ""))
    if not m: return None
    h, mi = int(m.group(1)), int(m.group(2) or 0)
    return h * 60 + mi if h < 30 and mi < 60 else None

def build_schedule():
    out = {}
    for sid, d in load("schedule"):
        dt = str(d.get("date") or "")[:10]
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dt): warn(f"スケジュール「{d.get('label')}」の日付がありません"); continue
        k = "off" if d.get("type") == "off" else "sp"
        item = {"k": k, "t": str(d.get("label") or "").strip() or ("休診" if k == "off" else "特別診療"), "d": str(d.get("note") or "").strip()}
        if k == "sp":
            st, en = hm_min(d.get("start") or "21:50"), hm_min(d.get("end") or "23:10")
            if st is None or en is None: warn(f"{dt} の時刻が読めないため 21:50〜23:10 にしました"); st, en = 21 * 60 + 50, 23 * 60 + 10
            if en <= st: en += 24 * 60   # 日をまたぐとき
            item.update(s=st, e=en)
        if dt in out: warn(f"{dt} に予定が2つあります（あとのものを使います）")
        out[dt] = item
    return dict(sorted(out.items()))

# ---------------------------------------------------------------- 動画（YouTube）
def yt_id(url):
    m = re.search(r"(?:youtu\.be/|v=|/shorts/|/embed/|/live/)([A-Za-z0-9_-]{11})", url or "")
    return m.group(1) if m else None

def fetch(url, timeout=15):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (site build)"})
    with urllib.request.urlopen(req, timeout=timeout) as r: return r.read()

def build_movies(cast):
    out = []
    for mid, d in load("movies"):
        vid = yt_id(d.get("url"))
        if not vid: warn(f"動画のURLがYouTubeとして読めません: {d.get('url')}"); continue
        title = str(d.get("title") or "").strip()
        if not title and not OFFLINE:
            try: title = json.loads(fetch("https://www.youtube.com/oembed?format=json&url=" + urllib.parse.quote(f"https://www.youtube.com/watch?v={vid}")))["title"]
            except Exception as e: warn(f"動画タイトルを取得できませんでした（{vid}: {e}）")
        thumb = f"img/movie/{vid}.webp"
        if not os.path.exists(os.path.join(OUT, thumb)):
            raw = None
            cache_raw = os.path.join(CACHE, f"yt-{vid}.jpg")
            if os.path.exists(cache_raw): raw = open(cache_raw, "rb").read()
            elif not OFFLINE:
                for q in ("maxresdefault", "sddefault", "hqdefault"):
                    try: raw = fetch(f"https://i.ytimg.com/vi/{vid}/{q}.jpg"); break
                    except Exception: pass
                if raw: os.makedirs(CACHE, exist_ok=True); open(cache_raw, "wb").write(raw)
            if raw: save_img(cache_raw, thumb, "movie800", lambda im: cover(16 / 9, 800, "center")(im).convert("RGB"), 82)
            else: warn(f"サムネイルを取得できませんでした（{vid}）"); thumb = "img/movie-none.webp"
        tag = d.get("tag") if d.get("tag") in ("short", "pv", "live", "cover") else "pv"
        url = f"https://youtube.com/shorts/{vid}" if tag == "short" else f"https://youtu.be/{vid}"
        out.append({"id": vid, "tag": tag, "title": title or "YouTube動画", "cast": str(d.get("cast") or "").strip(), "url": url, "thumb": thumb,
                    "_k": (str(d.get("date") or "")[:10], -num(d.get("order"), 9999))})
    out.sort(key=lambda m: m["_k"], reverse=True)
    return out

# ---------------------------------------------------------------- 集合写真
def build_photos():
    out = []
    for pid, d in load("photos"):
        src = source(d.get("image"), "photos")
        if not src: continue
        full = save_img(src, f"img/photo/{pid}.webp", "photo2560", max_width(2560), 84, 90)
        save_img(src, f"img/photo/s/{pid}.webp", "photo-thumb", contain(800, 400), 82, 90)
        hero = None
        if d.get("hero", True):
            anchor = d.get("hero_pos") if d.get("hero_pos") in ("top", "center", "bottom") else "top"
            hero = save_img(src, f"img/photo/h/{pid}.webp", "photo-hero-" + anchor, cover(2, 2560, anchor), 84, 90)
        out.append({"id": pid, "alt": str(d.get("alt") or "").strip() or f"{EVENT}のナースたち", "hero": hero, "full": full,
                    "gallery": d.get("gallery", True) is not False, "_k": (num(d.get("order"), 9999), pid)})
    out.sort(key=lambda p: p["_k"])
    return out

# ---------------------------------------------------------------- 共通パーツ
NAV = [("news", "News", "お知らせ"), ("about", "About", "病院案内"), ("nurses", "Nurses", "ナース紹介"), ("schedule", "Schedule", "診療時間"),
       ("menu", "Menu", "処方メニュー"), ("media", "Media", "メディア"), ("guidelines", "Guide", "入院のしおり"), ("faq", "FAQ", "問診票")]
NAV_IC = {"index": "n-home", "news": "n-news", "about": "n-clinic", "nurses": "n-cap", "schedule": "n-cal", "menu": "m-capsule",
          "media": "n-camera", "guidelines": "n-clip", "faq": "n-faq", "contact": "n-mail"}
def ic(name, cls="ic"):
    """HUD の線画アイコン（下の SPRITE の symbol を使う）"""
    return f'<svg class="{cls}" aria-hidden="true"><use href="#{name}"/></svg>'
ARROW = '<svg class="chev" viewBox="0 0 22 12" aria-hidden="true"><use href="#i-arrow"/></svg>'
AC = ' aria-current="page"'

# ---------------------------------------------------------------- ロゴ（いまは HTML と線画で作った仮のロゴ：小悪魔ハートのエンブレム＋テック系の文字組み）
# 正式なロゴ画像ができたら LOGO_IMG に画像のパスと大きさを書くだけで、ヘッダー・フッター・ロード画面・画面遷移・
# お知らせのサムネイルのロゴが、すべてその画像に置きかわります（例 LOGO_IMG = ("img/logo.webp", 960, 239)）
LOGO_IMG = None
def logo():
    if LOGO_IMG:
        src, w, h = LOGO_IMG
        return f'<img class="nlogo-img" src="{src}" alt="" width="{w}" height="{h}">'
    return ('<span class="nlogo" aria-hidden="true">'
            '<svg class="nlogo__mark"><use href="#m-devil"/></svg>'
            '<span class="nlogo__t"><b>SUCCUBUS</b><b>CLINIC</b></span>'
            '<span class="nlogo__s">-えすえすあーる-</span></span>')

# ---------------------------------------------------------------- 心電図の線（HUD の波形・ロード画面）
def ecg_path(width, beats, y=22):
    """beats の位置に心拍の山を入れた、横 width の折れ線"""
    d = f"M0 {y}"
    for x in beats:
        d += f"H{x}l3-4 3 4h5l4-17 6 33 5-25 3 9h8l4-5 4 5"
    return d + f"H{width}"
ECG_LONG_D = ecg_path(600, [40, 190, 340, 490])
ECG_LONG = (f'<svg class="ecg-long" viewBox="0 0 600 40" preserveAspectRatio="none" aria-hidden="true">'
            f'<path class="ecg__base" pathLength="100" d="{ECG_LONG_D}"/><path class="ecg__pulse" pathLength="100" d="{ECG_LONG_D}"/></svg>')

def _line(sid, vb, d, w=2):
    """フラットな HUD の線画（1本線）"""
    return (f'<symbol id="{sid}" viewBox="{vb}"><path d="{d}" fill="none" stroke="currentColor" stroke-width="{w}" '
            f'stroke-linecap="square" stroke-linejoin="miter"/></symbol>')
_HEART = "M16 27C6.5 20.5 3.5 15.5 3.5 11c0-3.6 2.7-6.3 6-6.3 2.9 0 5 1.7 6.5 4.3 1.5-2.6 3.6-4.3 6.5-4.3 3.3 0 6 2.7 6 6.3 0 4.5-3 9.5-12.5 16z"
ICONS = {
    # モチーフ（ハート・小悪魔ハート・十字・注射器・カプセル・点滴）
    "m-heart": ("0 0 32 32", _HEART),
    "m-cross": ("0 0 32 32", "M12.5 4.5h7v8h8v7h-8v8h-7v-8h-8v-7h8z"),
    "m-syringe": ("0 0 32 32", "M10 22L3.5 28.5M10 22l-2.8-2.8 11-11 5.6 5.6-11 11zM12.4 18.8l1.7 1.7M15.2 16l1.7 1.7M18 13.2l1.7 1.7M16.8 7l8.2 8.2M21 11l3.4-3.4M22.6 5.8l3.6 3.6"),
    "m-capsule": ("0 0 32 32", "M6.8 25.2a5.6 5.6 0 0 1 0-7.9L17.3 6.8a5.6 5.6 0 0 1 7.9 7.9L14.7 25.2a5.6 5.6 0 0 1-7.9 0zM12 12l8 8"),
    "m-drip": ("0 0 32 32", "M10 3.5h12v13.5c0 2.8-2 4.5-4.5 4.5h-3c-2.5 0-4.5-1.7-4.5-4.5zM10 9h12M14 13.5h4M16 21.5v3M14.6 24.5h2.8v2.6h-2.8zM16 27.1V30"),
    # ナビ・案内のアイコン
    "n-home": ("0 0 32 32", "M4.5 15L16 5.5 27.5 15M8 12.5V27h16V12.5M13.5 27v-6.5h5V27"),
    "n-news": ("0 0 32 32", "M5 13v6.5h4.5l9.5 6v-18l-9.5 6zM23.5 12.5c1.8 1.4 1.8 5.6 0 7M26.5 9.5c3.4 3 3.4 10 0 13"),
    "n-clinic": ("0 0 32 32", "M5 27.5V11.5l11-6 11 6v16M3 27.5h26M13.5 27.5v-5.5h5v5.5M16 9.5v8M12 13.5h8"),
    "n-cap": ("0 0 32 32", "M4.5 19c0-7.5 5-12 11.5-12s11.5 4.5 11.5 12l-3.5 3.5h-16zM16 10.5v8M12 14.5h8"),
    "n-cal": ("0 0 32 32", "M5 7.5h22v20H5zM5 13h22M10.5 4v6M21.5 4v6M11 20.5h4M17 20.5h4M11 24h4"),
    "n-pin": ("0 0 32 32", "M16 29c-5.5-6.5-9-11-9-15.5 0-5 4-8.5 9-8.5s9 3.5 9 8.5c0 4.5-3.5 9-9 15.5zM16 10.5v6M13 13.5h6"),
    "n-camera": ("0 0 32 32", "M3.5 10h25v17h-25zM11 10l2-4h6l2 4M16 13.5a4.5 4.5 0 1 1 0 9 4.5 4.5 0 0 1 0-9z"),
    "n-clip": ("0 0 32 32", "M7.5 6.5h17v22h-17zM12 4h8v4.5h-8zM11.5 14h9M11.5 18.5h9M11.5 23h5.5"),
    "n-faq": ("0 0 32 32", "M4 6.5h24v15H14l-6 5v-5H4zM13.3 11.5c0-1.7 1.2-2.8 2.7-2.8s2.7 1 2.7 2.5c0 2.2-2.7 2.2-2.7 4.3M16 18.6v.1"),
    "n-mail": ("0 0 32 32", "M4 8h24v17H4zM4 8.5l12 9 12-9"),
}
ICONS["i-heart"] = ICONS["m-heart"]
ICONS["i-cal"] = ICONS["n-cal"]
ICONS["i-vr"] = ("0 0 32 32", "M3.5 11.5c0-2 1.5-3.5 3.5-3.5h18c2 0 3.5 1.5 3.5 3.5v8c0 2-1.5 3.5-3.5 3.5h-5l-3-3.5h-2l-3 3.5H7c-2 0-3.5-1.5-3.5-3.5zM10.5 15.5h.1M21.5 15.5h.1")

# 小悪魔ハート（角・しっぽ・中に十字）：ロゴと HUD のエンブレム
DEVIL = ('<symbol id="m-devil" viewBox="0 0 44 40"><g fill="none" stroke="currentColor" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round">'
         '<path d="M21 35C10.5 28.5 6.5 23 6.5 17.5c0-4.2 3-7.3 6.8-7.3 3.3 0 5.9 2 7.7 5 1.8-3 4.4-5 7.7-5 3.8 0 6.8 3.1 6.8 7.3 0 5.5-4 11-14.5 17.5z"/>'
         '<path d="M11.2 11.4L9.6 3.6l6 5.2M30.8 11.4l1.6-7.8-6 5.2"/>'
         '<path d="M29.5 29.5c3.4 2.6 7 2.4 9.2-.6"/></g>'
         '<path d="M40.6 26.4l.5 4.6-4.4-1.4z" fill="currentColor"/>'
         '<path d="M19.4 16.5h3.2v4h4v3.2h-4v4h-3.2v-4h-4v-3.2h4z" fill="var(--emb-cross, currentColor)"/></symbol>')

# HUD の記号：ハートの照準（ローダー・トップのモニター・ナースの ID カード・フッター・カレンダー・NO SIGNAL で使い回す）／バーコード／45° のストライプ
RETICLE = ('<symbol id="m-reticle" viewBox="0 0 48 48"><g fill="none" stroke="currentColor" stroke-width="1.5">'
           '<circle cx="24" cy="24" r="20" stroke-dasharray="20 6.6" stroke-width="1"/>'
           '<path d="M24 2v7M24 39v7M2 24h7M39 24h7"/>'
           '<path d="M24 34.5C16.5 29.5 13.2 25.6 13.2 21.7c0-2.9 2.1-5 4.7-5 2.6 0 4.6 1.6 6.1 4 1.5-2.4 3.5-4 6.1-4 2.6 0 4.7 2.1 4.7 5 0 3.9-3.3 7.8-10.8 12.8z" stroke-linejoin="round"/></g>'
           '<path d="M23.1 21.6h1.8v1.6h1.6v1.8h-1.6v1.6h-1.8V25h-1.6v-1.8h1.6z" fill="currentColor"/></symbol>')
DECO = (
    '<symbol id="d-bars" viewBox="0 0 120 40"><g fill="currentColor">'
    + "".join(f'<rect x="{x}" y="0" width="{w}" height="40"/>' for x, w in ((0,2),(4,1),(7,3),(12,1),(15,1),(18,4),(24,1),(27,2),(31,1),(34,3),(39,1),(42,2),(46,1),(49,4),(55,1),(58,2),(62,1),(65,3),(70,1),(73,1),(76,2),(80,4),(86,1),(89,2),(93,1),(96,3),(101,1),(104,2),(108,1),(111,4),(117,2)))
    + '</g></symbol>'
    '<symbol id="d-stripe" viewBox="0 0 120 16"><g fill="currentColor">'
    + "".join(f'<path d="M{x} 16l16-16h6l-16 16z"/>' for x in range(-6, 120, 12))
    + '</g></symbol>'
)

SPRITE = ('<svg width="0" height="0" style="position:absolute" aria-hidden="true">\n  <defs>\n'
          '    <symbol id="i-arrow" viewBox="0 0 22 12"><path d="M1 1l5 5-5 5M8.5 1l5 5-5 5M16 1l5 5-5 5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="square"/></symbol>\n'
          '    <symbol id="i-x" viewBox="0 0 512 512"><path d="M389.2 48h70.6L305.6 224.2 487 464H345L233.7 318.6 106.5 464H35.8L200.7 275.5 26.8 48H172.4L272.9 180.9 389.2 48zM364.4 421.8h39.1L151.1 88h-42L364.4 421.8z"/></symbol>\n'
          + "".join(f"    {_line(k, vb, d)}\n" for k, (vb, d) in ICONS.items())
          + f"    {DEVIL}\n    {RETICLE}\n    {DECO}\n"
          + '  </defs>\n</svg>')

# 書体：見出し・UI ＝ Chakra Petch（縦長の角ばったサンセリフ）／ システム表示 ＝ Share Tech Mono ／ 日本語 ＝ Zen Kaku Gothic New
#       ネオン管（縦書きタイトル・ページの看板・トップの看板の絵）＝ M PLUS Rounded 1c（必要な文字だけを読み込む）
_TUBE_CHARS = "".join(sorted(set(KV_TATE_A + KV_TATE_B + "".join(v[1] for v in PHEAD_SIGN.values()) + COLLAGE_JP)))
FONTS = f'''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=Share+Tech+Mono&family=Zen+Kaku+Gothic+New:wght@400;500;700;900&display=swap">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=M+PLUS+Rounded+1c:wght@100;300&display=swap&text={urllib.parse.quote(_TUBE_CHARS)}">
<link rel="stylesheet" href="assets/site.css">'''

BG = '<div class="scanlines" aria-hidden="true"></div>'

# 画面遷移：斜めのストライプが走って覆い、システム表示が出る → 次のページでストライプが抜けていく（動きは site.js / site.css）
PAGE_TRANSITION = f'''<div class="pt" id="pt" aria-hidden="true">
  <div class="pt__bands"><i></i><i></i><i></i><i></i><i></i></div>
  <div class="pt__core">{logo()}<p class="pt__txt mono">&gt;&gt; ACCESSING<b><span>.</span><span>.</span><span>.</span></b></p><i class="pt__bar"></i></div>
</div>'''
# 前のページから画面遷移で来たときは、最初の表示から帯で覆っておく（読み込み中にページが見えないように）
PT_HEAD = '<script>try{if(sessionStorage.getItem("md-pt")){sessionStorage.removeItem("md-pt");if(!matchMedia("(prefers-reduced-motion: reduce)").matches)document.documentElement.classList.add("pt-arrive")}}catch(e){}</script>'

LOADING = f'''<div class="loader" id="loader" aria-hidden="true">
  <div class="loader__ui">
    <i class="loader__br --tl"></i><i class="loader__br --tr"></i><i class="loader__br --bl"></i><i class="loader__br --br"></i>
    <p class="loader__meta mono --tl">//SC_SYSTEM v2.0 <b>NURSE STATION</b></p>
    <p class="loader__meta mono --tr">VRCHAT // PCVR ONLY</p>
    <p class="loader__meta mono --bl">EVERY OTHER MONDAY 21:50 JST</p>
    <p class="loader__meta mono --br">CLICK TO SKIP &gt;&gt;&gt;</p>
    <div class="loader__core">
      <div class="loader__logo">{logo()}</div>
      <div class="loader__monitor">{ECG_LONG}</div>
      <div class="loader__prog">
        <div class="loader__track"><i class="loader__fill" id="ld-fill"></i></div>
        <p class="loader__pct mono"><b id="ld-pct">000</b>%</p>
      </div>
      <ol class="loader__log mono" id="ld-log">
        <li>&gt; BOOT SC_SYSTEM ............ <em>OK</em></li>
        <li>&gt; READ PATIENT CARD // PCVR . <em>OK</em></li>
        <li>&gt; MATCH KARTE: NURSES ....... <em>{{{{CASTN}}}}/{{{{CASTN}}}}</em></li>
        <li>&gt; VITAL MONITOR ............. <em>ONLINE</em></li>
        <li>&gt; WELCOME, PATIENT <b>&#9825;</b></li>
      </ol>
    </div>
  </div>
  <div class="loader__wipe"><i></i><i></i><i></i><i></i></div>
</div>'''

def nav_link(k, en, cur=""):
    return f'<a href="{k}.html"{AC if k == cur else ""}><span class="br">[</span>{en.upper()}<span class="br">]</span></a>'

def header(cur):
    lis = "".join(f'<li>{nav_link(k, en, cur)}</li>' for k, en, jp in NAV)
    sp = "\n".join(f'  <a class="sp-link" href="{k}.html"{AC if k == cur else ""}><span class="sp-link__no">{i:02d}</span><b>[{en.upper()}]</b><small>{jp}</small></a>' for i, (k, en, jp) in enumerate(NAV, 1))
    return f'''<header class="header">
  <a class="h-logo" href="index.html" aria-label="{EVENT_FULL} トップへ">{logo()}</a>
  <nav class="gnav" aria-label="メインメニュー">
    <ul>{lis}<li>{nav_link("contact", "Contact", cur)}</li></ul>
  </nav>
  <a class="h-x" {ext(X_URL)} aria-label="{EVENT}のX（{"新しいタブで開く" if X_URL != "#" else TBD}）"><svg viewBox="0 0 512 512" aria-hidden="true"><use href="#i-x"/></svg></a>
  <a class="h-join" {ext(GROUP_URL)}><small>VRCHAT</small>GROUP</a>
  <button class="menu-btn" id="menu-btn" type="button" aria-label="メニューを開く" aria-expanded="false" aria-controls="sp-menu"><span></span><span></span><span></span></button>
</header>
<nav class="sp-menu" id="sp-menu" aria-label="メニュー">
  <p class="sp-menu__h mono">&gt;&gt;NAVIGATION <span>//MENU</span></p>
  <a class="sp-link" href="index.html"><span class="sp-link__no">00</span><b>[TOP]</b><small>トップ</small></a>
{sp}
  <a class="sp-link" href="contact.html"{AC if cur == "contact" else ""}><span class="sp-link__no">{len(NAV) + 1:02d}</span><b>[CONTACT]</b><small>受付</small></a>
  <div class="sp-menu__ext"><a class="btn" {ext(GROUP_URL)}><span>VRCHAT GROUP</span><i>{ARROW}</i></a><a class="btn" {ext(X_URL)}><span>FOLLOW ON X</span><i>{ARROW}</i></a></div>
</nav>'''

def footer():
    links = "".join(f'<li>{nav_link(k, en)}</li>' for k, en, jp in NAV)
    return f'''<footer class="footer">
  <div class="inner">
    <div class="footer__top">
      <a class="f-logo" href="index.html" aria-label="{EVENT_FULL} トップへ">{logo()}<small class="f-tag mono">//VRC NURSE CAFÉ EVENT</small></a>
      <nav class="footer__nav" aria-label="フッターメニュー"><p class="mono">&gt;&gt;SITEMAP</p><ul>{links}<li>{nav_link("contact", "Contact")}</li><li><a {ext(X_URL)}><span class="br">[</span>X<span class="br">]</span></a></li></ul></nav>
      <button class="footer__mark" type="button" data-omikuji aria-label="あなたの推しがきっと見つかる（処方おみくじを引く）"><svg class="footer__dial" aria-hidden="true"><use href="#m-reticle"/></svg><span>あなたの推しが<br>きっと見つかる</span><small class="mono">OMIKUJI &gt;&gt;&gt;</small></button>
    </div>
    <div class="footer__sys mono" aria-hidden="true"><span>//SYSTEM STATUS: ONLINE</span><span>//EVERY OTHER MONDAY 21:50–23:10 JST</span><span>//PCVR ONLY</span><svg class="footer__bars"><use href="#d-bars"/></svg></div>
    <div class="footer__bottom"><span>{EVENT}はVRChat上の有志によるイベントです。VRChat Inc. とは関係ありません。</span><span class="mono">© {date.today().year} {EVENT}</span></div>
  </div>
</footer>
<a class="go-top" id="go-top" href="#top" aria-label="ページの先頭へ"><svg aria-hidden="true" viewBox="0 0 22 12"><use href="#i-arrow"/></svg><span>TOP</span></a>'''

def hx(en, jp, code="", no="", side="", tag="h2", sub=False):
    """セクション見出し（軽い型）：>>NEWS ＋ 小さな日本語、右端に //01 LATEST_INFO の1行だけ。side="r" で右寄せ"""
    meta = f'<span class="hx__code mono" aria-hidden="true">//{no + " " if no else ""}{code}</span>' if (code or no) else ""
    cls = "hx" + (" --sub" if sub else "") + (" --r" if side == "r" else "")
    return (f'<div class="{cls} rv"><{tag} class="hx__t"><span class="hx__en"><i>&gt;&gt;</i>{en.upper()}</span>'
            f'<span class="hx__jp">{jp}</span></{tag}>{meta}</div>')

def phead(en, jp, code, crumb=None, page=""):
    """下層ページの見出し：大きな欧文の看板＋そのページのデータ行、右に縦書きの小さなネオン看板"""
    crumb = crumb or f"<span>{en.upper()}</span>"
    data, sign = PHEAD_SIGN.get(page, ("", ""))
    sign = f'<p class="phead__sign" aria-hidden="true"><span>{sign}</span></p>' if sign else ""
    return f'''<section class="phead">
    <div class="inner">
      <nav class="crumb mono" aria-label="現在地"><a href="index.html">TOP</a><i>/</i>{crumb}</nav>
      <div class="phead__row">
        <h1 class="phead__t"><span class="phead__en"><i>&gt;&gt;</i>{en.upper()}</span><span class="phead__jp">{jp}</span></h1>
        {sign}
      </div>
      <p class="phead__data mono"><span class="phead__code">{code.replace("// ", "//")}</span><span class="phead__d">{data}</span></p>
    </div>
  </section>'''

def back(extra=""):
    return f'<div class="back">{extra}<a class="btn --line" href="index.html"><span>BACK TO TOP</span><i>{ARROW}</i></a></div>'

def kv_nav():
    """トップのファーストビュー：右上と右下の角かっこナビ（リンク先は NAV と URL の定数どおり）"""
    top = "".join(f'<li><a href="{k}.html"><span class="br">[</span>{en.upper()}<span class="br">]</span><small>{jp}</small></a></li>'
                  for k, en, jp in NAV if k in ("news", "about", "nurses", "schedule", "menu", "media"))
    bot = (f'<li><a href="guidelines.html"><span class="br">[</span>GUIDE<span class="br">]</span><small>入院のしおり</small></a></li>'
           f'<li><a href="faq.html"><span class="br">[</span>FAQ<span class="br">]</span><small>問診票</small></a></li>'
           f'<li><a href="contact.html"><span class="br">[</span>CONTACT<span class="br">]</span><small>受付</small></a></li>'
           f'<li><a {ext(GROUP_URL)}><span class="br">[</span>VRCHAT GROUP<span class="br">]</span><small>{"グループ" if GROUP_URL != "#" else TBD}</small></a></li>'
           f'<li><a {ext(X_URL)}><span class="br">[</span>X<span class="br">]</span><small>{esc(X_LABEL)}</small></a></li>')
    return top, bot

DESC = f"{EVENT_FULL}は、サキュバスたちがナースとして働くコンカフェ「{EVENT}」をテーマにした、VRChatで隔週月曜日の夜（21:50〜23:10）にひらく全年齢向けイベントです。"
PAGES = {
    # ファイル名: (メニューで光らせる項目, <title>, 説明文, ページ見出し)
    "index": ("", f"{EVENT_FULL}｜VRChat ナースコンカフェイベント", DESC, None),
    "news": ("news", f"NEWS｜{EVENT}", f"{EVENT}のお知らせ一覧", ("News", "お知らせ", "// LATEST_INFO")),
    "news-detail": ("news", f"NEWS｜{EVENT}", f"{EVENT}のお知らせ", ("News", "お知らせ", "// ARTICLE", '<a href="news.html">NEWS</a><i>/</i><span id="crumb-title">お知らせ</span>')),
    "about": ("about", f"ABOUT｜{EVENT}", f"{EVENT}の病院案内。" + DESC, ("About", "病院案内", "// CLINIC_GUIDE")),
    "nurses": ("nurses", f"NURSES｜{EVENT}", f"{EVENT}のナース紹介。在籍ナースのカルテ（プロフィール）を見られます。", ("Nurses", "ナース紹介", "// NURSE_KARTE")),
    "schedule": ("schedule", f"SCHEDULE｜{EVENT}", f"{EVENT}の診療日と診療時間（隔週月曜日 21:50〜23:10・日本時間）", ("Schedule", "診療時間", "// CLINIC_HOURS")),
    "menu": ("menu", f"MENU｜{EVENT}", f"{EVENT}の処方メニュー", ("Menu", "処方メニュー", "// PRESCRIPTION")),
    "media": ("media", f"MEDIA｜{EVENT}", f"{EVENT}のメディア（写真・動画）", ("Media", "メディア", "// MEDIA_ARCHIVE")),
    "guidelines": ("guidelines", f"GUIDELINES｜{EVENT}", f"{EVENT}の入院のしおり（ご来院のルール）", ("Guidelines", "入院のしおり", "// WARD_GUIDE")),
    "faq": ("faq", f"FAQ｜{EVENT}", f"{EVENT}の問診票（よくある質問）", ("FAQ", "問診票", "// MEDICAL_INTERVIEW")),
    "contact": ("contact", f"CONTACT｜{EVENT}", f"{EVENT}の受付（グループ・お問い合わせ）", ("Contact", "受付", "// RECEPTION")),
}

def head_meta(name, title, desc):
    url = f"{SITE_URL}/{'' if name == 'index' else name + '.html'}" if SITE_URL else ""
    ogimg = f"{SITE_URL}/img/ogp.jpg" if SITE_URL else "img/ogp.jpg"
    return "\n".join(filter(None, [
        f'<meta name="description" content="{esc(desc)}">',
        f'<link rel="canonical" href="{url}">' if url else "",
        f'<meta property="og:site_name" content="{esc(EVENT_FULL)}">',
        f'<meta property="og:type" content="{"website" if name == "index" else "article"}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{url}">' if url else "",
        f'<meta property="og:image" content="{ogimg}">',
        '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">' + (f'<meta name="twitter:site" content="@{esc(X_ID)}">' if X_ID else ""),
        '<meta name="theme-color" content="#07040b">',
        '<link rel="icon" href="favicon.png" type="image/png"><link rel="apple-touch-icon" href="apple-touch-icon.png">',
    ]))

# ---------------------------------------------------------------- トップ・共通の部品
def tate(text, flick=-1):
    """縦書きのネオン管の1列。flick 番目の1文字だけが、ときどき消える"""
    return "".join(f'<i class="flk">{esc(ch)}</i>' if k == flick else esc(ch) for k, ch in enumerate(text))

def nosig(label="IMG_PENDING", cls="", tag="div"):
    """仮画像（写真がまだないとき）：濃紫の面＋走査線＋ハートの照準＋ NO SIGNAL の表示＋四隅の L 字"""
    return (f'<{tag} class="nosig{" " + cls if cls else ""}" role="img" aria-label="画像は準備中です">'
            f'<svg class="nosig__mk" aria-hidden="true"><use href="#m-reticle"/></svg>'
            f'<span class="nosig__t mono" aria-hidden="true">NO SIGNAL</span><span class="nosig__s mono" aria-hidden="true">// {label}</span></{tag}>')

def band(kind, left="", right=""):
    """セクションの切り替えに入れる横いっぱいの帯（目盛り・心電図）"""
    if kind == "ecg":
        return (f'<div class="band --ecg" aria-hidden="true"><div class="inner band__in"><span class="mono">{left}</span>'
                f'<span class="band__ecg">{ECG_LONG}</span><span class="mono">{right}</span></div></div>')
    return (f'<div class="band --ruler" aria-hidden="true"><div class="inner band__in"><span class="mono">{left}</span>'
            f'<i class="band__rule"></i><span class="mono">{right}</span></div></div>')

# ---- トップの枠の中の「仮の主役」：ネオン看板のコラージュ（写真が1枚もないときだけ出す。人物・実在の看板は描かない）
_M, _C, _L = "#f046ff", "#46f0ff", "#e9a6ff"
def _tube(d, c, cls=""):
    """ネオン管の線（にじみ・管・白い芯の3層）"""
    return (f'<g class="tb{" " + cls if cls else ""}" style="--c:{c}"><path class="t-h" d="{d}"/><path class="t-m" d="{d}"/><path class="t-c" d="{d}"/></g>')
def _ttext(x, y, t, c, size, font="jp", extra=""):
    """ネオン管の文字（白い芯＋色の縁＋にじみ）"""
    a = f'x="{x}" y="{y}" font-size="{size}" text-anchor="middle" dominant-baseline="central" {extra}'
    return f'<g class="tt cl-{font}" style="--c:{c}"><text class="tt-h" {a}>{t}</text><text class="tt-c" {a}>{t}</text></g>'
def _heart(cx, cy, w):
    P = [(0, .42), (-.32, .2), (-.5, .02), (-.5, -.17), (-.5, -.36), (-.36, -.48), (-.22, -.48), (-.1, -.48), (-.03, -.41), (0, -.3),
         (.03, -.41), (.1, -.48), (.22, -.48), (.36, -.48), (.5, -.36), (.5, -.17), (.5, .02), (.32, .2), (0, .42)]
    f = lambda p: f"{cx + p[0] * w:.1f} {cy + p[1] * w:.1f}"
    return "M" + f(P[0]) + "".join("C" + " ".join(f(q) for q in P[k:k + 3]) for k in range(1, 19, 3)) + "Z"
def _rect(x, y, w, h, c=0):
    """角を 45° に切った箱（c ＝ 左上と右下の切り込み）"""
    return f"M{x + c} {y}H{x + w}V{y + h - c}L{x + w - c} {y + h}H{x}V{y + c}Z"

def collage_svg():
    import random
    R = random.Random(2156)
    out = ['<svg class="kvc" viewBox="0 0 820 700" preserveAspectRatio="xMidYMid slice" role="img" aria-label="ネオン看板が並ぶ夜の診療所（イメージ）">',
           '<defs><radialGradient id="kvc-g" cx="58%" cy="42%" r="60%"><stop offset="0" stop-color="#2a0f3d"/><stop offset=".6" stop-color="#12081f"/><stop offset="1" stop-color="#07040b"/></radialGradient></defs>',
           '<rect width="820" height="700" fill="url(#kvc-g)"/>']
    win = {}  # 窓（色ごとに1本の path にまとめる）
    def windows(x0, y0, x1, y1, sx, sy, prob, cols):
        for yy in range(y0, y1, sy):
            for xx in range(x0, x1, sx):
                if R.random() < prob:
                    k = (R.choice(cols), R.choice((.25, .45, .7)))
                    win.setdefault(k, []).append(f"M{xx} {yy}h4v6h-4z")
    # 遠くのビル（濃い紫のシルエット＋まばらな窓）
    x = -10
    while x < 820:
        w = R.randint(44, 92); h = R.randint(330, 610)
        out.append(f'<rect x="{x}" y="{700 - h}" width="{w - 5}" height="{h}" fill="#140a22"/>')
        windows(x + 6, 712 - h, x + w - 10, 690, 10, 17, .13, (_L, _C, _M))
        x += w
    # 手前のビル（輪郭の極細線＋規則的な窓の格子）
    for (bx, by, bw) in ((26, 236, 132), (216, 300, 186), (598, 196, 118), (730, 330, 100)):
        out.append(f'<path d="{_rect(bx, by, bw, 720 - by, 0)}" fill="#1b0d2d" stroke="{_M}" stroke-opacity=".32" stroke-width="1"/>')
        out.append(f'<path d="M{bx + 6} {by + 8}H{bx + bw - 6}" stroke="{_L}" stroke-opacity=".35" stroke-width="1"/>')
    windows(40, 410, 150, 680, 14, 18, .55, (_M, _L, _L))           # 左のビルの窓の格子
    windows(612, 330, 704, 470, 12, 16, .4, (_L, _C, _M))           # 右のビル
    windows(742, 352, 812, 600, 12, 18, .35, (_M, _L))
    for (c, a), ds in sorted(win.items()):
        out.append(f'<path d="{"".join(ds)}" fill="{c}" opacity="{a}"/>')
    # 電線（シアンの極細線）・位置合わせの＋
    for d in ("M150 262Q380 330 600 214", "M158 300Q300 360 420 330", "M402 318Q560 390 732 346", "M0 180Q90 220 160 236"):
        out.append(f'<path d="{d}" fill="none" stroke="{_C}" stroke-opacity=".32" stroke-width="1"/>')
    for (px, py) in ((216, 300), (402, 300), (598, 196), (716, 196), (730, 330)):
        out.append(f'<path d="M{px - 6} {py}h12M{px} {py - 6}v12" stroke="{_C}" stroke-opacity=".7" stroke-width="1"/>')
    # ハザードの帯（45°）
    out.append('<g fill="#f046ff" opacity=".85">' + "".join(f'<path d="M{x} 676l12-12h8l-12 12z"/>' for x in range(222, 396, 16)) + '</g>')
    # 点滴（ラベンダーのバッグ → シアンの管 → 「処方」の看板へ）
    out.append(_tube(_rect(166, 26, 48, 64, 8), _L))
    out.append(f'<path d="M174 46h32M174 56h20M174 66h26" stroke="{_L}" stroke-opacity=".6" stroke-width="1"/>')
    out.append(_tube("M190 90V112M190 124V196L160 226", _C))
    out.append(f'<g fill="{_C}"><circle cx="190" cy="118" r="2.4"/><circle cx="190" cy="140" r="1.8" opacity=".7"/><circle cx="190" cy="160" r="1.8" opacity=".5"/></g>')
    out.append(f'<text class="cl-mono" x="222" y="44" font-size="10" fill="{_L}" opacity=".7">Rx.DRIP</text>')
    # 「処方」の縦長の看板
    out.append(_tube(_rect(108, 226, 60, 160, 10), _M))
    out.append(_ttext(138, 278, "処", _M, 44) + _ttext(138, 336, "方", _M, 44))
    out.append(f'<text class="cl-mono" x="112" y="400" font-size="10" fill="{_L}" opacity=".7">SC-01</text>')
    # 「診」の大きな看板（二重の枠）
    out.append(_tube(_rect(236, 104, 152, 152, 14), _M))
    out.append(f'<path d="{_rect(248, 116, 128, 128, 8)}" fill="#1b0d2d" fill-opacity=".6" stroke="{_L}" stroke-opacity=".55" stroke-width="1"/>')
    out.append(_ttext(312, 182, "診", _M, 100))
    out.append(f'<text class="cl-mono" x="388" y="270" font-size="10" text-anchor="end" fill="{_L}" opacity=".7">WARD 02 // 3F</text>')
    # 十字の看板
    out.append(_tube("M590 40h22v22h22v22h-22v22h-22v-22h-22v-22h22z", _M))
    # 「24H」
    out.append(_tube(_rect(652, 100, 104, 48, 8), _M))
    out.append(_ttext(704, 125, "24H", _M, 30, "en"))
    # 「夢」の丸い看板（ときどき1回だけ消える）
    out.append('<g class="cl-flk">' + _tube("M668 172a42 42 0 1 1 0 84a42 42 0 1 1 0-84z", _L) + _ttext(668, 214, "夢", _L, 50) + '</g>')
    out.append(f'<path d="M668 150v22" stroke="{_L}" stroke-opacity=".5" stroke-width="1"/>')
    # ハートの照準（主役の中心：あなたをロックオン）
    out.append(f'<circle cx="505" cy="300" r="124" fill="none" stroke="{_C}" stroke-opacity=".55" stroke-width="1.2" stroke-dasharray="60 14 6 14"/>')
    out.append(f'<circle cx="505" cy="300" r="100" fill="none" stroke="{_C}" stroke-opacity=".25" stroke-width="1"/>')
    out.append(f'<path d="M505 164v28M505 408v28M369 300h28M613 300h28" stroke="{_C}" stroke-width="2"/>')
    out.append(f'<path d="M405 200h-18v18M605 200h18v18M405 400h-18v-18M605 400h18v-18" fill="none" stroke="{_C}" stroke-opacity=".8" stroke-width="1.5"/>')
    out.append(_tube(_heart(505, 300, 170), _M))
    out.append(_tube("M499 290h12M505 284v12", _M))
    out.append(f'<text class="cl-mono" x="505" y="452" font-size="12" text-anchor="middle" fill="{_C}">TARGET: YOU // LOCK ON</text>')
    out.append(f'<text class="cl-mono" x="560" y="160" font-size="10" fill="{_C}" opacity=".7">DIST 0.8m</text>')
    # 「NURSE」のステッカー（ラベンダーの面・光らない）
    out.append(f'<path d="{_rect(214, 424, 188, 50, 10)}" fill="{_L}"/>')
    out.append('<path d="M222 430h10v4h-10z" fill="#1a0a24"/>')
    out.append('<text class="cl-en" x="314" y="450" font-size="34" font-weight="700" text-anchor="middle" dominant-baseline="central" letter-spacing="4" fill="#1a0a24">NURSE</text>')
    # 「CLINIC」（シアンの管）
    out.append(_tube(_rect(470, 496, 228, 58, 10), _C))
    out.append(_ttext(584, 525, "CLINIC", _C, 38, "en", 'letter-spacing="5"'))
    # 吊り下げのハート
    out.append(f'<path d="M168 448L190 410M212 448L190 410" stroke="{_L}" stroke-opacity=".45" stroke-width="1"/>')
    out.append(_tube(_heart(190, 476, 54), _M))
    # カプセル（ラベンダーの面＋マゼンタの線、45°）
    for (cx, cy) in ((448, 580), (330, 560), (772, 430)):
        out.append(f'<g transform="rotate(-45 {cx} {cy})"><rect x="{cx - 26}" y="{cy - 10}" width="52" height="20" rx="10" fill="#1b0d2d" stroke="{_M}" stroke-width="1.5"/>'
                   f'<path d="M{cx} {cy - 10}h16a10 10 0 0 1 0 20h-16z" fill="{_L}"/></g>')
    # 心電図（山のひとつがハート）
    ecg = ("M40 628H210l8-8 8 8h10l8-34 12 64 10-50 6 18h20"
           "C318 600 304 586 318 580C330 576 336 588 336 596C336 588 342 576 354 580C368 586 354 600 336 628"
           "H460l8-8 8 8h10l8-30 12 56 10-44 6 18H800")
    out.append(_tube(ecg, _M, "cl-ecg"))
    out.append(f'<path class="cl-pulse" d="{ecg}" pathLength="100" fill="none" stroke="#fff" stroke-width="2.4" stroke-linecap="round"/>')
    out.append(f'<text class="cl-mono" x="790" y="652" font-size="11" text-anchor="end" fill="{_C}">VITAL ♡ 72BPM</text>')
    out.append('</svg>')
    return "".join(out)

def cast_ids(CAST, n=3):
    """トップの NURSES：ナースの ID カード（診察券）"""
    out = []
    for k, c in enumerate(CAST[:n], 1):
        nm = esc(c["name"]); p = c.get("p") or {}
        catch = esc(p.get("catch") or "カルテ準備中")
        out.append(f'<li class="idc rv"><a class="idc__a" href="nurses.html#{c["id"]}" aria-label="{nm}のカルテを見る">'
                   f'<span class="idc__top mono"><b>NRS-{k:02d}</b><span>SC // PATIENT CARE</span></span>'
                   f'<span class="idc__ph"><img src="img/cast/s/{c["id"]}.webp" alt="" width="400" height="601" loading="lazy" decoding="async"></span>'
                   f'<span class="idc__body"><b class="idc__name">{nm}</b><span class="idc__en mono">{esc(p.get("card") or "")}</span><span class="idc__catch">{catch}</span></span>'
                   f'<span class="idc__foot"><svg class="idc__bar" aria-hidden="true"><use href="#d-bars"/></svg><svg class="idc__rt" aria-hidden="true"><use href="#m-reticle"/></svg></span></a></li>')
    return "\n".join(out) or f'<li class="idc --empty">{nosig("NURSE_PENDING")}</li>'

def about_vis(PHOTOS):
    """病院案内の写真：集合写真があれば1枚目、なければ NO SIGNAL"""
    gs = [p for p in PHOTOS if p["gallery"]]
    if gs: return f'<img src="img/photo/s/{gs[0]["id"]}.webp" alt="{esc(gs[0]["alt"])}" width="800" height="400" loading="lazy" decoding="async">'
    return nosig("WARD_PHOTO")

# ---------------------------------------------------------------- 一覧の HTML
def cast_list(CAST):
    out = []
    for k, c in enumerate(CAST, 1):
        n = esc(c["name"]); p = c.get("p")
        gen = str(p["gen"]) if p else "0"
        chip = f'<span class="ccard__gen g{gen}">{gen}期生</span>' if p else '<span class="ccard__gen g0">準備中</span>'
        catch = f'<span class="ccard__catch">{esc(p["catch"])}</span>' if p and p["catch"] else ''
        out.append(f'        <li class="ccard rv" data-id="{c["id"]}" data-name="{n}" data-gen="{gen}" data-no="{k:02d}" style="--c:{c["c"]};--c2:{c["c2"]}"><button class="ccard__btn" type="button" aria-label="{n}のカルテを見る">'
                   f'<span class="ccard__top mono"><b>NRS-{k:02d}</b><span>SC // KARTE</span></span>'
                   f'<span class="ccard__ph"><img src="img/cast/s/{c["id"]}.webp" alt="{n}" width="400" height="601" loading="lazy" decoding="async">{chip}</span>'
                   f'<span class="ccard__name">{n}</span>{catch}'
                   f'<span class="ccard__foot"><svg aria-hidden="true"><use href="#d-bars"/></svg><svg class="ccard__rt" aria-hidden="true"><use href="#m-reticle"/></svg></span></button></li>')
    return "\n".join(out)

def cast_data(CAST):
    d = {c["id"]: c["p"] for c in CAST if c.get("p")}
    return '<script type="application/json" id="cast-data">' + json.dumps(d, ensure_ascii=False).replace("</", "<\\/") + '</script>'

def cast_tabs(CAST):
    gens = sorted({c["p"]["gen"] for c in CAST if c.get("p")})
    cnt = lambda g: sum(1 for c in CAST if (c["p"]["gen"] if c.get("p") else 0) == g)
    b = [f'<button type="button" role="tab" data-gen="all" aria-selected="true">すべて<small>{len(CAST)}</small></button>']
    b += [f'<button type="button" role="tab" data-gen="{g}" aria-selected="false">{g}期生<small>{cnt(g)}</small></button>' for g in gens]
    if cnt(0): b.append(f'<button type="button" role="tab" data-gen="0" aria-selected="false">カルテ準備中<small>{cnt(0)}</small></button>')
    return "".join(b)

MOVIE_TAGS = [("short", "ショート"), ("pv", "PV"), ("live", "配信"), ("cover", "歌ってみた")]
def movie_tabs(MOVIES):
    cnt = lambda t: sum(1 for m in MOVIES if m["tag"] == t)
    b = [f'<button type="button" role="tab" data-cat="all" aria-selected="true">すべて<small>{len(MOVIES)}</small></button>']
    b += [f'<button type="button" role="tab" data-cat="{k}" aria-selected="false">{v}<small>{cnt(k)}</small></button>' for k, v in MOVIE_TAGS]
    return "".join(b)

def movie_list(MOVIES, CAST):
    tagname = dict(MOVIE_TAGS); ccol = {c["name"]: c["c2"] for c in CAST}; out = []
    for m in MOVIES:
        t = esc(m["title"]); who = m["cast"]
        meta = f'<span class="mv__who" style="--c:{ccol.get(who, "#ff2e9a")}">{esc(who)}</span>' if who else ""
        out.append(f'        <li class="mv rv" data-cat="{m["tag"]}"><a class="mv__link{" --short" if m["tag"] == "short" else ""}" href="{esc(m["url"])}" target="_blank" rel="noopener" aria-label="{t}（YouTubeで見る・新しいタブ）">'
                   f'<span class="mv__thumb"><img src="{m["thumb"]}" alt="" width="800" height="450" loading="lazy" decoding="async"><span class="mv__play" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z" fill="currentColor"/></svg></span><span class="mv__tag --{m["tag"]}">{tagname[m["tag"]]}</span></span>'
                   f'<span class="mv__title">{t}</span><span class="mv__meta">{meta}<span class="mv__yt mono">YOUTUBE ↗</span></span></a></li>')
    return "\n".join(out) or f'        <li class="mv --empty">{nosig("MOVIE_PENDING")}<p class="empty">動画はまだありません。</p></li>'

def hero_slides(PHOTOS):
    hs = [p for p in PHOTOS if p["hero"]]
    out = []
    for k, p in enumerate(hs):
        w, h = p["hero"]
        if k == 0: out.append(f'          <img class="is-on" src="img/photo/h/{p["id"]}.webp" alt="{esc(p["alt"])}" width="{w}" height="{h}" fetchpriority="high" decoding="async">')
        else: out.append(f'          <img data-src="img/photo/h/{p["id"]}.webp" alt="{esc(p["alt"])}" width="{w}" height="{h}" decoding="async" aria-hidden="true">')
    return "\n".join(out) or f'          <div class="kv__collage">{collage_svg()}</div>'

def gallery(PHOTOS, kind):
    gs = [p for p in PHOTOS if p["gallery"]]; out = []
    for k, p in enumerate(gs, 1):
        img = f'<img src="img/photo/s/{p["id"]}.webp" alt="{esc(p["alt"])}" width="800" height="400" loading="lazy" decoding="async">'
        if kind == "nurses":
            out.append(f'        <li class="fr --s rv"><button class="gal-btn" type="button" data-full="img/photo/{p["id"]}.webp" aria-label="写真{k}を大きく見る">{img}</button><span class="mono">PHOTO {k:02d}</span></li>')
        else:
            out.append(f'        <li class="mitem rv"><button class="gal-btn" type="button" data-full="img/photo/{p["id"]}.webp" aria-label="PHOTO {k:02d}を大きく見る">{img}</button><span class="mitem__lab mono">PHOTO {k:02d}</span></li>')
    if not out:
        out.append(f'        <li class="gal-empty">{nosig("PHOTO 00 // IMG_PENDING")}</li>')
    return "\n".join(out), len(gs)

# ---------------------------------------------------------------- ページの書き出し
def build_page(name, D):
    cur, title, desc, ph = PAGES[name]
    body = open(os.path.join(SRC, name + ".html"), encoding="utf-8").read().strip()
    gal, photon = gallery(D["photos"], "nurses" if name == "nurses" else "media")
    kt, kb = kv_nav()
    rep = {"{{ARROW}}": ARROW, "{{BACK}}": back(), "{{CASTN}}": str(len(D["cast"])), "{{PHOTON}}": str(photon),
           "{{MOVIEN}}": str(len(D["movies"])), "{{LOGO}}": logo(), "{{ECG_LONG}}": ECG_LONG, "{{IC_CAL}}": ic("n-cal"), "{{IC_PIN}}": ic("n-pin"), "{{IC_DEVIL}}": ic("m-devil"), "{{HERO_SLIDES}}": hero_slides(D["photos"]), "{{GALLERY}}": gal,
           "{{KV_TATE_A}}": tate(KV_TATE_A, KV_FLICK), "{{KV_TATE_B}}": tate(KV_TATE_B), "{{KV_N_A}}": str(len(KV_TATE_A)), "{{KV_N_B}}": str(len(KV_TATE_B)), "{{KV_MODE}}": "--photo" if any(p["hero"] for p in D["photos"]) else "--collage",
           "{{CAST_IDS}}": cast_ids(D["cast"]), "{{ABOUT_VIS}}": about_vis(D["photos"]),
           "{{NEWSN}}": f'{len(D["news"]):02d}', "{{NEWSDATE}}": D["news"][0]["date"] if D["news"] else "----.--.--",
           "{{KV_NAV_TOP}}": kt, "{{KV_NAV_BOT}}": kb,
           "{{GROUP_LINK}}": ext(GROUP_URL), "{{X_LINK}}": ext(X_URL), "{{TAG_LINK}}": ext(TAG_URL), "{{X_ID}}": esc(X_LABEL), "{{HASHTAG}}": esc(TAG_LABEL),
           "{{WORLD}}": esc(WORLD or TBD), "{{EVENT}}": EVENT, "{{EVENT_FULL}}": EVENT_FULL}
    if "{{MOVIES}}" in body: rep.update({"{{MOVIES}}": movie_list(D["movies"], D["cast"]), "{{MOVIETABS}}": movie_tabs(D["movies"])})
    if "{{CAST}}" in body: rep.update({"{{CAST}}": cast_list(D["cast"]), "{{CASTTABS}}": cast_tabs(D["cast"]), "{{CASTDATA}}": cast_data(D["cast"])})
    if ph: body = body.replace("{{PHEAD}}", phead(*ph, page=name))
    for k, v in rep.items(): body = body.replace(k, v)
    body = re.sub(r"\{\{BAND:([^}]*)\}\}", lambda m: band(*(m.group(1).split("|") + ["", ""])[:3]), body)
    # 見出し：{{HX:英字|日本語|コード|番号}} と、各ページの小見出し（sub-h）を、記号付きのテック見出しに
    body = re.sub(r"\{\{HX:([^}]*)\}\}", lambda m: hx(*(m.group(1).split("|") + ["", "", "", ""])[:5]), body)
    body = re.sub(r'<div class="sub-h[^"]*"><b class="neon[^"]*">(.*?)</b><span>(.*?)</span><i></i></div>', lambda m: hx(m.group(1), m.group(2), sub=True), body)
    outside = ""
    if "{{OUT}}" in body:  # 本文の外（ヘッダーより前面）に置く部品
        i, j = body.index("{{OUT}}"), body.index("{{/OUT}}")
        outside = body[i + 7:j].strip(); body = (body[:i] + body[j + 8:]).strip()
    main = f'<main id="top" class="page-{name}">\n  {body}\n</main>'
    extra = ""
    if name == "index":
        extra = LOADING + "\n\n"
        outside = open(os.path.join(SRC, "index.modal.html"), encoding="utf-8").read().strip() + "\n" + outside
    out = f'''<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{esc(title)}</title>
{PT_HEAD}
{head_meta(name, title, desc)}
{FONTS}
</head>
<body{' class="is-home"' if name == "index" else ""}>
{PAGE_TRANSITION}
{SPRITE}

{BG}
{extra}
{header(cur)}

{main}

{footer()}
{outside}
<script src="assets/cast.js"></script>
<script src="assets/news.js"></script>
<script src="assets/schedule.js"></script>
<script src="assets/site.js"></script>
</body>
</html>
'''.replace("{{CASTN}}", str(len(D["cast"])))
    # CSS・JS にバージョン（中身のハッシュ）を付けて、更新したらブラウザが必ず新しいものを読むようにする
    for a in ("assets/site.css", "assets/site.js", "assets/cast.js", "assets/news.js", "assets/schedule.js"):
        fp = os.path.join(OUT, a)
        if os.path.exists(fp): out = out.replace(f'"{a}"', f'"{a}?v={hashlib.sha1(open(fp, "rb").read()).hexdigest()[:10]}"')
    left = re.findall(r"\{\{\w+\}\}", out)
    if left: raise SystemExit(f"{name}.html に置き換えていない部分があります: {left}")
    open(os.path.join(OUT, name + ".html"), "w", encoding="utf-8").write(out)

def write_js(D):
    cast = [{"id": c["id"], "n": c["name"], "c": c["c"], "c2": c["c2"], "g": (c.get("p") or {}).get("gen", 0), "t": (c.get("p") or {}).get("catch", ""), "r": (c.get("p") or {}).get("roles", []), "y": (c.get("p") or {}).get("type", "")} for c in D["cast"]]
    open(os.path.join(OUT, "assets", "cast.js"), "w", encoding="utf-8").write("/* 処方おみくじ・検温ゲーム・ナース大行進などで使うナース一覧（build.py が自動生成） */\nwindow.MD_CAST = " + json.dumps(cast, ensure_ascii=False) + ";\nwindow.MD_TYPES = " + json.dumps({str(k): v for k, v in sorted(TYPES.items())}, ensure_ascii=False) + ";\n")
    open(os.path.join(OUT, "assets", "schedule.js"), "w", encoding="utf-8").write("/* スケジュール：特別診療(sp)・休診(off)。s/e は開始・終了（0時からの分）（build.py が content/schedule から自動生成） */\nwindow.MD_SCHEDULE = " + json.dumps(D["schedule"], ensure_ascii=False).replace("</", "<\\/") + ";\n")
    open(os.path.join(OUT, "assets", "news.js"), "w", encoding="utf-8").write("/* お知らせ（build.py が content/news から自動生成。新しい順） */\nwindow.MD_NEWS = " + json.dumps(D["news"], ensure_ascii=False).replace("</", "<\\/") + ";\n")

def write_extras():
    open(os.path.join(OUT, ".nojekyll"), "w").write("")
    if SITE_URL:
        urls = "".join(f"<url><loc>{SITE_URL}/{'' if n == 'index' else n + '.html'}</loc></url>" for n in PAGES if n != "news-detail")
        open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
        open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nDisallow: /admin/\nSitemap: {SITE_URL}/sitemap.xml\n")
    shutil.copytree(os.path.join(ROOT, "admin"), os.path.join(OUT, "admin"))
    # 管理画面の設定に、リポジトリ名とサイトのURLを自動で書き入れる（GitHub Actions が教えてくれる）
    cfg_path = os.path.join(OUT, "admin", "config.yml"); cfg = open(cfg_path, encoding="utf-8").read()
    repo = os.environ.get("REPO", "")
    if repo: cfg = re.sub(r"(?m)^(\s*repo:\s*)OWNER/REPO\s*$", r"\g<1>" + repo, cfg)
    cfg = re.sub(r"(?m)^(site_url|display_url):\s*SITE_URL\s*$", (lambda m: f"{m.group(1)}: {SITE_URL}/") if SITE_URL else "", cfg)
    open(cfg_path, "w", encoding="utf-8").write(cfg)

if __name__ == "__main__":
    if os.path.isdir(OUT): shutil.rmtree(OUT)
    shutil.copytree(STATIC, OUT)
    D = {"cast": build_cast(), "news": build_news(), "photos": build_photos(), "schedule": build_schedule()}
    D["movies"] = build_movies(D["cast"])
    write_js(D)
    for n in PAGES:
        if os.path.exists(os.path.join(SRC, n + ".html")): build_page(n, D)
    write_extras()
    print(f"OK  ナース {len(D['cast'])}名 / お知らせ {len(D['news'])}件 / 動画 {len(D['movies'])}本 / 写真 {len(D['photos'])}枚 / 特別診療・休診 {len(D['schedule'])}件" + (f" / 注意 {len(WARN)}件" if WARN else ""))
