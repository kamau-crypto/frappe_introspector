# NGINX ERPNEXT SETUP FOR REDUCED LATENCY

- After deploying a erpnext site, sometimes, the resulting nginx config results in higher waiting times between a server request and response. To fix this, we have to modify the nginx server blocks for our sites to improve the configurations for performance gains however slight they might be.
## Solution

-  Navigate to the location where we have our erpnext **nginx.conf** file, and then we can replace the 

- Working with NGINX for serving https requests faster, I ran into the following errors. How can I remove the errors and move them into some sensible locale

```bash
upstream frappe-bench-frappe {
        server 127.0.0.1:8000 fail_timeout=0;
        keepalive 32;  # Enable connection pooling
}

upstream frappe-bench-socketio-server {
        server 127.0.0.1:9000 fail_timeout=0;
        keepalive 16;  # Enable connection pooling
}

# Proxy cache configuration
proxy_cache_path /var/cache/nginx/frappe levels=1:2 keys_zone=frappe_cache:10m max_size=100m inactive=60m use_temp_path=off;

server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;

        server_name test.leofresh.co.ke;
        root /home/leofresh/frappe-bench/sites;

        # Proxy headers hash configuration
        proxy_headers_hash_max_size 1024;
        proxy_headers_hash_bucket_size 128;

        # Increased buffer sizes for better performance
        proxy_buffer_size 128k;
        proxy_buffers 8 256k;
        proxy_busy_buffers_size 512k;

        # SSL optimizations
        ssl_certificate      /etc/letsencrypt/live/test.leofresh.co.ke/fullchain.pem;
        ssl_certificate_key  /etc/letsencrypt/live/test.leofresh.co.ke/privkey.pem;
        ssl_session_timeout  1d;
        ssl_session_cache shared:SSL:50m;
        ssl_session_tickets off;
        ssl_stapling on;
        ssl_stapling_verify on;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
        ssl_ecdh_curve secp384r1;
        ssl_prefer_server_ciphers on;
        ssl_buffer_size 4k;  # Reduce SSL buffer for faster initial response

        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "same-origin, strict-origin-when-cross-origin" always;

        location /assets {
                try_files $uri =404;
                add_header Cache-Control "public, max-age=31536000, immutable";
                expires 1y;
                access_log off;
        }

        location ~ ^/protected/(.*) {
                internal;
                try_files /$host/$1 =404;
        }

        location /socket.io {
                proxy_http_version 1.1;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection "upgrade";
                proxy_set_header X-Frappe-Site-Name $host;
                proxy_set_header Origin $scheme://$http_host;
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                
                # Socket.io specific timeouts
                proxy_connect_timeout 7d;
                proxy_send_timeout 7d;
                proxy_read_timeout 7d;
                
                proxy_pass http://frappe-bench-socketio-server;
                proxy_buffering off;
        }

        location / {
                rewrite ^(.+)/$ $1 permanent;
                rewrite ^(.+)/index\.html$ $1 permanent;
                rewrite ^(.+)\.html$ $1 permanent;

                location ~* ^/files/.*.(htm|html|svg|xml) {
                        add_header Content-disposition "attachment";
                        try_files /$host/public/$uri @webserver;
                }

                try_files /$host/public/$uri @webserver;
        }

        location @webserver {
                proxy_http_version 1.1;
                proxy_set_header Connection "";  # Enable keepalive to upstream
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-Proto $scheme;
                proxy_set_header X-Frappe-Site-Name $host;
                proxy_set_header Host $host;
                proxy_set_header X-Use-X-Accel-Redirect True;
                
                # Optimized timeouts
                proxy_connect_timeout 30s;
                proxy_send_timeout 60s;
                proxy_read_timeout 120s;
                proxy_redirect off;

                # Enable buffering for better performance
                proxy_buffering on;
                proxy_request_buffering on;

                proxy_pass http://frappe-bench-frappe;
        }

        error_page 502 /502.html;
        location /502.html {
                root /usr/local/lib/python3.12/dist-packages/bench/config/templates;
                internal;
        }

        # Performance optimizations
        sendfile on;
        tcp_nopush on;
        tcp_nodelay on;
        keepalive_timeout 65;
        keepalive_requests 100;
        
        client_max_body_size 50m;
        client_body_buffer_size 128k;
        client_header_buffer_size 2k;
        large_client_header_buffers 4 8k;

        # Gzip compression
        gzip on;
        gzip_vary on;
        gzip_proxied any;
        gzip_comp_level 6;
        gzip_min_length 1000;
        gzip_http_version 1.1;
        gzip_types
                application/atom+xml
                application/javascript
                application/json
                application/rss+xml
                application/vnd.ms-fontobject
                application/x-font-ttf
                application/font-woff
                application/x-web-app-manifest+json
                application/xhtml+xml
                application/xml
                font/opentype
                image/svg+xml
                image/x-icon
                text/css
                text/plain
                text/x-component;
        gzip_disable "msie6";
}

server {
        listen 80;
        listen [::]:80;
        server_name test.leofresh.co.ke;
        return 301 https://$host$request_uri;
}

server {
        listen 443 ssl http2;
        listen [::]:443 ssl http2;

        server_name app.leofresh.co.ke;
        root /home/leofresh/frappe-bench/sites;

        # Proxy headers hash configuration
        proxy_headers_hash_max_size 1024;
        proxy_headers_hash_bucket_size 128;

        # Increased buffer sizes for better performance
        proxy_buffer_size 128k;
        proxy_buffers 8 256k;
        proxy_busy_buffers_size 512k;

        # SSL optimizations
        ssl_certificate      /etc/letsencrypt/live/app.leofresh.co.ke/fullchain.pem;
        ssl_certificate_key  /etc/letsencrypt/live/app.leofresh.co.ke/privkey.pem;
        ssl_session_timeout  1d;
        ssl_session_cache shared:SSL:50m;
        ssl_session_tickets off;
        ssl_stapling on;
        ssl_stapling_verify on;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers EECDH+AESGCM:EDH+AESGCM;
        ssl_ecdh_curve secp384r1;
        ssl_prefer_server_ciphers on;
        ssl_buffer_size 4k;  # Reduce SSL buffer for faster initial response

        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
        add_header X-Content-Type-Options nosniff always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "same-origin, strict-origin-when-cross-origin" always;

        location /assets {
                try_files $uri =404;
                add_header Cache-Control "public, max-age=31536000, immutable";
                expires 1y;
                access_log off;
        }

        location ~ ^/protected/(.*) {
                internal;
                try_files /$host/$1 =404;
        }

        location /socket.io {
                proxy_http_version 1.1;
                proxy_set_header Upgrade $http_upgrade;
                proxy_set_header Connection "upgrade";
                proxy_set_header X-Frappe-Site-Name $host;
                proxy_set_header Origin $scheme://$http_host;
                proxy_set_header Host $host;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                
                # Socket.io specific timeouts
                proxy_connect_timeout 7d;
                proxy_send_timeout 7d;
                proxy_read_timeout 7d;
                
                proxy_pass http://frappe-bench-socketio-server;
                proxy_buffering off;
        }

        location / {
                rewrite ^(.+)/$ $1 permanent;
                rewrite ^(.+)/index\.html$ $1 permanent;
                rewrite ^(.+)\.html$ $1 permanent;

                location ~* ^/files/.*.(htm|html|svg|xml) {
                        add_header Content-disposition "attachment";
                        try_files /$host/public/$uri @webserver;
                }

                try_files /$host/public/$uri @webserver;
        }

        location @webserver {
                proxy_http_version 1.1;
                proxy_set_header Connection "";  # Enable keepalive to upstream
                proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
                proxy_set_header X-Real-IP $remote_addr;
                proxy_set_header X-Forwarded-Proto $scheme;
                proxy_set_header X-Frappe-Site-Name $host;
                proxy_set_header Host $host;
                proxy_set_header X-Use-X-Accel-Redirect True;
                
                # Optimized timeouts
                proxy_connect_timeout 30s;
                proxy_send_timeout 60s;
                proxy_read_timeout 120s;
                proxy_redirect off;

                # Enable buffering for better performance
                proxy_buffering on;
                proxy_request_buffering on;

                proxy_pass http://frappe-bench-frappe;
        }

        error_page 502 /502.html;
        location /502.html {
                root /usr/local/lib/python3.12/dist-packages/bench/config/templates;
                internal;
        }

        # Performance optimizations
        sendfile on;
        tcp_nopush on;
        tcp_nodelay on;
        keepalive_timeout 65;
        keepalive_requests 100;
        
        client_max_body_size 50m;
        client_body_buffer_size 128k;
        client_header_buffer_size 2k;
        large_client_header_buffers 4 8k;

        # Gzip compression
        gzip on;
        gzip_vary on;
        gzip_proxied any;
        gzip_comp_level 6;
        gzip_min_length 1000;
        gzip_http_version 1.1;
        gzip_types
                application/atom+xml
                application/javascript
                application/json
                application/rss+xml
                application/vnd.ms-fontobject
                application/x-font-ttf
                application/font-woff
                application/x-web-app-manifest+json
                application/xhtml+xml
                application/xml
                font/opentype
                image/svg+xml
                image/x-icon
                text/css
                text/plain
                text/x-component;
        gzip_disable "msie6";
}

server {
        listen 80;
        listen [::]:80;
        server_name app.leofresh.co.ke;
        return 301 https://$host$request_uri;
}

```
