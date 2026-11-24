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
PUBLIC_URL = "https://succubusclinicssr.github.io"  # 公開URL（GitHub Actions では環境変数 SITE_URL が優先されます）
NOINDEX = True     # 検索よけ。True のあいだは、検索サイトに「このサイトを載せないで」と伝えます。イベントを発表したら False にしてください
GROUP_URL = "#"    # VRChat グループの URL（未定のあいだは "#"）
X_URL = "#"        # 公式 X の URL（例 "https://x.com/xxxx"。未定のあいだは "#"）
X_ID = ""          # 公式 X の ID（@ は付けない。未定のあいだは空 → 「準備中」と表示、twitter:site も出さない）
HASHTAG = ""       # ハッシュタグ（# は付けない。未定のあいだは空 → 「準備中」と表示）
WORLD = ""         # 会場ワールド名（未定のあいだは空 → 「準備中」と表示）
TBD = "準備中"

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

# ---------------------------------------------------------------- 背景の六角タイル：ハチの巣のかたまりの並べ方（絵の組み立ては下の hexwall()、色は site.css の .hc）
#   壁ぜんぶを六角にはせず、画面の左上と右下にだけ六角のかたまりを置き、あいだは無地のまま残す。
#   かたまりは、わざと不ぞろいにする：色つきを散らし、ところどころ 1 枚ぬいて穴をあける（行の番号がとんでいる所が穴）。
#   1行＝1枚：(列, 行, 種類, マーク, 文字)。1枚足すときは1行足し、消すときは1行消すだけ。
#   列は「画面のはし」から数える（_L は左はしから、_R は右はしから。0 がいちばん外）。行は上から。どちらも 0 から。
#   となりの列とは半段ずつずれてかみ合う（ハチの巣の並び）。
#   種類：w 白いタイル（マークも文字もなし。見出しなどの文字の下に来てもじゃまにならない）
#         p ピンク / c シアン / v むらさき / k 紺紫（ここまで塗り）、pp うすいピンク / cp うすいシアン、o 白いタイルに線の枠
#   マーク：heart ハート / cross 十字 / pulse 心電図 / drop しずく
#   文字：NURSE CALL / HEART RATE / TOKIMEKI / SSR / CLINIC（PC だけ。スマホは文字を出さないので書かない）
#   PC は 16 行、スマホは 20 行ごとに、同じ並びが下へくり返される（縦に長い画面用）。
#   見出しやパンくずの文字が通る所（左上の内側）は w だけにしてある。紺紫（k）は文字が読めなくなるので、いちばん外の列だけ。
HEX_PC_L = [
    # 左上：左はしの列に色つき（行 2 は穴）、内側は白いタイル（パンくずの所は穴）
    (0, 0, "c",  "drop",  "SSR"),
    (0, 1, "p",  "heart", "NURSE CALL"),
    (0, 3, "k",  "pulse", "HEART RATE"),
    (0, 4, "pp", "drop",  "TOKIMEKI"),
    (1, 1, "w"),
    (1, 2, "w"),
    (1, 4, "cp", "pulse", "CLINIC"),
    (1, 5, "pp", "cross", "SSR"),
    (2, 1, "w"),
    (2, 3, "w"),
    (2, 4, "w"),
    (3, 1, "w"),
    (3, 2, "w"),
    (4, 1, "w"),
    (4, 2, "w"),
    (5, 1, "w"),
    # 少し離れて飛ぶタイル
    (7, 1, "w"),
]
HEX_PC_R = [
    # 右下（列 0 の行 5〜7 は、壁の照準と警告ラベルの場所なので空けてある）
    (0, 8,  "p",  "pulse", "SSR"),
    (0, 9,  "k",  "cross", "TOKIMEKI"),
    (0, 11, "p",  "heart", "NURSE CALL"),
    (0, 12, "pp", "cross", "HEART RATE"),
    (0, 14, "cp", "drop",  "CLINIC"),
    (0, 15, "o",  "pulse", "TOKIMEKI"),
    (1, 4,  "w"),
    (1, 5,  "o",  "cross", "SSR"),
    (1, 6,  "p",  "heart", "CLINIC"),
    (1, 8,  "v",  "drop",  "HEART RATE"),
    (1, 9,  "pp", "cross", "TOKIMEKI"),
    (1, 10, "c",  "pulse", "SSR"),
    (1, 12, "cp", "drop",  "CLINIC"),
    (1, 13, "w"),
    (2, 5,  "w"),
    (2, 6,  "pp", "pulse", "NURSE CALL"),
    (2, 7,  "o",  "drop",  "HEART RATE"),
    (2, 8,  "c",  "heart", "TOKIMEKI"),
    (2, 10, "p",  "cross", "CLINIC"),
    (2, 11, "o",  "heart", "NURSE CALL"),
    (2, 12, "w"),
    (3, 6,  "cp", "cross", "SSR"),
    (3, 7,  "w"),
    (3, 8,  "pp", "heart", "CLINIC"),
    (3, 9,  "c",  "drop",  "NURSE CALL"),
    (3, 11, "w"),
    (4, 6,  "o",  "heart", "TOKIMEKI"),
    (4, 7,  "pp", "drop",  "SSR"),
    (4, 9,  "o",  "pulse", "HEART RATE"),
    (4, 10, "pp", "cross", "TOKIMEKI"),
    (4, 11, "w"),
    (5, 6,  "w"),
    (5, 8,  "p",  "heart", "NURSE CALL"),
    (5, 9,  "w"),
    (5, 10, "cp", "pulse", "CLINIC"),
    (6, 7,  "cp", "drop",  "SSR"),
    (6, 9,  "o",  "cross", "CLINIC"),
    (6, 10, "w"),
    (7, 6,  "o",  "pulse", "TOKIMEKI"),
    (7, 8,  "w"),
    # 少し離れて飛ぶタイル
    (8, 10, "w"),
]
HEX_SP_L = [
    # 左上：ロゴのうしろの白いタイル（ところどころ穴）。色つきは、パンくず・見出しの文字と重ならない角とヘッダーのすき間だけ
    (0, 0, "cp", "heart"),
    (0, 1, "p",  "cross"),
    (0, 3, "w"),
    (0, 4, "w"),
    (1, 0, "w"),
    (1, 2, "w"),
    (1, 3, "w"),
    (2, 0, "w"),
    (2, 1, "w"),
    (2, 3, "w"),
    (3, 0, "w"),
    (3, 1, "w"),
    (4, 1, "w"),
    (5, 0, "cp", "drop"),
]
HEX_SP_R = [
    # 右下
    (0, 11, "pp", "drop"),
    (0, 12, "k",  "heart"),
    (0, 13, "p",  "cross"),
    (0, 15, "v",  "drop"),
    (0, 16, "pp", "heart"),
    (0, 18, "o",  "heart"),
    (1, 9,  "w"),
    (1, 10, "c",  "heart"),
    (1, 11, "cp", "pulse"),
    (1, 13, "pp", "pulse"),
    (1, 14, "c",  "drop"),
    (1, 15, "o",  "heart"),
    (1, 16, "w"),
    (2, 10, "o",  "drop"),
    (2, 11, "pp", "heart"),
    (2, 12, "p",  "cross"),
    (2, 14, "cp", "cross"),
    (2, 15, "w"),
    (3, 10, "w"),
    (3, 11, "o",  "pulse"),
    (3, 13, "c",  "drop"),
    (3, 14, "w"),
    (4, 11, "w"),
    (4, 12, "pp", "cross"),
    (4, 14, "o",  "heart"),
    (5, 12, "w"),
    (5, 13, "cp", "pulse"),
    # 少し離れて飛ぶタイル
    (6, 14, "w"),
]

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
METER = ("talk", "sweet", "spice", "dist")    # カルテの4項目：お話し・甘さ・刺激・距離
def meter_val(v):
    """1〜10 の整数ならその数、それ以外（""・None・範囲外・小数・文字）は None"""
    if isinstance(v, bool): return None
    try: f = float(str(v).strip())
    except (TypeError, ValueError): return None
    return int(f) if f.is_integer() and 1 <= f <= 10 else None
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
        # カルテの4項目（1〜10 の整数。空・範囲外・数字でないものは未入力＝None）
        meter = {k: meter_val(d.get(k)) for k in METER}
        catch = str(d.get("catch") or "").strip()
        p = None
        # カルテあり：期生がある、またはキャッチコピーがある、または4項目がそろっている
        if gen > 0 or catch or all(v is not None for v in meter.values()):
            p = {"card": str(d.get("card") or ""), "catch": catch}
            p.update(gen=gen, roles=roles, type=(TYPES.get(gen) or "ナース") if gen > 0 else "", **meter)
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
NAV = [("news", "NEWS", "お知らせ"), ("about", "ABOUT", "病院案内"), ("nurses", "NURSES", "ナース紹介"), ("schedule", "SCHEDULE", "診療時間"),
       ("menu", "MENU", "処方メニュー"), ("media", "MEDIA", "メディア"), ("guidelines", "GUIDELINES", "入院のしおり"), ("faq", "FAQ", "問診票")]
ARROW = '<svg viewBox="0 0 16 12"><use href="#i-arrow"/></svg>'
AC = ' aria-current="page"'

SPRITE = '''<svg width="0" height="0" style="position:absolute" aria-hidden="true">
  <defs>
    <linearGradient id="brim-g" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f954c2"/><stop offset=".5" stop-color="#9a6bf4"/><stop offset="1" stop-color="#00abfc"/></linearGradient>
    <symbol id="i-ribbon" viewBox="0 0 100 100">
      <path d="M50 46 C38 30 12 24 10 40 C8 56 30 62 50 50 C70 62 92 56 90 40 C88 24 62 30 50 46 Z" fill="#fa79d0" stroke="#fff" stroke-width="6" stroke-linejoin="round"/>
      <path d="M44 52 L32 84 L43 79 L48 90 L50 58 M56 52 L68 84 L57 79 L52 90 L50 58" fill="#01abfc" stroke="#fff" stroke-width="6" stroke-linejoin="round"/>
      <circle cx="50" cy="48" r="10" fill="#d8158f" stroke="#fff" stroke-width="5"/>
    </symbol>
    <symbol id="i-arrow" viewBox="0 0 16 12"><path d="M1 6h13M9.5 1.5L14 6l-4.5 4.5" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></symbol>
    <symbol id="i-x" viewBox="0 0 512 512"><path d="M389.2 48h70.6L305.6 224.2 487 464H345L233.7 318.6 106.5 464H35.8L200.7 275.5 26.8 48H172.4L272.9 180.9 389.2 48zM364.4 421.8h39.1L151.1 88h-42L364.4 421.8z"/></symbol>
    <symbol id="i-heart" viewBox="0 0 40 36"><path d="M20 34 C7 25 2 18 2 11 C2 5 6 2 11 2 C15 2 18 4 20 8 C22 4 25 2 29 2 C34 2 38 5 38 11 C38 18 33 25 20 34 Z" fill="#fa79d0" stroke="#2a1f4a" stroke-width="2.4" stroke-linejoin="round"/></symbol>
    <symbol id="i-vr" viewBox="0 0 40 30"><rect x="2" y="6" width="36" height="20" rx="7" fill="#01abfc" stroke="#2a1f4a" stroke-width="2.4"/><circle cx="13" cy="16" r="4.5" fill="#fff" stroke="#2a1f4a" stroke-width="2"/><circle cx="27" cy="16" r="4.5" fill="#fff" stroke="#2a1f4a" stroke-width="2"/><path d="M8 6 C10 2 30 2 32 6" fill="none" stroke="#2a1f4a" stroke-width="2.4"/></symbol>
    <symbol id="i-cal" viewBox="0 0 36 36"><rect x="3" y="6" width="30" height="27" rx="6" fill="#fff" stroke="#2a1f4a" stroke-width="2.4"/><path d="M3 14h30" stroke="#2a1f4a" stroke-width="2.4"/><path d="M11 3v6M25 3v6" stroke="#2a1f4a" stroke-width="2.4" stroke-linecap="round"/><path d="M18 30 C12 26 10 24 10 21 C10 19 11.5 18 13 18 C14.5 18 15.5 19 18 21 C20.5 19 21.5 18 23 18 C24.5 18 26 19 26 21 C26 24 24 26 18 30 Z" fill="#fa79d0"/></symbol>
  </defs>
</svg>'''

FONTS = '''<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Tomorrow:wght@700;900&family=Rajdhani:wght@500;600;700&family=IBM+Plex+Sans+JP:wght@400;500;700&display=swap">
<link rel="stylesheet" href="assets/site.css">'''

# 背景：病院の壁のような白いタイル（CSSだけで描く）＋ 心電図モニターの波形（ピンクとシアンの2本。動きは site.css）
# 波形は横1200の座標で、PC用（拍が細かい）とスマホ用（拍が大きい）の2本を持ち、CSSで出し分ける
ECG_PATHS = {
    "p": ("M0 60 L20 60 L28 54 L36 60 L52 60 L56 66 L62 14 L68 78 L73 60 L96 60 L108 48 L122 60 L200 60 L220 60 L228 54 L236 60 L252 60 L256 66 L262 18.6 L268 78 L273 60 L296 60 L308 48 L322 60 L400 60 L420 60 L428 54 L436 60 L452 60 L456 66 L462 11.7 L468 78 L473 60 L496 60 L508 48 L522 60 L600 60 L620 60 L628 54 L636 60 L652 60 L656 66 L662 20.9 L668 78 L673 60 L696 60 L708 48 L722 60 L800 60 L820 60 L828 54 L836 60 L852 60 L856 66 L862 14 L868 78 L873 60 L896 60 L908 48 L922 60 L1000 60 L1020 60 L1028 54 L1036 60 L1052 60 L1056 66 L1062 16.3 L1068 78 L1073 60 L1096 60 L1108 48 L1122 60 L1200 60",
          "M0 60 L40 60 L56 54 L72 60 L104 60 L112 66 L124 14 L136 78 L146 60 L192 60 L216 48 L244 60 L400 60 L440 60 L456 54 L472 60 L504 60 L512 66 L524 18.6 L536 78 L546 60 L592 60 L616 48 L644 60 L800 60 L840 60 L856 54 L872 60 L904 60 L912 66 L924 11.7 L936 78 L946 60 L992 60 L1016 48 L1044 60 L1200 60"),
    "c": ("M0 60 L24 60 L33.6 54 L43.2 60 L62.4 60 L67.2 66 L74.4 23.2 L81.6 78 L87.6 60 L115.2 60 L129.6 48 L146.4 60 L240 60 L264 60 L273.6 54 L283.2 60 L302.4 60 L307.2 66 L314.4 16.3 L321.6 78 L327.6 60 L355.2 60 L369.6 48 L386.4 60 L480 60 L504 60 L513.6 54 L523.2 60 L542.4 60 L547.2 66 L554.4 25.5 L561.6 78 L567.6 60 L595.2 60 L609.6 48 L626.4 60 L720 60 L744 60 L753.6 54 L763.2 60 L782.4 60 L787.2 66 L794.4 18.6 L801.6 78 L807.6 60 L835.2 60 L849.6 48 L866.4 60 L960 60 L984 60 L993.6 54 L1003.2 60 L1022.4 60 L1027.2 66 L1034.4 20.9 L1041.6 78 L1047.6 60 L1075.2 60 L1089.6 48 L1106.4 60 L1200 60",
          "M0 60 L60 60 L84 54 L108 60 L156 60 L168 66 L186 20.9 L204 78 L219 60 L288 60 L324 48 L366 60 L600 60 L660 60 L684 54 L708 60 L756 60 L768 66 L786 16.3 L804 78 L819 60 L888 60 L924 48 L966 60 L1200 60"),
}
def ecg_lane(k):
    pc, sp = ECG_PATHS[k]
    svg = lambda cls: (f'<svg class="ecg__svg {cls}" viewBox="0 0 1200 100" preserveAspectRatio="none">'
                       f'<path class="--pc" d="{pc}"/><path class="--sp" d="{sp}"/></svg>')
    # 薄い残像（いつも見えている）→ 左から右へ描かれていく線 → 先頭の光
    return (f'<div class="ecg__lane --{k}">{svg("ecg__ghost")}'
            f'<div class="ecg__draw">{svg("ecg__glow")}{svg("ecg__line")}</div><i class="ecg__head"></i></div>')

# 壁の飾り：基板の配線・照準・目盛り・警告ラベル（並べ方と絵は site.css。PC の左右の余白だけ）
WALL = '''<div class="wall" aria-hidden="true">
  <i class="wall__circuit"></i><i class="wall__reticle"></i><i class="wall__ruler"></i>
  <span class="wall__warn --p">ときめき注意</span>
  <span class="wall__warn --c">心拍上昇注意</span>
</div>'''

# 背景の六角タイル：左上と右下のかたまり（並べ方は上の HEX_PC_L / _R、HEX_SP_L / _R）を SVG に描く。
#   かたまりの外は何も描かない（無地の壁がそのまま見える）。1 単位 = 1rem（大きさと置き場所は site.css の .hexwall）
#   六角は平らな辺が上下にくる向き。R＝外接円の半径。列の間隔 1.5R、行の間隔 √3·R、となりの列は半段ずれる
HEX_MARK = {   # マーク（大きさ 18 の箱に描いた自作の形）
    "heart": '<path d="M0 8C-2 6.3-9 1.8-9-3.2-9-6.2-6.8-8-4.5-8-2.6-8-1-6.9 0-5.2 1-6.9 2.6-8 4.5-8 6.8-8 9-6.2 9-3.2 9 1.8 2 6.3 0 8Z" fill="currentColor"/>',
    "cross": '<path d="M-3-9H3V-3H9V3H3V9H-3V3H-9V-3H-3Z" fill="currentColor"/>',
    "pulse": '<path d="M-9.5 1H-4.5L-2-6.5 1.5 7.5 4 1H9.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>',
    "drop": '<path d="M0-9C2.6-5 7-1.2 7 3A7 7 0 0 1-7 3C-7-1.2-2.6-5 0-9Z" fill="currentColor"/>',
}
def hexwall(kind):
    # kind は "pc" か "sp"。左上用（--l）と右下用（--r）の 2 枚の SVG を返す。
    # 形の定義（defs）は左上用の中に 1 回だけ置き、右下用からも使う（2 枚はいつも同時に表示されるので参照できる）
    pc = kind == "pc"
    p, R, period, W = ("hwp", 52, 16, 780) if pc else ("hws", 30, 20, 300)
    left, right = (HEX_PC_L, HEX_PC_R) if pc else (HEX_SP_L, HEX_SP_R)
    rx0, rpar = (W - 28, 1) if pc else (W + 15, 0)   # 右下用：いちばん外の列の中心の x と、半段下がるのが奇数の列（1）か偶数の列（0）か
    s3 = 3 ** .5
    rs = s3 * R                               # 行の間隔
    H = rs * period * 2                       # 2 周期ぶんの高さ
    n = lambda v: f"{v:.2f}".rstrip("0").rstrip(".") if abs(v) >= .005 else "0"   # 小数 2 桁まで
    def hexd(r):                              # 平らな辺が上下の六角（中心 0,0）
        h = r * s3 / 2
        return f"M{n(r)} 0L{n(r/2)} {n(h)}H{n(-r/2)}L{n(-r)} 0L{n(-r/2)} {n(-h)}H{n(r/2)}Z"
    a = R - 2.75; ah = a * s3 / 2             # 面取りの光（目地から 1.5 ほど内側）
    b = R - 2.15; bh = b * s3 / 2             # 面取りの影
    grad = lambda i, c1, c2, attr: (f'<linearGradient id="{p}-{i}" {attr}><stop offset="0" stop-color="{c1}"/>'
                                    f'<stop offset="1" stop-color="{c2}"/></linearGradient>')
    my, ms = (-R * .22, 1) if pc else (0, 13 / 18)   # マークの高さと大きさ（スマホは文字が無いので中央）
    defs = (grad("g", "#fdfeff", "#edf1f7", 'x2="1" y2="1"')
            + f'<radialGradient id="{p}-l" cx=".3" cy=".22" r=".5"><stop offset="0" stop-color="#fff" stop-opacity=".9"/>'
              f'<stop offset="1" stop-color="#fff" stop-opacity="0"/></radialGradient>'
            + grad("gp", "#ff8ad6", "#f953c2", 'x2="0" y2="1"') + grad("gc", "#5ccfff", "#00abfc", 'x2="0" y2="1"')
            + grad("gv", "#c58af2", "#a651e4", 'x2="0" y2="1"')
            + f'<linearGradient id="{p}-gs" x2="0" y2="1"><stop offset="0" stop-color="#fff" stop-opacity=".3"/>'
              f'<stop offset=".5" stop-color="#fff" stop-opacity="0"/></linearGradient>'
            + f'<path id="{p}-h" d="{hexd(R - 1)}"/><path id="{p}-i" d="{hexd(R - 7)}"/>'
            # 目地：タイルより少し大きい六角を下に敷く（となり同士のあいだと、かたまりのふちに目地の色が出る）
            + f'<path id="{p}-b" d="{hexd(R + .5)}" fill="#d5dce7"/>'
            # 白いタイル1枚：陶器の面＋ツヤ＋上と左上の光＋下と右下の影
            + f'<g id="{p}-t"><use href="#{p}-h" fill="url(#{p}-g)"/><use href="#{p}-h" fill="url(#{p}-l)"/>'
              f'<path d="M{n(-a)} 0L{n(-a/2)} {n(-ah)}H{n(a/2)}" fill="none" stroke="#fff" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
              f'<path d="M{n(-b/2)} {n(bh)}H{n(b/2)}L{n(b)} 0" fill="none" stroke="rgba(120,138,172,.16)" stroke-width="2" stroke-linejoin="round"/></g>'
            + "".join(f'<g id="{p}-{k}" transform="translate(0 {n(my)}){f" scale({n(ms)})" if ms != 1 else ""}">{d}</g>' for k, d in HEX_MARK.items()))
    def cells(tiles, fx, par):                # fx：列 → 中心の x、par：半段下がる列（1 奇数／0 偶数）
        back, face = [], []
        for i in range(2):                    # 2 周期ぶん
            for c, r, k, *rest in tiles:
                m = rest[0] if rest else ""
                t = rest[1] if len(rest) > 1 else ""
                x, y = n(fx(c)), n(rs * (r + i * period + (.5 if c % 2 == par else 0)))
                back.append(f'<use href="#{p}-b" x="{x}" y="{y}"/>')
                if k == "w":
                    face.append(f'<use href="#{p}-t" x="{x}" y="{y}"/>')
                    continue
                tile = f'<use href="#{p}-t"/>' if k == "o" else ""
                shine = f'<use href="#{p}-h" fill="url(#{p}-gs)"/>' if k in ("p", "c", "v", "k") else ""
                fill = f' fill="url(#{p}-g{k})"' if k in ("p", "c", "v") else ""   # 塗りのグラデーションは属性で指定（CSS の url() は使わない）
                txt = f'<text y="{n(R * .33)}">{esc(t)}</text>' if pc and t else ""
                face.append(f'<g class="hc --{k}" transform="translate({x} {y})">{tile}<use href="#{p}-h" class="f"{fill}/>{shine}'
                            f'<use href="#{p}-i" class="i"/><use href="#{p}-{m}"/>{txt}</g>')
        return "".join(back) + "".join(face)  # 目地を先にぜんぶ敷いてから、タイルをのせる
    box = f'viewBox="0 0 {W} {n(H)}"'
    return (f'<svg class="hexwall --{kind} --l" {box}><defs>{defs}</defs>' + cells(left, lambda c: 1.5 * R * c, 1) + "</svg>"
            + f'<svg class="hexwall --{kind} --r" {box}>' + cells(right, lambda c: rx0 - 1.5 * R * c, rpar) + "</svg>")

BG = '''<div class="tilebg" aria-hidden="true">''' + hexwall("pc") + hexwall("sp") + '''</div>
''' + WALL + '''
<div class="ecg" aria-hidden="true">''' + ecg_lane("p") + ecg_lane("c") + '''</div>
<div class="cursor" id="cursor" aria-hidden="true"><i></i></div>
<div class="grain" aria-hidden="true"></div>'''

# 画面遷移：ロード画面と同じ色の帯が斜めに覆って、次のページで抜けていく（動きは site.js / site.css）
PAGE_TRANSITION = '''<div class="pt" id="pt" aria-hidden="true">
  <div class="pt__bands"><i></i><i></i><i></i><i></i></div>
  <div class="pt__core"><img src="img/logo.webp" alt="" width="720" height="435"><p class="pt__txt mono"><i></i>NOW LOADING<b><span>.</span><span>.</span><span>.</span></b></p></div>
</div>'''
# 前のページから画面遷移で来たときは、最初の表示から帯で覆っておく（読み込み中にページが見えないように）
PT_HEAD = '<script>try{if(sessionStorage.getItem("md-pt")){sessionStorage.removeItem("md-pt");if(!matchMedia("(prefers-reduced-motion: reduce)").matches)document.documentElement.classList.add("pt-arrive")}}catch(e){}</script>'

LOADING = '''<div class="loader" id="loader" aria-hidden="true">
  <div class="loader__bg"><div class="loader__hearts" id="ld-hearts"></div></div>
  <div class="loader__ui">
    <div class="loader__hud"><i></i><i></i><i></i><i></i></div>
    <p class="loader__meta mono --tl"><b>●</b> SUCCUBUS CLINIC SYSTEM v1.0 // NURSE STATION</p>
    <p class="loader__meta mono --tr">VRChat · PCVR ONLY</p>
    <p class="loader__meta mono --bl">EVERY OTHER MONDAY · 21:50 JST</p>
    <p class="loader__meta mono --br">CLICK TO SKIP ▶</p>
    <div class="loader__core">
      <div class="loader__mark">
        <svg class="loader__ring" viewBox="0 0 200 200"><defs><path id="ld-ring" d="M100 100m-86 0a86 86 0 1 1 172 0a86 86 0 1 1-172 0"/></defs>
          <circle cx="100" cy="100" r="96" fill="none" stroke="rgba(216,21,143,.45)" stroke-width=".6" stroke-dasharray="2 4"/>
          <circle cx="100" cy="100" r="78" fill="none" stroke="rgba(0,119,182,.4)" stroke-width=".5"/>
          <text><textPath href="#ld-ring">SUCCUBUS CLINIC ✦ VR NURSE CAFÉ ✦ WELCOME PATIENT ✦ SUCCUBUS CLINIC ✦ VR NURSE CAFÉ ✦ WELCOME PATIENT ✦</textPath></text></svg>
        <div class="loader__logo"><img src="img/logo-full.webp" alt="" width="1000" height="604"><img class="--a" src="img/logo-full.webp" alt="" width="1000" height="604"><img class="--b" src="img/logo-full.webp" alt="" width="1000" height="604"></div>
      </div>
      <div class="loader__stage">
        <div class="loader__prog">
          <div class="loader__track"><i class="loader__fill" id="ld-fill"></i><img class="loader__chibi" id="ld-chibi" src="img/chibi.webp" alt="" width="900" height="932"></div>
          <p class="loader__pct"><b id="ld-pct">000</b><small>%</small></p>
        </div>
        <ol class="loader__log mono" id="ld-log">
          <li>&gt; BOOT <b>SC_SYSTEM</b> v1.0 ........... <em>OK</em></li>
          <li>&gt; READ PATIENT CARD // PCVR ... <em>OK</em></li>
          <li>&gt; MATCH KARTE: NURSES ......... <em>{{CASTN}}/{{CASTN}}</em></li>
          <li>&gt; HIDE SECRET HEARTS ............ <em>8</em></li>
          <li>&gt; WELCOME, PATIENT <b>♡</b></li>
        </ol>
      </div>
    </div>
  </div>
  <div class="loader__wipe"><i></i><i></i><i></i></div>
</div>'''

def header(cur):
    lis = "".join(f'<li><a href="{k}.html"{AC if k == cur else ""}>{en}</a></li>' for k, en, jp in NAV)
    sp = "\n".join(f'  <a class="sp-link" href="{k}.html"{AC if k == cur else ""}>{en}<small>{jp}</small></a>' for k, en, jp in NAV)
    return f'''<header class="header">
  <span class="os-dots h-dots" aria-hidden="true"><i></i><i></i><i></i></span>
  <a class="h-logo" href="index.html"><img src="img/logo.webp" alt="{EVENT_FULL} トップへ" width="720" height="435"></a>
  <nav class="gnav" aria-label="メインメニュー">
    <ul class="glass">{lis}</ul>
  </nav>
  <a class="h-join" {ext(GROUP_URL)}>JOIN GROUP<i>{ARROW}</i></a>
  <a class="h-bell glass" href="contact.html" aria-label="受付（お問い合わせ）"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M5 24h22" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/><path d="M7 21.5a9 9 0 0 1 18 0z" fill="#fa79d0" stroke="currentColor" stroke-width="2.4" stroke-linejoin="round"/><path d="M16 12.5V9.5M13 9.5h6" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/><path d="M11.2 18.6a5.4 5.4 0 0 1 3.2-3.2" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg></a>
  <a class="h-x glass" {ext(X_URL)} aria-label="{EVENT}のX（{"新しいタブで開く" if X_URL != "#" else TBD}）"><svg viewBox="0 0 512 512" aria-hidden="true"><use href="#i-x"/></svg></a>
  <button class="menu-btn" id="menu-btn" type="button" aria-label="メニューを開く" aria-expanded="false" aria-controls="sp-menu"><span></span><span></span></button>
</header>
<nav class="sp-menu" id="sp-menu" aria-label="メニュー">
  <a class="sp-link" href="index.html">TOP<small>トップ</small></a>
{sp}
  <a class="sp-link" href="contact.html"{AC if cur == "contact" else ""}>CONTACT<small>受付</small></a>
  <a class="btn" {ext(X_URL)}><span>FOLLOW ON X</span><i>{ARROW}</i></a>
</nav>'''

def win_nav():
    """トップのウィンドウのタイトルバー＝ナビゲーション（PCの広い画面）"""
    lis = "".join(f'<li><a href="{k}.html">{en}</a></li>' for k, en, jp in NAV)
    xl = "新しいタブで開く" if X_URL != "#" else TBD
    return (f'<a class="h-logo" href="index.html"><img src="img/logo.webp" alt="{EVENT_FULL} トップへ" width="720" height="435"></a>'
            f'<nav class="gnav" aria-label="メインメニュー"><ul>{lis}</ul></nav>'
            f'<a class="h-join" {ext(GROUP_URL)}>JOIN GROUP<i>{ARROW}</i></a>'
            f'<a class="h-bell glass" href="contact.html" aria-label="受付（お問い合わせ）"><svg viewBox="0 0 32 32" aria-hidden="true"><path d="M5 24h22" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"/><path d="M7 21.5a9 9 0 0 1 18 0z" fill="#fa79d0" stroke="currentColor" stroke-width="2.4" stroke-linejoin="round"/><path d="M16 12.5V9.5M13 9.5h6" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/><path d="M11.2 18.6a5.4 5.4 0 0 1 3.2-3.2" fill="none" stroke="#fff" stroke-width="2" stroke-linecap="round"/></svg></a><a class="h-x glass" {ext(X_URL)} aria-label="{EVENT}のX（{xl}）"><svg viewBox="0 0 512 512" aria-hidden="true"><use href="#i-x"/></svg></a>')

def footer():
    links = "".join(f'<a href="{k}.html">{en}</a>' for k, en, jp in NAV)
    return f'''<footer class="footer">
  <div class="inner">
    <div class="footer__top">
      <a class="f-logo" href="index.html"><img src="img/logo.webp" alt="{EVENT_FULL}" width="720" height="435"><small class="f-tag">VRC NURSE CAFÉ EVENT</small></a>
      <nav class="footer__nav" aria-label="フッターメニュー">{links}<a href="contact.html">CONTACT</a><a {ext(X_URL)}>X</a></nav>
    </div>
    <button class="footer__mark" type="button" data-omikuji aria-label="あなたの推しがきっと見つかる（処方おみくじを引く）"><span>あなたの推しが</span><span>きっと見つかる</span></button>
    <div class="footer__bottom"><span>{EVENT}はVRChat上の有志によるイベントです。VRChat Inc. とは関係ありません。</span><span>© {date.today().year} {EVENT}</span></div>
  </div>
</footer>
<a class="go-top" id="go-top" href="#top" aria-label="ページの先頭へ"><i class="go-top__ic" aria-hidden="true"></i><span>TOP</span></a>'''

def phead(en, jp, code, crumb=None, lead=""):
    crumb = crumb or f"<span>{en}</span>"
    lead = f'\n      <p class="phead__lead">{lead}</p>' if lead else ""
    return f'''<section class="phead">
    <div class="fx" data-fx="phead" aria-hidden="true"></div>
    <div class="inner">
      <nav class="crumb mono" aria-label="現在地"><a href="index.html">TOP</a><i>/</i>{crumb}</nav>
      <div class="phead__row">
        <h1 class="phead__en grad-text" style="--len:{len(en)}">{en}</h1>
        <div class="phead__side"><p class="phead__jp">{jp}</p><p class="phead__code mono">{code}</p></div>
        <i class="phead__line" aria-hidden="true"></i>
      </div>{lead}
    </div>
  </section>'''

def back(extra=""):
    return f'<div class="back">{extra}<a class="btn" href="index.html"><span>BACK TO TOP</span><i>{ARROW}</i></a></div>'

DESC = f"{EVENT_FULL}は、サキュバスたちがナースとして働くコンカフェ「{EVENT}」をテーマにした、VRChatで隔週月曜日の夜（21:50〜23:10）にひらく全年齢向けイベントです。"
PAGES = {
    # ファイル名: (メニューで光らせる項目, <title>, 説明文, ページ見出し)
    "index": ("", f"{EVENT_FULL}｜VRChat ナースコンカフェイベント", DESC, None),
    "news": ("news", f"NEWS｜{EVENT}", f"{EVENT}のお知らせ一覧", ("NEWS", "お知らせ", "// LATEST_INFO")),
    "news-detail": ("news", f"NEWS｜{EVENT}", f"{EVENT}のお知らせ", ("NEWS", "お知らせ", "// ARTICLE", '<a href="news.html">NEWS</a><i>/</i><span id="crumb-title">お知らせ</span>')),
    "about": ("about", f"ABOUT｜{EVENT}", f"{EVENT}の病院案内。" + DESC, ("ABOUT", "病院案内", "// CLINIC_GUIDE")),
    "nurses": ("nurses", f"NURSES｜{EVENT}", f"{EVENT}のナース紹介。在籍ナースのカルテ（プロフィール）を見られます。", ("NURSES", "ナース紹介", "// NURSE_KARTE")),
    "schedule": ("schedule", f"SCHEDULE｜{EVENT}", f"{EVENT}の診療日と診療時間（隔週月曜日 21:50〜23:10・日本時間）", ("SCHEDULE", "診療時間", "// CLINIC_HOURS")),
    "menu": ("menu", f"MENU｜{EVENT}", f"{EVENT}の処方メニュー", ("MENU", "処方メニュー", "// PRESCRIPTION")),
    "media": ("media", f"MEDIA｜{EVENT}", f"{EVENT}のメディア（写真・動画）", ("MEDIA", "メディア", "// MEDIA_ARCHIVE")),
    "guidelines": ("guidelines", f"GUIDELINES｜{EVENT}", f"{EVENT}の入院のしおり（ご来院のルール）", ("GUIDELINES", "入院のしおり", "// WARD_GUIDE")),
    "faq": ("faq", f"FAQ｜{EVENT}", f"{EVENT}の問診票（よくある質問）", ("FAQ", "問診票", "// MEDICAL_INTERVIEW")),
    "contact": ("contact", f"CONTACT｜{EVENT}", f"{EVENT}の受付（グループ・お問い合わせ）", ("CONTACT", "受付", "// RECEPTION")),
}

def head_meta(name, title, desc):
    url = f"{SITE_URL}/{'' if name == 'index' else name + '.html'}" if SITE_URL else ""
    ogimg = f"{SITE_URL}/img/ogp.jpg" if SITE_URL else "img/ogp.jpg"
    return "\n".join(filter(None, [
        f'<meta name="description" content="{esc(desc)}">',
        '<meta name="robots" content="noindex, nofollow">' if NOINDEX else "",
        f'<link rel="canonical" href="{url}">' if url else "",
        f'<meta property="og:site_name" content="{esc(EVENT_FULL)}">',
        f'<meta property="og:type" content="{"website" if name == "index" else "article"}">',
        f'<meta property="og:title" content="{esc(title)}">',
        f'<meta property="og:description" content="{esc(desc)}">',
        f'<meta property="og:url" content="{url}">' if url else "",
        f'<meta property="og:image" content="{ogimg}">',
        '<meta property="og:image:width" content="1200"><meta property="og:image:height" content="630">',
        '<meta name="twitter:card" content="summary_large_image">' + (f'<meta name="twitter:site" content="@{esc(X_ID)}">' if X_ID else ""),
        '<meta name="theme-color" content="#f4f6fa">',
        '<link rel="icon" href="favicon.png" type="image/png"><link rel="apple-touch-icon" href="apple-touch-icon.png">',
    ]))

# ---------------------------------------------------------------- 一覧の HTML
def cast_list(CAST):
    out = []
    for k, c in enumerate(CAST, 1):
        n = esc(c["name"]); p = c.get("p")
        # data-gen：期生（1〜）、カルテ準備中は "0"、カルテありで期生なしは ""（どの期生タブにも入らない）
        gen = (str(p["gen"]) if p["gen"] > 0 else "") if p else "0"
        chip = (f'<span class="ccard__gen g{gen}">{gen}期生</span>' if gen else '') if p else '<span class="ccard__gen g0">準備中</span>'
        catch = f'<span class="ccard__catch">{esc(p["catch"])}</span>' if p and p["catch"] else ''
        out.append(f'        <li class="ccard rv" data-id="{c["id"]}" data-name="{n}" data-gen="{gen}" data-no="{k:02d}" style="--c:{c["c"]};--c2:{c["c2"]}"><button class="ccard__btn" type="button" aria-label="{n}のカルテを見る">'
                   f'<span class="ccard__ph"><img src="img/cast/s/{c["id"]}.webp" alt="{n}" width="400" height="601" loading="lazy" decoding="async">{chip}</span>'
                   f'<span class="ccard__no mono">No.{k:02d}</span><span class="ccard__name">{n}</span>{catch}</button></li>')
    return "\n".join(out)

def cast_data(CAST):
    d = {c["id"]: c["p"] for c in CAST if c.get("p")}
    return '<script type="application/json" id="cast-data">' + json.dumps(d, ensure_ascii=False).replace("</", "<\\/") + '</script>'

def cast_tabs(CAST):
    """絞り込みタブ：すべて＋期生（1〜）＋カルテ準備中。「すべて」しか無いときはタブの列ごと出さない"""
    gens = sorted({c["p"]["gen"] for c in CAST if c.get("p") and c["p"]["gen"] > 0})
    cnt = lambda g: sum(1 for c in CAST if c.get("p") and c["p"]["gen"] == g)
    none = sum(1 for c in CAST if not c.get("p"))
    b = [f'<button type="button" role="tab" data-gen="{g}" aria-selected="false">{g}期生<small>{cnt(g)}</small></button>' for g in gens]
    if none: b.append(f'<button type="button" role="tab" data-gen="0" aria-selected="false">カルテ準備中<small>{none}</small></button>')
    if not b: return ""
    b.insert(0, f'<button type="button" role="tab" data-gen="all" aria-selected="true">すべて<small>{len(CAST)}</small></button>')
    return '<div class="tabs ctabs rv" id="cast-tabs" role="tablist" aria-label="期生で絞り込む">' + "".join(b) + "</div>"

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
        meta = f'<span class="mv__who" style="--c:{ccol.get(who, "#f472a8")}">{esc(who)}</span>' if who else ""
        out.append(f'        <li class="mv rv" data-cat="{m["tag"]}"><a class="mv__link{" --short" if m["tag"] == "short" else ""}" href="{esc(m["url"])}" target="_blank" rel="noopener" aria-label="{t}（YouTubeで見る・新しいタブ）">'
                   f'<span class="mv__thumb"><img src="{m["thumb"]}" alt="" width="800" height="450" loading="lazy" decoding="async"><span class="mv__play" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M8 5.5v13l11-6.5z" fill="currentColor"/></svg></span><span class="mv__tag --{m["tag"]}">{tagname[m["tag"]]}</span></span>'
                   f'<span class="mv__title">{t}</span><span class="mv__meta">{meta}<span class="mv__yt mono">YOUTUBE ↗</span></span></a></li>')
    return "\n".join(out) or '        <li class="empty">動画はまだありません。</li>'

def hero_slides(PHOTOS):
    hs = [p for p in PHOTOS if p["hero"]]
    out = []
    for k, p in enumerate(hs):
        w, h = p["hero"]
        if k == 0: out.append(f'          <img class="is-on" src="img/photo/h/{p["id"]}.webp" alt="{esc(p["alt"])}" width="{w}" height="{h}" fetchpriority="high" decoding="async">')
        else: out.append(f'          <img data-src="img/photo/h/{p["id"]}.webp" alt="{esc(p["alt"])}" width="{w}" height="{h}" decoding="async" aria-hidden="true">')
    return "\n".join(out) or '          <img class="is-on" src="img/pickup.webp" alt="{EVENT}のナースたち" width="2560" height="1280">'

def gallery(PHOTOS, kind):
    gs = [p for p in PHOTOS if p["gallery"]]; out = []
    for k, p in enumerate(gs, 1):
        img = f'<img src="img/photo/s/{p["id"]}.webp" alt="{esc(p["alt"])}" width="800" height="400" loading="lazy" decoding="async">'
        if kind == "nurses":
            out.append(f'        <li class="glass rv"><button class="gal-btn" type="button" data-full="img/photo/{p["id"]}.webp" aria-label="写真{k}を大きく見る">{img}</button><span class="mono">PHOTO {k:02d}</span></li>')
        else:
            out.append(f'        <li class="mitem rv"><button class="gal-btn" type="button" data-full="img/photo/{p["id"]}.webp" aria-label="PHOTO {k:02d}を大きく見る">{img}</button><span class="mitem__lab mono">PHOTO {k:02d}</span></li>')
    return "\n".join(out), len(gs)

# ---------------------------------------------------------------- ページの書き出し
def build_page(name, D):
    cur, title, desc, ph = PAGES[name]
    body = open(os.path.join(SRC, name + ".html"), encoding="utf-8").read().strip()
    gal, photon = gallery(D["photos"], "nurses" if name == "nurses" else "media")
    rep = {"{{ARROW}}": ARROW, "{{BACK}}": back(), "{{CASTN}}": str(len(D["cast"])), "{{PHOTON}}": str(photon),
           "{{MOVIEN}}": str(len(D["movies"])), "{{WINNAV}}": win_nav(), "{{HERO_SLIDES}}": hero_slides(D["photos"]), "{{GALLERY}}": gal,
           "{{GROUP_LINK}}": ext(GROUP_URL), "{{X_LINK}}": ext(X_URL), "{{TAG_LINK}}": ext(TAG_URL), "{{X_ID}}": esc(X_LABEL), "{{HASHTAG}}": esc(TAG_LABEL),
           "{{WORLD}}": esc(WORLD or TBD), "{{EVENT}}": EVENT, "{{EVENT_FULL}}": EVENT_FULL}
    if "{{MOVIES}}" in body: rep.update({"{{MOVIES}}": movie_list(D["movies"], D["cast"]), "{{MOVIETABS}}": movie_tabs(D["movies"])})
    if "{{CAST}}" in body: rep.update({"{{CAST}}": cast_list(D["cast"]), "{{CASTTABS}}": cast_tabs(D["cast"]), "{{CASTDATA}}": cast_data(D["cast"])})
    if ph: rep["{{PHEAD}}"] = phead(*ph)
    for k, v in rep.items(): body = body.replace(k, v)
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
    if SITE_URL and not NOINDEX:
        urls = "".join(f"<url><loc>{SITE_URL}/{'' if n == 'index' else n + '.html'}</loc></url>" for n in PAGES if n != "news-detail")
        open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8").write(f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">{urls}</urlset>\n')
        open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8").write(f"User-agent: *\nDisallow: /admin/\nSitemap: {SITE_URL}/sitemap.xml\n")
    elif NOINDEX:
        # 検索よけの間はサイトマップを出さない。巡回そのものは止めない（止めると、各ページの「載せないで」の指定を読んでもらえないため）
        open(os.path.join(OUT, "robots.txt"), "w", encoding="utf-8").write("User-agent: *\nDisallow: /admin/\n")
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
