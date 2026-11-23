/* SuccubusClinic 共通スクリプト（全ページ共通。要素があるページでだけ動く） */
document.documentElement.classList.add("js");
(function () {
  var $ = function (id) { return document.getElementById(id); };
  var reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
  var fine = matchMedia("(pointer: fine)").matches;
  var pad = function (n) { return String(n).padStart(2, "0"); };
  var root = document.documentElement, readyFns = [];
  var onReady = function (fn) { if (root.classList.contains("is-ready")) fn(); else readyFns.push(fn); };
  var setReady = function () { if (root.classList.contains("is-ready")) return; root.classList.add("is-ready"); readyFns.splice(0).forEach(function (f) { f(); }); };
  var esc = function (t) { return String(t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };
  var ARROW = '<svg viewBox="0 0 16 12" aria-hidden="true"><use href="#i-arrow"/></svg>';

  /* お知らせのデータ（新しい順）。管理画面（/admin）の「お知らせ」で追加・編集すると、
     build.py が assets/news.js を作り直し、トップ・NEWS一覧・記事ページのすべてに反映されます。 */
  var CAT = { event: ["イベント", "EVENT"], maid: ["ナース", "NURSE"], menu: ["メニュー", "MENU"], info: ["お知らせ", "INFO"] };
  var NEWS = (window.MD_NEWS || []).filter(function (n) { return CAT[n.cat]; });
  var link = function (n) { return "news-detail.html#" + n.id; };
  function thumb(n) {
    var t = n.th;
    if (t.img) return '<div class="th th-img"><img src="' + t.img + '" alt="" loading="lazy" style="object-position:' + (t.pos || "50% 20%") + '"></div>';
    if (t.logo) return '<div class="th th-logo"><img src="img/logo.webp" alt="" loading="lazy"></div>';
    return '<div class="th ' + t.cls + '"><span>' + t.t + (t.s ? "<small>" + t.s + "</small>" : "") + "</span></div>";
  }

  /* ---------- お知らせの1行（トップとNEWS一覧で共通）----------
     番号（CSS）・チェック欄・件名・種類（選んだものだけ表示。ほかの選択肢は隠して読み上げない）・日付 */
  function qrow(n) {
    var opts = Object.keys(CAT).map(function (k) {
      var on = k === n.cat;
      return '<span class="qopt' + (on ? " is-on" : "") + '"' + (on ? "" : ' aria-hidden="true"') + ">" + CAT[k][0] + "</span>";
    }).join("");
    return '<a class="qrow --' + n.cat + '" href="' + link(n) + '"><span class="qrow__box" aria-hidden="true"></span><span class="qrow__title">' + esc(n.title) +
      '</span><span class="qrow__cat">' + opts + '</span><span class="qrow__date">' + n.date + "</span></a>";
  }
  /* 問診票のタイトルバー（トップ用。お知らせページは news.html に同じ形を直接書いている）と、下のステータスの帯（飾りなので読み上げない） */
  function mqHead(count) {
    return '<div class="mq-head"><p class="mq-title" aria-hidden="true"><b>問診票</b><span>MEDICAL INTERVIEW SHEET</span></p>' +
      '<div class="mq-fields"><span class="mq-field --no" aria-hidden="true"><i>受付番号</i><b>SC-NEWS</b></span><span class="mq-field"><i aria-hidden="true">件数</i><b>' + count + " 件</b></span></div></div>";
  }
  var MQ_FOOT = '<div class="mq-foot" aria-hidden="true"><span class="mq-foot__l"></span><i class="mq-foot__cur"></i><span class="mq-foot__r"></span></div>';

  /* ---------- トップ：お知らせ（電子問診票：タイトルバー・添付のプレビュー・一覧・ステータスの帯） ---------- */
  var bento = $("news-bento");
  if (bento) {
    var TOPN = 5, tops = NEWS.slice(0, TOPN), f = tops[0];
    bento.innerHTML = '<div class="qboard --top rv"><div class="qsheet">' + mqHead(tops.length) +
      (f ? '<a class="qphoto" href="' + link(f) + '" tabindex="-1" aria-hidden="true"><span class="qphoto__img">' + thumb(f) + "</span></a>" : "") +
      '<div class="qform">' + tops.map(qrow).join("") + "</div>" + MQ_FOOT + "</div></div>";
    // 6件目以降は「VIEW ALL」から（用紙の行にまとめたので、下の文字だけの一覧は使わない）
    if ($("news-list")) $("news-list").hidden = true;
  }

  /* ---------- NEWS一覧：カテゴリとページ送り ---------- */
  var nlist = $("nlist");
  if (nlist) {
    var PER = 6, cur = "all", page = 1, tabs = $("news-tabs"), pager = $("pager");
    var cats = [["all", "すべて"]].concat(Object.keys(CAT).map(function (k) { return [k, CAT[k][0]]; }));
    tabs.innerHTML = cats.map(function (c) {
      var count = c[0] === "all" ? NEWS.length : NEWS.filter(function (n) { return n.cat === c[0]; }).length;
      return '<button type="button" role="tab" data-cat="' + c[0] + '" aria-selected="' + (c[0] === cur) + '">' + c[1] + "<small>" + count + "</small></button>";
    }).join("");
    tabs.addEventListener("click", function (e) { var b = e.target.closest("button"); if (!b) return; cur = b.dataset.cat; page = 1; drawNews(true); });
    pager.addEventListener("click", function (e) { var b = e.target.closest("button"); if (!b || b.disabled) return; page = Number(b.dataset.p); drawNews(true); });
    function drawNews(scroll) {
      var list = NEWS.filter(function (n) { return cur === "all" || n.cat === cur; }), pages = Math.max(1, Math.ceil(list.length / PER));
      page = Math.min(page, pages);
      [].forEach.call(tabs.children, function (b) { b.setAttribute("aria-selected", b.dataset.cat === cur); });
      /* 1ページ分（PER 行）の行を描く。空の行は足さない（番号は CSS のカウンター） */
      var shown = list.slice((page - 1) * PER, page * PER);
      nlist.innerHTML = shown.map(qrow).join("") || '<p class="empty">このカテゴリのお知らせはまだありません。</p>';
      var cnt = $("nwin-count"); if (cnt) cnt.textContent = list.length + " 件";
      var h = '<button type="button" class="--prev" aria-label="前のページ" data-p="' + (page - 1) + '"' + (page === 1 ? " disabled" : "") + ">" + ARROW + "</button>";
      for (var p = 1; p <= pages; p++) h += '<button type="button" data-p="' + p + '"' + (p === page ? ' aria-current="page"' : "") + ">" + p + "</button>";
      h += '<button type="button" class="--next" aria-label="次のページ" data-p="' + (page + 1) + '"' + (page === pages ? " disabled" : "") + ">" + ARROW + "</button>";
      pager.innerHTML = h;
      if (scroll) { var y = tabs.getBoundingClientRect().top + scrollY - 130; if (scrollY > y) scrollTo({ top: y, behavior: reduce ? "auto" : "smooth" }); }
    }
    drawNews(false);
  }

  /* ---------- 記事ページ ---------- */
  var art = $("article");
  if (art) {
    var drawArticle = function () {
      var id = location.hash.slice(1), i = 0;
      NEWS.forEach(function (n, k) { if (n.id === id) i = k; });
      var n = NEWS[i], newer = NEWS[i - 1], older = NEWS[i + 1];
      if (!n) { art.innerHTML = '<p class="empty">お知らせはまだありません。</p>'; return; }
      art.innerHTML = '<div class="card__thumb">' + thumb(n) + '</div><div class="article__meta nfile --' + n.cat + '"><span class="nfile__type"><i></i>' + CAT[n.cat][0] + '</span><span class="nfile__date">' + n.date +
        '</span></div><h2 class="article__title">' + esc(n.title) + '</h2><div class="article__body">' + n.body + "</div>";
      $("article-nav").innerHTML =
        (newer ? '<a class="pn --prev" href="' + link(newer) + '"><small>‹ NEWER</small><span>' + esc(newer.title) + "</span></a>" : '<span class="ph"></span>') +
        '<a class="btn" href="news.html"><span>BACK TO LIST</span><i>' + ARROW + "</i></a>" +
        (older ? '<a class="pn --next" href="' + link(older) + '"><small>OLDER ›</small><span>' + esc(older.title) + "</span></a>" : '<span class="ph"></span>');
      var cr = $("crumb-title"); if (cr) cr.textContent = n.title.length > 22 ? n.title.slice(0, 22) + "…" : n.title;
      document.title = n.title + "｜SuccubusClinic";
    };
    drawArticle();
    addEventListener("hashchange", function () { drawArticle(); scrollTo({ top: 0, behavior: reduce ? "auto" : "smooth" }); });
  }

  /* ---------- 文字のデコード演出 ---------- */
  var GLYPH = "ABCDEFGHKLNOPRSTUVXYZ0123456789#*+";
  var scrBusy = 0, fitPending = false;
  function scramble(root, dur) {
    if (reduce || !root) return;
    dur = dur || 700;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT), nodes = [], n;
    while ((n = walker.nextNode())) if (n.nodeValue.trim()) nodes.push({ n: n, t: n.__orig || (n.__orig = n.nodeValue) });
    var start = performance.now(); scrBusy++;
    (function frame(now) {
      var p = Math.min(1, (now - start) / dur);
      nodes.forEach(function (o) { var t = o.t, keep = Math.floor(t.length * p), out = t.slice(0, keep); for (var k = keep; k < t.length; k++) out += t[k] === " " ? " " : GLYPH[(Math.random() * GLYPH.length) | 0]; o.n.nodeValue = out; });
      if (p < 1) requestAnimationFrame(frame); else { nodes.forEach(function (o) { o.n.nodeValue = o.t; }); scrBusy--; if (!scrBusy && fitPending) { fitPending = false; fitTitle(); } }
    })(start);
  }

  /* ---------- トップの大きな文字を幅いっぱいに ---------- */
  /* トップの大きな文字：病院の端末のように1文字ずつタイプされる（最後にカーソル） */
  function typeTitle() {
    var longest = 0;
    document.querySelectorAll("#hero-title .lines").forEach(function (lines) {
      var t = 0;
      lines.querySelectorAll(":scope > .fit").forEach(function (f) {
        if (reduce) { f.classList.add("is-typed"); return; }
        var n = Math.max(4, f.textContent.length), d = n * 62;
        f.style.setProperty("--n", n); f.style.setProperty("--td", d + "ms"); f.style.animationDelay = t + "ms";
        f.classList.remove("is-typing", "is-erasing"); void f.offsetWidth; f.classList.add("is-typing"); t += d + 90;
      });
      longest = Math.max(longest, t);
    });
    return longest;
  }
  /* はじめに「Hello, World!」とタイプ → 少し止まって消す → 「WELCOME TO SUCCUBUS CLINIC」をタイプ */
  var HELLO = { pc: '<span class="fit --hello">Hello, <span class="g">World!</span><i class="hero__cur"></i></span>',
                sp: '<span class="fit --hello">Hello,</span><span class="fit --hello"><span class="g">World!</span><i class="hero__cur"></i></span>' };
  function introTitle() {
    var t = $("hero-title");
    if (!t || reduce || root.classList.contains("is-open-now")) { typeTitle(); return; }
    var groups = [].slice.call(t.querySelectorAll(".lines")), saved = groups.map(function (g) { return g.innerHTML; });
    fitTitle();
    var sizes = groups.map(function (g) { return [].map.call(g.querySelectorAll(":scope > .fit"), function (f) { return f.style.fontSize; }); });
    scrBusy++;   // タイプ中は文字の大きさを測り直さない
    groups.forEach(function (g, i) {
      g.innerHTML = g.classList.contains("lines--sp") ? HELLO.sp : HELLO.pc;
      [].forEach.call(g.querySelectorAll(":scope > .fit"), function (f, k) { f.style.fontSize = sizes[i][Math.min(k, sizes[i].length - 1)]; });
    });
    var tHello = typeTitle();
    setTimeout(function () {
      var tErase = 0;
      groups.forEach(function (g) {
        var t2 = 0;
        [].slice.call(g.querySelectorAll(":scope > .fit")).reverse().forEach(function (f) {
          var n = Math.max(4, f.textContent.length), d = n * 30;
          f.style.setProperty("--n", n); f.style.setProperty("--ed", d + "ms"); f.style.animationDelay = t2 + "ms";
          f.classList.remove("is-typing", "is-typed"); void f.offsetWidth; f.classList.add("is-erasing"); t2 += d + 40;
        });
        tErase = Math.max(tErase, t2);
      });
      setTimeout(function () {
        groups.forEach(function (g, i) { g.innerHTML = saved[i]; });
        scrBusy--; fitPending = false; fitTitle(); typeTitle();
      }, tErase + 140);
    }, tHello + 950);
  }
  function fitTitle() {
    if (scrBusy > 0) { fitPending = true; return; }
    document.querySelectorAll("#hero-title .lines").forEach(function (lines) {
      if (getComputedStyle(lines).display === "none") return;
      var W = lines.clientWidth, H = lines.clientHeight; if (!W) return;
      var fits = lines.querySelectorAll(":scope > .fit"), sizes = [];
      fits.forEach(function (f) { f.style.fontSize = "100px"; sizes.push(100 * W / (f.offsetWidth || 1)); });
      fits.forEach(function (f, k) { f.style.fontSize = sizes[k] + "px"; });
      var total = 0; fits.forEach(function (f) { total += f.offsetHeight; });
      if (total > H) { var r = H / total; fits.forEach(function (f, k) { f.style.fontSize = (sizes[k] * r) + "px"; }); }
    });
  }

  /* ---------- 背景の演出 ----------
     計器に見えるHUD（ロックオン枠・回るリング・システム表示）とピクセルハートはやめた。
     いまは壁に後付けされたケーブル・警告ラベル・ステッカー（build.py の WALL と site.css）だけで、ここでは何も作らない */

  /* ---------- ネオンの見出し・ロゴのグリッチ：同時に起きないよう、1つずつ時間をずらす（周期は site.css の 10 秒） ---------- */
  var glits = document.querySelectorAll(".sec-head__en, .phead__en, .sub-h b, .faq__label b, .h-logo img, .f-logo img");
  [].forEach.call(glits, function (el, i) { el.style.setProperty("--gdl", (-(i * 10 / glits.length)).toFixed(2) + "s"); });

  /* ---------- トップ：ウィンドウのタイトルバー（ナビ）が画面から出たら、上にヘッダーを出す ---------- */
  var winBar = document.querySelector(".board__bar");
  if (winBar && document.body.classList.contains("is-home") && "IntersectionObserver" in window) {
    new IntersectionObserver(function (es) { document.body.classList.toggle("is-hdr", !es[0].isIntersecting); }, { rootMargin: "-8px 0px 0px 0px" }).observe(winBar);
  }

  /* ---------- トップ：写真の切り替え（文字は固定、写真はハートが広がって切り替わる） ---------- */
  var slideBox = $("hero-slides");
  if (slideBox) {
    var slides = slideBox.querySelectorAll("img"), si = 0, sTimer, SINT = 5200, dotBox = $("hero-dots");
    var ensure = function (k) { var im = slides[(k + slides.length) % slides.length]; if (im.dataset.src && !im.getAttribute("src")) im.src = im.dataset.src; return im; };
    var total = $("hero-total"); if (total) total.textContent = pad(slides.length);
    addEventListener("load", function () { setTimeout(function () { ensure(1); }, 600); });
    $("hero-bar").style.setProperty("--int", SINT + "ms");
    slides.forEach(function (im, k) {
      var b = document.createElement("button"); b.type = "button"; b.setAttribute("aria-label", "写真 " + (k + 1)); b.setAttribute("aria-current", k === 0 ? "true" : "false");
      b.addEventListener("click", function () { showSlide(k); }); dotBox.appendChild(b);
    });
    var wantSlide = -1;
    var showSlide = function (k) {
      k = (k + slides.length) % slides.length; if (k === si) return;
      var im = ensure(k); ensure(k + 1); wantSlide = k;
      if (!im.complete && im.decode) { im.decode().catch(function () {}).then(function () { if (wantSlide === k) swapSlide(k); }); return; }
      swapSlide(k);
    };
    var swapSlide = function (k) {
      if (k === si) return;
      var prev = slides[si], next = slides[k];
      prev.classList.remove("is-on", "is-in"); prev.setAttribute("aria-hidden", "true");
      next.classList.remove("is-in"); void next.offsetWidth; next.classList.add("is-on"); next.removeAttribute("aria-hidden");
      if (!reduce) {
        next.classList.add("is-in");
      }
      si = k; $("hero-no").textContent = pad(k + 1);
      [].forEach.call(dotBox.children, function (b, n) { b.setAttribute("aria-current", n === k ? "true" : "false"); });
      restartSlides();
    };
    var restartSlides = function () {
      clearInterval(sTimer);
      var bar = $("hero-bar"), nb = bar.cloneNode(true); bar.parentNode.replaceChild(nb, bar);
      if (!reduce) sTimer = setInterval(function () { showSlide(si + 1); }, SINT);
    };
    $("hero-prev").addEventListener("click", function () { showSlide(si - 1); });
    $("hero-next").addEventListener("click", function () { showSlide(si + 1); });
    onReady(restartSlides);
  }

  /* ---------- トップ：奥行き（マウス） ---------- */
  var hero = $("hero"), fig = $("hero-fig");
  if (hero && fig && !reduce && fine) {
    fig.style.transition = "transform .8s cubic-bezier(.22,1,.36,1)";
    hero.addEventListener("pointermove", function (e) {
      var r = hero.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - .5, y = (e.clientY - r.top) / r.height - .5;
      fig.style.transform = "translate(" + (x * 22) + "px," + (y * 10) + "px)";
      $("hero-title").style.translate = (-x * 12) + "px " + (-y * 8) + "px";
    });
    hero.addEventListener("pointerleave", function () { fig.style.transform = ""; $("hero-title").style.translate = ""; });
  }

  /* ---------- カーソルの光 ---------- */
  var curEl = $("cursor");
  if (curEl && !reduce && fine) {
    var cx = -100, cy = -100, tx = -100, ty = -100;
    addEventListener("pointermove", function (e) { tx = e.clientX; ty = e.clientY; curEl.classList.add("is-on"); curEl.classList.toggle("is-hover", !!e.target.closest("a, button, summary")); }, { passive: true });
    document.addEventListener("pointerleave", function () { curEl.classList.remove("is-on"); });
    (function loop() { cx += (tx - cx) * .2; cy += (ty - cy) * .2; curEl.style.transform = "translate(" + cx + "px," + cy + "px)"; requestAnimationFrame(loop); })();
  }

  /* ---------- 診療日：隔週月曜日 21:50–23:10 JST（2026-12-07 から14日ごと）＋ 管理画面の「スケジュール」（特別診療・休診） ----------
     MD_SCHEDULE（assets/schedule.js）: { "2026-12-24": { k: "sp"=特別診療 / "off"=休診, t: カレンダーの文字, d: 説明, s/e: 開始・終了（0時からの分） } }
     日付（y, m, d）はすべて日本時間の暦日。Date.UTC で「その日の0時」を作って日数を数えるので、見ている端末のタイムゾーンに左右されない */
  var SPECIAL = window.MD_SCHEDULE || {};
  var JST = 9 * 3600e3, WD = ["SUN","MON","TUE","WED","THU","FRI","SAT"], REG = { s: 21 * 60 + 50, e: 23 * 60 + 10 };
  var REG_START = Date.UTC(2026, 11, 7), REG_EVERY = 14;   // 起点：2026-12-07（月）／14日ごと
  var dkey = function (y, m, d) { return y + "-" + pad(m + 1) + "-" + pad(d); };
  function isRegular(y, m, d) { var n = Math.round((Date.UTC(y, m, d) - REG_START) / 864e5); return n >= 0 && n % REG_EVERY === 0; }
  function isOpen(y, m, d) { var sp = SPECIAL[dkey(y, m, d)]; return sp ? sp.k !== "off" : isRegular(y, m, d); }
  function hours(y, m, d) { var sp = SPECIAL[dkey(y, m, d)]; return sp && sp.k !== "off" && sp.s != null ? { s: sp.s, e: sp.e } : REG; }
  var hm = function (min) { min = ((min % 1440) + 1440) % 1440; return pad(Math.floor(min / 60)) + ":" + pad(min % 60); };
  var hoursAt = function (t) { var j = new Date(t + JST); return hours(j.getUTCFullYear(), j.getUTCMonth(), j.getUTCDate()); };
  var timeLabel = function (t, sep) { var h = hoursAt(t); return hm(h.s) + (sep || "–") + hm(h.e); };
  function openList(now, count) {
    var j = new Date(now + JST), out = [];
    for (var k = -1; k < 800 && out.length < count; k++) {
      var dt = new Date(Date.UTC(j.getUTCFullYear(), j.getUTCMonth(), j.getUTCDate() + k)), y = dt.getUTCFullYear(), m = dt.getUTCMonth(), d = dt.getUTCDate();
      if (!isOpen(y, m, d)) continue;
      var h = hours(y, m, d), t = Date.UTC(y, m, d, 0, h.s) - JST;
      if (Date.UTC(y, m, d, 0, h.e) - JST > now) out.push(t);
    }
    return out;
  }
  function md(t) { var j = new Date(t + JST); return pad(j.getUTCMonth() + 1) + "." + pad(j.getUTCDate()); }

  /* ---------- トップ：「診療中」のネオン看板 ----------
     日付の判定は上の openList（隔週月曜＋特別診療・休診）をそのまま使う。
     a. 開催時間内 →「診療中」点灯 ／ b. 開催日でまだ始まっていない →「本日診療」点灯＋開始時刻 ／ c. それ以外 →「休診」消灯＋次回の日時
     スクリプトが動かないときは、HTML に書いてある c の見た目（次回の表示なし）のまま */
  var sign = $("csign");
  if (sign) {
    var JWD = ["日", "月", "火", "水", "木", "金", "土"];
    var jday = function (t) { return new Date(t + JST).toISOString().slice(0, 10); };
    var drawSign = function () {
      var n = Date.now(), t = openList(n, 1)[0], st = "off", main = "休診", sub = [];
      if (t != null && t <= n) { st = "open"; main = "診療中"; }
      else if (t != null && jday(t) === jday(n)) { st = "today"; main = "本日診療"; sub = [hm(hoursAt(t).s) + "〜"]; }
      else if (t != null) { var j = new Date(t + JST); sub = ["次回 " + (j.getUTCMonth() + 1) + "/" + j.getUTCDate() + "（" + JWD[j.getUTCDay()] + "）", hm(hoursAt(t).s) + "〜"]; }
      var key = st + "|" + main + "|" + sub.join("|");
      if (sign.__key === key) return; sign.__key = key;
      sign.dataset.state = st;
      $("csign-main").textContent = main;
      var sb = $("csign-sub"); sb.innerHTML = sub.map(function (x) { return "<span>" + x + "</span>"; }).join(""); sb.hidden = !sub.length;
    };
    drawSign();
    setInterval(drawSign, 20000);
    // 点灯している看板は、読み込みのあとに1回だけ「パチパチッ」と点く（動きを減らす設定のときはしない）
    if (!reduce) onReady(function () { setTimeout(function () { sign.classList.add("is-boot"); }, 400); });
  }
  function setNum(id, v) { var el = $(id); if (el.textContent !== v) { el.textContent = v; if (!reduce && id !== "cd-s") { el.classList.remove("flash"); void el.offsetWidth; el.classList.add("flash"); } } }
  var lastMd = "";
  function tick() {
    var now = Date.now(), jn = new Date(now + JST);
    if ($("jst-clock")) $("jst-clock").textContent = pad(jn.getUTCHours()) + ":" + pad(jn.getUTCMinutes()) + ":" + pad(jn.getUTCSeconds());
    if (!$("t-date")) return;
    var list = openList(now, 4), t = list[0], j = new Date(t + JST), diff = Math.max(0, t - now), s = Math.floor(diff / 1000), m = md(t);
    if (m !== lastMd) {
      lastMd = m; $("t-date").innerHTML = m + "<small>" + WD[j.getUTCDay()] + "</small>";
      var tt0 = document.querySelector(".ticket__time"); if (tt0) tt0.textContent = timeLabel(t, " — ") + " JST";
      var st0 = $("t-note") && $("t-note").querySelector("strong"); if (st0 && diff > 0) st0.textContent = hm(hoursAt(t).s);
      var ul = $("upcoming");
      if (ul) { ul.innerHTML = ""; list.forEach(function (tt, k) { var li = document.createElement("li"); li.innerHTML = md(tt) + "<small>" + (k === 0 ? "NEXT" : WD[new Date(tt + JST).getUTCDay()]) + "</small>"; ul.appendChild(li); }); }
    }
    setNum("cd-d", String(Math.floor(s / 86400))); setNum("cd-h", pad(Math.floor(s % 86400 / 3600))); setNum("cd-m", pad(Math.floor(s % 3600 / 60))); setNum("cd-s", pad(s % 60));
    if (diff === 0 && $("t-note")) $("t-note").innerHTML = "<strong>ただいま診療中です。</strong> 会場へお越しください、患者さま♡";
  }
  if ($("jst-clock") || $("t-date")) { tick(); setInterval(tick, 1000); }

  /* ---------- SCHEDULE：カレンダー ---------- */
  var calBox = $("cal");
  if (calBox) {
    var nowJ = new Date(Date.now() + JST), todayKey = nowJ.getUTCFullYear() + "-" + pad(nowJ.getUTCMonth() + 1) + "-" + pad(nowJ.getUTCDate());
    var html = "";
    for (var mo = 0; mo < 2; mo++) {
      var first = new Date(Date.UTC(nowJ.getUTCFullYear(), nowJ.getUTCMonth() + mo, 1)), Y = first.getUTCFullYear(), M = first.getUTCMonth(), days = new Date(Date.UTC(Y, M + 1, 0)).getUTCDate();
      var g = ["SUN","MON","TUE","WED","THU","FRI","SAT"].map(function (w, k) { return '<span class="w' + (k === 0 ? " --sun" : k === 6 ? " --sat" : "") + '">' + w + "</span>"; }).join("");
      for (var b = 0; b < first.getUTCDay(); b++) g += '<span class="d --blank"></span>';
      for (var d = 1; d <= days; d++) {
        var key = Y + "-" + pad(M + 1) + "-" + pad(d), wd = (first.getUTCDay() + d - 1) % 7, sp = SPECIAL[key], cls = "d", lab = "";
        if (sp) { cls += " --" + sp.k; lab = sp.t; } else if (isRegular(Y, M, d)) { cls += " --open"; lab = "OPEN"; }
        if (key < todayKey) cls += " --past";
        if (key === todayKey) cls += " --today";
        g += '<span class="' + cls + '"' + (sp ? ' title="' + esc(sp.d || (sp.k === "off" ? "休診" : hm(sp.s) + "–" + hm(sp.e))) + '"' : "") + ">" + d + (lab ? "<em>" + esc(lab) + "</em>" : "") + "</span>";
      }
      html += '<div class="cal glass rv"><div class="cal__head"><b class="grad-text">' + Y + "." + pad(M + 1) + '</b><span class="mono">' + ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"][M] + '</span></div><div class="cal__grid">' + g + "</div></div>";
    }
    calBox.innerHTML = html;
    var ev = $("events");
    if (ev) ev.innerHTML = Object.keys(SPECIAL).filter(function (k) { return k >= todayKey; }).sort().map(function (k) {
      var sp = SPECIAL[k], dt = new Date(k + "T00:00:00Z"), off = sp.k === "off";
      var desc = sp.d || (off ? "この日は休診です" : "特別診療です");
      return '<li class="glass rv"><time>' + k.slice(5).replace("-", ".") + " " + WD[dt.getUTCDay()] + '</time><span class="tag' + (off ? " --off" : "") + '">' + esc(sp.t) + "</span><p>" + esc(desc) +
        (off ? "" : "<small>" + hm(sp.s) + "–" + hm(sp.e) + " JST</small>") + "</p></li>";
    }).join("") || '<li class="glass --empty">予定されている特別診療・休診はありません。</li>';
  }

  /* ---------- タブで絞り込み（MENU・FAQ） ---------- */
  document.querySelectorAll("[data-filter]").forEach(function (tabs) {
    var items = document.querySelectorAll(tabs.dataset.filter);
    tabs.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return;
      [].forEach.call(tabs.children, function (t) { t.setAttribute("aria-selected", t === b); });
      var shownN = 0;
      items.forEach(function (it) { it.hidden = !(b.dataset.cat === "all" || it.dataset.cat === b.dataset.cat); if (!it.hidden) shownN++; });
      if (tabs.dataset.empty && $(tabs.dataset.empty)) $(tabs.dataset.empty).hidden = shownN > 0;
    });
  });

  /* ---------- MEDIA：写真のページ送り（data-per 枚ずつ） ---------- */
  document.querySelectorAll("[data-per]").forEach(function (list) {
    var per = +list.dataset.per, items = [].slice.call(list.children), pages = Math.ceil(items.length / per), pg = 1, nav = list.nextElementSibling;
    if (pages < 2 || !nav) return;
    var draw = function (scroll) {
      items.forEach(function (it, k) { it.hidden = Math.floor(k / per) + 1 !== pg; if (!it.hidden) it.classList.add("is-in"); });
      var h = '<button type="button" class="--prev" aria-label="前のページ" data-p="' + (pg - 1) + '"' + (pg === 1 ? " disabled" : "") + ">" + ARROW + "</button>";
      for (var p = 1; p <= pages; p++) h += '<button type="button" data-p="' + p + '"' + (p === pg ? ' aria-current="page"' : "") + ">" + p + "</button>";
      h += '<button type="button" class="--next" aria-label="次のページ" data-p="' + (pg + 1) + '"' + (pg === pages ? " disabled" : "") + ">" + ARROW + "</button>";
      nav.innerHTML = h;
      if (scroll) scrollTo({ top: list.getBoundingClientRect().top + scrollY - 150, behavior: reduce ? "auto" : "smooth" });
    };
    // ページ切り替えのアニメーション：今の写真が流れて消え → 新しい写真が反対側から順番に入る（＋光のライン）
    var busy = false;
    var shown = function () { return items.filter(function (it) { return !it.hidden; }); };
    var go = function (np) {
      np = Math.max(1, Math.min(pages, np));
      if (np === pg || busy) return;
      var dir = np > pg ? 1 : -1;
      if (reduce || !list.animate) { pg = np; draw(true); return; }
      busy = true;
      scrollTo({ top: list.getBoundingClientRect().top + scrollY - 150, behavior: "smooth" });
      list.classList.remove("is-paging"); void list.offsetWidth; list.classList.add("is-paging");
      var old = shown(), h0 = list.offsetHeight, outMs = 240 + old.length * 22;
      old.forEach(function (it, k) {
        it.animate([{ opacity: 1, transform: "none", filter: "blur(0)" }, { opacity: 0, transform: "translateX(" + (-dir * 46) + "rem) scale(.92) rotate(" + (-dir * 2) + "deg)", filter: "blur(5px)" }],
          { duration: 240, delay: k * 22, easing: "cubic-bezier(.55,0,.8,.2)", fill: "forwards" });
      });
      setTimeout(function () {
        old.forEach(function (it) { it.getAnimations().forEach(function (a) { a.cancel(); }); });
        pg = np; draw(false);
        var now = shown(), h1 = list.offsetHeight;
        if (h1 !== h0) list.animate([{ height: h0 + "px" }, { height: h1 + "px" }], { duration: 420, easing: "cubic-bezier(.2,.8,.2,1)" });
        now.forEach(function (it, k) {
          it.animate([{ opacity: 0, transform: "translate(" + (dir * 70) + "rem, 16rem) scale(.88) rotate(" + (dir * 3) + "deg)", filter: "blur(6px)" },
                      { opacity: 1, offset: .6, filter: "blur(0)" },
                      { opacity: 1, transform: "none", filter: "blur(0)" }],
            { duration: 560, delay: k * 55, easing: "cubic-bezier(.2,1.25,.35,1)", fill: "backwards" });
        });
        setTimeout(function () { busy = false; list.classList.remove("is-paging"); }, 560 + now.length * 55);
      }, outMs);
    };
    nav.addEventListener("click", function (e) { var b = e.target.closest("button"); if (!b || b.disabled) return; go(+b.dataset.p); });
    // スマホ：写真の上を左右にスワイプしてもページ送り
    var sx = 0, sy = 0, st = 0;
    list.addEventListener("touchstart", function (e) { var t = e.touches[0]; sx = t.clientX; sy = t.clientY; st = Date.now(); }, { passive: true });
    list.addEventListener("touchend", function (e) {
      var t = e.changedTouches[0], dx = t.clientX - sx, dy = t.clientY - sy;
      if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.5 && Date.now() - st < 700) go(pg + (dx < 0 ? 1 : -1));
    }, { passive: true });
    draw(false);
  });

  /* ---------- GUIDELINES：目次の現在地 ---------- */
  var toc = document.querySelectorAll(".toc a");
  if (toc.length && "IntersectionObserver" in window) {
    var secIo = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) toc.forEach(function (a) { a.classList.toggle("is-active", a.getAttribute("href") === "#" + e.target.id); }); });
    }, { rootMargin: "-12% 0px -80% 0px" });
    document.querySelectorAll(".gl__sec").forEach(function (s) { secIo.observe(s); });
  }

  /* ---------- NURSES：集合写真の拡大表示 ---------- */
  var lb = $("lightbox"), lbItems = document.querySelectorAll("#gallery [data-full]"), lbi = 0, lbLast;
  function lbShow(k) {
    lbi = (k + lbItems.length) % lbItems.length;
    var b = lbItems[lbi], img = $("lb-img");
    img.src = b.dataset.full; img.alt = b.querySelector("img").alt;
    $("lb-cap").textContent = "PHOTO " + pad(lbi + 1) + " / " + pad(lbItems.length);
  }
  function lbClose() { if (!lb || lb.hidden) return; lb.hidden = true; document.body.style.overflow = ""; if (lbLast) lbLast.focus(); }
  if (lb && lbItems.length) {
    lbItems.forEach(function (b, k) { b.addEventListener("click", function () { lbLast = b; lbShow(k); lb.hidden = false; document.body.style.overflow = "hidden"; lb.querySelector(".lightbox__close").focus(); }); });
    lb.querySelectorAll("[data-lb-close]").forEach(function (b) { b.addEventListener("click", lbClose); });
    $("lb-prev").addEventListener("click", function () { lbShow(lbi - 1); });
    $("lb-next").addEventListener("click", function () { lbShow(lbi + 1); });
    addEventListener("keydown", function (e) {
      if (lb.hidden) return;
      if (e.key === "ArrowLeft") lbShow(lbi - 1); else if (e.key === "ArrowRight") lbShow(lbi + 1); else if (e.key === "Escape") lbClose();
    });
  }

  /* ---------- NURSES：キャスト一覧（期生・名前で絞り込み）とカルテ（プロフィール） ---------- */
  var roster = $("croster");
  if (roster) {
    var cards = [].slice.call(roster.querySelectorAll(".ccard")), cq = $("cast-q"), ctabs = $("cast-tabs"), cm = $("cmodal"), cmBox = $("cm-box"), cmImg = $("cm-img"), cmIdx = 0, cmLast, cmWant = "", curGen = "all";
    var PROF = {}; try { PROF = JSON.parse($("cast-data").textContent); } catch (e) {}
    var shown = function () { return cards.filter(function (c) { return !c.hidden; }); };
    var applyFilter = function () {
      var v = cq.value.trim().toLowerCase(), n = 0;
      cards.forEach(function (c) {
        var p = PROF[c.dataset.id], hay = (c.dataset.name + " " + (p ? p.card : "")).toLowerCase();
        var hit = (!v || hay.indexOf(v) > -1) && (curGen === "all" || c.dataset.gen === curGen);
        c.hidden = !hit; if (hit) n++;
      });
      $("cast-count").textContent = n; $("cast-empty").hidden = n > 0;
    };
    cq.addEventListener("input", applyFilter);
    if (ctabs) ctabs.addEventListener("click", function (e) {
      var b = e.target.closest("button"); if (!b) return; curGen = b.dataset.gen;
      [].forEach.call(ctabs.children, function (t) { t.setAttribute("aria-selected", t === b); }); applyFilter();
    });
    // カルテの4項目メーター（数字が大きいほど右＝10側の意味）。4つの値がそろっていないときは "" を返す
    var KM = [
      { key: "talk", name: "お話し", lo: "聞き役", hi: "おしゃべり" },
      { key: "sweet", name: "甘さ", lo: "クール", hi: "あまあま" },
      { key: "spice", name: "刺激", lo: "おだやか", hi: "ドキドキ" },
      { key: "dist", name: "距離", lo: "ひかえめ", hi: "ぐっと近い" }
    ];
    var kmRender = function (p) {
      var vals = KM.map(function (it) { var v = Number(p && p[it.key]); return v >= 1 && v <= 10 && Math.round(v) === v ? v : 0; });
      if (vals.indexOf(0) > -1) return "";
      return KM.map(function (it, k) {
        var v = vals[k], cells = "";
        for (var i = 0; i < 10; i++) cells += '<i style="--i:' + i + '"' + (i < v ? ' class="on"' : "") + "></i>";
        return '<div class="km__item" role="listitem"><span class="km__sr">' + it.name + " 10段階中" + v + "。1は" + it.lo + "、10は" + it.hi + "</span>" +
          '<span class="km__k" aria-hidden="true">' + it.name + '</span><span class="km__bar" aria-hidden="true">' + cells + '</span><span class="km__n" aria-hidden="true">' + v + "</span>" +
          '<span class="km__ends" aria-hidden="true"><span class="km__end">' + it.lo + '</span><span class="km__end">' + it.hi + "</span></span></div>";
      }).join("");
    };
    var cmShow = function (card) {
      var list = shown(), d = card.dataset, p = PROF[d.id]; cmIdx = list.indexOf(card);
      cmBox.style.setProperty("--c", card.style.getPropertyValue("--c"));
      cmBox.style.setProperty("--c2", card.style.getPropertyValue("--c2"));
      cmWant = d.id; cmImg.src = "img/cast/s/" + d.id + ".webp"; cmImg.alt = d.name;
      var big = new Image(); big.onload = function () { if (cmWant === d.id) cmImg.src = big.src; }; big.src = "img/cast/" + d.id + ".webp";
      $("cm-name").textContent = d.name; $("cm-no").textContent = "No." + d.no;
      $("cm-catch").textContent = p ? p.catch : "";
      // 役職（院長・婦長・主任）→ ナースの種類（期生ごと）→ 担当（シンガーなど）→ 期生（期生があるときだけ）。何も無ければ行ごと消える（.cm-tags:empty）
      var lead = p ? p.roles.filter(function (r) { return /院長|婦長|主任/.test(r); }) : [], rest = p ? p.roles.filter(function (r) { return !/院長|婦長|主任/.test(r); }) : [];
      $("cm-tags").innerHTML = p ? lead.map(function (r) { return '<span class="--lead">' + esc(r) + "</span>"; }).join("") + (p.type ? '<span class="--type">' + esc(p.type) + "</span>" : "") +
        rest.map(function (r) { return "<span>" + esc(r) + "</span>"; }).join("") + (p.gen > 0 ? '<span class="--gen g' + p.gen + '">' + p.gen + "期生</span>" : "") : '<span class="--gen g0">カルテ準備中</span>';
      var km = kmRender(p);
      $("cm-spec").innerHTML = km; $("cm-spec").hidden = !km; $("cm-empty").hidden = !!p;
      $("cm-pos").textContent = pad(cmIdx + 1) + " / " + pad(list.length);
    };
    var cmClose = function () { if (cm.hidden) return; cm.hidden = true; document.body.style.overflow = ""; if (cmLast) cmLast.focus(); };
    var cmStep = function (n) { var list = shown(); if (list.length) cmShow(list[(cmIdx + n + list.length) % list.length]); };
    cards.forEach(function (c) {
      var b = c.querySelector("button");
      b.addEventListener("click", function () { cmLast = b; cmShow(c); cm.hidden = false; document.body.style.overflow = "hidden"; cm.querySelector(".cmodal__close").focus(); });
    });
    cm.querySelectorAll("[data-cm-close]").forEach(function (b) { b.addEventListener("click", cmClose); });
    $("cm-prev").addEventListener("click", function () { cmStep(-1); });
    var openMaid = function (id) {
      var hc = roster.querySelector('.ccard[data-id="' + id + '"]'); if (!hc) return false;
      if (hc.hidden) { cq.value = ""; curGen = "all"; if (ctabs) [].forEach.call(ctabs.children, function (t) { t.setAttribute("aria-selected", t.dataset.gen === "all"); }); applyFilter(); }
      hc.scrollIntoView({ block: "center" }); cmLast = hc.querySelector("button"); cmShow(hc); cm.hidden = false; document.body.style.overflow = "hidden"; return true;
    };
    window.mdOpenMaid = openMaid;
    var fromHash = function () { var h = location.hash.slice(1); if (/^c\d+$/.test(h)) setTimeout(function () { openMaid(h); }, 300); };
    fromHash(); addEventListener("hashchange", fromHash);
    $("cm-next").addEventListener("click", function () { cmStep(1); });
    addEventListener("keydown", function (e) {
      if (cm.hidden) return;
      if (e.key === "ArrowLeft") cmStep(-1); else if (e.key === "ArrowRight") cmStep(1); else if (e.key === "Escape") cmClose();
    });
  }

  /* ---------- トップ：はじめての患者さまへ（病院システムのダイアログ → 閉じるとデスクトップの「はじめに.txt」） ---------- */
  var dlg = $("hero-dlg"), dIcon = $("hero-icon");
  if (dlg && dIcon) {
    var ss = function (k, v) { try { if (v === undefined) return sessionStorage.getItem(k); sessionStorage.setItem(k, v); } catch (e) { return null; } };
    var toIcon = function (focusIcon) {
      if (dlg.hidden) return;
      ss("md-dlg", "1"); dlg.classList.add("is-closing");
      setTimeout(function () { dlg.hidden = true; dIcon.hidden = false; dIcon.classList.add("is-new"); if (focusIcon) dIcon.focus(); }, reduce ? 0 : 360);
    };
    if (ss("md-dlg")) { dlg.hidden = true; dIcon.hidden = false; }
    dlg.querySelectorAll("[data-dlg-close]").forEach(function (b) { b.addEventListener("click", function () { toIcon(true); }); });
    // 「はい」でガイドを開き、ガイドを閉じたらダイアログはアイコンにしまう
    var guide = $("modal"), wantIcon = false;
    dlg.querySelector("[data-open-about]").addEventListener("click", function () { wantIcon = true; });
    if (guide && "MutationObserver" in window) new MutationObserver(function () { if (wantIcon && guide.hidden) { wantIcon = false; toIcon(true); } }).observe(guide, { attributes: true, attributeFilter: ["hidden"] });
  }

  /* ---------- はじめてのご来院ガイド（モーダル） ---------- */
  var modal = $("modal"), lastFocus;
  function closeModal() { if (!modal || modal.hidden) return; modal.hidden = true; if (lastFocus) lastFocus.focus(); }
  if (modal) {
    var openModal = function () { lastFocus = document.activeElement; modal.hidden = false; modal.querySelector(".modal__close").focus(); };
    document.querySelectorAll("[data-open-about]").forEach(function (b) { b.addEventListener("click", openModal); });
    modal.querySelectorAll("[data-close]").forEach(function (b) { b.addEventListener("click", closeModal); });
  }

  /* ---------- SPメニュー ---------- */
  var mb = $("menu-btn");
  function setMenu(open) { document.body.classList.toggle("menu-open", open); mb.setAttribute("aria-expanded", open); mb.setAttribute("aria-label", open ? "メニューを閉じる" : "メニューを開く"); }
  if (mb) {
    mb.addEventListener("click", function () { setMenu(!document.body.classList.contains("menu-open")); });
    document.querySelectorAll(".sp-menu a").forEach(function (a) { a.addEventListener("click", function () { setMenu(false); }); });
  }
  addEventListener("keydown", function (e) { if (e.key === "Escape") { closeModal(); if (mb) setMenu(false); } });

  /* ---------- TOPへ ---------- */
  var gt = $("go-top");
  if (gt) addEventListener("scroll", function () { gt.classList.toggle("is-show", scrollY > 500); }, { passive: true });

  /* ---------- コピー ---------- */
  document.querySelectorAll("[data-copy]").forEach(function (b) {
    var tx = b.querySelector("span") || b, label = tx.textContent;
    b.addEventListener("click", function () {
      var el = $(b.dataset.copy);
      function done() { tx.textContent = "コピーしました"; setTimeout(function () { tx.textContent = label; }, 1800); }
      function fb() { var r = document.createRange(); r.selectNodeContents(el); var s = getSelection(); s.removeAllRanges(); s.addRange(r); tx.textContent = "選択しました"; }
      try { navigator.clipboard.writeText(el.textContent).then(done, fb); } catch (e) { fb(); }
    });
  });

  /* =========================================================
     あそび：隠れハート（スタンプラリー）・処方おみくじ・隠しコマンド
     ========================================================= */
  (function () {
    var store = {
      get: function (k, d) { try { var v = localStorage.getItem(k); return v ? JSON.parse(v) : d; } catch (e) { return d; } },
      set: function (k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
    };
    var CLOSE = '<svg viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"><path d="M2 2l10 10M12 2L2 12"/></svg>';
    var HEART = '<svg viewBox="0 0 40 36" aria-hidden="true"><path d="M20 34 C7 25 2 18 2 11 C2 5 6 2 11 2 C15 2 18 4 20 8 C22 4 25 2 29 2 C34 2 38 5 38 11 C38 18 33 25 20 34 Z"/></svg>';
    var mainEl = document.querySelector("main"), page = mainEl ? (mainEl.className.match(/page-([\w-]+)/) || [])[1] : "";

    /* ---- 小さなお知らせ ---- */
    var toast = document.createElement("div"); toast.className = "md-toast"; toast.setAttribute("role", "status"); document.body.appendChild(toast);
    var tTimer; function say(h) { toast.innerHTML = h; toast.classList.add("is-on"); clearTimeout(tTimer); tTimer = setTimeout(function () { toast.classList.remove("is-on"); }, 2800); }

    /* ---- ハートがはじける ---- */
    function burst(x, y, n, spread) {
      if (reduce) return;
      var cols = ["#f953c2", "#c8107f", "#00abfc", "#7fd5fe", "#ffd36e"];
      for (var k = 0; k < n; k++) {
        var h = document.createElement("i"), a = Math.random() * Math.PI * 2, d = (spread || 120) * (.4 + Math.random() * .8);
        h.className = "md-pop"; h.style.cssText = "left:" + x + "px;top:" + y + "px;--c:" + cols[k % cols.length] + ";--dx:" + Math.cos(a) * d + "px;--dy:" + (Math.sin(a) * d - 40) + "px;--r:" + (Math.random() * 120 - 60) + "deg;--s:" + (.5 + Math.random() * .8);
        document.body.appendChild(h); setTimeout(function (el) { el.remove(); }.bind(null, h), 1300);
      }
    }

    /* ---- ポップアップの土台 ---- */
    var openM = null;
    function makeModal(cls, label, inner) {
      var m = document.createElement("div"); m.className = "md-modal " + cls; m.hidden = true;
      m.setAttribute("role", "dialog"); m.setAttribute("aria-modal", "true"); m.setAttribute("aria-label", label);
      m.innerHTML = '<div class="md-modal__bg" data-x></div><div class="md-modal__box"><button class="md-modal__close" type="button" data-x aria-label="閉じる">' + CLOSE + "</button>" + inner + "</div>";
      document.body.appendChild(m);
      m.querySelectorAll("[data-x]").forEach(function (b) { b.addEventListener("click", function () { closeModal2(m); }); });
      return m;
    }
    function openModal2(m) { if (openM) closeModal2(openM); m.hidden = false; openM = m; document.body.style.overflow = "hidden"; var c = m.querySelector(".md-modal__close"); if (c) c.focus(); }
    function closeModal2(m) { m.hidden = true; if (openM === m) openM = null; document.body.style.overflow = ""; }
    addEventListener("keydown", function (e) { if (e.key === "Escape" && openM) closeModal2(openM); });

    /* =========================================================
       1. 隠れハート（8ページに1こずつ）
       ========================================================= */
    var SPOTS = [
      { id: "top", page: "index", label: "TOP", sel: "#news .sec-head", x: 97, y: 2 },
      { id: "about", page: "about", label: "ABOUT", sel: ".concept", x: 100, y: -4 },
      { id: "nurses", page: "nurses", label: "NURSES", sel: ".ctool", x: 99.5, y: 50 },
      { id: "schedule", page: "schedule", label: "SCHEDULE", sel: ".cal-wrap", x: 100, y: -3 },
      { id: "menu", page: "menu", label: "MENU", sel: ".rota", x: 94, y: 18 },
      { id: "media", page: "media", label: "MEDIA", sel: ".share", x: 7, y: 16 },
      { id: "guide", page: "guidelines", label: "GUIDELINES", sel: ".gl__doc", x: 50, y: 100 },
      { id: "faq", page: "faq", label: "FAQ", sel: ".faq-more", x: 76, y: 4 }
    ];
    var got = store.get("md-hearts", []).filter(function (id) { return SPOTS.some(function (p) { return p.id === id; }); });
    var isVip = function () { return got.length >= SPOTS.length; };

    var badge = document.createElement("button"); badge.type = "button"; badge.className = "md-badge"; badge.setAttribute("aria-label", "シークレットスタンプカードを開く");
    document.body.appendChild(badge);
    var heroEl = document.querySelector(".hero");
    function badgePos() { badge.classList.toggle("--away", !!heroEl && scrollY < heroEl.offsetHeight * .7); }
    addEventListener("scroll", badgePos, { passive: true }); badgePos();
    function drawBadge() { badge.innerHTML = HEART + "<span><b>" + got.length + "</b><small>/" + SPOTS.length + "</small></span>"; badge.hidden = got.length === 0; badge.classList.toggle("--vip", isVip()); }

    var card = makeModal("md-stamp", "シークレットスタンプカード",
      '<p class="md-stamp__label mono">SECRET STAMP CARD</p><h2 class="md-stamp__title">隠れハートを探せ！</h2>' +
      '<p class="md-stamp__lead">サイトのどこかに、キラキラ光るハートが <b>' + SPOTS.length + 'こ</b> 隠れているよ。<br>ぜんぶ見つけると、なにかが起きるかも…♡</p>' +
      '<div class="md-stamp__bar"><i id="md-bar"></i></div><p class="md-stamp__count mono"><b id="md-count">0</b> / ' + SPOTS.length + ' FOUND</p>' +
      '<ul class="md-stamp__grid" id="md-grid"></ul><div class="md-stamp__vip" id="md-vip" hidden></div>' +
      '<button class="md-stamp__reset" type="button" id="md-reset">スタンプをリセット</button>');
    function drawCard() {
      $("md-grid").innerHTML = SPOTS.map(function (p, k) {
        var on = got.indexOf(p.id) > -1;
        return '<li class="' + (on ? "is-on" : "") + '"><span class="md-stamp__no mono">' + pad(k + 1) + "</span>" + (on ? HEART : "<em>?</em>") + '<span class="md-stamp__pg mono">' + (on ? p.label : "???") + "</span></li>";
      }).join("");
      $("md-count").textContent = got.length; $("md-bar").style.width = (got.length / SPOTS.length * 100) + "%";
      var v = $("md-vip"); v.hidden = !isVip();
      if (isVip()) v.innerHTML = '<p class="mono">COMPLETE ♡ VIP PATIENT</p><p>ぜんぶ見つけてくれてありがとう！<br>あなたはSuccubusClinicの <b>VIP患者さま</b> です♡</p><p class="md-stamp__word mono">SECRET WORD ▶ <b>succubus</b></p><p class="md-stamp__hint">キーボードで打ってみてね（スマホはロゴを長押し）</p><button class="btn" type="button" data-omikuji><span>処方おみくじ</span><i>' + ARROW + "</i></button>";
      bindOmikuji(v);
    }
    badge.addEventListener("click", function () { drawCard(); openModal2(card); });
    $("md-reset").addEventListener("click", function () { got = []; store.set("md-hearts", got); applyVip(); drawBadge(); drawCard(); placeHeart(); say("スタンプをリセットしました"); });

    function applyVip() {
      root.classList.toggle("is-vip", isVip());
      var dt = document.querySelector(".dlg__title"); if (dt) dt.textContent = isVip() ? "SUCCUBUS CLINIC SYSTEM — VIP PATIENT ♡" : "SUCCUBUS CLINIC SYSTEM";
    }
    function placeHeart() {
      var sp = SPOTS.filter(function (p) { return p.page === page; })[0];
      var old = document.querySelector(".secret-heart"); if (old) old.remove();
      if (!sp || got.indexOf(sp.id) > -1) return;
      var box = document.querySelector(sp.sel); if (!box) return;
      if (getComputedStyle(box).position === "static") box.style.position = "relative";
      var b = document.createElement("button"); b.type = "button"; b.className = "secret-heart"; b.setAttribute("aria-label", "隠れハート"); b.innerHTML = HEART;
      b.style.left = sp.x + "%"; b.style.top = sp.y + "%";
      b.addEventListener("click", function (e) {
        e.preventDefault(); e.stopPropagation();
        if (got.indexOf(sp.id) < 0) got.push(sp.id); store.set("md-hearts", got);
        var r = b.getBoundingClientRect(); burst(r.left + r.width / 2, r.top + r.height / 2, 16, 110);
        b.classList.add("is-got"); setTimeout(function () { b.remove(); }, 600);
        drawBadge(); applyVip();
        if (isVip()) { setTimeout(function () { burst(innerWidth / 2, innerHeight / 2, 60, 360); drawCard(); openModal2(card); }, 500); say("コンプリート！ <b>VIP患者さま</b> になりました♡"); }
        else say("隠れハートを見つけた！ <b>" + got.length + "</b> / " + SPOTS.length);
      });
      box.appendChild(b);
    }

    /* =========================================================
       2. 処方おみくじ（フッターの「あなたの推しがきっと見つかる」）
       ========================================================= */
    var CAST = window.MD_CAST || [], last = "", omk = null;
    var MENU = ["発熱注意♡ドクターカレー", "小悪魔のハートけーき", "おえかき♡ハート錠", "恋わずらいぷりんあらもーど", "回復のいちごポーション", "とろける☆点滴ふらっぺ", "からふる☆カプセルそーだ", "ナースの栄養べんとう♡", "診察室のハンバーグ", "微熱ラテ", "ひみつの特効薬"];
    var LUCK = ["超大吉", "大吉", "大吉", "中吉", "吉"];
    function omikuji() {
      if (!CAST.length) return;
      if (!omk) {
        omk = makeModal("md-omk", "処方おみくじ",
          '<p class="md-omk__label mono">PRESCRIPTION OMIKUJI</p><h2 class="md-omk__title">処方おみくじ</h2>' +
          '<div class="md-omk__stage"><div class="md-omk__cap" id="omk-cap"><i class="--t"></i><i class="--b"></i><span>?</span></div>' +
          '<div class="md-omk__res" id="omk-res" hidden><figure class="md-omk__ph" id="omk-ph"><img id="omk-img" src="" alt=""></figure><div class="md-omk__info">' +
          '<p class="md-omk__luck"><span class="mono">TODAY</span><b id="omk-luck"></b></p><p class="md-omk__lead">今日のあなたに処方される推しナースは…</p>' +
          '<p class="md-omk__name" id="omk-name"></p><p class="md-omk__catch" id="omk-catch"></p>' +
          '<dl class="md-omk__spec"><div><dt>相性</dt><dd id="omk-love"></dd></div><div><dt>ラッキー処方</dt><dd id="omk-menu"></dd></div></dl></div></div></div>' +
          '<div class="md-omk__btns"><button class="btn" type="button" id="omk-draw"><span>おみくじを引く</span><i>' + ARROW + '</i></button><a class="btn" id="omk-prof" href="nurses.html" hidden><span>カルテを見る</span><i>' + ARROW + "</i></a></div>");
        $("omk-draw").addEventListener("click", draw);
        $("omk-prof").addEventListener("click", function (e) {
          var id = this.getAttribute("href").split("#")[1];
          if (window.mdOpenMaid) { e.preventDefault(); closeModal2(omk); if (history.replaceState) history.replaceState(null, "", "#" + id); window.mdOpenMaid(id); }
        });
      }
      $("omk-res").hidden = true; $("omk-prof").hidden = true; $("omk-cap").className = "md-omk__cap";
      $("omk-draw").querySelector("span").textContent = "おみくじを引く";
      openModal2(omk);
    }
    function draw() {
      var btn = $("omk-draw"), cap = $("omk-cap"), res = $("omk-res"); btn.disabled = true;
      res.hidden = true; $("omk-prof").hidden = true; cap.className = "md-omk__cap"; void cap.offsetWidth; cap.classList.add("is-shake");
      var m; do { m = CAST[Math.floor(Math.random() * CAST.length)]; } while (CAST.length > 1 && m.id === last); last = m.id;
      var ok = function () {
        cap.classList.add("is-open");
        $("omk-ph").style.setProperty("--c", m.c); $("omk-img").src = "img/cast/s/" + m.id + ".webp"; $("omk-img").alt = m.n;
        $("omk-name").textContent = m.n; $("omk-catch").textContent = m.t || "";
        $("omk-luck").textContent = LUCK[Math.floor(Math.random() * LUCK.length)];
        var love = 3 + Math.floor(Math.random() * 3); $("omk-love").innerHTML = '<span class="--on">' + "♥".repeat(love) + "</span>" + "♡".repeat(5 - love);
        $("omk-menu").textContent = MENU[Math.floor(Math.random() * MENU.length)];
        $("omk-prof").href = "nurses.html#" + m.id;
        setTimeout(function () {
          res.hidden = false; $("omk-prof").hidden = false; btn.disabled = false; btn.querySelector("span").textContent = "もう一回引く";
          var r = res.getBoundingClientRect(); burst(r.left + r.width * .3, r.top + r.height * .4, 22, 160);
        }, reduce ? 0 : 420);
      };
      setTimeout(ok, reduce ? 0 : 1100);
    }
    function bindOmikuji(scope) { (scope || document).querySelectorAll("[data-omikuji]").forEach(function (b) { if (b.__omk) return; b.__omk = 1; b.addEventListener("click", function () { if (openM) closeModal2(openM); omikuji(); }); }); }

    /* =========================================================
       3. ひみつのことば（キーボードで入力）と、スマホ用のしかけ
          succubus … SUCCUBUS CLINIC SYSTEM ターミナル（ロゴを長押し）
          kenon … ナースと検温ゲーム（MENUの「診療のおたのしみは…」を5回タップ）
          kusuri … お薬にお絵描き（MENUの「おえかき♡ハート錠」を長押し）
          parade … ナース大行進（フッターのロゴを5回タップ）
          ＋ 隔週月曜 21:50〜23:10 だけの「開院モード」
       ========================================================= */
    var shuffle = function (a) { a = a.slice(); for (var i = a.length - 1; i > 0; i--) { var j = Math.floor(Math.random() * (i + 1)), t = a[i]; a[i] = a[j]; a[j] = t; } return a; };
    var pick = function (a) { return a[Math.floor(Math.random() * a.length)]; };
    var goMaid = function (id) { if (window.mdOpenMaid) { if (openM) closeModal2(openM); window.mdOpenMaid(id); } else location.href = "nurses.html#" + id; };
    var esc2 = function (t) { return String(t).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); };

    /* ---------- 1. SUCCUBUS CLINIC SYSTEM ターミナル ---------- */
    var term = null, hist = [], hpos = 0, openPreview = false;
    function tPrint(html, cls) { var o = $("tm-out"), p = document.createElement("p"); p.className = cls || ""; p.innerHTML = html; o.appendChild(p); o.scrollTop = o.scrollHeight; }
    var CMDS = [
      ["help", "コマンドの一覧"], ["next", "次の診療日"], ["nurses", "在籍ナースの数"], ["hearts", "隠れハートの進みぐあい"],
      ["omikuji", "処方おみくじ"], ["kenon", "ナースと検温ゲーム"], ["kusuri", "お薬にお絵描き"],
      ["parade", "ナース大行進"], ["openmode", "開院モードをのぞき見"], ["whoami", "あなたはだれ？"], ["clear", "画面をきれいにする"], ["exit", "ターミナルを閉じる"]
    ];
    function run(raw) {
      var cmd = raw.trim().toLowerCase(); if (!cmd) return;
      tPrint('<span class="--p">patient@succubus:~$</span> ' + esc2(raw), "--in");
      hist.push(raw); hpos = hist.length;
      var later = function (fn) { tPrint("起動します…", "--ok"); setTimeout(function () { closeModal2(term); fn(); }, 450); };
      switch (cmd) {
        case "help": tPrint(CMDS.map(function (c) { return '<b>' + c[0] + "</b>" + c[1]; }).join("<br>"), "--list"); break;
        case "next":
          var L = openList(Date.now(), 3);
          tPrint(L.map(function (t, k) { var j = new Date(t + JST); return (k ? "　　　　 " : "NEXT VISIT ") + md(t) + " (" + WD[j.getUTCDay()] + ") " + timeLabel(t) + " JST"; }).join("<br>"), "--ok"); break;
        case "nurses":
          var gens = {}; CAST.forEach(function (c) { gens[c.g] = (gens[c.g] || 0) + 1; });
          tPrint("在籍ナース：<b>" + CAST.length + "名</b><br>" + Object.keys(gens).sort(function (a, b) { return a - b; }).map(function (g) { return (+g ? g + "期生" + ((window.MD_TYPES || {})[g] ? "（" + window.MD_TYPES[g] + "）" : "") : "その他") + " " + gens[g] + "名"; }).join("<br>") + '<br><a href="nurses.html">→ NURSES ページへ</a>', "--ok"); break;
        case "hearts":
          var rest = SPOTS.filter(function (p) { return got.indexOf(p.id) < 0; }).map(function (p) { return p.label; });
          tPrint("隠れハート：<b>" + got.length + " / " + SPOTS.length + "</b>" + (rest.length ? "<br>まだのページ：" + rest.join(", ") : "<br>COMPLETE ♡ あなたはVIP患者さまです"), "--ok"); break;
        case "omikuji": later(omikuji); break;
        case "kenon": later(chinchiro); break;
        case "kusuri": later(omurice); break;
        case "parade": later(parade); break;
        case "openmode": openPreview = !openPreview; checkOpen(); tPrint("開院モードのぞき見：<b>" + (openPreview ? "ON" : "OFF") + "</b>" + (page === "index" ? "" : '<br>（トップページで見られます → <a href="index.html">TOP</a>）'), "--ok"); break;
        case "whoami": tPrint(isVip() ? "VIP患者さま ♡" : "患者さま（診察券 No.0001）", "--ok"); break;
        case "sudo": case "sudo su": tPrint("Permission denied. 婦長に聞いてね♡", "--err"); break;
        case "clear": $("tm-out").innerHTML = ""; break;
        case "exit": case "quit": closeModal2(term); break;
        default: tPrint("command not found: " + esc2(cmd) + "（<b>help</b> で一覧を表示）", "--err");
      }
    }
    function terminal() {
      if (!term) {
        term = makeModal("md-term", "SUCCUBUS CLINIC SYSTEM ターミナル",
          '<div class="md-term__bar"><i></i><i></i><i></i><span class="mono">SUCCUBUS CLINIC SYSTEM — nurse station</span></div>' +
          '<div class="md-term__screen" id="tm-out" aria-live="polite"></div>' +
          '<form class="md-term__line" id="tm-form" autocomplete="off"><label class="--p" for="tm-in">patient@succubus:~$</label><input id="tm-in" type="text" spellcheck="false" autocapitalize="off" autocomplete="off" enterkeyhint="send" aria-label="コマンドを入力"></form>' +
          '<div class="md-term__chips">' + CMDS.slice(1, 10).map(function (c) { return '<button type="button" data-cmd="' + c[0] + '">' + c[0] + "</button>"; }).join("") + "</div>");
        $("tm-form").addEventListener("submit", function (e) { e.preventDefault(); var i = $("tm-in"); run(i.value); i.value = ""; });
        $("tm-in").addEventListener("keydown", function (e) {
          if (e.key === "ArrowUp" && hist.length) { e.preventDefault(); hpos = Math.max(0, hpos - 1); this.value = hist[hpos]; }
          else if (e.key === "ArrowDown" && hist.length) { e.preventDefault(); hpos = Math.min(hist.length, hpos + 1); this.value = hist[hpos] || ""; }
          else if (e.key === "Tab") { e.preventDefault(); var v = this.value.toLowerCase(), m = CMDS.filter(function (c) { return c[0].indexOf(v) === 0; }); if (m.length === 1) this.value = m[0][0]; }
        });
        term.querySelector(".md-term__chips").addEventListener("click", function (e) { var b = e.target.closest("[data-cmd]"); if (b) run(b.dataset.cmd); });
        $("tm-out").addEventListener("click", function () { $("tm-in").focus(); });
        var boot = ["SUCCUBUS CLINIC SYSTEM v1.0 — nurse station terminal", "(c) 2026 SuccubusClinic. All nurses on duty ♡", "&gt; reading patient card ............... <b>OK</b>", "&gt; matching karte: nurses ............. <b>" + CAST.length + "/" + CAST.length + "</b>", "いらっしゃいませ、患者さま。<b>help</b> と入力すると、コマンドの一覧が出ます。"];
        boot.forEach(function (l, k) { setTimeout(function () { tPrint(l, k < 2 ? "--sys" : "--ok"); }, reduce ? 0 : 140 * k); });
      }
      openModal2(term); setTimeout(function () { $("tm-in").focus({ preventScroll: true }); }, 80);
    }

    /* ---------- 2. ナースと検温ゲーム（しくみはサイコロ3つのチンチロ） ---------- */
    var chin = null, chMaid = null, chTries = 0, chBusy = false, chYou = null, chGen = 0, chSayT = 0;
    var PIPS = { 1: [4], 2: [0, 8], 3: [0, 4, 8], 4: [0, 2, 6, 8], 5: [0, 2, 4, 6, 8], 6: [0, 2, 3, 5, 6, 8] };
    // 立方体のサイコロ（1の裏が6・2の裏が5・3の裏が4）。SHOW は、その目を正面に向ける角度
    var SHOW = { 1: [0, 0], 6: [0, 180], 2: [0, -90], 5: [0, 90], 3: [-90, 0], 4: [90, 0] };
    var faceHTML = function (v) { var h = '<span class="die3__f --f' + v + '">'; for (var k = 0; k < 9; k++) h += PIPS[v].indexOf(k) > -1 ? '<i class="on"></i>' : "<i></i>"; return h + "</span>"; };
    var CUBE = [1, 2, 3, 4, 5, 6].map(faceHTML).join("");
    var cubeT = function (v, z, ex, ey) { var a = SHOW[v]; return "rotateX(-18deg) rotateZ(" + z + "deg) rotateX(" + (a[0] + ex) + "deg) rotateY(" + (a[1] + ey) + "deg)"; };
    var roll3 = function () { return [1, 2, 3].map(function () { return 1 + Math.floor(Math.random() * 6); }); };
    function judge(d) {
      var s = d.slice().sort(), a = s[0], b = s[1], c = s[2];
      if (a === 1 && b === 1 && c === 1) return { v: 100, n: "ピンゾロ", k: "pin" };
      if (a === b && b === c) return { v: 90 + a, n: a + "のゾロ目", k: "zoro" };
      if (a === 4 && b === 5 && c === 6) return { v: 80, n: "シゴロ", k: "shigoro" };
      if (a === 1 && b === 2 && c === 3) return { v: -10, n: "ヒフミ", k: "hifumi" };
      if (a === b) return { v: 10 + c, n: c + "の目", k: "me" };
      if (b === c) return { v: 10 + a, n: a + "の目", k: "me" };
      return null;
    }
    var NOPT = { v: 0, n: "目なし", k: "none" };
    function blankDice(box) { box.innerHTML = '<span class="die3 --blank"></span><span class="die3 --blank"></span><span class="die3 --blank"></span>'; }
    function bowlHit(bowl) { bowl.classList.remove("is-hit"); void bowl.offsetWidth; bowl.classList.add("is-hit"); }
    // どんぶりにサイコロを投げ入れる（上から落ちて2回はねて、くるくる回って目が止まる）
    function throwDice(box, cb) {
      var final = roll3(), g = chGen, bowl = box.parentNode;
      box.innerHTML = final.map(function () { return '<span class="die3"><i class="die3__sh"></i><span class="die3__cube">' + CUBE + "</span></span>"; }).join("");
      var dice = box.querySelectorAll(".die3"), side = Math.random() < .5 ? -1 : 1;
      var fins = final.map(function (v) { return cubeT(v, Math.round(Math.random() * 36 - 18), 0, 0); });
      dice.forEach(function (d, k) { d.querySelector(".die3__cube").style.transform = fins[k]; });
      var done = function () { if (g === chGen) cb(final); };
      if (reduce || !box.animate) return done();
      var s = dice[0].getBoundingClientRect().width || 40, dur = 1080, EI = "cubic-bezier(.55,0,1,.45)", EO = "cubic-bezier(0,.55,.45,1)";
      box.classList.add("is-rolling");
      dice.forEach(function (d, k) {
        var cube = d.querySelector(".die3__cube"), sh = d.querySelector(".die3__sh"), dl = k * 90;
        var sx = side * s * (1.1 + Math.random() * 1.3), h = s * (2.6 + Math.random() * .9), z0 = side * (160 + Math.random() * 120);
        d.animate([
          { transform: "translate(" + sx + "px," + -h + "px) scale(1.35)", easing: EI },
          { transform: "translate(" + sx * .42 + "px,0) scale(1)", offset: .42, easing: EO },
          { transform: "translate(" + sx * .18 + "px," + -h * .32 + "px) scale(1.07)", offset: .6, easing: EI },
          { transform: "translate(" + sx * .06 + "px,0) scale(1)", offset: .76, easing: EO },
          { transform: "translate(" + sx * .02 + "px," + -h * .08 + "px) scale(1.01)", offset: .87, easing: EI },
          { transform: "translate(0,0) scale(1)" }
        ], { duration: dur, delay: dl, fill: "backwards" });
        cube.animate([{ transform: cubeT(final[k], z0, side * (540 + 180 * (k % 2)), -side * (360 + 90 * k)) }, { transform: fins[k] }],
          { duration: dur * .92, delay: dl, easing: "cubic-bezier(.12,.62,.3,1)", fill: "backwards" });
        sh.animate([{ opacity: 0, transform: "scale(.3)" }, { opacity: 1, transform: "scale(1)", offset: .42 }, { opacity: .45, transform: "scale(.7)", offset: .6 }, { opacity: 1, transform: "scale(1)", offset: .76 }, { opacity: 1, transform: "scale(1)" }],
          { duration: dur, delay: dl, fill: "backwards" });
      });
      [.42, .76].forEach(function (o) { setTimeout(function () { if (g === chGen) bowlHit(bowl); }, dur * o + 90); });
      setTimeout(function () { box.classList.remove("is-rolling"); done(); }, dur + 260);
    }
    function chTurn(who) { $("ch-yside").classList.toggle("is-turn", who === "you"); $("ch-mside").classList.toggle("is-turn", who === "maid"); }
    function chSay(t) { var b = $("ch-say"); b.textContent = t; b.classList.remove("is-on"); void b.offsetWidth; b.classList.add("is-on"); clearTimeout(chSayT); chSayT = setTimeout(function () { b.classList.remove("is-on"); }, 2200); }
    function chShake() { var bx = chin.querySelector(".md-modal__box"); bx.classList.remove("is-shake"); void bx.offsetWidth; bx.classList.add("is-shake"); }
    function chPop(el, t) { el.textContent = t; el.classList.remove("is-pop"); void el.offsetWidth; el.classList.add("is-pop"); }
    // 役のカットイン（ピンゾロ・ゾロ目・シゴロ・ヒフミは大きく、目あり・目なしは小さく）
    var CUT = { pin: ["PINZORO!!", "--gold"], zoro: ["ZOROME!", "--zoro"], shigoro: ["SHIGORO!", "--shigoro"], hifumi: ["HIFUMI…", "--hifumi"], me: ["POINT", "--me"], none: ["NO POINT", "--none"] };
    function cutIn(j, who, sub, cb) {
      var el = $("ch-cut"), big = j.k !== "me" && j.k !== "none", c = CUT[j.k], g = chGen;
      el.className = "md-chin__cut " + c[1] + (big ? " --big" : "");
      el.querySelector(".md-chin__cutWho").textContent = who;
      el.querySelector(".md-chin__cutJp").textContent = j.n;
      el.querySelector(".md-chin__cutEn").textContent = c[0] + (sub ? " — " + sub : "");
      void el.offsetWidth; el.classList.add("is-on");
      var r = $("ch-board").getBoundingClientRect(), cx = r.left + r.width / 2, cy = r.top + r.height / 2;
      if (j.k === "pin" || j.k === "zoro") { var f = $("ch-flash"); f.className = "md-chin__flash " + c[1]; void f.offsetWidth; f.classList.add("is-on"); burst(cx, cy, j.k === "pin" ? 44 : 30, 260); chShake(); }
      else if (j.k === "shigoro") burst(cx, cy, 22, 200);
      else if (j.k === "hifumi") chShake();
      setTimeout(function () { el.classList.remove("is-on"); if (g === chGen && cb) cb(); }, reduce ? 400 : big ? 1650 : 900);
    }
    function chReset(msg) {
      chGen++; chTries = 0; chYou = null; chBusy = false;
      blankDice($("ch-ydice")); blankDice($("ch-mdice"));
      $("ch-yrole").textContent = "—"; $("ch-mrole").textContent = "—";
      $("ch-roll").hidden = false; $("ch-roll").disabled = false; $("ch-roll").querySelector("span").textContent = "サイコロを振る"; $("ch-again").hidden = true;
      $("ch-stamp").classList.remove("is-on"); $("ch-cut").classList.remove("is-on"); chTurn("you");
      $("ch-msg").innerHTML = msg || "<b>" + esc2(chMaid.n) + "</b>「検温の時間だよ、患者さま♡ 先にどうぞ！」";
      chSay(pick(["検温しよ♡", "負けないよ〜！", "いざ、勝負♡"]));
    }
    function chScore() { var st = store.get("md-chin", { s: 0, b: 0 }); $("ch-streak").textContent = st.s; $("ch-best").textContent = st.b; return st; }
    function chEnd(res) {
      var st = chScore(), old = st.b;
      if (res > 0) { st.s++; st.b = Math.max(st.b, st.s); } else if (res < 0) st.s = 0;
      store.set("md-chin", st); chScore(); chTurn("");
      var rec = res > 0 && st.b > old;
      if (res > 0) { var sk = $("ch-sk"); sk.classList.remove("is-pop"); void sk.offsetWidth; sk.classList.add("is-pop"); }
      var name = "<b>" + esc2(chMaid.n) + "</b>";
      $("ch-msg").innerHTML = res > 0 ? '<span class="--win">WIN!</span> ' + name + "「" + pick(["つよいね〜！ 負けちゃった…", "えーっ！ 患者さま、元気すぎ！", "くやしい〜！ もう一回！"]) + "」"
        : res < 0 ? '<span class="--lose">LOSE…</span> ' + name + "「" + pick(["やった〜！ わたしの勝ち♡", "ふふっ、安静にしててね♡", "今日はわたしがついてるみたい♡"]) + "」"
        : '<span class="--draw">DRAW</span> ' + name + "「引き分け！ 気が合うね♡」";
      chSay(res > 0 ? pick(["くやしい〜！", "うそ〜っ！", "まいりました…"]) : res < 0 ? pick(["やった〜♡", "勝っちゃった♡", "ふふん♡"]) : "引き分け〜！");
      var s = $("ch-stamp");
      s.className = "md-chin__stamp " + (res > 0 ? "--win" : res < 0 ? "--lose" : "--draw") + (rec ? " --rec" : "");
      s.querySelector("b").textContent = res > 0 ? "WIN!" : res < 0 ? "LOSE…" : "DRAW";
      void s.offsetWidth; s.classList.add("is-on");
      setTimeout(chShake, reduce ? 0 : 260);
      if (res > 0) { var r = $("ch-board").getBoundingClientRect(); setTimeout(function () { burst(r.left + r.width / 2, r.top + r.height / 2, 30, 240); }, 300); }
      $("ch-roll").hidden = true; $("ch-again").hidden = false; chBusy = false;
    }
    function maidTurn(you) {
      var tries = 0, g = chGen;
      chTurn("maid");
      (function go() {
        if (g !== chGen) return;
        tries++; $("ch-mrole").textContent = "…"; chSay(tries === 1 ? pick(["えいっ！", "いくよ〜！", "それっ♡"]) : pick(["もう一回！", "次こそ…！", "お願い〜！"]));
        throwDice($("ch-mdice"), function (d) {
          var j = judge(d);
          if (!j && tries < 3) { chPop($("ch-mrole"), "目なし（あと" + (3 - tries) + "回）"); cutIn(NOPT, chMaid.n, "あと" + (3 - tries) + "回", function () { chSay("あれれ…"); setTimeout(go, 450); }); return; }
          j = j || NOPT; chPop($("ch-mrole"), j.n);
          if (j.k === "pin" || j.k === "zoro" || j.k === "shigoro") chSay("やったぁ♡");
          else if (j.k === "hifumi") chSay("ひえぇ…");
          cutIn(j, chMaid.n, "", function () { chEnd(you.v > j.v ? 1 : you.v < j.v ? -1 : 0); });
        });
      })();
    }
    function chRoll() {
      if (chBusy) return; chBusy = true; chTries++; $("ch-roll").disabled = true; $("ch-yrole").textContent = "…";
      chTurn("you"); chSay(pick(["がんばって〜！", "どきどき…", "いい目、出るかな？"]));
      throwDice($("ch-ydice"), function (d) {
        var j = judge(d);
        if (!j && chTries < 3) {
          chPop($("ch-yrole"), "目なし");
          cutIn(NOPT, "患者さま", "あと" + (3 - chTries) + "回", function () { $("ch-roll").disabled = false; $("ch-roll").querySelector("span").textContent = "もう一回振る（あと" + (3 - chTries) + "回）"; chBusy = false; });
          return;
        }
        j = j || NOPT; chYou = j; chPop($("ch-yrole"), j.n);
        if (j.k === "pin" || j.k === "zoro") chSay("うそっ…！？");
        else if (j.k === "shigoro") chSay("つよい…！");
        else if (j.k === "hifumi") chSay("あらら〜♡");
        cutIn(j, "患者さま", "", function () {
          if (j.v < 0) return chEnd(-1);
          $("ch-msg").innerHTML = "<b>" + esc2(chMaid.n) + "</b>「つぎはわたしの番だね…えいっ！」";
          setTimeout(function () { maidTurn(j); }, 350);
        });
      });
    }
    function chinchiro() {
      if (!chin) {
        chin = makeModal("md-chin", "ナースと検温ゲーム",
          '<p class="md-stamp__label mono">TEMPERATURE BATTLE</p><h2 class="md-omk__title">ナースと検温ゲーム</h2>' +
          '<p class="md-chin__score mono"><span id="ch-sk">WIN STREAK <b id="ch-streak">0</b><em>+1</em></span><span>BEST <b id="ch-best">0</b></span></p>' +
          '<div class="md-chin__board" id="ch-board">' +
          '<div class="md-chin__side" id="ch-mside"><span class="md-chin__turn mono">NURSE TURN</span><figure class="md-chin__ava" id="ch-ava"><img id="ch-img" src="" alt=""></figure><p class="md-chin__say" id="ch-say" aria-live="polite"></p><p class="md-chin__name" id="ch-name"></p><div class="md-chin__bowl"><div class="md-chin__dice" id="ch-mdice"></div></div><p class="md-chin__role" id="ch-mrole">—</p></div>' +
          '<p class="md-chin__vs mono">VS</p>' +
          '<div class="md-chin__side" id="ch-yside"><span class="md-chin__turn mono">YOUR TURN</span><figure class="md-chin__ava --you"><span class="mono">YOU</span></figure><p class="md-chin__name">患者さま</p><div class="md-chin__bowl"><div class="md-chin__dice" id="ch-ydice"></div></div><p class="md-chin__role" id="ch-yrole">—</p></div>' +
          '<div class="md-chin__cut" id="ch-cut" aria-hidden="true"><i class="md-chin__rays"></i><span class="md-chin__cutWho"></span><b class="md-chin__cutJp"></b><span class="md-chin__cutEn mono"></span></div>' +
          '<div class="md-chin__stamp" id="ch-stamp" aria-hidden="true"><b></b><small class="mono">NEW RECORD!</small></div>' +
          "</div>" +
          '<p class="md-chin__msg" id="ch-msg" aria-live="polite"></p>' +
          '<div class="md-omk__btns"><button class="btn" type="button" id="ch-roll"><span>サイコロを振る</span><i>' + ARROW + '</i></button><button class="btn" type="button" id="ch-again" hidden><span>もう一勝負</span><i>' + ARROW + '</i></button><button class="btn" type="button" id="ch-change"><span>ナースを変える</span><i>' + ARROW + "</i></button></div>" +
          '<p class="md-chin__rule">サイコロ3つで“体温”をはかって、ナースと勝負！<br>役の強さ：ピンゾロ ＞ ゾロ目 ＞ シゴロ ＞ 目あり（6〜1）＞ 目なし ＞ ヒフミ<br>役が出るまで3回まで振れます。</p>' +
          '<div class="md-chin__flash" id="ch-flash" aria-hidden="true"></div>');
        $("ch-roll").addEventListener("click", chRoll);
        $("ch-again").addEventListener("click", function () { chReset(); });
        $("ch-change").addEventListener("click", function () { if (chBusy) return; chSetMaid(); chReset(); });
      }
      chSetMaid(); chScore(); openModal2(chin); chReset();
    }
    function chSetMaid() {
      var c = pick(CAST); chMaid = c;
      $("ch-img").src = "img/cast/s/" + c.id + ".webp"; $("ch-img").alt = c.n; $("ch-ava").style.setProperty("--c", c.c);
      $("ch-name").textContent = c.n;
    }

    /* ---------- 3. お薬（錠剤）にお絵描き ---------- */
    var omu = null, cv, cx2, drawing = false, inkLen = 0, lastPt = null, omuMaid = null;
    function omuBase() {
      var W = cv.width, H = cv.height, s = W / 520;
      cx2.setTransform(1, 0, 0, 1, 0, 0); cx2.clearRect(0, 0, W, H);
      var g = cx2.createRadialGradient(W / 2, H * .52, W * .1, W / 2, H * .52, W * .48); g.addColorStop(0, "#ffffff"); g.addColorStop(.85, "#f6f2fb"); g.addColorStop(1, "#e3dcf2");
      cx2.fillStyle = g; cx2.beginPath(); cx2.ellipse(W / 2, H * .52, W * .47, H * .44, 0, 0, Math.PI * 2); cx2.fill();
      cx2.strokeStyle = "#ffb3d1"; cx2.lineWidth = 6 * s; cx2.setLineDash([2 * s, 12 * s]); cx2.lineCap = "round"; cx2.beginPath(); cx2.ellipse(W / 2, H * .52, W * .43, H * .4, 0, 0, Math.PI * 2); cx2.stroke(); cx2.setLineDash([]);
      cx2.fillStyle = "rgba(46,42,58,.10)"; cx2.beginPath(); cx2.ellipse(W / 2, H * .58, W * .33, H * .24, 0, 0, Math.PI * 2); cx2.fill();
      var e = cx2.createRadialGradient(W * .44, H * .42, W * .02, W / 2, H * .52, W * .36); e.addColorStop(0, "#fff6c2"); e.addColorStop(.5, "#ffd76a"); e.addColorStop(1, "#f2b33d");
      cx2.fillStyle = e; cx2.beginPath(); cx2.ellipse(W / 2, H * .53, W * .33, H * .24, -.04, 0, Math.PI * 2); cx2.fill();
      cx2.fillStyle = "rgba(255,255,255,.55)"; cx2.beginPath(); cx2.ellipse(W * .41, H * .43, W * .1, H * .035, -.3, 0, Math.PI * 2); cx2.fill();
      inkLen = 0;
    }
    function omuPt(e) { var r = cv.getBoundingClientRect(); return { x: (e.clientX - r.left) * cv.width / r.width, y: (e.clientY - r.top) * cv.height / r.height }; }
    function omuLine(a, b) {
      var s = cv.width / 520;
      cx2.lineCap = "round"; cx2.lineJoin = "round";
      cx2.strokeStyle = "#c8102e"; cx2.lineWidth = 11 * s; cx2.beginPath(); cx2.moveTo(a.x, a.y); cx2.lineTo(b.x, b.y); cx2.stroke();
      cx2.strokeStyle = "rgba(255,255,255,.35)"; cx2.lineWidth = 3 * s; cx2.beginPath(); cx2.moveTo(a.x - 2 * s, a.y - 2 * s); cx2.lineTo(b.x - 2 * s, b.y - 2 * s); cx2.stroke();
      inkLen += Math.hypot(b.x - a.x, b.y - a.y) / s;
    }
    function omurice() {
      if (!omu) {
        omu = makeModal("md-omu", "お薬にお絵描き",
          '<p class="md-stamp__label mono">TABLET DRAWING</p><h2 class="md-omk__title">お薬にお絵描き</h2>' +
          '<div class="md-omu__host"><figure class="md-omu__ava" id="omu-ava"><img id="omu-ava-img" src="" alt=""></figure><p class="md-omu__lead" id="omu-lead"></p></div>' +
          '<div class="md-omu__stage"><canvas id="omu-cv" width="1040" height="800" aria-label="大きな錠剤（指やマウスでシロップを描けます）"></canvas><div class="md-omu__fx" id="omu-fx" aria-hidden="true"><span class="md-omu__fxava" id="omu-fxava"><img src="" alt=""></span></div></div>' +
          '<div class="md-omu__res" id="omu-res" hidden><p class="md-omu__score"><span class="mono">LOVE</span><b id="omu-pt">0</b><small>%</small><em id="omu-rank">S</em></p><p class="md-omu__cmt" id="omu-cmt"></p>' +
          '<figure class="md-omu__img"><img id="omu-img" alt="お絵描きしたお薬"><figcaption>画像を長押し（右クリック）でも保存できます</figcaption></figure></div>' +
          '<div class="md-omk__btns"><button class="btn" type="button" id="omu-clear"><span>消して描きなおす</span><i>' + ARROW + '</i></button><button class="btn --ink" type="button" id="omu-done"><span>はやくよくなあれ♡</span><i>' + ARROW + '</i></button><a class="btn" id="omu-save" download="succubusclinic-medicine.png" hidden><span>画像を保存</span><i>' + ARROW + "</i></a></div>");
        cv = $("omu-cv"); cx2 = cv.getContext("2d");
        cv.addEventListener("pointerdown", function (e) { if (!$("omu-res").hidden) return; drawing = true; lastPt = omuPt(e); cv.setPointerCapture(e.pointerId); omuLine(lastPt, { x: lastPt.x + .1, y: lastPt.y + .1 }); });
        cv.addEventListener("pointermove", function (e) { if (!drawing) return; var p = omuPt(e); omuLine(lastPt, p); lastPt = p; });
        ["pointerup", "pointercancel"].forEach(function (ev) { cv.addEventListener(ev, function () { drawing = false; }); });
        $("omu-clear").addEventListener("click", omuStart);
        $("omu-done").addEventListener("click", function () {
          if (inkLen < 60) { say("シロップで何か描いてね♡"); return; }
          var pt = Math.min(100, Math.round(72 + Math.min(inkLen, 2400) / 2400 * 20 + Math.random() * 8)), rank = pt >= 95 ? "S" : pt >= 85 ? "A" : "B";
          $("omu-pt").textContent = pt; $("omu-rank").textContent = rank;
          $("omu-cmt").innerHTML = '<span class="md-omu__mini" style="--c:' + omuMaid.c + '"><img src="img/cast/s/' + omuMaid.id + '.webp" alt=""></span><span><b>' + esc2(omuMaid.n) + "</b>「" + pick(["とってもじょうず！ よく効くおまじない、かけちゃうね♡", "かわいい〜！ 飲むのもったいないね♡", "愛情たっぷり！ はやくよくなあれ♡", "すてきな絵！ 診察室に飾りたいくらい♡"]) + "」</span>";
          var url = omuExport(); $("omu-img").src = url; $("omu-save").href = url;
          $("omu-res").hidden = false; $("omu-save").hidden = false; $("omu-done").hidden = true; $("omu-clear").querySelector("span").textContent = "もう一錠描く";
          var fx = $("omu-fx"); fx.classList.remove("is-on"); void fx.offsetWidth; fx.classList.add("is-on");
          var r = cv.getBoundingClientRect(); burst(r.left + r.width / 2, r.top + r.height / 2, 36, 220);
        });
      }
      omuStart(); openModal2(omu);
    }
    // 保存する画像：右下に、おまじないをかけてくれたナースの〇アイコンと名前を入れる
    function omuExport() {
      try {
        var ex = document.createElement("canvas"), g = ex.getContext("2d"), W = cv.width, H = cv.height, s = W / 520, im = $("omu-ava-img");
        ex.width = W; ex.height = H; g.drawImage(cv, 0, 0);
        if (im.complete && im.naturalWidth) {
          var r = 40 * s, x = W - r - 20 * s, y = H - r - 18 * s, H0 = 2 * r * im.naturalHeight / im.naturalWidth;
          g.save(); g.shadowColor = "rgba(46,42,58,.35)"; g.shadowBlur = 14 * s; g.shadowOffsetY = 5 * s;
          g.fillStyle = "#fff"; g.beginPath(); g.arc(x, y, r + 5 * s, 0, Math.PI * 2); g.fill(); g.restore();
          g.save(); g.beginPath(); g.arc(x, y, r, 0, Math.PI * 2); g.clip();
          var gr = g.createRadialGradient(x, y - r * .4, r * .1, x, y, r); gr.addColorStop(0, "#fff"); gr.addColorStop(1, omuMaid.c || "#ffe3ef");
          g.fillStyle = gr; g.fillRect(x - r, y - r, 2 * r, 2 * r);
          g.drawImage(im, x - 1.5 * r, y - r - .06 * H0, 3 * r, 1.5 * H0); g.restore();
          g.font = "700 " + 15 * s + "px 'IBM Plex Sans JP', sans-serif"; g.textBaseline = "middle";
          var t = "♡ " + omuMaid.n, tw = g.measureText(t).width, px = x - r - 14 * s - tw - 24 * s, ph = 30 * s;
          g.fillStyle = "rgba(255,255,255,.94)"; g.beginPath();
          if (g.roundRect) g.roundRect(px, y - ph / 2, tw + 24 * s, ph, ph / 2); else g.rect(px, y - ph / 2, tw + 24 * s, ph);
          g.fill(); g.fillStyle = "#f472a8"; g.fillText(t, px + 12 * s, y + 1 * s);
        }
        return ex.toDataURL("image/png");
      } catch (err) { return cv.toDataURL("image/png"); }
    }
    function omuStart() {
      omuMaid = pick(CAST); omuBase();
      var src = "img/cast/s/" + omuMaid.id + ".webp";
      $("omu-ava-img").src = src; $("omu-ava-img").alt = omuMaid.n; $("omu-ava").style.setProperty("--c", omuMaid.c);
      var fa = $("omu-fxava"); fa.style.setProperty("--c", omuMaid.c); fa.querySelector("img").src = src; $("omu-res").hidden = true; $("omu-save").hidden = true; $("omu-done").hidden = false;
      $("omu-clear").querySelector("span").textContent = "消して描きなおす"; $("omu-fx").classList.remove("is-on");
      $("omu-lead").innerHTML = "<b>" + esc2(omuMaid.n) + "</b>「シロップで、すきな絵を描いてね♡ 描けたら、元気になるおまじないをかけちゃいます！」";
    }

    /* ---------- 4. ナース大行進 ---------- */
    var paradeEl = null, pTimers = [];
    function endParade() { if (!paradeEl) return; pTimers.forEach(clearTimeout); pTimers = []; var el = paradeEl; paradeEl = null; el.classList.add("is-out"); setTimeout(function () { el.remove(); }, 500); }
    function parade() {
      if (paradeEl || !CAST.length) return;
      if (openM) closeModal2(openM);
      paradeEl = document.createElement("div"); paradeEl.className = "md-parade";
      paradeEl.innerHTML = '<p class="md-parade__banner"><span class="mono">IRASSHAIMASE</span><b>ナース大行進</b><small>ナースを押すとカルテが見られます</small></p><button class="md-parade__close" type="button" aria-label="大行進を終わる">' + CLOSE + "</button>";
      document.body.appendChild(paradeEl);
      paradeEl.querySelector(".md-parade__close").addEventListener("click", endParade);
      var list = shuffle(CAST), gap = reduce ? 0 : 300, dur = 9000;
      list.forEach(function (c, k) {
        pTimers.push(setTimeout(function () {
          if (!paradeEl) return;
          var lane = k % 3, b = document.createElement("button"); b.type = "button"; b.className = "md-pm --l" + lane;
          b.style.cssText = "--c:" + c.c + ";--c2:" + c.c2 + ";--d:" + (dur + (k % 5) * 400) + "ms";
          b.setAttribute("aria-label", c.n + "のカルテを見る");
          b.innerHTML = '<span class="md-pm__ph"><img src="img/cast/s/' + c.id + '.webp" alt=""></span><span class="md-pm__nm">' + esc2(c.n) + "</span>";
          b.addEventListener("click", function () { endParade(); goMaid(c.id); });
          b.addEventListener("animationend", function (e) { if (e.animationName === "pmWalk") b.remove(); });
          paradeEl.appendChild(b);
        }, k * gap));
      });
      pTimers.push(setTimeout(endParade, list.length * gap + dur + 2200));
      say("いらっしゃいませ、患者さま♡ ナース大行進！");
    }

    /* ---------- 5. 開院モード（診療日の 21:50〜23:10 だけ。特別診療・休診も反映） ---------- */
    var titleBackup = null, openBadge = null;
    function nowOpen() { var n = Date.now(), l = openList(n, 1); return l.length > 0 && l[0] <= n; }
    function checkOpen() {
      var on = nowOpen() || openPreview;
      if (on === root.classList.contains("is-open-now")) return;
      root.classList.toggle("is-open-now", on);
      if (!openBadge) {
        openBadge = document.createElement("a"); openBadge.className = "md-open"; openBadge.href = "schedule.html";
        openBadge.innerHTML = "<i></i><b>NOW OPEN</b><span>ただいま開院中</span>";
        var hd = document.querySelector(".header"), ref = document.querySelector(".h-join") || document.querySelector(".h-x");
        if (hd) hd.insertBefore(openBadge, ref);
      }
      var t = $("hero-title"); if (!t) return;
      var lp = t.querySelector(".lines--pc"), ls = t.querySelector(".lines--sp");
      if (on) {
        titleBackup = titleBackup || { pc: lp.innerHTML, sp: ls.innerHTML, label: t.getAttribute("aria-label") };
        lp.innerHTML = '<span class="fit">CLINIC <span class="g">NOW OPEN</span><i class="hero__cur"></i></span>';
        ls.innerHTML = '<span class="fit">CLINIC</span><span class="fit"><span class="g">NOW OPEN</span><i class="hero__cur"></i></span>';
        t.setAttribute("aria-label", "いらっしゃいませ、患者さま（ただいま開院中）");
      } else if (titleBackup) { lp.innerHTML = titleBackup.pc; ls.innerHTML = titleBackup.sp; t.setAttribute("aria-label", titleBackup.label); }
      fitTitle(); typeTitle();
    }
    onReady(checkOpen); setInterval(checkOpen, 30000);

    /* ---------- ひみつのことば・スマホ用のしかけ ---------- */
    var WORDS = { succubus: terminal, kenon: chinchiro, kusuri: omurice, parade: parade };
    var typed = "";
    addEventListener("keydown", function (e) {
      var t = e.target; if (t && (t.isContentEditable || /^(input|textarea|select)$/i.test(t.tagName))) return;
      if (e.ctrlKey || e.metaKey || e.altKey || !e.key || e.key.length !== 1) return;
      typed = (typed + e.key.toLowerCase()).slice(-12);
      for (var w in WORDS) if (typed.slice(-w.length) === w) { typed = ""; WORDS[w](); break; }
    });
    function onTaps(el, n, fn) { if (!el) return; var ts = []; el.addEventListener("click", function () { var now = Date.now(); ts = ts.filter(function (x) { return now - x < 1800; }); ts.push(now); if (ts.length >= n) { ts = []; fn(); } }); }
    function onHold(el, ms, fn) {
      if (!el) return; var tm, fired = false;
      el.classList.add("md-holdable");
      el.addEventListener("pointerdown", function () { fired = false; clearTimeout(tm); tm = setTimeout(function () { fired = true; fn(); }, ms); });
      ["pointerup", "pointerleave", "pointercancel"].forEach(function (ev) { el.addEventListener(ev, function () { clearTimeout(tm); }); });
      el.addEventListener("click", function (e) { if (fired) { e.preventDefault(); e.stopPropagation(); fired = false; } }, true);
      el.addEventListener("contextmenu", function (e) { if (fired || e.pointerType !== "mouse") e.preventDefault(); });
    }
    onHold(document.querySelector(".h-logo"), 800, terminal);
    onTaps(document.querySelector(".rota"), 5, chinchiro);
    [].forEach.call(document.querySelectorAll(".menu__list li"), function (li) { var t = li.querySelector(".dish__title"); if (t && t.textContent.trim() === "おえかき♡ハート錠") onHold(li, 700, omurice); });
    var fl = document.querySelector(".f-logo");
    if (fl) { var fts = [], ftm; fl.addEventListener("click", function (e) { e.preventDefault(); var now = Date.now(); fts = fts.filter(function (x) { return now - x < 1500; }); fts.push(now); clearTimeout(ftm); if (fts.length >= 5) { fts = []; parade(); return; } ftm = setTimeout(function () { if (fts.length === 1) location.href = fl.href; }, 420); }); }

    drawBadge(); applyVip(); placeHeart(); bindOmikuji();
  })();

  /* ---------- 出てくる動き＋見出しデコード ---------- */
  if ("IntersectionObserver" in window && !reduce) {
    var io = new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add("is-in"); var t = e.target.querySelector(".sec-head__en, .faq__label b, .sub-h b"); if (t) scramble(t, 800); io.unobserve(e.target); } }); }, { rootMargin: "0px 0px -6% 0px" });
    document.querySelectorAll(".rv").forEach(function (el) { io.observe(el); });
  } else document.querySelectorAll(".rv").forEach(function (el) { el.classList.add("is-in"); });

  /* ---------- 画面遷移：サイト内のページへ移るとき、ロード画面と同じ色の帯で覆ってから移動する ----------
     前のページから来たときは <head> のスクリプトが html に pt-arrive を付けて覆った状態で始まるので、ここで帯を抜く */
  var pt = $("pt"), arrived = root.classList.contains("pt-arrive");
  if (pt) {
    if (arrived) {
      var revealed = false, reveal = function () {
        if (revealed) return; revealed = true;
        pt.classList.add("is-reveal");
        setTimeout(function () { root.classList.remove("pt-arrive"); pt.classList.remove("is-reveal"); }, 900);
      };
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { setTimeout(reveal, 60); });
      setTimeout(reveal, 500);
    }
    var leaving = false, samePage = function (u) { return u.pathname.replace(/index\.html$/, "") === location.pathname.replace(/index\.html$/, ""); };
    document.addEventListener("click", function (e) {
      if (reduce || leaving || e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
      var a = e.target.closest && e.target.closest("a[href]");
      if (!a || (a.target && a.target !== "_self") || a.hasAttribute("download")) return;
      var url = new URL(a.href, location.href);
      if (url.origin !== location.origin || samePage(url) || !/(\.html|\/)$/.test(url.pathname) || /\/admin\//.test(url.pathname)) return;
      e.preventDefault(); leaving = true;
      root.classList.remove("pt-arrive"); pt.classList.remove("is-reveal"); pt.classList.add("is-cover");
      try { sessionStorage.setItem("md-pt", "1"); } catch (err) {}
      setTimeout(function () { location.href = url.href; }, 760);
    });
    /* 戻るボタンでこのページに戻ってきたとき（前の状態のまま表示される場合）は、覆いを外す */
    addEventListener("pageshow", function (e) { if (e.persisted) { leaving = false; pt.classList.remove("is-cover", "is-reveal"); root.classList.remove("pt-arrive"); } });
  }

  /* ---------- 起動演出（初回ロード） ---------- */
  var loader = $("loader");
  /* 起動演出は最初に開いたときだけ。サイト内の画面遷移でトップに来たときは、帯が抜ける演出だけにする */
  if (!loader || reduce || arrived) { if (loader) loader.classList.add("is-gone"); if (arrived) setTimeout(setReady, 450); else setReady(); }
  else (function () {
    var hearts = $("ld-hearts"), cols = ["#f953c2", "#c8107f", "#00abfc", "#f953c2", "#7fd5fe"];
    for (var h = 0; h < 14; h++) {
      var hi = document.createElement("i");
      hi.style.cssText = "left:" + ((h * 37 + 7) % 100) + "%;--c:" + cols[h % cols.length] + ";--s:" + (.35 + (h * 13 % 10) / 14) + ";--d:" + (3.2 + (h * 7 % 5) * .55) + "s;--dl:" + (-(h * 0.43) % 4).toFixed(2) + "s;--r:" + ((h * 23 % 40) - 20) + "deg";
      hearts.appendChild(hi);
    }
    var fill = $("ld-fill"), chibi = $("ld-chibi"), num = $("ld-pct"), logs = loader.querySelectorAll("#ld-log li");
    var STEPS = [1, 24, 50, 74, 97], pct = 0, start = performance.now(), MIN = 3900, MAX = 6500, loaded = document.readyState === "complete", state = 0;
    addEventListener("load", function () { loaded = true; });
    var render = function () {
      fill.style.width = pct + "%"; chibi.style.left = pct + "%";
      num.textContent = String(Math.round(pct)).padStart(3, "0");
      logs.forEach(function (li, k) { if (pct >= STEPS[k]) li.classList.add("is-show"); });
    };
    var out = function () {
      if (state > 1) return; state = 2;
      loader.classList.add("is-out");
      setTimeout(function () { loader.classList.add("is-clear"); setReady(); }, 720);
      setTimeout(function () { loader.classList.add("is-gone"); }, 1500);
    };
    var finish = function (fast) {
      if (state) return; state = 1; pct = 100; render();
      loader.classList.add("is-done");
      setTimeout(out, fast ? 250 : 650);
    };
    loader.addEventListener("click", function () { if (!state) finish(true); else out(); });
    loader.classList.add("is-on");
    (function step(now) {
      if (state) return;
      var t = now - start, tp = Math.min(1, t / MIN), target = (1 - Math.pow(1 - tp, 2.4)) * 100;
      if (!loaded && t < MAX) target = Math.min(target, 92);
      pct += (target - pct) * 0.16; if (target >= 100 && pct > 99.4) pct = 100;
      render();
      if (pct >= 100) setTimeout(finish, 180); else requestAnimationFrame(step);
    })(start);
  })();

  /* ---------- トップ：ナースの壁（見る人を囲むように内側へ曲がる立体のカルーセル） ----------
     平らな写真のパネルを、見る人を軸にした円弧に内向きに並べる（中央がいちばん奥で小さく、左右ほど手前で大きい）。
     円弧は 1 周ぶんのスロット（S 個）で閉じていて、回した量 p（パネル何枚ぶんかの連続値。中央が p 番目）に対し、
     スロット i には k = i + S×round((p − i)/S) 番目のナース（MD_CAST[k を人数で割った余り]）を出す。
     見えるのは軸より奥（±90°以内）だけ。差し替えは見る人の後ろ側で起きるので見えない。
     ドラッグ（つかんだ点がポインタの下にとどまる。離すと惰性→中央に吸いつく）・横ホイール・前へ／次へ・矢印キー・スペースで一時停止。
     自動の動きは、マウスを乗せている間・キーボードの focus が中にある間・操作の直後・画面外・裏のタブ・一時停止中は止める */
  var RING = {
    aspect: 0.67,       // パネルの幅÷高さ（0.67＝縦長 2:3）。写真はこの形に切り抜く
    size: 0.74,         // 中央のパネルの高さが、題名より上の舞台（.ring__view。高さは CSS）の高さに占める割合
    curvature: 0.62,    // 壁の曲がりの強さ（0 平ら〜1 きつい筒）。となりとの角度 ≒ curvature×40°。1 周で閉じるよう、スロット数＝360÷その角度を丸めた数
    distance: 4.4,      // 見る人から壁までの距離（中央のパネルの高さ何枚ぶんか）。perspective になる。小さいほど遠近が強い
    tilt: 0,            // 見上げ・見下ろしの角度（度。0 は水平）
    gap: 13,            // パネルのすき間（中央のパネルの位置で。PC の px。スマホは rem で縮む）
    radius: 17,         // パネルの角の丸み（同上）
    reflection: 0.23,   // 床の映りこみの強さ（0 で無し）
    dim: 0.35,          // 左右のはしへ向かって白くかすませる強さ（いちばん外側でこの値）
    autoplay: "drift",  // "drift" ゆっくり回り続ける／"step" interval 秒ごとに 1 枚／"off" 自動で動かさない
    speed: 0.16,        // drift の速さ（1 秒あたりのパネル数）
    interval: 5.5,      // step の間隔（秒）
    inertia: 0.72,      // はじいたときにどれだけ流れるか（0〜1）
    snap: true,         // 止まるとき、パネルが中央に来るように吸いつく
    pauseOnHover: true  // マウスを乗せている間は自動の動きを止める
  };
  var ring = $("ring"), RC = window.MD_CAST || [];
  if (ring && RC.length) (function () {
    var view = $("ring-view"), spin = $("ring-spin"), now = $("ring-now"), count = $("ring-count"), playBtn = $("ring-play");
    var N = RC.length, S = Math.max(6, Math.round(360 / (Math.max(0.05, RING.curvature) * 40))), A = 360 / S, QUAR = S / 4, slots = [], unit = 200;
    var p = 0, vel = 0, target = null, raf = 0, last = 0, front = null, ptr = null, drag = false, moved = false, wheeling = false, wheelT, stepT;
    var userPaused = reduce || RING.autoplay === "off", hover = false, focused = false, inView = false, seen = false, idleUntil = 0, idleT;
    var mod = function (a, b) { return ((a % b) + b) % b; };
    var noOf = function (d) { return "No." + d.id.replace(/\D/g, ""); };
    ring.hidden = false;
    if (userPaused) playBtn.hidden = true;

    // 設定から寸法を出して CSS の変数に入れる（舞台の高さが変わったら呼び直す）
    function layout() {
      var rem = parseFloat(getComputedStyle(document.documentElement).fontSize) || 1;
      var h = view.clientHeight * RING.size, w = h * RING.aspect, gap = RING.gap * rem;
      var r = (w + gap) / (2 * Math.tan(A / 2 * Math.PI / 180));
      unit = w + gap;                                             // 中央のパネル 1 枚ぶんの横の長さ（px）
      [["--w", w], ["--h", h], ["--r", r], ["--persp", RING.distance * h], ["--rad", RING.radius * rem]].forEach(function (v) { ring.style.setProperty(v[0], v[1].toFixed(1) + "px"); });
      ring.style.setProperty("--a", A + "deg"); ring.style.setProperty("--tilt", RING.tilt + "deg"); ring.style.setProperty("--ref", RING.reflection);
    }
    function build() {
      for (var i = 0; i < S; i++) {
        var a = document.createElement("a");
        a.className = "ring__card"; a.draggable = false; a.style.setProperty("--i", i);
        a.innerHTML = '<span class="ring__ph"><img alt="" width="400" height="601" decoding="async" draggable="false"></span>' +
          '<span class="ring__ref" aria-hidden="true"><img alt="" width="400" height="601" decoding="async" draggable="false"></span>';
        spin.appendChild(a);
        var im = a.querySelectorAll("img");
        slots.push({ el: a, i: i, k: null, img: im[0], ref: im[1] });
      }
      render();
    }
    // スロットに k 番目のナースを入れる（写真は、見えている位置にあり、壁が画面の近くに来てから読みこむ）
    function fill(s, k) {
      var d = RC[mod(k, N)];
      s.k = k; s.want = "img/cast/s/" + d.id + ".webp";
      s.el.href = "nurses.html#" + d.id;
      s.el.setAttribute("aria-label", noOf(d) + " " + d.n);
      s.el.style.setProperty("--c", d.c);
    }
    function render() {
      spin.style.setProperty("--rot", (p * A).toFixed(3) + "deg");
      slots.forEach(function (s) {
        var k = s.i + S * Math.round((p - s.i) / S);
        if (k !== s.k) fill(s, k);
        var r = Math.abs(k - p), vis = r < QUAR - 0.05;            // 中央から何枚ぶん離れているか。±90° より手前（見る人の後ろ）は出さない
        s.el.style.visibility = vis ? "" : "hidden";
        if (!vis) return;
        s.el.style.setProperty("--hz", (RING.dim * Math.min(1, r / Math.max(1, QUAR - 0.75))).toFixed(3));   // 左右ほど白くかすむ
        if (seen && s.src !== s.want) { s.src = s.want; s.img.src = s.ref.src = s.want; }
      });
      var f = Math.round(p);
      if (f !== front) setFront(f);
    }
    // 中央のパネルだけをリンクとして読み上げ・focus できるようにし、下に名前と番号を出す
    function setFront(f) {
      var had = document.activeElement && document.activeElement.classList.contains("ring__card"), d = RC[mod(f, N)];
      front = f;
      slots.forEach(function (s) {
        var on = s.k === f;
        s.el.classList.toggle("is-front", on);
        if (on) { s.el.removeAttribute("aria-hidden"); s.el.removeAttribute("tabindex"); if (had) s.el.focus({ preventScroll: true }); }
        else { s.el.setAttribute("aria-hidden", "true"); s.el.tabIndex = -1; }
      });
      now.innerHTML = '<span class="ring__now-nm">' + esc(d.n) + "</span>" + (d.t ? '<span class="ring__now-t">' + esc(d.t) + "</span>" : "");
      count.innerHTML = "<b>" + pad(mod(f, N) + 1) + "</b> / " + pad(N);
    }

    function autoOn() {
      return !userPaused && !(hover && RING.pauseOnHover) && !focused && !ptr && !wheeling && inView && !document.hidden && performance.now() >= idleUntil;
    }
    function kick() { if (!raf) { last = performance.now(); raf = requestAnimationFrame(tick); } }
    // step のとき：interval 秒ごとに 1 枚（rAF は動いている間だけ）
    function stepTimer(on) {
      clearTimeout(stepT);
      if (on && RING.autoplay === "step") stepT = setTimeout(function () { if (autoOn()) goTo(Math.round(p) + 1); stepTimer(autoOn()); }, RING.interval * 1000);
    }
    // 止める条件が変わったとき：止まるなら、いちばん近いパネルへ吸いつく
    function update() {
      var on = autoOn();
      now.setAttribute("aria-live", on ? "off" : "polite");      // 自動で動いている間は読み上げない
      stepTimer(on);
      if (!on && target === null && !drag && !wheeling && RING.snap) target = Math.round(p);
      if (reduce && target !== null) { p = target; target = null; vel = 0; render(); return; }
      kick();
    }
    function tick(t) {
      var dt = Math.min(0.05, (t - last) / 1000), go = false, drift = RING.autoplay === "drift";
      last = t; raf = 0;
      if (!drag) {
        if (target !== null) {
          // 臨界減衰のばねで target へ（離したときの勢いを vel に持ちこむ）
          var w = 9;
          vel += (-w * w * (p - target) - 2 * w * vel) * dt; p += vel * dt;
          if (Math.abs(p - target) < 0.002 && Math.abs(vel) < 0.02) { p = target; vel = 0; target = null; go = drift && autoOn(); } else go = true;
        } else if (drift && autoOn()) { p += RING.speed * dt; vel = RING.speed; go = true; }
      }
      render();
      if (go) raf = requestAnimationFrame(tick);
    }
    function goTo(k) {
      target = k;
      if (reduce) { p = k; target = null; vel = 0; render(); } else kick();
    }
    // 操作の直後は 3 秒ほど自動回転を待つ
    function poke() { idleUntil = performance.now() + 3000; clearTimeout(idleT); idleT = setTimeout(update, 3050); update(); }
    function step(d) { goTo((target !== null ? target : Math.round(p)) + d); poke(); }

    /* ドラッグ（マウス・タッチ）。縦のスクロールはブラウザにまかせる（CSS の touch-action: pan-y） */
    view.addEventListener("pointerdown", function (e) {
      if (e.button !== 0 || ptr) return;
      moved = false; ptr = { id: e.pointerId, x: e.clientX, p: p, w: unit, hist: [] };
      update();
    });
    view.addEventListener("pointermove", function (e) {
      if (!ptr || e.pointerId !== ptr.id) return;
      var dx = e.clientX - ptr.x;
      if (!drag) {
        if (Math.abs(dx) < 6) return;
        drag = moved = true; target = null; vel = 0; ptr.x = e.clientX; ptr.p = p; dx = 0;
        view.classList.add("is-drag");
        try { view.setPointerCapture(e.pointerId); } catch (er) {}
      }
      p = ptr.p - dx / ptr.w;
      ptr.hist.push([e.timeStamp, p]);
      while (ptr.hist.length > 2 && e.timeStamp - ptr.hist[0][0] > 100) ptr.hist.shift();
      render();
    });
    function release(e) {
      if (!ptr || e.pointerId !== ptr.id) return;
      if (drag) {
        var h = ptr.hist, a = h[0], b = h[h.length - 1], v = 0;
        if (a && b[0] > a[0] && e.timeStamp - b[0] < 80) v = (b[1] - a[1]) / (b[0] - a[0]) * 1000;   // カード何枚／秒
        v = Math.max(-10, Math.min(10, v));
        drag = false; view.classList.remove("is-drag");
        var to = reduce ? p : p + v * (0.1 + 0.6 * RING.inertia);  // inertia が大きいほど遠くまで流れる
        if (!reduce) vel = v;
        goTo(RING.snap ? Math.round(to) : to);
        setTimeout(function () { moved = false; }, 60);
        ptr = null; poke(); return;
      }
      ptr = null; update();
    }
    view.addEventListener("pointerup", release);
    view.addEventListener("pointercancel", release);
    view.addEventListener("dragstart", function (e) { e.preventDefault(); });
    // 横方向のホイール（トラックパッドの左右）だけで回す。縦のホイールはページのスクロールにまかせる
    view.addEventListener("wheel", function (e) {
      if (Math.abs(e.deltaX) <= Math.abs(e.deltaY)) return;
      e.preventDefault();
      if (!wheeling) { wheeling = true; target = null; vel = 0; update(); }
      p += (e.deltaMode === 1 ? e.deltaX * 16 : e.deltaX) / unit;
      render(); clearTimeout(wheelT);
      wheelT = setTimeout(function () { wheeling = false; goTo(RING.snap ? Math.round(p) : p); poke(); }, 160);
    }, { passive: false });
    // ドラッグのあとのクリックは無視。中央以外のパネルは、押すとそのパネルが中央へ
    view.addEventListener("click", function (e) {
      if (moved) { e.preventDefault(); e.stopPropagation(); moved = false; return; }
      var a = e.target.closest(".ring__card");
      if (!a || a.classList.contains("is-front")) return;
      e.preventDefault();
      slots.forEach(function (s) { if (s.el === a) goTo(s.k); });
      poke();
    }, true);

    /* ボタン（前へ／次へ／一時停止）と、輪の中に focus があるときのキー（左右の矢印で 1 枚、スペースで一時停止の切り替え。
       ボタンの上のスペースは、そのボタンを押す標準の動きのまま） */
    $("ring-prev").addEventListener("click", function () { step(-1); });
    $("ring-next").addEventListener("click", function () { step(1); });
    ring.addEventListener("keydown", function (e) {
      if (e.key === "ArrowLeft" || e.key === "ArrowRight") { e.preventDefault(); step(e.key === "ArrowLeft" ? -1 : 1); }
      else if (e.key === " " && !e.target.closest("button") && !playBtn.hidden) { e.preventDefault(); playBtn.click(); }
    });
    playBtn.addEventListener("click", function () {
      userPaused = !userPaused;
      playBtn.classList.toggle("is-paused", userPaused);
      playBtn.setAttribute("aria-label", userPaused ? "自動回転を再生" : "自動回転を止める");
      idleUntil = 0; update();
    });
    if (userPaused) playBtn.classList.add("is-paused");

    /* 止める条件：カードの上にマウス／キーボードの focus が中／画面外／裏のタブ */
    view.addEventListener("pointerenter", function (e) { if (e.pointerType === "mouse") { hover = true; update(); } });
    view.addEventListener("pointerleave", function (e) { if (e.pointerType === "mouse") { hover = false; update(); } });
    ring.addEventListener("focusin", function (e) { var v = true; try { v = e.target.matches(":focus-visible"); } catch (er) {} focused = v; update(); });
    ring.addEventListener("focusout", function (e) { if (!ring.contains(e.relatedTarget)) { focused = false; update(); } });
    document.addEventListener("visibilitychange", update);
    if ("IntersectionObserver" in window) {
      new IntersectionObserver(function (es) { inView = es[0].isIntersecting; update(); }).observe(view);
      new IntersectionObserver(function (es, o) {
        if (!es[0].isIntersecting) return;
        seen = true; o.disconnect(); render();
      }, { rootMargin: "400px 0px" }).observe(view);
    } else { inView = seen = true; }
    var rsT;
    addEventListener("resize", function () { clearTimeout(rsT); rsT = setTimeout(function () { layout(); render(); }, 120); });
    layout(); build(); update();
  })();

  /* ---------- 読み込み時 ---------- */
  if ($("hero-title")) {
    fitTitle();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitTitle);
    var rt; addEventListener("resize", function () { clearTimeout(rt); rt = setTimeout(fitTitle, 120); });
    onReady(function () { setTimeout(introTitle, 250); });
  }
  var ph = document.querySelector(".phead__en");
  if (ph) setTimeout(function () { scramble(ph, 800); }, 150);
})();
