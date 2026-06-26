# ProTify Shuffle · BG Practice

A lightweight web app for practicing Bhagavad Gita verses by playing either odd or even shlokas, while inserting a pause equal to the duration of the skipped verse between selections.

## Features
- Chapter selector for future expansion
- Playback modes for odd, even, or all verses
- Gap timing based on the skipped verse's duration
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

## Custom domain (Namecheap)
The safest option is to use a subdomain such as `bg.protify-shuffle.com` so you do not interfere with your existing root domain usage. Point that subdomain to GitHub Pages using a CNAME record.

## AWS Lightsail deployment
If you prefer a custom server instead of GitHub Pages:
1. Launch an Ubuntu Lightsail instance.
2. Open ports 80 and 443.
3. Install Nginx.
4. Upload the project files into `/var/www/bg-practice`.
5. Configure Nginx to serve that directory.

A ready-to-use deployment script is included at `deploy.sh`.

## Deployment notes for the Namecheap domain
- Use a subdomain such as `bg.protify-shuffle.com` rather than the root domain if the root is already in use.
- In GitHub Pages, add the custom domain under Settings → Pages.
- In Namecheap, add a CNAME record:
  - Host: `bg`
  - Value: `<your-username>.github.io`

If you want the root domain to act as a landing page for both apps, deploy this repository to a subdomain and keep your existing ProTify Shuffle app at the main domain.
