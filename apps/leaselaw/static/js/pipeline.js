async function loadPipeline() {
  const el = document.getElementById("pipeline-data");
  const steps = document.getElementById("pipeline-steps");
  try {
    const d = await fetch("/api/pipeline").then((r) => r.json());
    const methods = Object.entries(d.by_extraction_method || {})
      .map(([k, v]) => `${k}: ${v}`)
      .join(" · ");
    steps.innerHTML = `
      <div class="pipeline-step"><span class="step-num">1</span><div><strong>Corpus</strong><br/>54 text docs from starter pack manifest</div></div>
      <div class="pipeline-step"><span class="step-num">2</span><div><strong>Extract</strong><br/>${d.rules_total} rules · ${methods || "canonical"}</div></div>
      <div class="pipeline-step"><span class="step-num">3</span><div><strong>Verify</strong><br/>Literal <code>quoted_span</code> check; drop failures</div></div>
      <div class="pipeline-step"><span class="step-num">4</span><div><strong>Lookup</strong><br/>500 addresses · engine coverage + as-of</div></div>
    `;
    el.textContent = JSON.stringify(d, null, 2);
  } catch (e) {
    el.textContent = "Failed to load pipeline: " + e.message;
  }
}
loadPipeline();
