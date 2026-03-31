# AI Feed Design System

> Anthropic-inspired warm cream design language

---

## Color Palette

### Backgrounds

| Token | Hex | Usage |
|-------|-----|-------|
| `cream` | `#faf9f5` | Primary background, sidebar, cards |
| `cream-dark` | `#f0eee6` | Secondary background, inputs, hover states, collapsed sections |
| `cream-content` | `#f5f3ec` | Main content area background |

### Text

| Token | Hex | Usage |
|-------|-----|-------|
| `ink` | `#141413` | Primary text, headings |
| `ink-secondary` | `#878680` | Secondary text, labels, timestamps |
| `ink-muted` | `#b0aea5` | Placeholder text, disabled states, dividers |

### Accent Colors

| Token | Hex | Usage |
|-------|-----|-------|
| `accent` (Terracotta) | `#c6613f` | Primary accent: unread dots, active highlights, hover effects, CTA buttons |
| `accent-sage` (Sage Green) | `#5c7a6e` | Success states, sync indicator, secondary tags |
| `accent-brown` (Warm Brown) | `#8b7355` | Code/language badges, tertiary tags |
| `accent-plum` (Plum) | `#6b5b73` | Paper/topic tags, quaternary accent |

### Borders

| Level | Value | Usage |
|-------|-------|-------|
| Light | `rgba(20,20,19,0.06)` | Card borders, subtle dividers |
| Default | `rgba(20,20,19,0.08)` | Input borders, section dividers |
| Dark | `rgba(20,20,19,0.12)` | Hover borders, active states |

---

## Typography

| Role | Font Stack | Weight |
|------|-----------|--------|
| Content / Body | `'Source Serif 4', Georgia, serif` | 400, 500, 600, 700 |
| UI / Interface | `'Inter', -apple-system, BlinkMacSystemFont, sans-serif` | 400, 500, 600, 700 |
| Code / Monospace | `'SF Mono', 'Fira Code', 'Consolas', monospace` | 500, 600 |

### Font Import

```css
@import url('https://fonts.googleapis.com/css2?family=Source+Serif+4:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap');
```

---

## Components

### Cards

```css
.card {
  background-color: #faf9f5;
  border: 1px solid rgba(20,20,19,0.06);
  border-radius: 16px;
  padding: 20px;
  transition: all 0.2s;
}

.card:hover {
  border-color: rgba(20,20,19,0.12);
  box-shadow: 0 2px 8px rgba(0,0,0,0.04);
}
```

### Tags / Pills

Tags use **10% opacity** of their accent color as background:

```css
/* Terracotta */
.tag-terra { background: rgba(198,97,63,0.10); color: #c6613f; }

/* Sage */
.tag-sage { background: rgba(92,122,110,0.10); color: #5c7a6e; }

/* Brown */
.tag-brown { background: rgba(139,115,85,0.10); color: #8b7355; }

/* Plum */
.tag-plum { background: rgba(107,91,115,0.10); color: #6b5b73; }

/* Neutral */
.tag-neutral { background: rgba(20,20,19,0.06); color: #141413; }
```

```css
.tag {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 6px;
  font-weight: 500;
  white-space: nowrap;
}
```

### Navigation Items

```css
/* Default */
.nav-item {
  padding: 9px 14px;
  border-radius: 10px;
  color: #141413;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
}

.nav-item:hover {
  background-color: rgba(20,20,19,0.03);
}

/* Active — inverted dark */
.nav-item.active {
  background-color: #141413;
  color: #faf9f5;
}

/* Active badge */
.nav-badge {
  font-size: 11px;
  font-weight: 600;
  color: #c6613f;
  background: rgba(198,97,63,0.10);
  padding: 2px 8px;
  border-radius: 10px;
}

.nav-item.active .nav-badge {
  color: #faf9f5;
  background: rgba(250,249,245,0.15);
}
```

### Buttons

```css
/* Primary */
.btn-primary {
  background-color: #c6613f;
  color: #ffffff;
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  transition: background-color 0.15s;
}

.btn-primary:hover {
  background-color: #b5552f;
}

/* Ghost */
.btn-ghost {
  color: #878680;
  padding: 8px 16px;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.15s;
}

.btn-ghost:hover {
  color: #141413;
  background-color: rgba(20,20,19,0.03);
}

/* Action (small, inline) */
.btn-action {
  color: #b0aea5;
  font-size: 12px;
  font-weight: 500;
  padding: 5px 10px;
  border-radius: 6px;
  transition: all 0.15s;
}

.btn-action:hover {
  color: #c6613f;
  background: rgba(198,97,63,0.06);
}
```

### Inputs

```css
.input {
  background-color: #f0eee6;
  border: 1px solid rgba(20,20,19,0.08);
  border-radius: 10px;
  padding: 10px 14px;
  font-size: 13px;
  color: #141413;
  outline: none;
  transition: border-color 0.15s;
}

.input::placeholder {
  color: #b0aea5;
}

.input:focus {
  border-color: rgba(198,97,63,0.3);
  box-shadow: 0 0 0 3px rgba(198,97,63,0.08);
}
```

### Avatar Circles

```css
.avatar {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  color: #faf9f5;
  /* background-color set per person */
}
```

Preset avatar colors cycle through: `#141413`, `#c6613f`, `#5c7a6e`, `#8b7355`, `#6b5b73`

### Unread Indicator

```css
.unread-dot {
  width: 7px;
  height: 7px;
  background-color: #c6613f;
  border-radius: 50%;
}
```

### Sync Status Indicator

```css
/* Idle */
.sync-dot-idle { background-color: #5c7a6e; }

/* Running */
.sync-dot-running { background-color: #c6613f; }

/* Error */
.sync-dot-error { background-color: #e74c3c; }
```

---

## Special States

### Timeline Active Node

```css
.timeline-dot.active {
  background-color: #c6613f;
  border-color: #c6613f;
  box-shadow: 0 0 0 4px rgba(198,97,63,0.15);
}
```

### Collapsed / Expandable Content

```css
.collapsed-content {
  background-color: #f0eee6;
  border-radius: 10px;
  border-left: 3px solid rgba(20,20,19,0.08);
  padding: 12px 16px;
  color: #878680;
  font-style: italic;
}
```

### Modal Overlay

```css
.modal-overlay {
  background-color: rgba(20,20,19,0.3);
  backdrop-filter: blur(4px);
}

.modal-content {
  background-color: #faf9f5;
  border: 1px solid rgba(20,20,19,0.08);
  border-radius: 16px;
  box-shadow: 0 24px 48px rgba(0,0,0,0.12);
}
```

### Date Divider

```css
.date-divider {
  display: flex;
  align-items: center;
  gap: 12px;
}

.date-divider-label {
  font-size: 12px;
  font-weight: 600;
  color: #b0aea5;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.date-divider-line {
  flex: 1;
  height: 1px;
  background-color: rgba(20,20,19,0.06);
}
```

### Scrollbar

```css
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(20,20,19,0.08); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(20,20,19,0.15); }
```

---

## Tailwind Configuration

```typescript
// tailwind.config.ts
export default {
  theme: {
    extend: {
      colors: {
        cream:  { DEFAULT: '#faf9f5', dark: '#f0eee6', content: '#f5f3ec' },
        ink:    { DEFAULT: '#141413', secondary: '#878680', muted: '#b0aea5' },
        accent: { DEFAULT: '#c6613f', sage: '#5c7a6e', brown: '#8b7355', plum: '#6b5b73' },
        border: { light: 'rgba(20,20,19,0.06)', DEFAULT: 'rgba(20,20,19,0.08)', dark: 'rgba(20,20,19,0.12)' },
      },
      fontFamily: {
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        sans:  ['Inter', '-apple-system', 'BlinkMacSystemFont', 'sans-serif'],
      },
      borderRadius: {
        card: '16px',
      },
    },
  },
}
```

---

## Design Principles

1. **Warm, not cold** — Cream backgrounds instead of pure white or dark mode
2. **Restrained accent** — Terracotta `#c6613f` used sparingly for emphasis, never overwhelming
3. **Serif for content, sans for UI** — Source Serif 4 brings editorial elegance to body text
4. **Generous whitespace** — Let content breathe, avoid visual clutter
5. **Subtle depth** — Borders and shadows are barely visible, creating soft layering
6. **Inverted navigation** — Active nav items use dark `#141413` background for clear focus
7. **10% opacity tags** — Topic tags use their accent color at 10% opacity for gentle categorization
