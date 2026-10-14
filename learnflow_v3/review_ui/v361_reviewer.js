/* V3-61 local-only masked reviewer interface: no network, no treatment key. */
(function (scope) {
  "use strict";
  const FIELDS = Object.freeze([
    "rater_id", "case_id", "clip_id", "clarity", "causal_witness",
    "semantic_continuity", "legibility", "pacing", "confidence",
    "watched_full_video", "replay_count", "timestamp_failure_notes"
  ]);
  const CRITERIA = Object.freeze([
    ["clarity", "Clarity — can you follow the intended claim?"],
    ["causal_witness", "Causal witness — is the explanatory cause shown before its effect?"],
    ["semantic_continuity", "Semantic continuity — are objects and states consistent?"],
    ["legibility", "Legibility — can you read the symbols and diagrams?"],
    ["pacing", "Pacing — is there sufficient time to think?"]
  ]);
  const RATE = [1, 2, 3, 4, 5];
  const BAD = /(?:^|[^A-Za-z0-9])(?:original_motion|static_end_state|causal_reveal)(?:$|[^A-Za-z0-9])/;
  function validRater(s) { return /^[A-Za-z0-9_-]{3,40}$/.test(s); }
  function escapeCSV(value) {
    const s = String(value === undefined || value === null ? "" : value);
    return /[",\r\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
  }
  function validateRow(row, expected) {
    if (!validRater(row.rater_id)) return "Enter a 3–40 character pseudonym (letters/numbers/_/-).";
    if (row.case_id !== expected.case_id || row.clip_id !== expected.clip_id) return "Frozen case/clip IDs changed.";
    for (const [field] of CRITERIA) {
      if (!RATE.includes(Number(row[field])) || !/^[1-5]$/.test(String(row[field]))) {
        return "Score every criterion 1–5.";
      }
    }
    if (!/^[1-5]$/.test(String(row.confidence))) return "Select confidence 1–5.";
    if (row.watched_full_video !== "YES") return "Watch this video fully and confirm it.";
    if (!/^\d{1,2}$/.test(String(row.replay_count))) return "Replay count must be 0–99.";
    if (CRITERIA.some(([field]) => Number(row[field]) <= 2) &&
        !/\b\d+(?:\.\d+)?s\b/.test(row.timestamp_failure_notes || "")) {
      return "For scores 1–2, record a concrete timestamp (e.g. 6.5s: too fast).";
    }
    return null;
  }
  function serializeCSV(rows, expected, frozenId) {
    if (!Array.isArray(rows) || rows.length !== 9 || expected.length !== 9) {
      throw new Error("Exactly nine rows required.");
    }
    const seen = new Set();
    for (let i = 0; i < 9; i++) {
      const r = rows[i], e = expected[i];
      const error = validateRow(r, e);
      if (error) throw new Error("Clip " + (i + 1) + ": " + error);
      if (r.rater_id !== frozenId) throw new Error("Inconsistent reviewer ID.");
      if (seen.has(r.clip_id)) throw new Error("Duplicate clip.");
      seen.add(r.clip_id);
    }
    return FIELDS.join(",") + "\n" +
      rows.map(r => FIELDS.map(k => escapeCSV(r[k])).join(",")).join("\n") + "\n";
  }
  const publicAPI = { FIELDS, CRITERIA, validRater, escapeCSV, validateRow, serializeCSV };
  if (typeof module !== "undefined" && module.exports) module.exports = publicAPI;
  if (!scope || !scope.document) return;

  scope.document.addEventListener("DOMContentLoaded", () => {
    const doc = scope.document;
    const cfgNode = doc.getElementById("frozen-configuration");
    if (!cfgNode) return;
    const cfg = JSON.parse(cfgNode.textContent);
    const ids = Array.isArray(cfg.clips) ? cfg.clips : [];
    if (ids.length !== 9 || new Set(ids.map(x => x.clip_id)).size !== 9 ||
        cfg.checkpoint !== "V3-61" || JSON.stringify(cfg).match(BAD)) {
      throw new Error("Invalid or unmasked reviewer configuration.");
    }
    const $ = id => doc.getElementById(id);
    const player = $("clip-video");
    const fields = $("rating-fields");
    const message = $("message");
    const scores = Object.create(null);
    const watched = Object.create(null);
    const events = Object.create(null);
    let index = 0, lastShown = -1;
    function say(text, bad) {
      message.textContent = text;
      message.className = bad ? "message error" : "message";
    }
    function current() { return ids[index]; }
    function id() { return current().clip_id; }
    function eventState(clip) {
      return events[clip] || (events[clip] = { bins: new Set(), ended: false, played: false });
    }
    function rowsSnapshot(clipId) {
      const r = scores[clipId] || {};
      return {
        rater_id: $("rater-id").value.trim(), case_id: current().case_id,
        clip_id: clipId, clarity: r.clarity || "", causal_witness: r.causal_witness || "",
        semantic_continuity: r.semantic_continuity || "", legibility: r.legibility || "",
        pacing: r.pacing || "", confidence: r.confidence || "",
        watched_full_video: r.watched_full_video || "",
        replay_count: r.replay_count === undefined ? "0" : r.replay_count,
        timestamp_failure_notes: r.timestamp_failure_notes || ""
      };
    }
    function collect() {
      const clip = id();
      const result = scores[clip] || (scores[clip] = {});
      for (const field of [...CRITERIA.map(x => x[0]), "confidence"]) {
        result[field] = fields.querySelector('[name="' + field + '"]').value;
      }
      result.replay_count = fields.querySelector('[name="replay_count"]').value;
      result.timestamp_failure_notes = $("failure-notes").value;
      result.watched_full_video = $("attest-full").checked ? "YES" : "";
    }
    function renderFields(clip) {
      fields.innerHTML = "";
      const prior = scores[clip] || {};
      function select(labelText, name) {
        const label = doc.createElement("label");
        label.textContent = labelText;
        const el = doc.createElement("select");
        el.name = name;
        el.required = true;
        el.append(new Option("Select…", ""));
        for (const n of RATE) el.append(new Option(String(n), String(n)));
        el.value = prior[name] || "";
        label.append(el); fields.append(label);
      }
      for (const [name, label] of CRITERIA) select(label, name);
      select("Confidence in your rating (1–5)", "confidence");
      const replay = doc.createElement("label");
      replay.textContent = "Times replayed (0–99)";
      const count = doc.createElement("input");
      count.name = "replay_count"; count.type = "number";
      count.min = "0"; count.max = "99"; count.step = "1";
      count.value = prior.replay_count === undefined ? "0" : prior.replay_count;
      replay.append(count); fields.append(replay);
      $("failure-notes").value = prior.timestamp_failure_notes || "";
      $("attest-full").checked = prior.watched_full_video === "YES";
    }
    function show(i) {
      if (i < 0 || i >= 9) return;
      index = i; lastShown = i;
      const item = current();
      $("progress").textContent = "Clip " + (i + 1) + " of 9 · Topic " + item.case_id.replace(/_/g," ");
      $("clip-id").textContent = item.clip_id;
      const path = "media/" + item.clip_id;
      if (!/^[a-z0-9_]+_[ABC]\.mp4$/.test(item.clip_id)) throw new Error("Unsafe filename.");
      player.pause();
      player.src = path;
      player.load();
      renderFields(item.clip_id);
      $("previous").disabled = i === 0;
      $("next").textContent = i === 8 ? "Check all nine ratings" : "Save and continue →";
      $("watch-state").textContent = eventState(item.clip_id).ended
        ? "Played to end (self-attestation still required)"
        : "Not yet played to end";
      say("This is a masked clip. Ratings are not transmitted anywhere.", false);
      $("export").hidden = true;
    }
    player.addEventListener("timeupdate", () => {
      const state = eventState(id());
      if (player.currentTime > 0 && !player.seeking) state.bins.add(Math.floor(player.currentTime));
    });
    player.addEventListener("play", () => {
      const state = eventState(id());
      if (state.played && state.ended) {
        const n = fields.querySelector('[name="replay_count"]');
        n.value = String(Math.min(99, Number(n.value || 0) + 1));
      }
      state.played = true;
    });
    player.addEventListener("ended", () => {
      const state = eventState(id());
      const duration = Number(player.duration || 0);
      const nominal = Math.max(1, Math.floor(duration));
      if (duration > 1 && state.bins.size >= Math.max(1, Math.floor(nominal * .7))) {
        state.ended = true;
        $("watch-state").textContent = "Played to end (self-attestation still required)";
      } else {
        say("Full playback was not observed; replay rather than seeking to the end.", true);
      }
    });
    $("timestamp").addEventListener("click", () => {
      const t = Math.max(0, Math.round(Number(player.currentTime || 0) * 10) / 10);
      const note = $("failure-notes");
      note.value += (note.value.trim() ? "\n" : "") + t.toFixed(1) + "s: ";
      note.focus();
    });
    $("next").addEventListener("click", () => {
      collect();
      const entry = rowsSnapshot(id());
      const error = validateRow(entry, current());
      if (!eventState(id()).ended) {
        say("Play this clip to the end; skipping to the final second is not sufficient.", true);
        return;
      }
      if (error) { say(error, true); return; }
      if (index < 8) { show(index + 1); return; }
      try {
        const idValue = $("rater-id").value.trim();
        const rows = ids.map(item => {
          const row = scores[item.clip_id] || {};
          return {rater_id:idValue,case_id:item.case_id,clip_id:item.clip_id,
            ...Object.fromEntries([...CRITERIA.map(x=>x[0]),"confidence","watched_full_video",
              "replay_count","timestamp_failure_notes"].map(k=>[k,row[k]===undefined?"":row[k]]))};
        });
        const csv = serializeCSV(rows, ids, idValue);
        const blob = new Blob([csv], {type:"text/csv;charset=utf-8"});
        const url = URL.createObjectURL(blob);
        const a = doc.createElement("a");
        a.href = url; a.download = "V361_masked_ratings_" + idValue + ".csv";
        doc.body.append(a); a.click(); a.remove();
        setTimeout(() => URL.revokeObjectURL(url), 20000);
        $("export").hidden = false;
        say("CSV exported locally. Send it privately to your coordinator; they must SHA-lock all ratings BEFORE opening the admin key.", false);
      } catch (error) {
        say(error.message || String(error), true);
      }
    });
    $("previous").addEventListener("click", () => {
      collect();
      show(index - 1);
    });
    show(0);
  });
})(typeof window !== "undefined" ? window : null);
