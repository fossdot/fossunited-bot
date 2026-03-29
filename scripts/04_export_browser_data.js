// ============================================================
// scripts/04_export_browser_data.js
// Run this in the browser console on tg.fossunited.org tab
// AFTER the scraper has finished (window._scrapeState.done === true)
// Then run again on forum.fossunited.org tab for forum data
// ============================================================

// ---- TELEGRAM EXPORT ----
// Run on tg.fossunited.org tab after scraping
function exportTelegram() {
  const state = window._scrapeState;
  if (!state || !state.done) {
    console.error('Telegram scrape not done yet. Check window._scrapeState.done');
    return;
  }
  const jsonl = state.allMessages.map(m => JSON.stringify(m)).join('\n');
  const blob = new Blob([jsonl], { type: 'application/jsonlines' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'telegram_messages.jsonl';
  a.click();
  console.log(`Exported ${state.allMessages.length} messages`);
}

// ---- FORUM EXPORT ----
// Run on forum.fossunited.org tab after scraping
function exportForum() {
  const state = window._forumState;
  if (!state || state.phase !== 'done') {
    console.log('Forum scrape status:', state?.phase, '| Topics done:', state?.topicIndex, '/', state?.topics?.length);
    return;
  }

  // Export posts as JSONL
  const postsJsonl = state.posts.map(p => JSON.stringify(p)).join('\n');
  const postsBlob = new Blob([postsJsonl], { type: 'application/jsonlines' });
  const a1 = document.createElement('a');
  a1.href = URL.createObjectURL(postsBlob);
  a1.download = 'forum_posts.jsonl';
  a1.click();

  // Export topics metadata separately
  const topicsJson = JSON.stringify(state.topics, null, 2);
  const topicsBlob = new Blob([topicsJson], { type: 'application/json' });
  const a2 = document.createElement('a');
  a2.href = URL.createObjectURL(topicsBlob);
  a2.download = 'forum_topics.json';
  a2.click();

  console.log(`Exported ${state.posts.length} posts from ${state.topics.length} topics`);
}

// ---- CHECK PROGRESS ----
function checkProgress() {
  const tg = window._scrapeState;
  const forum = window._forumState;
  
  if (tg) {
    console.log(`Telegram: ${tg.done ? 'DONE' : 'running'} | ${tg.allMessages?.length} messages | month ${tg.currentIndex+1}/${tg.months?.length}`);
  }
  if (forum) {
    console.log(`Forum: ${forum.phase} | ${forum.posts?.length} posts | topic ${forum.topicIndex}/${forum.topics?.length} | errors: ${forum.errors?.length}`);
  }
}

// Run checkProgress() to see status
// Run exportTelegram() or exportForum() when done
checkProgress();
