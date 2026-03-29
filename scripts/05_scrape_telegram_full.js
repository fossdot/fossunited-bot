// ============================================================
// scripts/05_scrape_telegram_full.js
// Run this in the browser console on tg.fossunited.org
//
// The basic scraper only gets the first page (~300 msgs) per month.
// This script checks for pagination within months and fetches all pages.
// Some months had 1000-4000+ messages — this gets everything.
// ============================================================

window._fullScrapeState = {
  months: [],
  allMessages: [],
  currentMonth: null,
  currentPage: 0,
  done: false,
  errors: [],
  skippedMonths: []
};

// Generate month list Jul 2020 to Mar 2024
const months = [];
for (let year = 2020; year <= 2024; year++) {
  for (let month = 1; month <= 12; month++) {
    if (year === 2020 && month < 7) continue;
    if (year === 2024 && month > 3) break;
    months.push(`${year}-${String(month).padStart(2,'0')}`);
  }
}
window._fullScrapeState.months = months;

const parseMessages = function(html, yearMonth) {
  const parser = new DOMParser();
  const doc = parser.parseFromString(html, 'text/html');
  const messages = [];
  let currentDay = '';

  doc.querySelectorAll('li.message, li.day').forEach(li => {
    if (li.classList.contains('day')) {
      currentDay = li.id || '';
      return;
    }
    const id = li.id || '';
    const username = li.querySelector('.username')?.textContent.trim() || '';
    const time = li.querySelector('.time')?.textContent.trim() || '';
    const textEl = li.querySelector('.text');
    const text = textEl?.textContent.trim() || '';
    const replyEl = li.querySelector('[class*="reply"]');
    const replyTo = replyEl ? replyEl.textContent.trim().replace('↶ Reply to ', '') : '';
    const isService = li.classList.contains('type-service');
    if (!text && !isService) return;
    messages.push({ id, month: yearMonth, day: currentDay, time, username, text, replyTo, isService });
  });

  // Check if there's a "next page" link (pagination within month)
  const nextLink = doc.querySelector('a[href*=".html"]:not([href*="//"])');
  const allLinks = Array.from(doc.querySelectorAll('a[href]'))
    .map(a => a.getAttribute('href'))
    .filter(h => h && !h.startsWith('http') && h.endsWith('.html') && h !== './');

  return { messages, allLinks };
};

(async () => {
  const delay = ms => new Promise(r => setTimeout(r, ms));
  const state = window._fullScrapeState;
  const seen = new Set(); // dedupe by message ID

  for (const ym of state.months) {
    state.currentMonth = ym;
    let page = 1;
    let url = `https://tg.fossunited.org/${ym}.html`;
    const monthMsgs = [];

    while (url) {
      try {
        const resp = await fetch(url);
        if (!resp.ok) { state.errors.push({month: ym, url, status: resp.status}); break; }
        const html = await resp.text();
        const { messages, allLinks } = parseMessages(html, ym);

        let added = 0;
        for (const m of messages) {
          if (!seen.has(m.id)) {
            seen.add(m.id);
            monthMsgs.push(m);
            state.allMessages.push(m);
            added++;
          }
        }

        console.log(`${ym} page ${page}: ${added} new msgs (month total: ${monthMsgs.length})`);

        // Find next page link - tg-archive uses YYYY-MM-N.html pattern
        const nextPageUrl = allLinks.find(h => {
          const base = `${ym}-${page + 1}.html`;
          return h === base || h.endsWith('/' + base);
        });

        if (nextPageUrl) {
          url = `https://tg.fossunited.org/${nextPageUrl}`;
          page++;
        } else {
          url = null; // no more pages for this month
        }

        await delay(400);
      } catch(e) {
        state.errors.push({month: ym, url, error: e.message});
        break;
      }
    }

    console.log(`✓ ${ym}: ${monthMsgs.length} total messages`);
  }

  state.done = true;
  console.log(`\n✓ FULL SCRAPE DONE: ${state.allMessages.length} messages total`);
  console.log(`Errors: ${state.errors.length}`);
})();

console.log(`Full scraper started for ${months.length} months. Check window._fullScrapeState for progress.`);

// To export when done:
// const jsonl = window._fullScrapeState.allMessages.map(m => JSON.stringify(m)).join('\n');
// const blob = new Blob([jsonl], {type:'application/jsonlines'});
// const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
// a.download = 'telegram_messages_full.jsonl'; a.click();
