#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/var/www/bg-practice"

sudo mkdir -p "$APP_DIR"
sudo rsync -av --delete ./ "$APP_DIR"/

sudo tee /etc/nginx/sites-available/bg-practice >/dev/null <<'EOF'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    root /var/www/bg-practice;
    index index.html;

    location / {
        try_files $uri $uri/ =404;
    }
}
EOF

sudo ln -sf /etc/nginx/sites-available/bg-practice /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx

echo "Deployment complete. Visit your server IP to see the site."
