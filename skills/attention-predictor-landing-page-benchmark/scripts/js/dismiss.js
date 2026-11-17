// Decline cookie banners (privacy-preserving choice), then hide leftovers and chat widgets so they don't skew attention.
(() => {
  const deep = (root, sel, acc = [], d = 0) => { try { root.querySelectorAll(sel).forEach(e => acc.push(e)); if (d < 4) root.querySelectorAll('*').forEach(e => { if (e.shadowRoot) deep(e.shadowRoot, sel, acc, d + 1); }); } catch (x) {} return acc; };
  const label = e => ((e.innerText || e.value || e.getAttribute('aria-label') || '') + '').trim();
  const re = /^(reject|decline|deny|refuse|do not allow|don.?t allow|disallow|accept necessary|accept only necessary|accept essential|only (strictly )?necessary|necessary only|use necessary|essential only|allow essential|continue without|no,? thanks)/i;
  let out = 'none', hidden = 0;
  const hit = deep(document, 'button, a, [role=button], input[type=button], input[type=submit]').find(e => re.test(label(e)) && e.getClientRects().length);
  if (hit) { try { hit.click(); out = 'rejected:' + label(hit).slice(0, 30); } catch (x) {} }
  const hide = e => { try { e.style.setProperty('display', 'none', 'important'); hidden++; } catch (x) {} };
  const words = /cookie|consent|privacy preferences|we value your privacy|tracking technologies/i;
  document.querySelectorAll('body *').forEach(e => {
    const s = getComputedStyle(e); if (s.position !== 'fixed' && s.position !== 'sticky') return;
    const r = e.getBoundingClientRect(); if (r.width < 180 || r.height < 50) return;
    const t = ((e.innerText || '') + ' ' + (e.shadowRoot ? e.shadowRoot.textContent : '')).slice(0, 4000);
    const isConsent = words.test(t) && r.height < innerHeight * 0.98;
    const isOverlay = r.width >= innerWidth * 0.95 && r.height >= innerHeight * 0.95 && (e.innerText || '').trim().length < 5 && s.backgroundColor !== 'rgba(0, 0, 0, 0)' && !e.querySelector('img, video, canvas, svg');
    if (isConsent || isOverlay) hide(e);
  });
  // consent managers that live in shadow roots / iframes, and live-chat widgets (not part of the design)
  document.querySelectorAll('[id*="onetrust" i], [id*="usercentrics" i], [id*="CybotCookiebot" i], [id*="truste" i], [class*="truste" i], [id*="cookie-banner" i], [class*="cookie-banner" i], [id*="cookiebanner" i], [class*="cookiebanner" i], [id*="consent-banner" i], [class*="consent-banner" i], [aria-label*="cookie" i][role="dialog"], [aria-label*="consent" i][role="dialog"], iframe[title*="cookie" i], iframe[title*="consent" i], iframe[src*="consent" i], transcend-consent-manager, #transcend-consent-manager, #hubspot-messages-iframe-container, [id*="intercom-" i], [class*="intercom-lightweight" i], [id*="drift-" i], [id*="crisp" i], [id*="zendesk" i][id*="launcher" i], [id*="launcher" i], iframe[title*="chat" i], iframe[title*="messag" i], [class*="chat-widget" i], [id*="chat-widget" i]')
    .forEach(e => { if (e === document.body || e === document.documentElement || e.contains(document.querySelector('main, h1'))) return; hide(e); });
  // full-screen dimming overlays that sit behind a consent dialog (fixed, semi-transparent, no own content)
  document.querySelectorAll('body *').forEach(e => {
    const s = getComputedStyle(e); if (s.position !== 'fixed') return; const r = e.getBoundingClientRect();
    if (r.width < innerWidth * 0.9 || r.height < innerHeight * 0.9) return;
    const a = (s.backgroundColor.match(/[\d.]+/g) || []).map(Number); const alpha = a.length < 4 ? (a.length ? 1 : 0) : a[3];
    if (alpha > 0.05 && alpha < 0.95 && !e.querySelector('h1, main, img, video') && (e.innerText || '').trim().length < 400 && /cookie|consent|privacy/i.test((e.innerText || '') + ' ' + e.id + ' ' + e.className)) hide(e);
    if (alpha > 0.05 && alpha < 0.95 && (e.innerText || '').trim().length < 3 && !e.querySelector('img, video, canvas, svg')) hide(e);
  });
  // any custom element with a shadow root that mentions cookies and floats above the page
  document.querySelectorAll('body > *').forEach(e => { if (e.shadowRoot && words.test((e.shadowRoot.textContent || '').slice(0, 6000))) hide(e); });
  document.documentElement.style.setProperty('overflow', 'hidden', 'important');
  return out + '|hidden:' + hidden;
})()
