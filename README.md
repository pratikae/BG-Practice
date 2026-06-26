# Bhagavad Gita Practice

A lightweight static web app for practicing Bhagavad Gita verses by playing either odd or even shlokas, while inserting a pause equal to the duration of the skipped verse between selections.

## Features
- Chapter selector for future expansion
- Playback modes for odd, even, or all verses
- Gap timing based on the skipped verse's duration
- Adjustable playback speed from 0.25x to 10x in 0.25x steps
- Clean, accessible UI with a warm orange, green, and blue palette

## Local development
Run a local static server from this folder:

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000.

## GitHub Pages deployment
1. Create a GitHub repository for this project.
2. Push the contents of this folder to the repository.
3. In GitHub, open Settings → Pages.
4. Choose the main branch and the root folder.
5. Save the settings.
6. Your site will be published at `https://<your-username>.github.io/<repo-name>/`.
7. The landing page is at the root, and the practice app is at `/bg-practice.html`.

## Custom domain
If you want to use a custom domain, point a subdomain such as `bg.yourdomain.com` to GitHub Pages using a CNAME record.

## Static hosting notes
This app is designed to be fully static, so it can be hosted on GitHub Pages or any other simple static host without a backend.
