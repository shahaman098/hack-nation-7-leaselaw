async function loadPipeline() {
  const steps = document.getElementById("pipeline-steps");
  if (!steps) return;
  steps.innerHTML = `
    <div class="pipeline-step"><span class="step-num">1</span><div><strong>Collect laws</strong><br/>We save official tenant and landlord rules from California, New Jersey, and Massachusetts.</div></div>
    <div class="pipeline-step"><span class="step-num">2</span><div><strong>Match your address</strong><br/>City, state, building age, and unit count can change what applies.</div></div>
    <div class="pipeline-step"><span class="step-num">3</span><div><strong>Check the date</strong><br/>A rule might not apply yet, or a city rule may replace a state rule.</div></div>
    <div class="pipeline-step"><span class="step-num">4</span><div><strong>Show plain English</strong><br/>Always with the original law text underneath — not legal advice.</div></div>
  `;
}
loadPipeline();
