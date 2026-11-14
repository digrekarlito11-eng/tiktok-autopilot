#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <command...>" >&2
  exit 2
fi

# En mode DRY-RUN, on ne déclenche pas de rotation proxy lourde
if [ "${DRY_RUN:-false}" = "true" ]; then
  exec "$@"
fi

SOCKS_PID=""
cleanup() {
  if [ -n "${SOCKS_PID:-}" ]; then
    kill "$SOCKS_PID" 2>/dev/null || true
    wait "$SOCKS_PID" 2>/dev/null || true
    SOCKS_PID=""
  fi
}
trap cleanup EXIT

resolve_probe_url() {
  if [ -n "${PROBE_VIDEO_URL:-}" ]; then
    echo "$PROBE_VIDEO_URL"
    return 0
  fi
  if [ -n "${FORCE_VIDEO_ID:-}" ]; then
    echo "https://www.youtube.com/watch?v=${FORCE_VIDEO_ID}"
    return 0
  fi
  local next_url=""
  next_url=$(python - <<'PY' 2>/dev/null || true
import contextlib, io
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    from src.library_autopilot import LibraryAutopilot
    items = LibraryAutopilot().get_unprocessed_videos()
if items and items[0].get("url"):
    print(items[0]["url"])
PY
  )
  next_url=$(printf '%s\n' "$next_url" | grep -E '^https?://' | head -n 1 || true)
  if [ -n "$next_url" ]; then
    echo "$next_url"
  else
    echo "https://www.youtube.com/watch?v=g2cfTnE_Hpw"
  fi
}

PROBE_URL="$(resolve_probe_url)"
echo "🔍 [YouTube-Network] Cible de vérification : $PROBE_URL"

probe_youtube() {
  local proxy="${1:-}"
  local common_args=(--simulate --no-warnings --no-playlist)
  if [ -n "$proxy" ]; then
    common_args+=(--proxy "$proxy")
  fi
  if [ -n "${YOUTUBE_COOKIES_FILE:-}" ] && [ -f "$YOUTUBE_COOKIES_FILE" ]; then
    common_args+=(--cookies "$YOUTUBE_COOKIES_FILE")
  fi

  if timeout 20 python -m yt_dlp "${common_args[@]}" \
      --js-runtimes node --remote-components ejs:github \
      --extractor-args "youtube:player_client=tv,web_embedded;player_skip=webpage" \
      "$PROBE_URL" >/dev/null 2>&1; then
    return 0
  fi

  if timeout 20 python -m yt_dlp "${common_args[@]}" --force-ipv4 \
      --js-runtimes node --remote-components ejs:github \
      --extractor-args "youtube:player_client=tv_simply,web_safari" \
      "$PROBE_URL" >/dev/null 2>&1; then
    return 0
  fi

  if timeout 20 python -m yt_dlp "${common_args[@]}" --force-ipv4 \
      --extractor-args "youtube:player_client=android_vr" \
      "$PROBE_URL" >/dev/null 2>&1; then
    return 0
  fi

  return 1
}

# 1. Vérification rapide sur le tunnel actuel (Cloudflare WARP ou direct)
if probe_youtube ""; then
  echo "✅ [YouTube-Network] Accès YouTube validé sur le réseau actif."
  "$@"
  exit $?
fi

echo "⚠️ [YouTube-Network] Blocage YouTube détecté sur l'IP actuelle, recherche d'une route alternative..."

BAD_COLO=""
BAD_COLO=$(curl -sm5 -H "Referer: https://speed.cloudflare.com" https://speed.cloudflare.com/meta 2>/dev/null \
  | python -c 'import sys,json; d=json.load(sys.stdin); print((d.get("colo") or {}).get("iata",""))' 2>/dev/null || true)
if [ -z "$BAD_COLO" ]; then
  BAD_COLO=$(curl -sm5 https://www.cloudflare.com/cdn-cgi/trace 2>/dev/null \
    | sed -n 's/^colo=//p' | head -n 1 || true)
fi
echo "🔎 [YouTube-Network] Nœud Cloudflare initial : ${BAD_COLO:-inconnu}"

# Si le tunnel wg-quick WARP générique est actif et bloqué, on le coupe pour tester en direct / warpscout
if command -v wg-quick >/dev/null 2>&1 && ip link show warp >/dev/null 2>&1; then
  sudo wg-quick down warp >/dev/null 2>&1 || true
  if probe_youtube ""; then
    echo "✅ [YouTube-Network] Accès YouTube validé en direct sans WARP."
    "$@"
    exit $?
  fi
fi

# 2. Rotation via warpscout (compte WARP dédié + scan multi-sous-réseaux / MASQUE)
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64|amd64) WS_ARCH="linux_amd64" ;;
  aarch64|arm64) WS_ARCH="linux_arm64" ;;
  *) WS_ARCH="" ;;
esac

YT_ROUTE_FOUND=false

if [ -n "$WS_ARCH" ]; then
  WS_VER="v0.16.1"
  WS_TAR="warpscout_${WS_VER#v}_${WS_ARCH}.tar.gz"
  WS_URL="https://github.com/vernette/warpscout/releases/download/${WS_VER}/${WS_TAR}"
  echo "⬇️ [YouTube-Network] Téléchargement de warpscout (${WS_ARCH})..."
  if curl -fsSL --retry 2 "$WS_URL" | tar -xz -C /tmp warpscout 2>/dev/null; then
    chmod +x /tmp/warpscout
    ACCT_FILE="/tmp/warpscout-account.json"
    if timeout 35 /tmp/warpscout register -plain -a "$ACCT_FILE" >/tmp/ws-reg.log 2>&1; then
      echo "✅ [YouTube-Network] Compte Cloudflare WARP dédié enregistré."
      timeout 45 /tmp/warpscout scan -a "$ACCT_FILE" -p wg -n 5 -jt 12 -plain -o /tmp/ws-wg.txt >/tmp/ws-wg.out 2>&1 || true
      timeout 35 /tmp/warpscout scan -a "$ACCT_FILE" -p masque -n 3 -jt 8 -plain -o /tmp/ws-masque.txt >/tmp/ws-masque.out 2>&1 || true

      CANDIDATES=$(python - "$BAD_COLO" <<'PY'
import re, sys

bad_colo = (sys.argv[1] or "").strip().upper()
ep_re = re.compile(r"\b(\d{1,3}(?:\.\d{1,3}){3}:\d+)\b")
colo_re = re.compile(r"\b([A-Z]{3})\b")
ignore_tokens = {"RTT", "DNS", "TCP", "UDP", "TLS", "USA", "UTC", "PIN", "LOS", "SUB", "NOD", "LOC"}

def parse_file(path, proto):
    found = []
    try:
        text = open(path, "r", encoding="utf-8", errors="ignore").read()
    except OSError:
        return found
    in_torn = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            lower = stripped.lower()
            if "torn down" in lower:
                in_torn = True
            elif "best endpoint" in lower:
                in_torn = False
            continue
        if in_torn or not stripped:
            continue
        m_ep = ep_re.search(line)
        if not m_ep:
            continue
        ep = m_ep.group(1)
        cols = [c for c in colo_re.findall(line) if c not in ignore_tokens]
        if cols and line.lstrip().startswith(cols[0]):
            colo = cols[0]
        elif cols:
            colo = cols[-1]
        else:
            colo = "?"
        found.append((proto, ep, colo))
    return found

wg_items = parse_file("/tmp/ws-wg.txt", "wg") or parse_file("/tmp/ws-wg.out", "wg")
masque_items = parse_file("/tmp/ws-masque.txt", "masque") or parse_file("/tmp/ws-masque.out", "masque")

seen_ep = set()
seen_colos = set()
priority_1 = []
priority_2 = []
priority_3 = []

for proto, ep, colo in wg_items:
    if ep in seen_ep:
        continue
    seen_ep.add(ep)
    if bad_colo and colo != bad_colo and colo != "?":
        if colo not in seen_colos:
            seen_colos.add(colo)
            priority_1.append((proto, ep, colo))
        else:
            priority_2.append((proto, ep, colo))
    else:
        priority_3.append((proto, ep, colo))

unique_masque = []
seen_masque = set()
for proto, ep, colo in masque_items:
    if ep not in seen_masque:
        seen_masque.add(ep)
        unique_masque.append((proto, ep, colo))

ordered = priority_1[:5] + unique_masque[:2] + priority_2[:3] + priority_3[:3]
emitted = set()
for proto, ep, colo in ordered:
    key = (proto, ep)
    if key in emitted:
        continue
    emitted.add(key)
    print(f"{proto}|{ep}|{colo}")
PY
      )

      if [ -n "$CANDIDATES" ]; then
        while IFS='|' read -r proto ep colo; do
          [ -n "$ep" ] || continue
          echo "🧪 [YouTube-Network] Test tunnel WARP : proto=$proto endpoint=$ep (colo=${colo})"
          cleanup
          /tmp/warpscout socks -a "$ACCT_FILE" -p "$proto" -e "$ep" -l 127.0.0.1 -P 18080 >/tmp/ws-socks.log 2>&1 &
          SOCKS_PID=$!

          ready=false
          for _ in $(seq 1 16); do
            if ! kill -0 "$SOCKS_PID" 2>/dev/null; then
              break
            fi
            if python -c "import socket; s=socket.create_connection(('127.0.0.1', 18080), 0.5); s.close()" 2>/dev/null; then
              ready=true
              break
            fi
            sleep 0.5
          done

          if [ "$ready" = "true" ]; then
            tunnel_colo=$(curl --socks5-hostname 127.0.0.1:18080 -sm6 https://www.cloudflare.com/cdn-cgi/trace 2>/dev/null | sed -n 's/^colo=//p' | head -n 1 || true)
            if [ -z "$tunnel_colo" ]; then
              echo "⚠️ [YouTube-Network] Tunnel $proto ($ep) inactif (échec trace HTTP), passage au suivant."
              cleanup
              continue
            fi
            echo "📡 [YouTube-Network] Tunnel $proto ($ep) connecté (colo réel : $tunnel_colo)"
            if probe_youtube "socks5h://127.0.0.1:18080"; then
              echo "✅ [YouTube-Network] Route YouTube débloquée via $proto ($ep, colo=${tunnel_colo}) !"
              export YT_DLP_PROXY="socks5h://127.0.0.1:18080"
              YT_ROUTE_FOUND=true
              break
            fi
          fi
          cleanup
        done <<< "$CANDIDATES"
      else
        echo "⚠️ [YouTube-Network] Aucun endpoint exploitable remonté par warpscout."
      fi
    else
      echo "⚠️ [YouTube-Network] Échec enregistrement warpscout."
      cat /tmp/ws-reg.log 2>/dev/null | tail -n 10 || true
    fi
  else
    echo "⚠️ [YouTube-Network] Impossible de télécharger warpscout depuis GitHub."
  fi
fi

if [ "$YT_ROUTE_FOUND" != "true" ] && [ "${ABORT_IF_YOUTUBE_BLOCKED:-0}" = "1" ]; then
  echo "❌ [YouTube-Network] Tous les chemins YouTube testés sur ce runner sont bloqués (code retour 1 pour bascule vers le runner de secours)."
  exit 1
fi

"$@"
