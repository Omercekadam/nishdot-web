/*
 * Nishdot — Yılan (stand haftası oyunu)
 * =====================================
 * Kütüphanesiz. Ayarlar ana sayfadaki #oyun bölümünün data-* niteliklerinden
 * okunur (templates/arcade/_section.html).
 *
 * Kurallar sunucuyla uyumlu olmalı (arcade/models.py → MAX_SCORE = 397):
 * 20x20 ızgara, başlangıç uzunluğu 3 → en fazla 397 yem. GRID ya da START_LEN
 * değişirse MAX_SCORE da değişmeli.
 *
 * Akış: Başla → POST basla/ (bilet) → oyun → bitiş → POST bitir/ → tablo güncellenir.
 * Duraklatma yok: sekme gizlenirse oyun biter ve skor keepalive ile gönderilir.
 */
(function () {
    "use strict";

    const root = document.querySelector("[data-arcade]");
    if (!root) return;

    const GRID = 20;
    const START_LEN = 3;
    const BASE_SPEED = 8;      // adım/sn
    const SPEED_STEP = 0.25;   // her yemde eklenen adım/sn
    const MAX_SPEED = 16;
    const SWIPE_MIN = 24;      // px — bu kadar kaymadan yön değişmez
    const MAX_FRAME_MS = 250;  // takılan bir karede yılan ışınlanmasın

    const COLORS = {
        bg: "#09090b",
        grid: "rgba(255, 255, 255, 0.035)",
        head: "#EB596D",
        body: "rgba(235, 89, 109, 0.72)",
        food: "#fecdd3",
        glow: "#EB596D",
    };

    const DIRS = { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] };
    const KEYS = {
        ArrowUp: "up", KeyW: "up",
        ArrowDown: "down", KeyS: "down",
        ArrowLeft: "left", KeyA: "left",
        ArrowRight: "right", KeyD: "right",
    };

    const cfg = root.dataset;
    const $ = (sel) => root.querySelector(sel);
    const canvas = $("#snake-canvas");
    const ctx = canvas.getContext("2d");
    const ui = {
        play: $("#snake-play"),
        start: $("#snake-start"),
        startBtn: $("#snake-start-btn"),
        over: $("#snake-over"),
        final: $("#snake-final"),
        best: $("#snake-best"),
        msg: $("#snake-msg"),
        guest: $("#snake-guest"),
        again: $("#snake-again"),
        score: $("#snake-score"),
        pad: $("#snake-pad"),
        board: $("#arcade-board"),
        rowTpl: $("#arcade-row"),
        me: $("#arcade-me"),
        verify: $("#arcade-verify"),
    };

    let game = null;      // null: hiç oynanmadı; game.over: bitti
    let cell = 0;         // bir hücrenin CSS piksel boyu
    let localBest = 0;    // bu sayfa açıkken en iyi skor (anonim için)
    let starting = false;

    // ---------------------------------------------------------------- çizim

    function resize() {
        const size = canvas.clientWidth;
        const dpr = window.devicePixelRatio || 1;
        canvas.width = Math.round(size * dpr);
        canvas.height = Math.round(size * dpr);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        cell = size / GRID;
        draw();
    }

    function block(x, y, color) {
        const pad = cell * 0.06;
        const s = cell - pad * 2;
        ctx.fillStyle = color;
        if (ctx.roundRect) {
            ctx.beginPath();
            ctx.roundRect(x * cell + pad, y * cell + pad, s, s, s * 0.3);
            ctx.fill();
        } else {
            ctx.fillRect(x * cell + pad, y * cell + pad, s, s);
        }
    }

    function draw() {
        const size = cell * GRID;
        ctx.fillStyle = COLORS.bg;
        ctx.fillRect(0, 0, size, size);

        ctx.strokeStyle = COLORS.grid;
        ctx.lineWidth = 1;
        ctx.beginPath();
        for (let i = 1; i < GRID; i++) {
            ctx.moveTo(i * cell, 0);
            ctx.lineTo(i * cell, size);
            ctx.moveTo(0, i * cell);
            ctx.lineTo(size, i * cell);
        }
        ctx.stroke();

        if (!game) return;

        if (game.food) {
            ctx.save();
            ctx.shadowColor = COLORS.glow;
            ctx.shadowBlur = cell * 0.8;
            ctx.fillStyle = COLORS.food;
            ctx.beginPath();
            ctx.arc((game.food[0] + 0.5) * cell, (game.food[1] + 0.5) * cell, cell * 0.3, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        }

        for (let i = game.snake.length - 1; i >= 0; i--) {
            const p = game.snake[i];
            block(p[0], p[1], i === 0 ? COLORS.head : COLORS.body);
        }
    }

    // ---------------------------------------------------------------- oyun

    function newGame(ticket) {
        const mid = Math.floor(GRID / 2);
        const snake = [];
        for (let i = 0; i < START_LEN; i++) snake.push([mid - i, mid]);   // sağa bakar
        game = {
            snake,
            dir: "right",
            queue: [],          // tamponlanmış yön değişiklikleri (en fazla 2)
            food: null,
            score: 0,
            speed: BASE_SPEED,
            acc: 0,
            last: 0,
            startedAt: performance.now(),
            ticket,
            over: false,
        };
        game.food = placeFood();
    }

    function placeFood() {
        const taken = new Set(game.snake.map((p) => p[0] * GRID + p[1]));
        const free = [];
        for (let x = 0; x < GRID; x++) {
            for (let y = 0; y < GRID; y++) {
                if (!taken.has(x * GRID + y)) free.push([x, y]);
            }
        }
        return free.length ? free[Math.floor(Math.random() * free.length)] : null;
    }

    function step() {
        if (game.queue.length) game.dir = game.queue.shift();
        const d = DIRS[game.dir];
        const head = game.snake[0];
        const next = [head[0] + d[0], head[1] + d[1]];
        const eats = game.food && next[0] === game.food[0] && next[1] === game.food[1];

        // Yem yenmiyorsa kuyruk bu adımda çekilir; kuyruğun hücresine girmek serbest.
        const body = eats ? game.snake : game.snake.slice(0, -1);
        const hitsWall = next[0] < 0 || next[1] < 0 || next[0] >= GRID || next[1] >= GRID;
        const hitsSelf = body.some((p) => p[0] === next[0] && p[1] === next[1]);
        if (hitsWall || hitsSelf) {
            end(false);
            return;
        }

        game.snake.unshift(next);
        if (eats) {
            game.score += 1;
            game.speed = Math.min(MAX_SPEED, BASE_SPEED + game.score * SPEED_STEP);
            ui.score.textContent = game.score;
            game.food = placeFood();
            if (!game.food) end(false);   // tahta doldu (397)
        } else {
            game.snake.pop();
        }
    }

    function turn(dir) {
        if (!game || game.over) return;
        const q = game.queue;
        const last = q.length ? q[q.length - 1] : game.dir;
        if (q.length >= 2 || dir === last) return;
        const a = DIRS[dir];
        const b = DIRS[last];
        if (a[0] === -b[0] && a[1] === -b[1]) return;   // 180° geri dönüş yok
        q.push(dir);
    }

    function frame(now) {
        if (!game || game.over) return;
        if (!game.last) game.last = now;
        game.acc += Math.min(now - game.last, MAX_FRAME_MS);
        game.last = now;
        while (!game.over && game.acc >= 1000 / game.speed) {
            game.acc -= 1000 / game.speed;
            step();
        }
        draw();
        if (!game.over) requestAnimationFrame(frame);
    }

    async function start() {
        if (starting || (game && !game.over)) return;
        starting = true;
        ui.startBtn.disabled = true;
        ui.again.disabled = true;

        let ticket = null;
        try {
            const res = await post(cfg.startUrl, {});
            if (res.ok) ticket = (await res.json()).bilet;
        } catch (err) {
            // Bağlantı yoksa yine oynansın; skor kaydedilemez, bitişte söylenir.
        }

        starting = false;
        ui.startBtn.disabled = false;
        ui.again.disabled = false;
        newGame(ticket);
        ui.score.textContent = "0";
        ui.start.classList.add("hidden");
        ui.over.classList.add("hidden");
        // Tuval yapışkan menünün hemen altına gelsin (scroll-mt-24); telefonda yön tuşları da ekranda kalır.
        ui.play.scrollIntoView({ behavior: "smooth", block: "start" });
        requestAnimationFrame(frame);
    }

    function end(hidden) {
        game.over = true;
        draw();
        const score = game.score;
        const durationMs = Math.max(1, Math.round(performance.now() - game.startedAt));
        localBest = Math.max(localBest, score);

        ui.final.textContent = score;
        ui.best.textContent = "En iyin: " + localBest;
        ui.msg.textContent = "Kaydediliyor…";
        ui.guest.classList.add("hidden");
        ui.over.classList.remove("hidden");

        submit(score, durationMs, game.ticket, hidden);
    }

    // ---------------------------------------------------------------- sunucu

    function post(url, body, keepalive) {
        // keepalive: sekme kapanırken de istek tamamlanır; özel başlığa (CSRF) izin verir.
        return fetch(url, {
            method: "POST",
            credentials: "same-origin",
            keepalive: Boolean(keepalive),
            headers: { "Content-Type": "application/json", "X-CSRFToken": cfg.csrf },
            body: JSON.stringify(body),
        });
    }

    async function submit(score, durationMs, ticket, keepalive) {
        const failed = "Bağlantı sorunu nedeniyle bu skor kaydedilemedi.";
        if (!ticket) {
            ui.msg.textContent = failed;
            return;
        }
        let res;
        let data;
        try {
            res = await post(cfg.finishUrl, { bilet: ticket, skor: score, sure_ms: durationMs }, keepalive);
            data = await res.json();
        } catch (err) {
            ui.msg.textContent = failed;
            return;
        }
        if (!res.ok) {
            ui.msg.textContent = data.error || "Skor kaydedilemedi.";
            return;
        }

        if (data.sen) ui.best.textContent = "En iyin: " + data.sen.en_iyi;

        if (data.durum === "ended") {
            ui.msg.textContent = "Yarışma bitti; bu skor sıralamaya girmez.";
        } else if (data.durum === "upcoming") {
            ui.msg.textContent = "Isınma turu! Yarışma başlayınca skorlar sayılmaya başlar.";
        } else if (data.bekliyor) {
            ui.msg.textContent = "Skorun bu tarayıcıda 24 saat bekler; üye olursan ya da giriş yaparsan tabloya eklenir.";
        } else {
            ui.msg.textContent = data.sen ? "Tablodaki sıran: #" + data.sen.sira : "Skorun kaydedildi.";
        }
        if (data.bekliyor) ui.guest.classList.remove("hidden");

        renderBoard(data.tablo, data.sen);
    }

    function renderBoard(rows, me) {
        if (!ui.board || !ui.rowTpl) return;   // yarışma başlamadı: tablo yok
        if (rows.length) {
            ui.board.replaceChildren(...rows.map((r) => {
                const li = ui.rowTpl.content.firstElementChild.cloneNode(true);
                li.querySelector("[data-sira]").textContent = "#" + r.sira;
                li.querySelector("[data-ad]").textContent = r.ad;
                li.querySelector("[data-skor]").textContent = r.skor;
                if (r.bu_sen_misin) li.setAttribute("data-me", "");
                return li;
            }));
        }
        if (ui.me) {
            const outside = Boolean(me) && me.sira > rows.length;
            ui.me.textContent = outside ? "Senin sıran: #" + me.sira + " · en iyin " + me.en_iyi : "";
            ui.me.classList.toggle("hidden", !outside);
        }
        if (ui.verify) ui.verify.classList.toggle("hidden", !(me && cfg.verified !== "1"));
    }

    // ---------------------------------------------------------------- girdi

    window.addEventListener("keydown", (e) => {
        if (!game || game.over) return;
        const dir = KEYS[e.code];
        if (dir) {
            e.preventDefault();   // oyun sürerken sayfa kaymasın
            turn(dir);
        } else if (e.code === "Space") {
            e.preventDefault();
        }
    });

    let touch = null;
    canvas.addEventListener("touchstart", (e) => {
        const t = e.changedTouches[0];
        touch = [t.clientX, t.clientY];
    }, { passive: true });
    canvas.addEventListener("touchmove", (e) => {
        if (!touch) return;
        const t = e.changedTouches[0];
        const dx = t.clientX - touch[0];
        const dy = t.clientY - touch[1];
        if (Math.max(Math.abs(dx), Math.abs(dy)) < SWIPE_MIN) return;
        turn(Math.abs(dx) > Math.abs(dy) ? (dx > 0 ? "right" : "left") : (dy > 0 ? "down" : "up"));
        touch = [t.clientX, t.clientY];   // parmağı kaldırmadan art arda dönülebilsin
    }, { passive: true });
    canvas.addEventListener("touchend", () => { touch = null; });
    canvas.addEventListener("touchcancel", () => { touch = null; });

    ui.pad.querySelectorAll("[data-dir]").forEach((btn) => {
        btn.addEventListener("pointerdown", (e) => {
            e.preventDefault();
            turn(btn.dataset.dir);
        });
    });

    ui.startBtn.addEventListener("click", start);
    ui.again.addEventListener("click", start);

    document.addEventListener("visibilitychange", () => {
        if (document.hidden && game && !game.over) end(true);
    });

    if ("ResizeObserver" in window) {
        new ResizeObserver(resize).observe(canvas);
    } else {
        window.addEventListener("resize", resize);
    }
    resize();
})();
