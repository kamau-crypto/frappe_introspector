. .v# TLS/SSL Management for ERPNext + Non-Bench Apps on a Shared DigitalOcean VPS

Tags: `nginx` `certbot` `erpnext` `bench` `letsencrypt` `wildcard` `dns` `ubuntu`
Topics: SSL provisioning, multitenancy, Let’s Encrypt automation, bench limitations, mixed workloads
Last Updated: 2025-11-26

## Overview

This guide consolidates a real-world troubleshooting scenario where an ERPNext installation (Frappe Bench) and a non-bench web application share the same DigitalOcean VPS. Challenges included mixing Bench-managed SSL, Certbot DNS challenges, wildcard certificate failures, and broken Bench commands under sudo.

The document describes:

The original SSL issuance failures

Why Certbot DNS-01 challenges failed

Why bench setup lets-encrypt could not run under sudo

How to inspect which domains Certbot can renew

How to set up reliable auto-renew on a mixed Nginx server

Final recommended configuration strategy

## Problem Description
Primary Problems Encountered

Wildcard Certificate Failure (*.leofresh.co.ke)

Certbot with DigitalOcean DNS plugin returned:

Incorrect TXT record errors

Permission “not authorized” errors

Root cause: The apex domain is not fully controlled by the user, or DNS records are not exclusively managed under the provided DigitalOcean API token.

bench setup lets-encrypt Failing Under sudo

Running sudo bench … caused:

ModuleNotFoundError: No module named 'bench'


Running full path (sudo /home/leofresh/.local/bin/bench) also failed.

Cause: Bench was installed per-user, not system-wide.
Sudo switches Python environment → Bench’s Python package unavailable.

Mixed Web Applications on the Same Server

ERPNext (Bench-managed nginx)

Another web application (manual nginx config)
Both require certificates → Certbot auto-renew management must coexist.

Nginx Warning

"ssl_stapling" ignored, no OCSP responder URL


Harmless

Caused by Let’s Encrypt chain not providing OCSP for development/staging certs

## Key Setbacks & Diagnostics
❌ Wildcard DNS-01 Challenge Failed

DO API token lacked delete permissions

DNS zone not fully controlled

TXT record did not propagate within 10s

CA saw a completely different TXT record

❌ Bench CLI Not Found Under sudo

/home/leofresh/.local/bin exists only in user PATH

Sudo uses its own secure_path

Symlink attempt failed because the bench python package was not installed system-wide

❌ Mixing Certbot & Bench SSL

Bench modifies /etc/nginx/conf.d

Certbot modifies /etc/letsencrypt/live

Both expect ownership of Nginx server blocks → conflict risk

✔ Certbot Certificates Already Installed

Verified using:

ls /etc/letsencrypt/live

✔ Nginx configuration valid

Verified using:

sudo nginx -t

✔ Certbot Renewal Framework Already Installed

Verified with:

sudo certbot renew --dry-run

## Solutions Implemented
### 1. Abandoned Wildcard SSL

Because:

Apex domain shared/administered by others

DigitalOcean DNS API insufficient permissions

TXT record mismatch

Decision:
Use per-subdomain SSL instead of wildcard.

### 2. Stopped Using bench setup lets-encrypt

Because:

Bench CLI not usable under sudo

Python environment mismatch

Desired domain is not exclusively ERPNext (bench-managed SSL becomes problematic)

Decision:
Use standalone Certbot-managed SSL for all domains, including ERPNext.

### 3. Certbot Certificate Issuance Flow for Each Domain

Create or renew certs manually:

sudo certbot --nginx -d test.leofresh.co.ke
sudo certbot --nginx -d app.leofresh.co.ke
sudo certbot --nginx -d web.leofresh.co.ke


Or for multiple:

sudo certbot --nginx -d app.leofresh.co.ke -d web.leofresh.co.ke

### 4. How Nginx Auto-Renew is Handled

Certbot installs a cron + systemd timer automatically:

Check timers:

systemctl list-timers | grep certbot


Check logs:

journalctl -u certbot.timer


Test renewal:

sudo certbot renew --dry-run

### 5. Checking Which Domains Are Set to Auto-Renew

Every domain has a renewal file:

ls /etc/letsencrypt/renewal


Each corresponds to a certificate, e.g.:

test.leofresh.co.ke.conf
app.leofresh.co.ke.conf
web.leofresh.co.ke.conf


Show details for one:

sudo cat /etc/letsencrypt/renewal/test.leofresh.co.ke.conf


This confirms:

Which domains are part of the certificate

Which authenticator (nginx/manual/dns) was used

Renewal methods used

## Recommended Architecture (Final Outcome)
✔ Use Certbot-only SSL for ALL domains (bench + non-bench)

Why?

Reliable

Compatible with mixed web apps

Automatic renewal works with Nginx globally

Avoids bench PATH & environment problems

✔ Do Not Add Bench SSL on This Server

Bench should only generate Nginx server blocks:

bench setup nginx
sudo nginx -t
sudo systemctl reload nginx


SSL should ONLY come from Certbot:

sudo certbot --nginx -d <domain>

## Reusable Checklist (DigitalOcean Style)
1. Check bench path
which bench

2. Validate Nginx configuration
sudo nginx -t

3. List issued certs
ls /etc/letsencrypt/live

4. List renewal configs
ls /etc/letsencrypt/renewal

5. Dry-run auto-renew
sudo certbot renew --dry-run

6. Renew one or all domains
sudo certbot --nginx -d subdomain.domain.com

## Conclusion

The final stable solution:

Stop trying to use wildcard SSL (blocked by DNS access issues)

Stop trying to use Bench’s Let’s Encrypt (broken under sudo + mixed workloads)

Use Certbot with Nginx plugin as the single SSL authority on the VPS

Allow Bench to handle only web app routing (not SSL)

Gain predictable, automatic certificate renewal for all applications (ERPNext + external)

This architecture is robust, maintainable, and compatible with DigitalOcean hosting
