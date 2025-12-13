# ProxyTorrent Marketing Site

This directory contains the static marketing website for ProxyTorrent, designed to be hosted via GitHub Pages.

## Structure

```
site/
├── index.html          # Root redirect to English version
├── assets/
│   └── style.css       # Shared stylesheet for all languages
├── en/
│   └── index.html      # English landing page (default)
├── ru/
│   └── index.html      # Russian landing page
├── ar/
│   └── index.html      # Arabic landing page (RTL layout)
└── zh/
    └── index.html      # Chinese landing page
```

## Features

- **Single-page design**: Hero, Why, How it Works, Features, Use Cases, Get Started, Footer
- **4 languages**: English (default), Russian, Arabic (RTL), Chinese
- **Language switcher**: Easy navigation between translations
- **Responsive design**: Mobile-friendly, accessible contrast
- **No build required**: Pure HTML/CSS, no external dependencies
- **GitHub-friendly**: Fast loading, optimized for GitHub Pages
- **SEO optimized**: Meta tags and Open Graph support for each language
- **Documentation links**: Points to existing repo docs (README, QUICKSTART, ARCHITECTURE, etc.)

## GitHub Pages Setup

To enable GitHub Pages for this marketing site:

1. **Go to Repository Settings**
   - Navigate to your repository on GitHub
   - Click on **Settings** (top right)

2. **Configure GitHub Pages**
   - In the left sidebar, click **Pages** (under "Code and automation")
   - Under **Source**, select **Deploy from a branch**
   - Under **Branch**, select:
     - Branch: `main` (or your default branch)
     - Folder: `/site`
   - Click **Save**

3. **Wait for Deployment**
   - GitHub will automatically build and deploy your site
   - This usually takes 1-2 minutes
   - You'll see a notification with the URL once ready

4. **Access Your Site**
   - Your site will be available at: `https://[username].github.io/[repository]/`
   - For this repo: `https://nickscherbakov.github.io/proxytorrent/`
   - The root will redirect to the English version (`/en/`)

## Language Routes

Each language is available at a distinct path:

- **English**: `/site/en/` (default)
- **Russian**: `/site/ru/`
- **Arabic**: `/site/ar/`
- **Chinese**: `/site/zh/`

The root `/site/` redirects to `/site/en/` by default.

## Local Development

To test the site locally:

### Option 1: Python HTTP Server
```bash
cd site
python3 -m http.server 8080
# Visit http://localhost:8080
```

### Option 2: Node.js HTTP Server
```bash
cd site
npx http-server -p 8080
# Visit http://localhost:8080
```

### Option 3: PHP Built-in Server
```bash
cd site
php -S localhost:8080
# Visit http://localhost:8080
```

## Customization

### Adding a New Language

1. Create a new directory: `site/[lang-code]/`
2. Copy `site/en/index.html` as a template
3. Update `<html lang="...">` attribute
4. Translate all content
5. Add RTL support if needed (see Arabic example)
6. Update language switcher in all existing pages

### Updating Styles

- Edit `site/assets/style.css`
- Changes apply globally to all language versions
- RTL-specific styles use `[dir="rtl"]` selector

### Adding Images/Icons

- Place images in `site/assets/`
- Reference them as `../assets/[filename]`
- Keep files small for fast loading

## RTL Support (Arabic)

The Arabic version includes:

- `<html dir="rtl">` attribute
- Mirrored spacing and alignment
- Arabic font stack in CSS
- Code blocks remain LTR for readability

## Browser Support

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Mobile browsers (iOS Safari, Chrome Mobile)
- Graceful degradation for older browsers

## Performance

- No external dependencies
- Single CSS file (< 10KB)
- Optimized for fast loading
- Minimal JavaScript (redirect only)

## Accessibility

- Semantic HTML structure
- High contrast color scheme
- Focus visible on interactive elements
- Reduced motion support
- Screen reader friendly

## Contributing

When making changes:

1. Test all language versions
2. Verify responsive layout on mobile
3. Check RTL layout for Arabic
4. Ensure all links work
5. Validate HTML/CSS

## License

This marketing site is part of the ProxyTorrent project and is released under the MIT License.
