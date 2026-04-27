# 🛰️ Wormlogic VPS Services

> Public edge + private backbone for the Wormlogic homelab

This repository defines the **VPS layer** of the Wormlogic infrastructure.  
It acts as the **entry point, VPN hub, and public service host**, connecting the internet to a private homelab network.

---

## 🧠 Philosophy

Wormlogic infrastructure is built around a few core principles:

- 🔁 **Reproducible** — rebuild everything from scratch with minimal steps  
- 🔐 **Private-first** — internal services are never exposed directly  
- 🧩 **Composable** — clean separation between host, VPN, and services  
- 📡 **Remote-native** — full LAN access from anywhere  

---

## 🏗️ Architecture

```
        Internet
            │
            ▼
       VPS (vps01)
   ┌─────────────────┐
   │  WireGuard Hub  │
   │  Caddy (public) │
   │  Docker stack   │
   └────────┬────────┘
            │
            ▼
     WireGuard Tunnel
            │
            ▼
     server01 (LAN)
            │
            ▼
     Homelab Services
```

---

## 🚀 Responsibilities

### 🔐 WireGuard Hub
- Accepts connections from:
  - laptop clients
  - server01 (homelab gateway)
- Routes traffic between peers
- Enables remote LAN access

---

### 🌐 Caddy (Public Edge)
- Handles HTTPS (Let's Encrypt)
- Routes domains to containers
- Hosts public services

---

### 🐳 Docker Stack
Defined in:

```
compose.yml
```

Runs:
- Caddy
- public-facing apps
- future edge services

---

### 🩺 Monitoring

Located in:

```
monitoring/
```

- systemd timers
- health checks
- integrates with your notification system

---

## 📂 Structure

```
vps-services/
├── compose.yml
├── caddy/
│   ├── Caddyfile
│   └── sites/
├── wireguard/
│   └── wg0.conf.example
├── secrets/
│   └── wg0.conf
├── systemd/
│   └── wormlogic-wireguard-forwarding.service
├── monitoring/
│   ├── scripts/
│   └── systemd/
├── scripts/
│   ├── install.sh
│   ├── deploy.sh
│   └── status.sh
└── .env.example
```

---

## ⚙️ Setup

### 1. Clone

```
git clone https://github.com/matthewjgarry/vps-services.git
cd vps-services
```

---

### 2. Provide secrets

Create:

```
secrets/wg0.conf
```

Based on:

```
wireguard/wg0.conf.example
```

---

### 3. Install

```
./scripts/install.sh
```

---

## 🔁 WireGuard Forwarding

Handled by:

```
systemd/wormlogic-wireguard-forwarding.service
```

Ensures:

- ip_forward enabled
- wg0 ↔ wg0 routing allowed
- Docker does not block VPN traffic

---

## 🔍 Verification

```
sudo wg show
cat /proc/sys/net/ipv4/ip_forward
docker ps
```

---

## 🔗 Integration

### linux-environments
- laptop01 → VPN client
- server01 → LAN gateway

### docker-services
- runs homelab services
- accessed via VPN + internal DNS

---

## 🧭 Traffic Flow

```
laptop01
  ↓
WireGuard
  ↓
vps01
  ↓
WireGuard
  ↓
server01
  ↓
LAN services
```

---

## 🔐 Security Model

- No direct LAN exposure
- VPN required for access
- Public services isolated
- Internal DNS only available over VPN

---

## 🚧 Future

- automated peer management
- VPN monitoring integration
- multi-VPS failover
- metrics/observability

---

## 🧬 Wormlogic

```
{~} wormlogic
```

Minimal. Reproducible. Automated.
