/* ============================================================
   wan·6gb — device picker, copy buttons, nav state
   No dependencies. Runs on the cheapest laptop that can open it.
   ============================================================ */

(function () {
  "use strict";

  /* ------------------------------------------------------------
     Device table.
     Only the 6 GB row is measured. Every other row is an
     extrapolation from docs/hardware.md — labelled as such in
     the UI so nobody quotes it as a benchmark.
     ------------------------------------------------------------ */

  var devices = {
    4: {
      badge: "Possible · slow",
      badgeClass: "warn",
      title: "4 GB — the floor",
      verdict: "It runs, and you will feel every second of it. Expect drafts, not deliverables.",
      model: "Wan22-Turbo-Q3_K_M.gguf",
      modelNote: "~2.7 GiB on disk · partially offloaded",
      enc: "umt5-xxl Q3_K_M",
      encNote: "on CPU · ~2.7 GB streamed from RAM",
      res: "512 × 288",
      frames: "33–49",
      dur: "1.4–2.0 s at 24 fps · 4n+1 rule",
      steps: "4",
      time: "~5–8 min",
      timeNote: "estimated · not measured",
      note: "The UNet cannot stay fully resident, so --lowvram is mandatory. Drop to Q3_K_S, close every GPU app, and use 33 frames. 480p is out of reach; treat this as a preview machine.",
      meter: [62, 22, 16],
      meterLabel: "~3.6 / 4.0 GB",
      flags: "--lowvram --reserve-vram 0.3",
      fine: "Estimated. On 4 GB the wall is the model itself, not your patience."
    },

    6: {
      badge: "Recommended",
      badgeClass: "",
      title: "6 GB — the reference machine",
      verdict: "The configuration this whole site is measured on.",
      model: "Wan22-Turbo-Q4_K_M.gguf",
      modelNote: "3.3 GiB on disk · fully resident on the GPU",
      enc: "umt5-xxl Q4_K_M",
      encNote: "on CPU · 4.66 GB streamed from RAM",
      res: "704 × 480",
      frames: "81",
      dur: "3.4 s at 24 fps · 4n+1 rule",
      steps: "4",
      time: "~2.5 min",
      timeNote: "measured, warm GPU",
      note: "The 5B model fits with latents and VAE headroom to spare. The encoder cannot join it, so it streams from system RAM — that is the 75% of wall-clock nobody warns you about.",
      meter: [56, 28, 16],
      meterLabel: "5.7 / 6.0 GB",
      flags: "--reserve-vram 0.2",
      fine: "Measured on this exact card. Other GPUs change the seconds, not the shape of the curve."
    },

    8: {
      badge: "Comfortable",
      badgeClass: "cool",
      title: "8 GB — the easy tier",
      verdict: "The VRAM cliff moves above 832×480. You stop tuning and start iterating.",
      model: "Wan22-Turbo-Q5_K_M.gguf",
      modelNote: "~4.1 GiB on disk · fully resident on the GPU",
      enc: "umt5-xxl Q4_K_M",
      encNote: "CPU first · try GPU only if it loads fully",
      res: "832 × 480",
      frames: "81",
      dur: "3.4 s at 24 fps · 4n+1 rule",
      steps: "4",
      time: "~2–3 min",
      timeNote: "estimated · not measured",
      note: "Q5_K_M buys a little quality over Q4 at the same speed. 832×480 is viable here, unlike on 6 GB. A partial encoder offload is slower than a clean CPU pass, so check the log before moving it.",
      meter: [51, 30, 19],
      meterLabel: "~6.5 / 8.0 GB",
      flags: "--reserve-vram 0.3",
      fine: "Estimated. The main gain over 6 GB is that 832×480 stops thrashing."
    },

    12: {
      badge: "Good",
      badgeClass: "cool",
      title: "12 GB — encoder on the GPU",
      verdict: "The encoder pass stops dominating. Sampling becomes the bottleneck again.",
      model: "Wan22-Turbo-Q8_0.gguf",
      modelNote: "~5.4 GiB on disk · fully resident on the GPU",
      enc: "umt5-xxl Q8_0",
      encNote: "on GPU · ~4.9 GB, no streaming",
      res: "832 × 480",
      frames: "121",
      dur: "5.0 s at 24 fps · 4n+1 rule",
      steps: "4",
      time: "~70–100 s",
      timeNote: "estimated · not measured",
      note: "With both the model and encoder resident, the fixed cost per prompt mostly disappears. 121 frames is comfortable. Wan 2.1 VACE 1.3B fits easily; the 14B VACE still does not.",
      meter: [44, 40, 16],
      meterLabel: "~10.6 / 12.0 GB",
      flags: "--reserve-vram 0.5",
      fine: "Estimated. The step from 8 GB is mostly about the encoder, not the model."
    },

    16: {
      badge: "No compromises at 480p",
      badgeClass: "",
      title: "16 GB — 480p solved",
      verdict: "Everything at 480p is fast. This is the tier where the workflow disappears.",
      model: "Wan22-Turbo-Q8_0.gguf",
      modelNote: "~5.4 GiB on disk · fully resident on the GPU",
      enc: "umt5-xxl Q8_0",
      encNote: "on GPU · no streaming, no pagefile",
      res: "832 × 480",
      frames: "121",
      dur: "5.0 s at 24 fps · 4n+1 rule",
      steps: "4",
      time: "~45–70 s",
      timeNote: "estimated · not measured",
      note: "Longer clips and batch sizes stop being scary. Wan 2.2 14B at Q4_K_M becomes possible with block offload, at 480p — budget 2–4× the 5B time and expect to tune --reserve-vram.",
      meter: [34, 40, 26],
      meterLabel: "~10.5 / 16.0 GB",
      flags: "--reserve-vram 0.8",
      fine: "Estimated. Above this point the 5B model is limited by clocks, not memory."
    },

    24: {
      badge: "Different class",
      badgeClass: "cool",
      title: "24 GB — the 14B tier",
      verdict: "Wan 2.2 14B at 720p, VACE 14B, Wan Animate. This is where identity starts to hold.",
      model: "Wan22-14B-Q4_K_M.gguf",
      modelNote: "~9 GiB on disk · resident with block offload",
      enc: "umt5-xxl Q8_0",
      encNote: "on GPU · ~4.9 GB, no streaming",
      res: "1280 × 720",
      frames: "81",
      dur: "3.4 s at 24 fps · 4n+1 rule",
      steps: "4–8",
      time: "~3–5 min",
      timeNote: "estimated · not measured",
      note: "The 14B model is a genuine quality jump, especially for faces and hands. The 5B setup still wins on iteration speed, so keep both graphs around rather than choosing one.",
      meter: [40, 32, 28],
      meterLabel: "~16.5 / 24.0 GB",
      flags: "--reserve-vram 1.0",
      fine: "Estimated. 24 GB is the first tier where 14B is pleasant instead of merely possible."
    }
  };

  var fields = {
    badge: "d-badge",
    title: "d-title",
    verdict: "d-verdict",
    model: "d-model",
    modelNote: "d-model-note",
    enc: "d-enc",
    encNote: "d-enc-note",
    res: "d-res",
    frames: "d-frames",
    dur: "d-dur",
    steps: "d-steps",
    time: "d-time",
    timeNote: "d-time-note",
    note: "d-note",
    meterLabel: "d-meter-label",
    flags: "d-flags",
    fine: "d-fine"
  };

  var chips = Array.prototype.slice.call(document.querySelectorAll(".chip[data-gb]"));
  var meter = document.getElementById("d-meter");
  var noteBox = document.getElementById("d-note");

  function setText(id, value) {
    var el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function paintMeter(widths) {
    if (!meter) return;
    var segs = meter.querySelectorAll(".seg");
    for (var i = 0; i < segs.length && i < widths.length; i++) {
      segs[i].style.width = widths[i] + "%";
    }
    meter.setAttribute(
      "aria-label",
      "Estimated VRAM split: weights " + widths[0] +
      " percent, activations " + widths[1] +
      " percent, headroom " + widths[2] + " percent"
    );
  }

  function render(gb) {
    var d = devices[gb];
    if (!d) return;

    Object.keys(fields).forEach(function (key) {
      if (key === "note" || key === "meterLabel") return;
      setText(fields[key], d[key]);
    });

    setText(fields.meterLabel, d.meterLabel);

    var badge = document.getElementById(fields.badge);
    if (badge) {
      badge.className = "badge" + (d.badgeClass ? " " + d.badgeClass : "");
    }

    if (noteBox) {
      var body = noteBox.querySelector("p");
      if (body) body.textContent = d.note;
    }

    paintMeter(d.meter);

    chips.forEach(function (chip) {
      var on = chip.getAttribute("data-gb") === String(gb);
      chip.classList.toggle("is-on", on);
      chip.setAttribute("aria-pressed", on ? "true" : "false");
    });

    /* Keep the choice in the URL so a link can point at a tier. */
    if (window.history && window.history.replaceState) {
      var url = window.location.pathname + window.location.search + "#device";
      try {
        window.history.replaceState(null, "", gb === 6 ? url : url + "-" + gb);
      } catch (e) {
        /* file:// and sandboxed contexts can refuse this; not worth breaking over. */
      }
    }
  }

  chips.forEach(function (chip) {
    chip.addEventListener("click", function () {
      var gb = parseInt(chip.getAttribute("data-gb"), 10);
      if (devices[gb]) render(gb);
    });
  });

  /* Deep link: #device-8 selects 8 GB. */
  var hash = window.location.hash;
  var match = /^#device-(\d+)$/.exec(hash);
  if (match && devices[match[1]]) {
    render(parseInt(match[1], 10));
    /* The fragment has no matching element id, so scroll manually. */
    window.setTimeout(function () {
      var el = document.getElementById("device");
      if (el) window.scrollTo({ top: el.offsetTop - 90, behavior: "instant" });
    }, 0);
  }

  window.addEventListener("hashchange", function () {
    var m = /^#device-(\d+)$/.exec(window.location.hash);
    if (m && devices[m[1]]) render(parseInt(m[1], 10));
  });

  /* ------------------------------------------------------------
     Copy buttons. Clipboard API first, execCommand as a fallback
     for file:// and older browsers.
     ------------------------------------------------------------ */

  function legacyCopy(text) {
    var ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.position = "fixed";
    ta.style.top = "-1000px";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    return ok;
  }

  function flash(btn, ok) {
    if (!btn.getAttribute("data-label")) {
      btn.setAttribute("data-label", btn.textContent);
    }
    var original = btn.getAttribute("data-label");
    btn.textContent = ok ? "copied" : "select + Ctrl+C";
    btn.classList.toggle("done", ok);
    window.setTimeout(function () {
      btn.textContent = original;
      btn.classList.remove("done");
    }, 1600);
  }

  Array.prototype.forEach.call(document.querySelectorAll(".copy"), function (btn) {
    btn.addEventListener("click", function () {
      var box = btn.closest(".code");
      var code = box ? box.querySelector("code") : null;
      var text = code ? code.textContent : "";
      if (!text) return;

      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(text).then(
          function () { flash(btn, true); },
          function () { flash(btn, legacyCopy(text)); }
        );
      } else {
        flash(btn, legacyCopy(text));
      }
    });
  });

  /* ------------------------------------------------------------
     Nav: highlight the section you are looking at.
     ------------------------------------------------------------ */

  var links = Array.prototype.slice.call(document.querySelectorAll(".nav-links a"));
  var targets = links
    .map(function (a) {
      var id = a.getAttribute("href");
      var el = id && id.charAt(0) === "#" ? document.querySelector(id) : null;
      return el ? { link: a, el: el } : null;
    })
    .filter(Boolean);

  if ("IntersectionObserver" in window && targets.length) {
    var visible = new Set();

    var obs = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        var hit = targets.find(function (t) { return t.el === entry.target; });
        if (!hit) return;
        if (entry.isIntersecting) visible.add(hit.link);
        else visible.delete(hit.link);
      });

      links.forEach(function (a) { a.classList.remove("is-current"); });
      if (visible.size) {
        var first = targets.find(function (t) { return visible.has(t.link); });
        if (first) first.link.classList.add("is-current");
      }
    }, { rootMargin: "-45% 0px -45% 0px", threshold: 0 });

    targets.forEach(function (t) { obs.observe(t.el); });
  }

  /* ------------------------------------------------------------
     Small nicety: open one troubleshooting item at a time in the
     failure list, but leave the FAQ free-form.
     ------------------------------------------------------------ */

  var failures = document.querySelectorAll("#fix .acc details");
  Array.prototype.forEach.call(failures, function (item) {
    item.addEventListener("toggle", function () {
      if (!item.open) return;
      Array.prototype.forEach.call(failures, function (other) {
        if (other !== item) other.open = false;
      });
    });
  });
})();
