# Spec: Kindle-Style Reader Theme System

Date: 2026-05-13 | Status: approved

## Context

The reading app currently has four hardcoded background colors (`theme-white/beige/green/dark`) applied as CSS classes. Fonts, spacing, and other typographic properties are set via inline React state. This makes theming fragile, inconsistent between EPUB and PDF readers, and difficult to extend. The user wants a Kindle-inspired reading experience — warm paper tones, serif typography, generous spacing — as the first citizen theme.

## Design

### 1. CSS Custom Properties Theme System

Replace hardcoded inline styles and ad-hoc CSS classes with a single set of CSS custom properties on a theme container. Each theme is a data attribute or class that sets the property values.

```css
/* Base defaults */
:root {
  --reader-bg: #FFFFFF;
  --reader-text: #1A1A1A;
  --reader-accent: #07c160;
  --reader-border: #E8E8E8;
  --reader-font-body: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
  --reader-font-heading: inherit;
  --reader-font-size: 16px;
  --reader-line-height: 1.8;
  --reader-paragraph-gap: 0.6em;
  --reader-text-indent: 0;
  --reader-content-width: 750px;
  --reader-content-padding: 32px 40px;
  --reader-bar-bg: rgba(255,255,255,0.85);
  --reader-bar-border: #E8E8E8;
  --reader-bar-height: 56px;
  --reader-status-height: 48px;
}

/* Kindle theme */
[data-reader-theme="kindle"] {
  --reader-bg: #F5F0E8;
  --reader-text: #3E3232;
  --reader-accent: #8B7355;
  --reader-border: #D4C5A9;
  --reader-font-body: Georgia, "Noto Serif SC", "Songti SC", "STSong", serif;
  --reader-font-heading: "Songti SC", "STSong", "KaiTi", serif;
  --reader-font-size: 16px;
  --reader-line-height: 1.9;
  --reader-paragraph-gap: 0.8em;
  --reader-text-indent: 2em;
  --reader-content-width: 680px;
  --reader-content-padding: 48px 64px;
  --reader-bar-bg: rgba(237,228,211,0.9);
  --reader-bar-border: #D4C5A9;
}
```

### 2. Kindle Theme Specifics

| Property | Value | Rationale |
|----------|-------|-----------|
| Background | `#F5F0E8` | Warm parchment, softer than pure white |
| Text color | `#3E3232` | Dark brown, not pure black — lower contrast for comfort |
| Accent | `#8B7355` | Links, highlights, progress bar |
| Body font | `Georgia, "Noto Serif SC", "Songti SC", serif` | Western serif + Chinese Songti |
| Heading font | `"Songti SC", "STSong", "KaiTi", serif` | Traditional Chinese serif |
| Font size | `16px` | Slightly larger for Chinese readability |
| Line height | `1.9` | Generous spacing, book-like |
| Text indent | `2em` | Chinese paragraph convention |
| Content width | `680px` | ~40 Chinese characters per line (optimal) |
| Bar background | `rgba(237,228,211,0.9)` | Book-liner feel, semi-transparent |

Optional: subtle paper texture via inline SVG noise as `background-image` on the content container.

### 3. Layout

```
┌──────────────────────────────────────┐
│ ← Back   Title        Aa ☰ ⛶  🔖  │  Toolbar (floating, auto-hide)
├──────────────────────────────────────┤
│                                      │
│         Chapter Title                │  Centered, serif heading, 22px
│                                      │
│    Paragraph text with 2em indent…   │  680px centered content
│    Line height 1.9, generous gaps…   │  CSS variable-controlled
│                                      │
│                                      │
│              ← 1 / 420 →             │  Page nav (floating, frosted glass pill)
├──────────────────────────────────────┤
│       Page 1 · 420 total · 0.2%     │  Status bar
└──────────────────────────────────────┘
```

- **Toolbar**: Fixed top, semi-transparent, hides on scroll-down, reveals on scroll-up/mouse-to-top
- **Page navigation**: Floating pill at bottom-center of content area, frosted glass effect (`backdrop-filter: blur`). Contains left arrow, page indicator, right arrow
- **Status bar**: Fixed bottom, shows page/total/percentage, centered, 11px muted text
- **Content area**: Fills remaining space, vertically centered when content is short

### 4. Page Navigation & Keyboard

- **Keyboard**: `←` prev page/chapter, `→` next page/chapter, `Space` next page (already implemented in Reader.tsx)
- **Click zones**: Left 20% of content area = prev, right 20% = next
- **Floating pill**: Left/right arrow buttons with page indicator
- **Chapters**: In HtmlEpubReader, "page" = chapter. Prev/next buttons navigate between chapters
- **PDF**: Each page = one PDF page

### 5. Reader Component Changes

**Reader.tsx** — replace inline `readerStyle` and ad-hoc theme classes with CSS variables:
- Remove `readerStyle` object (fontSize, lineHeight, maxWidth)
- Set `data-reader-theme` attribute on root reader div
- Remove `THEME_CLASSES` map, replace with theme name state
- Keep all existing state (readingMode, autoFlip, blueLight, bookmarks, etc.) — unchanged
- Settings panel: update theme picker to show theme names and preview swatches

**HtmlEpubReader.tsx** — use CSS variables from parent instead of inline styles:
- Remove inline style injection for colors/fonts/sizes
- Inherit `--reader-*` custom properties from reader container
- iframe body reads CSS variables from parent via `postMessage` or inline variable copy

**PdfReader.tsx** — unchanged (already renders images), but inherits background/bar colors

**index.css** — add `[data-reader-theme]` block with all `--reader-*` variables. Add Kindle theme values under `[data-reader-theme="kindle"]`. Add `.reader-page-nav` floating pill styles. Add paper texture CSS.

### 6. Scope: What we do NOT change

- EPUB chapter loading logic (HtmlEpubReader already working)
- PDF page rendering (PdfReader already working)
- Auto-flip, blue light filter, break reminder, focus mode (all keep working)
- Keyboard shortcuts (keep working, made more visible)

## Verification

1. Open an EPUB book → warm paper background, serif fonts, 2em indent → "feels like Kindle"
2. Open a PDF book → same toolbar/status bar theming, page images centered
3. Switch theme to old ones (white/beige/green/dark) → still work via CSS variable overrides
4. Keyboard ← → turns pages in both page and scroll modes
5. Click left/right 20% zones → page turns
6. Floating pill nav → shows correct page, arrows work
7. Toolbar auto-hides on scroll down, shows on mouse-to-top
8. Settings panel → shows theme picker with Kindle option
