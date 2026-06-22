/**
 * Email Parser Utility
 * Converts email text/markdown to properly rendered HTML with styled links
 */

/**
 * Parse email body and convert markdown-style links to proper HTML
 * Matches patterns like: "text (URL)" or "text [URL]" or bare URLs
 * Returns JSX-compatible object with paragraphs and links
 */
export const parseEmailBody = (bodyText) => {
  if (!bodyText) return [];

  // Split by lines to preserve paragraph structure
  const lines = bodyText.split('\n');
  const result = [];

  lines.forEach((line, lineIndex) => {
    if (!line.trim()) {
      result.push({ type: 'empty', key: `empty-${lineIndex}` });
      return;
    }

    // Parse the line for links
    const parsed = parseLineForLinks(line);
    result.push({ type: 'paragraph', content: parsed, key: `line-${lineIndex}` });
  });

  return result;
};

/**
 * Parse a single line for URLs, images and styled text
 * Returns array of objects with type: 'text' | 'link' | 'image'
 */
const isImageUrl = (url) => /\.(png|jpe?g|gif|webp|svg)(\?.*)?$/i.test(url);
export const shortenUrl = (url, max = 40) => {
  try {
    const u = new URL(url);
    const host = u.hostname.replace(/^www\./, '');
    const path = u.pathname === '/' ? '' : u.pathname;
    const display = `${host}${path}`;
    if (display.length <= max) return display;
    return `${display.slice(0, max - 3)}...`;
  } catch (e) {
    return url.length > max ? `${url.slice(0, max - 3)}...` : url;
  }
};

const parseLineForLinks = (line) => {
  const result = [];
  const trimmed = line.trim();

  // Pattern 0: Explicit label formats from some newsletter/text exports
  // Example: "View image:https://...."
  // Example: "Follow image link:https://...."
  const labelUrl = trimmed.match(/^(view image|follow image link|link|url)\s*:\s*(https?:\/\/\S+)$/i);
  if (labelUrl) {
    const [, label, url] = labelUrl;
    if (isImageUrl(url)) {
      return [{ type: 'text', content: `${label}: ` }, { type: 'image', url }];
    }
    return [{ type: 'text', content: `${label}: ` }, { type: 'link', text: shortenUrl(url), url }];
  }

  // Pattern 1: "text (URL)" or "text [URL]"
  const linkPattern1 = /^(.+?)\s*[\(\[]((?:https?:\/\/)\S+)[\)\]]\s*$/;
  const match1 = line.match(linkPattern1);
  if (match1) {
    const [, text, url] = match1;
    if (isImageUrl(url)) {
      return [ { type: 'text', content: text.trim() }, { type: 'image', url } ];
    }
    return [ { type: 'text', content: text.trim() }, { type: 'link', text: shortenUrl(url), url } ];
  }

  // Pattern 2: split on URLs
  const urlRegex = /(\bhttps?:\/\/[^\s\)]+)/g;
  const parts = line.split(urlRegex);

  parts.forEach((part) => {
    if (!part) return;
    if (part.match(urlRegex)) {
      if (isImageUrl(part)) {
        result.push({ type: 'image', url: part });
      } else {
        result.push({ type: 'link', text: shortenUrl(part), url: part });
      }
    } else {
      result.push({ type: 'text', content: part });
    }
  });

  return result.length > 0 ? result : [{ type: 'text', content: line }];
};

/**
 * Component to render parsed email body with proper styling
 */
export const EmailBodyRenderer = ({ bodyText, className = '' }) => {
  const parsed = parseEmailBody(bodyText);

  return (
    <div className={`whitespace-pre-wrap font-sans text-slate-800 text-[15px] leading-relaxed ${className}`}>
      {parsed.map((paragraph) => {
        if (paragraph.type === 'empty') {
          return <div key={paragraph.key} className="h-4" />;
        }

        if (paragraph.type === 'paragraph') {
          return (
            <p key={paragraph.key} className="mb-2">
              {paragraph.content.map((item, idx) => {
                if (item.type === 'text') {
                  return (
                    <span key={`${paragraph.key}-text-${idx}`}>
                      {item.content}
                    </span>
                  );
                }

                if (item.type === 'link') {
                  return (
                    <a
                      key={`${paragraph.key}-link-${idx}`}
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 hover:underline visited:text-purple-600 transition-colors break-words"
                      title={item.url}
                    >
                      {item.text}
                    </a>
                  );
                }

                if (item.type === 'image') {
                  return (
                    <div key={`${paragraph.key}-img-${idx}`} style={{ margin: '8px 0' }}>
                      <img src={item.url} alt="inline" className="max-w-full rounded shadow-sm" />
                    </div>
                  );
                }

                return null;
              })}
            </p>
          );
        }

        return null;
      })}
    </div>
  );
};

const sanitizeHtml = (html) => {
  if (!html) return '';
  try {
    if (typeof window === 'undefined' || !window.DOMParser) return html;
    const parser = new window.DOMParser();
    const doc = parser.parseFromString(html, 'text/html');

    doc.querySelectorAll('script, iframe, object, embed').forEach((n) => n.remove());
    doc.querySelectorAll('*').forEach((node) => {
      [...node.attributes].forEach((attr) => {
        const key = attr.name.toLowerCase();
        const val = String(attr.value || '');
        if (key.startsWith('on')) {
          node.removeAttribute(attr.name);
          return;
        }
        if ((key === 'href' || key === 'src') && val.toLowerCase().startsWith('javascript:')) {
          node.removeAttribute(attr.name);
          return;
        }
      });
      if (node.tagName === 'A') {
        node.setAttribute('target', '_blank');
        node.setAttribute('rel', 'noopener noreferrer');
      }
      if (node.tagName === 'IMG') {
        node.setAttribute('loading', 'lazy');
        node.style.maxWidth = '100%';
        node.style.height = 'auto';
        node.style.borderRadius = '8px';
      }
    });
    return doc.body.innerHTML;
  } catch (e) {
    return html;
  }
};

export const EmailContentRenderer = ({ bodyText, bodyHtml, className = '' }) => {
  if (bodyHtml && bodyHtml.trim()) {
    const safeHtml = sanitizeHtml(bodyHtml);
    return (
      <div
        className={`prose max-w-none prose-a:text-blue-600 prose-img:rounded-lg ${className}`}
        dangerouslySetInnerHTML={{ __html: safeHtml }}
      />
    );
  }

  const parsed = parseEmailBody(bodyText);

  return (
    <div className={`whitespace-pre-wrap font-sans text-slate-800 text-[15px] leading-relaxed ${className}`}>
      {parsed.map((paragraph) => {
        if (paragraph.type === 'empty') {
          return <div key={paragraph.key} className="h-4" />;
        }

        if (paragraph.type === 'paragraph') {
          return (
            <p key={paragraph.key} className="mb-2">
              {paragraph.content.map((item, idx) => {
                if (item.type === 'text') {
                  return (
                    <span key={`${paragraph.key}-text-${idx}`}>
                      {item.content}
                    </span>
                  );
                }

                if (item.type === 'link') {
                  return (
                    <a
                      key={`${paragraph.key}-link-${idx}`}
                      href={item.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 hover:underline visited:text-purple-600 transition-colors break-words"
                      title={item.url}
                    >
                      {item.text}
                    </a>
                  );
                }

                if (item.type === 'image') {
                  return (
                    <div key={`${paragraph.key}-img-${idx}`} style={{ margin: '8px 0' }}>
                      <img src={item.url} alt="inline" className="max-w-full rounded shadow-sm" />
                    </div>
                  );
                }

                return null;
              })}
            </p>
          );
        }

        return null;
      })}
    </div>
  );
};

/**
 * Extract all links from email body
 */
export const extractLinksFromEmail = (bodyText) => {
  const links = [];
  const urlRegex = /https?:\/\/[^\s\)]+/g;
  let match;

  const source = bodyText || '';
  while ((match = urlRegex.exec(source)) !== null) {
    links.push(match[0]);
  }

  // Also parse href links if the source contains HTML.
  try {
    if (typeof window !== 'undefined' && window.DOMParser && /<a\s/i.test(source)) {
      const parser = new window.DOMParser();
      const doc = parser.parseFromString(source, 'text/html');
      doc.querySelectorAll('a[href]').forEach((a) => {
        const href = a.getAttribute('href');
        if (href && /^https?:\/\//i.test(href)) links.push(href);
      });
    }
  } catch (e) {
    // no-op
  }

  return [...new Set(links)]; // Remove duplicates
};

/**
 * Generate plain text preview from email body (for list view)
 */
export const getEmailPreview = (bodyText, length = 100) => {
  if (!bodyText) return '';
  
  // Remove URLs for cleaner preview
  const textOnly = bodyText
    .replace(/https?:\/\/[^\s\)]+/g, '')
    .replace(/[\(\)\[\]]/g, '')
    .trim();
  
  return textOnly.substring(0, length);
};
