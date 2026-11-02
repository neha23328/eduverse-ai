// Small, safe Markdown renderer (no dependency). Escapes HTML first, so AI
// output can never inject markup.
function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function inline(s) {
  return esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>');
}

export function renderMarkdown(text = '') {
  const lines = text.replace(/\r/g, '').split('\n');
  const out = [];
  let list = null; // 'ul' | 'ol'
  let inCode = false;
  let code = [];

  const closeList = () => {
    if (list) { out.push(`</${list}>`); list = null; }
  };

  for (const raw of lines) {
    if (raw.trim().startsWith('```')) {
      if (inCode) {
        out.push(`<pre><code>${esc(code.join('\n'))}</code></pre>`);
        code = []; inCode = false;
      } else {
        closeList(); inCode = true;
      }
      continue;
    }
    if (inCode) { code.push(raw); continue; }

    const line = raw.trimEnd();
    let m;
    if ((m = line.match(/^(#{1,4})\s+(.*)/))) {
      closeList();
      const lvl = Math.min(m[1].length + 1, 4);
      out.push(`<h${lvl}>${inline(m[2])}</h${lvl}>`);
    } else if ((m = line.match(/^\s*[-*•]\s+(.*)/))) {
      if (list !== 'ul') { closeList(); out.push('<ul>'); list = 'ul'; }
      out.push(`<li>${inline(m[1])}</li>`);
    } else if ((m = line.match(/^\s*\d+[.)]\s+(.*)/))) {
      if (list !== 'ol') { closeList(); out.push('<ol>'); list = 'ol'; }
      out.push(`<li>${inline(m[1])}</li>`);
    } else if (line.startsWith('>')) {
      closeList();
      out.push(`<blockquote>${inline(line.replace(/^>\s?/, ''))}</blockquote>`);
    } else if (line.trim() === '') {
      closeList();
    } else {
      closeList();
      out.push(`<p>${inline(line)}</p>`);
    }
  }
  if (inCode) out.push(`<pre><code>${esc(code.join('\n'))}</code></pre>`);
  closeList();
  return out.join('');
}

// "Q: ... A: ..." blocks -> [{q, a}]
export function parseFlashcards(text = '') {
  const cards = [];
  let cur = null;
  for (const line of text.replace(/\r/g, '').split('\n')) {
    const q = line.match(/^\s*(?:\*\*)?(?:\d+[.)]\s*)?Q\s*[:.]\s*(?:\*\*)?\s*(.*)/i);
    const a = line.match(/^\s*(?:\*\*)?A\s*[:.]\s*(?:\*\*)?\s*(.*)/i);
    if (q) { cur = { q: q[1].replace(/\*\*/g, ''), a: '' }; cards.push(cur); }
    else if (a && cur) { cur.a = a[1].replace(/\*\*/g, ''); }
    else if (cur && line.trim() && cur.a) { cur.a += ' ' + line.trim(); }
  }
  return cards.filter((c) => c.q && c.a);
}
