/* Frontend Logic */
(function () {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  /* ---- State ---- */
  const state = {
    allergies: new Set(),
    sensitivities: new Set(),
  };

  /* ---- Slider bindings ---- */
  function bindSlider(id, display, fmt) {
    const el = $(`#${id}`);
    const out = $(`#${display}`);
    const update = () => { out.textContent = fmt(el.value); };
    el.addEventListener("input", update);
    update();
  }
  bindSlider("calories", "caloriesValue", (v) => `${v} kcal`);
  bindSlider("protein", "proteinValue", (v) => `${Math.round(v * 100)}%`);
  bindSlider("fat", "fatValue", (v) => `${Math.round(v * 100)}%`);
  bindSlider("carbs", "carbsValue", (v) => `${Math.round(v * 100)}%`);

  /* ---- Chip toggle ---- */
  function setupChips(groupId, stateSet) {
    $(`#${groupId}`).addEventListener("click", (e) => {
      const chip = e.target.closest(".chip");
      if (!chip) return;
      const val = chip.dataset.val;
      chip.classList.toggle("active");
      if (stateSet.has(val)) stateSet.delete(val);
      else stateSet.add(val);
    });
  }
  setupChips("allergyGroup", state.allergies);
  setupChips("sensitivityGroup", state.sensitivities);

  /* ---- Tabs ---- */
  $$(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      $$(".tab").forEach((t) => t.classList.remove("active"));
      $$(".tab-content").forEach((c) => c.classList.remove("active"));
      tab.classList.add("active");
      $(`#tab-${tab.dataset.tab}`).classList.add("active");
    });
  });

  /* ---- Generate Plan ---- */
  $("#generateBtn").addEventListener("click", async () => {
    const payload = {
      calories: parseInt($("#calories").value),
      allergies: [...state.allergies],
      sensitivities: [...state.sensitivities],
      macro_split: {
        protein: parseFloat($("#protein").value),
        fat: parseFloat($("#fat").value),
        carbs: parseFloat($("#carbs").value),
      },
      query: $("#query").value || "healthy meal",
    };

    $("#loading").classList.remove("hidden");
    $("#generateBtn").disabled = true;

    try {
      const resp = await fetch("/api/generate-plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || "Server error");
      renderResults(data);
    } catch (err) {
      alert("Error: " + err.message);
    } finally {
      $("#loading").classList.add("hidden");
      $("#generateBtn").disabled = false;
    }
  });

  /* ---- Render Results ---- */
  function renderResults(data) {
    $("#results").classList.remove("hidden");

    const existingBanner = document.getElementById("demoBanner");
    if (existingBanner) existingBanner.remove();
    if (data.demo_mode) {
      const banner = document.createElement("div");
      banner.id = "demoBanner";
      banner.className = "card";
      banner.style.cssText = "background:#fef3c7;border-left:4px solid #f59e0b;";
      banner.innerHTML = `<p style="margin:0;font-size:.9rem"><strong>Demo Mode</strong> — Edamam API keys not configured. Using built-in sample recipes. Add your free keys to <code>.env</code> for real recipe search.</p>`;
      $("#results").prepend(banner);
    }

    if (data.sensitivity_notes && data.sensitivity_notes.length) {
      $("#sensitivityNotes").classList.remove("hidden");
      $("#notesList").innerHTML = data.sensitivity_notes.map((n) => `<li>${n}</li>`).join("");
    } else {
      $("#sensitivityNotes").classList.add("hidden");
    }

    const m = data.metrics;
    $("#metricsGrid").innerHTML = [
      metric(m.avg_daily_calories, "Avg kcal/day"),
      metric(m.avg_daily_protein + "g", "Avg Protein/day"),
      metric(m.avg_daily_fat + "g", "Avg Fat/day"),
      metric(m.avg_daily_carbs + "g", "Avg Carbs/day"),
      metric(m.calorie_mae, "Calorie MAE"),
      metric(`${m.unique_recipes}/${m.total_recipes}`, "Unique Recipes"),
      metric(m.diversity_index, "Diversity Index"),
    ].join("");

    // plan, grocery, usda lookup
    let planHTML = "";
    for (let day = 1; day <= 7; day++) {
      const meals = data.plan[String(day)] || [];
      const total = meals.reduce((s, m) => s + m.calories, 0);
      planHTML += `<div class="day-card">
        <div class="day-header"><span>Day ${day}</span><span class="day-total">${total} kcal</span></div>`;
      meals.forEach((m) => {
        const imgSrc = m.image || "";
        planHTML += `<div class="meal-row">
          ${imgSrc ? `<img class="meal-img" src="${imgSrc}" alt="" loading="lazy">` : `<div class="meal-img"></div>`}
          <div class="meal-info">
            <div class="meal-type">${m.meal}</div>
            <div class="meal-name">${m.url ? `<a href="${m.url}" target="_blank">${m.recipe}</a>` : m.recipe}</div>
            <div class="meal-macros">${m.calories} kcal · P ${m.protein_g}g · F ${m.fat_g}g · C ${m.carbs_g}g</div>
          </div>
        </div>`;
      });
      planHTML += `</div>`;
    }
    $("#planContainer").innerHTML = planHTML;

    const gl = data.grocery_list || [];
    $("#groceryList").innerHTML = gl.map((item) => `<li>${item}</li>`).join("");

    $("#results").scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function metric(value, label) {
    return `<div class="metric-box"><span class="metric-num">${value}</span><span class="metric-label">${label}</span></div>`;
  }

  $("#usdaSearchBtn").addEventListener("click", async () => {
    const q = $("#usdaQuery").value.trim();
    if (!q) return;
    $("#usdaSearchBtn").disabled = true;
    try {
      const resp = await fetch("/api/nutrition-lookup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: q }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.error || "Error");
      renderUSDA(data.results || []);
    } catch (err) {
      $("#usdaResults").innerHTML = `<p style="color:red">${err.message}</p>`;
    } finally {
      $("#usdaSearchBtn").disabled = false;
    }
  });

  $("#usdaQuery").addEventListener("keydown", (e) => {
    if (e.key === "Enter") $("#usdaSearchBtn").click();
  });

  function renderUSDA(results) {
    if (!results.length) {
      $("#usdaResults").innerHTML = "<p>No results found.</p>";
      return;
    }
    let html = `<p style="font-size:.8rem;color:var(--text-muted);margin-bottom:.8rem">Showing ${results.length} results (USDA standard reference prioritized over branded products)</p>`;
    html += `<table class="usda-table"><thead><tr>
      <th>Food</th><th>Category</th><th>Serving</th><th>Calories</th><th>Protein (g)</th><th>Fat (g)</th><th>Carbs (g)</th><th>Fiber (g)</th>
    </tr></thead><tbody>`;
    results.forEach((r) => {
      const typeTag = r.data_type === "Branded" ? '<span style="color:#9ca3af;font-size:.7rem"> [Branded]</span>' : "";
      html += `<tr>
        <td>${r.description || "—"}${typeTag}</td>
        <td style="font-size:.8rem;color:var(--text-muted)">${r.category || "—"}</td>
        <td style="font-size:.8rem">${r.serving_size || "—"}</td>
        <td>${fmt(r.calories)}</td>
        <td>${fmt(r.protein)}</td>
        <td>${fmt(r.fat)}</td>
        <td>${fmt(r.carbs)}</td>
        <td>${fmt(r.fiber)}</td>
      </tr>`;
    });
    html += `</tbody></table>`;
    $("#usdaResults").innerHTML = html;
  }

  function fmt(v) {
    return v != null ? (typeof v === "number" ? v.toFixed(1) : v) : "—";
  }
})();
