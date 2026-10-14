const iso = d => d.toISOString().slice(0, 10);

window.OZU_THEME = {
  setup({ recent }) {
    if (recent[0]) document.getElementById('rev').textContent = iso(recent[0].date).replace(/-/g, '.');
  },
  renderHome({ recent }, { link, esc }) {
    const revs = recent.map(r => `
      <tr><td class="c-date">${iso(r.date)}</td><td class="c-pn"><a ${link(r.course)}>${esc(r.course)}</a></td><td>${esc(r.text)}</td></tr>`).join('');

    return `
      <section class="home">
        <div class="ds-title">
          <p class="ds-kicker">Coursework Repository</p>
          <h1>Electrical &amp; Electronics Engineering<br><span>Labs, Projects, Homework &amp; Lecture Notes</span></h1>
        </div>
        ${revs ? `<section class="ds-sec">
          <h2><span>1</span>Revision History</h2>
          <div class="tbl-wrap">
            <table class="tbl tbl-rev">
              <thead><tr><th>Date</th><th>Course</th><th>Change</th></tr></thead>
              <tbody>${revs}</tbody>
            </table>
          </div>
        </section>` : ''}
      </section>`;
  },
};
