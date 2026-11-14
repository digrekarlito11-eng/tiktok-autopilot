import os
import sys
import time
import json
from typing import Dict, Any, Optional, List

class TikTokStudioUploader:
    """
    Sous-agent DevOps-Bot : Navigateur Virtuel Furtif pour TikTok Studio.
    
    Permet de transférer automatiquement une vidéo et sa légende vers TikTok Studio :
    - Utilise le cookie de session TIKTOK_SESSION_ID.
    - Évite la détection robot (anti-bot stealth : désactivation de navigator.webdriver, faux user-agent, viewport HD).
    - Téléverse le fichier MP4 via le composant d'upload TikTok.
    - Renseigne l'accroche, la légende et les hashtags viraux.
    - Clique sur 'Enregistrer comme brouillon' (Draft) ou 'Publier' (Post).
    - Enregistre des captures d'écran à chaque étape pour transparence totale.
    """

    def __init__(self, session_id: Optional[str] = None, screenshots_dir: str = "output/screenshots"):
        self.session_id = session_id or os.environ.get("TIKTOK_SESSION_ID")
        self.screenshots_dir = screenshots_dir
        os.makedirs(self.screenshots_dir, exist_ok=True)

    @staticmethod
    def _normalize_same_site(value: Any) -> str:
        """Convertit les valeurs sameSite diverses vers 'Strict' | 'Lax' | 'None' (Playwright)."""
        if not value:
            return "Lax"
        s = str(value).strip().lower()
        if s in ("none", "no_restriction", "norestriction"):
            return "None"
        if s == "strict":
            return "Strict"
        return "Lax"

    @staticmethod
    def _build_cookie(
        name: str,
        value: str,
        domain: str = ".tiktok.com",
        path: str = "/",
        secure: bool = True,
        http_only: bool = True,
        same_site: Any = "Lax",
        expires: Any = None,
    ) -> Optional[Dict[str, Any]]:
        clean_name = str(name or "").strip()
        clean_value = str(value if value is not None else "").strip()
        if not clean_name or not clean_value:
            return None

        clean_domain = str(domain or ".tiktok.com").strip() or ".tiktok.com"
        clean_path = str(path or "/").strip() or "/"
        normalized_same_site = TikTokStudioUploader._normalize_same_site(same_site)
        is_secure = True if normalized_same_site == "None" else bool(secure)

        cookie: Dict[str, Any] = {
            "name": clean_name,
            "value": clean_value,
            "domain": clean_domain,
            "path": clean_path,
            "secure": is_secure,
            "httpOnly": bool(http_only),
            "sameSite": normalized_same_site,
        }

        if expires is not None and str(expires).strip() != "":
            try:
                exp_ts = int(float(expires))
                if exp_ts > 0:
                    cookie["expires"] = exp_ts
            except (TypeError, ValueError):
                pass

        return cookie

    @staticmethod
    def parse_and_prepare_cookies(raw_value: str) -> List[Dict[str, Any]]:
        """
        Normalise et prépare les cookies TikTok à partir de multiples formats :
        - Export JSON (Cookie-Editor: [{"name": "sessionid", "value": "..."}], Playwright storageState {"cookies": [...]}, ou dict simple)
        - Format Netscape cookies.txt (# Netscape HTTP Cookie File / lignes tabulées à 7 colonnes)
        - Copie directe Chrome DevTools Application -> Cookies (lignes tabulées Name\\tValue\\tDomain...)
        - Chaîne d'en-tête Cookie complète (ex: 'sessionid=7f8b...; sid_tt=...; sessionid_ss=...')
        - Format clé=valeur (ex: 'sessionid=7f8b9c...')
        - Valeur brute du sessionid (ex: '7f8b9c...')
        - Détection d'anomalies (URL collée, JSON tronqué, texte invalide) sans jamais afficher la valeur du secret
        """
        if not raw_value:
            return []

        raw = raw_value.strip()
        if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in ('"', "'"):
            raw = raw[1:-1].strip()
        if not raw:
            return []

        # Détection d'un lien web (URL) au lieu d'un cookie
        is_json_like = raw.lstrip().startswith(("[", "{"))
        if (
            raw.startswith("http://")
            or raw.startswith("https://")
            or ("tiktok.com/" in raw and "=" not in raw and "\t" not in raw and not is_json_like)
        ):
            print("⚠️ [DevOps-Bot] ANOMALIE DÉTECTÉE : TIKTOK_SESSION_ID contient un LIEN WEB (URL) au lieu d'un cookie.")
            print("💡 Explication : Vous avez collé une adresse de site web au lieu des cookies de session.")
            print("👉 Utilisez l'extension Cookie-Editor sur TikTok Studio -> Export -> Export as JSON.")
            return []

        cookies: List[Dict[str, Any]] = []
        detected_format = "inconnu"

        def _append_cookie(item: Optional[Dict[str, Any]]) -> None:
            if item is not None:
                cookies.append(item)

        # Cas 1 : Export JSON (Cookie-Editor, Playwright storageState ou dict clé/valeur)
        if (raw.startswith("[") and raw.endswith("]")) or (raw.startswith("{") and raw.endswith("}")):
            try:
                data = json.loads(raw)
                items_list: Optional[List[Any]] = None
                if isinstance(data, list):
                    items_list = data
                    detected_format = "JSON Cookie-Editor (liste)"
                elif isinstance(data, dict):
                    if isinstance(data.get("cookies"), list):
                        items_list = data["cookies"]
                        detected_format = "JSON storageState (cookies)"
                    else:
                        detected_format = "JSON dictionnaire"
                        for k, v in data.items():
                            _append_cookie(TikTokStudioUploader._build_cookie(str(k), str(v)))

                if items_list is not None:
                    for item in items_list:
                        if isinstance(item, dict) and "name" in item and "value" in item:
                            exp = item.get("expirationDate", item.get("expires", item.get("expiry")))
                            _append_cookie(
                                TikTokStudioUploader._build_cookie(
                                    name=item["name"],
                                    value=item["value"],
                                    domain=item.get("domain") or ".tiktok.com",
                                    path=item.get("path") or "/",
                                    secure=item.get("secure", True),
                                    http_only=item.get("httpOnly", True),
                                    same_site=item.get("sameSite", "Lax"),
                                    expires=exp,
                                )
                            )
            except Exception as e_json:
                print(f"⚠️ [DevOps-Bot] JSON cookies invalide ou tronqué ({e_json}). Ré-exportez via Cookie-Editor -> Export as JSON.")
                return []
        elif raw.startswith("[") or raw.startswith("{"):
            print("⚠️ [DevOps-Bot] JSON cookies tronqué détecté (accolade/crochet non fermé). Copiez tout le texte JSON sans le couper.")
            return []

        # Cas 2 : Format Netscape cookies.txt ou copie directe Chrome DevTools (tabulations)
        if not cookies and ("\t" in raw or raw.lstrip().startswith(("# Netscape", "# HTTP Cookie File"))):
            for line in raw.splitlines():
                if not line.strip():
                    continue
                stripped = line.strip()
                if stripped.startswith("#") and not stripped.startswith("#HttpOnly_"):
                    continue
                parts = line.rstrip("\r\n").split("\t")
                if len(parts) >= 7 and (
                    parts[0].strip().startswith("#HttpOnly_")
                    or parts[1].strip().upper() in ("TRUE", "FALSE")
                ):
                    detected_format = "Netscape cookies.txt"
                    raw_domain = parts[0].strip()
                    http_only = False
                    if raw_domain.startswith("#HttpOnly_"):
                        http_only = True
                        raw_domain = raw_domain[len("#HttpOnly_"):]
                    _append_cookie(
                        TikTokStudioUploader._build_cookie(
                            name=parts[5],
                            value="\t".join(parts[6:]),
                            domain=raw_domain or ".tiktok.com",
                            path=parts[2] or "/",
                            secure=(parts[3].strip().upper() == "TRUE"),
                            http_only=http_only,
                            same_site="Lax",
                            expires=parts[4],
                        )
                    )
                elif len(parts) >= 2:
                    c_name = parts[0].strip()
                    c_val = parts[1].strip()
                    if c_name.lower() == "name" and c_val.lower() == "value":
                        continue
                    detected_format = "Tableau Chrome DevTools"
                    c_domain = parts[2].strip() if len(parts) > 2 and "." in parts[2] else ".tiktok.com"
                    c_path = parts[3].strip() if len(parts) > 3 and parts[3].strip().startswith("/") else "/"
                    _append_cookie(
                        TikTokStudioUploader._build_cookie(
                            name=c_name,
                            value=c_val,
                            domain=c_domain,
                            path=c_path,
                        )
                    )
            if not cookies:
                print("⚠️ [DevOps-Bot] En-tête Netscape/tableau détecté mais aucun cookie valide n'a pu être extrait.")
                return []

        # Cas 3 : Header Cookie complet (ex: sessionid=...; sid_tt=...)
        if not cookies and ";" in raw:
            detected_format = "En-tête HTTP Cookie (;)"
            for part in raw.split(";"):
                part = part.strip()
                if "=" in part:
                    k, v = part.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                        v = v[1:-1].strip()
                    _append_cookie(TikTokStudioUploader._build_cookie(k, v))

        # Cas 4 : Multi-lignes ou format clé=valeur unique (ex: sessionid=...)
        if not cookies and "=" in raw:
            if "\n" in raw:
                detected_format = "Lignes clé=valeur"
                for line in raw.splitlines():
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    k, v = line.split("=", 1)
                    k = k.strip()
                    v = v.strip()
                    if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                        v = v[1:-1].strip()
                    _append_cookie(TikTokStudioUploader._build_cookie(k, v))
            else:
                detected_format = "Paire clé=valeur unique"
                k, v = raw.split("=", 1)
                k = k.strip()
                v = v.strip()
                if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
                    v = v[1:-1].strip()
                _append_cookie(TikTokStudioUploader._build_cookie(k, v))

        # Cas 5 : Valeur brute du token sessionid seul (un seul bloc sans espace ni retour ligne)
        if not cookies and raw:
            if "\n" in raw or any(ch.isspace() for ch in raw):
                line_count = len(raw.splitlines())
                print(
                    f"⚠️ [DevOps-Bot] Format TIKTOK_SESSION_ID non reconnu ({line_count} ligne(s), contient des espaces). "
                    "Collez soit un export JSON Cookie-Editor complet, soit le format Netscape, soit uniquement la valeur du cookie sessionid."
                )
                return []
            detected_format = "Jeton sessionid brut unique"
            _append_cookie(TikTokStudioUploader._build_cookie("sessionid", raw))

        if not cookies:
            return []

        # S'assurer que sessionid_ss est toujours présent si sessionid existe
        cookie_names = {c["name"] for c in cookies}
        if "sessionid" in cookie_names and "sessionid_ss" not in cookie_names:
            s_val = next(c["value"] for c in cookies if c["name"] == "sessionid")
            _append_cookie(TikTokStudioUploader._build_cookie("sessionid_ss", s_val))

        print(f"🔎 [DevOps-Bot] Format cookies détecté : {detected_format} ({len(cookies)} cookie(s), {len(raw)} caractères).")
        return cookies

    def _dismiss_popups(self, page) -> None:
        """Ferme les bannières de cookies, guides d'utilisation, tours React Joyride et modales superposées."""
        dismiss_selectors = [
            # Modales flottantes TikTok Studio ("Nouvelles fonctionnalités", vérifications auto, etc.)
            "div[data-floating-ui-portal] button:has-text(\"J'ai compris\")",
            "div[data-floating-ui-portal] button:has-text('Compris')",
            "div[data-floating-ui-portal] button:has-text('Got it')",
            "div[data-floating-ui-portal] button:has-text('Pas maintenant')",
            "div[data-floating-ui-portal] button:has-text('Not now')",
            # Consentement cookies
            "button:has-text('Tout accepter')",
            "button:has-text('Accepter tout')",
            "button:has-text('Accept all')",
            "button:has-text('Allow all')",
            # Guides & infobulles de démarrage
            "button:has-text(\"J'ai compris\")",
            "button:has-text('Compris')",
            "button:has-text('Got it')",
            "button:has-text('Pas maintenant')",
            "button:has-text('Not now')",
            "button:has-text('Passer')",
            "button:has-text('Skip')",
            "button:has-text('Plus tard')",
            "button:has-text('Fermer')",
            "button[aria-label='Fermer']",
            "button[aria-label='Close']",
            ".modal-close",
            ".guide-close",
        ]
        for sel in dismiss_selectors:
            try:
                loc = page.locator(sel)
                if loc.count() > 0:
                    elem = loc.first
                    if elem.is_visible():
                        print(f"🧹 [DevOps-Bot] Fermeture popup : '{sel}'")
                        elem.click(timeout=1000)
                        time.sleep(0.3)
            except Exception:
                pass

        # Suppression de secours des surcouches React Joyride et modales backdrop résiduelles
        try:
            page.evaluate("""() => {
                document.querySelectorAll('.react-joyride__overlay, #react-joyride-portal, [id^="react-joyride-step-"]')
                    .forEach(el => el.remove());
                document.querySelectorAll('[data-floating-ui-portal]')
                    .forEach(portal => {
                        if (portal.querySelector('.TUXModal-overlay')) {
                            portal.remove();
                        }
                    });
            }""")
        except Exception:
            pass

    @staticmethod
    def _find_visible_element(page, selectors: List[str]):
        """Retourne (locator, selector) pour le premier élément visible trouvé parmi les sélecteurs."""
        for sel in selectors:
            try:
                loc = page.locator(sel)
                count = loc.count()
                if count <= 0:
                    continue
                if hasattr(loc, "nth"):
                    for i in range(count):
                        elem = loc.nth(i)
                        if elem.is_visible():
                            return elem, sel
                elif loc.first.is_visible():
                    return loc.first, sel
            except Exception:
                continue
        return None, None

    @staticmethod
    def _is_button_disabled(button) -> bool:
        """Vérifie si un bouton TikTok Studio est désactivé."""
        try:
            return (
                button.get_attribute("disabled") is not None
                or button.get_attribute("aria-disabled") == "true"
                or button.get_attribute("data-disabled") == "true"
                or "disabled" in (button.get_attribute("class") or "")
            )
        except Exception:
            return False

    @staticmethod
    def _confirm_and_wait_publish(page, action_button, mode: str, screenshot_clicked_path: Optional[str] = None) -> tuple[bool, bool]:
        """
        Clique sur action_button une fois actif, valide toute modale de confirmation éventuelle
        et attend la confirmation réelle de sauvegarde/publication TikTok Studio.
        Retourne (action_clicked, success_detected).
        """
        pub_confirm_selectors = [
            "div[role='dialog'] button:has-text('Publier maintenant')",
            "div[role='dialog'] button:has-text('Publier quand même')",
            "div[role='dialog'] button:has-text('Continuer à publier')",
            "div[role='dialog'] button:has-text('Continue to post')",
            "div[role='dialog'] button:has-text('Post anyway')",
            "div[role='dialog'] button:has-text('Post now')",
            "div[role='dialog'] button:has-text('Publier')",
            "div[role='dialog'] button:has-text('Post')",
            "div[role='dialog'] button:has-text('Continuer')",
            "div[role='dialog'] button:has-text('Continue')",
            "[data-floating-ui-portal] button:has-text('Publier maintenant')",
            "[data-floating-ui-portal] button:has-text('Publier quand même')",
            "[data-floating-ui-portal] button:has-text('Post now')",
            "[data-floating-ui-portal] button:has-text('Post anyway')",
            "[data-floating-ui-portal] button:has-text('Continue to post')",
            "button:has-text('Publier maintenant')",
            "button:has-text('Publier quand même')",
            "button:has-text('Post now')",
            "button:has-text('Continue to post')",
        ]
        draft_confirm_selectors = [
            "div[role='dialog'] button:has-text('Enregistrer')",
            "div[role='dialog'] button:has-text('Save')",
            "div[role='dialog'] button:has-text('Continuer')",
            "div[role='dialog'] button:has-text('Continue')",
            "button:has-text('Post now')",
            "button:has-text('Publier maintenant')",
        ]
        confirm_selectors = draft_confirm_selectors if mode == "draft" else pub_confirm_selectors

        action_clicked = False
        print("⏳ [DevOps-Bot] Attente de l'activation du bouton...")
        for _attempt in range(30):
            if not TikTokStudioUploader._is_button_disabled(action_button):
                print("⚡ [DevOps-Bot] Le bouton est ACTIF ! Clic en cours...")
                try:
                    action_button.scroll_into_view_if_needed()
                except Exception:
                    pass
                try:
                    action_button.click(timeout=5000)
                except Exception:
                    action_button.click(force=True)
                action_clicked = True
                time.sleep(2)
                for _c_pass in range(2):
                    c_btn, c_sel = TikTokStudioUploader._find_visible_element(page, confirm_selectors)
                    if c_btn is not None:
                        print(f"✅ [DevOps-Bot] Validation modale confirmation : '{c_sel}'")
                        try:
                            c_btn.click(timeout=3000)
                        except Exception:
                            c_btn.click(force=True)
                        time.sleep(2)
                    else:
                        break
                break
            time.sleep(2)

        if screenshot_clicked_path:
            try:
                page.screenshot(path=screenshot_clicked_path)
            except Exception:
                pass

        if not action_clicked:
            return False, False

        success_detected = False
        max_wait_iters = 12 if mode == "public" else 8
        for _ in range(max_wait_iters):
            time.sleep(2)
            # Gestion d'une modale tardive (vérification copyright / confirmation post)
            c_btn, c_sel = TikTokStudioUploader._find_visible_element(page, confirm_selectors)
            if c_btn is not None:
                print(f"✅ [DevOps-Bot] Validation modale tardive : '{c_sel}'")
                try:
                    c_btn.click(timeout=3000)
                except Exception:
                    c_btn.click(force=True)
                time.sleep(2)

            current_after = (page.url or "").lower()
            try:
                body_text = (page.inner_text("body") or "").lower()
            except Exception:
                body_text = ""

            btn_gone = False
            try:
                btn_gone = not action_button.is_visible()
            except Exception:
                btn_gone = True

            draft_ok = mode == "draft" and (
                "enregistré dans les brouillons" in body_text
                or "enregistré" in body_text
                or "saved to drafts" in body_text
                or "saved" in body_text
            )
            public_ok = (
                "en cours de publication" in body_text
                or "a été publiée" in body_text
                or "vidéo publiée" in body_text
                or "en cours de mise en ligne" in body_text
                or "mis en ligne" in body_text
                or "video is being uploaded" in body_text
                or "your video has been uploaded" in body_text
                or "video published" in body_text
            )
            if (
                "tiktokstudio/content" in current_after
                or btn_gone
                or draft_ok
                or public_ok
                or "your video has been uploaded" in body_text
                or "gérer vos publications" in body_text
                or "manage your posts" in body_text
            ):
                success_detected = True
                break

        return action_clicked, success_detected

    def _validate_and_prepare_cookies(self) -> tuple[Optional[List[Dict[str, Any]]], Optional[Dict[str, Any]]]:
        """Valide TIKTOK_SESSION_ID et retourne (cookies, erreur_eventuelle)."""
        if not self.session_id:
            return None, {
                "status": "error",
                "error": "Aucun TIKTOK_SESSION_ID configuré. Impossible d'ouvrir la session TikTok Studio."
            }

        cookies = self.parse_and_prepare_cookies(self.session_id)
        if not cookies:
            return None, {
                "status": "auth_error",
                "error": "Aucun cookie TikTok valide trouvé dans TIKTOK_SESSION_ID. Vérifiez que vous avez collé l'export JSON Cookie-Editor complet ou le cookie 'sessionid' (et non un lien web)."
            }

        parsed_names = {c["name"] for c in cookies}
        if "sessionid" not in parsed_names and "sessionid_ss" not in parsed_names:
            names_preview = ", ".join(sorted(parsed_names)[:10])
            print(f"❌ [DevOps-Bot] Cookie obligatoire 'sessionid' absent de l'export (cookies reçus : {names_preview}).")
            return None, {
                "status": "auth_error",
                "error": "Le cookie indispensable 'sessionid' est absent de TIKTOK_SESSION_ID. Connectez-vous à TikTok Studio puis exportez TOUS les cookies en JSON via Cookie-Editor."
            }

        companion_keys = [k for k in ("sid_tt", "uid_tt", "sid_guard", "tt_chain_token", "store-idc", "ttwid") if k in parsed_names]
        if not companion_keys:
            print("⚠️ [DevOps-Bot] Attention : Seul 'sessionid' a été fourni sans les cookies compagnons (sid_tt, sid_guard, tt_chain_token, store-idc). Si TikTok redirige vers /login, utilisez Cookie-Editor -> Export -> Export as JSON.")

        return cookies, None

    def _launch_stealth_context(self, playwright, cookies: List[Dict[str, Any]]):
        """Lance Chromium en mode furtif, injecte les cookies et retourne (browser, context, page) ou (browser, None, None)."""
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-setuid-sandbox",
                "--window-size=1920,1080"
            ]
        )

        major_ver = (getattr(browser, "version", "") or "131.0.0.0").split(".")[0]
        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                f"Mozilla/5.0 (X11; Linux x86_64) "
                f"AppleWebKit/537.36 (KHTML, like Gecko) "
                f"Chrome/{major_ver}.0.0.0 Safari/537.36"
            ),
            locale="fr-FR",
            timezone_id="Africa/Abidjan"
        )

        context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['fr-FR', 'fr', 'en-US', 'en']
            });
            window.chrome = {
                runtime: {}
            };
            (function () {
                function dismissTour() {
                    try {
                        document.querySelectorAll('.react-joyride__overlay, #react-joyride-portal, [id^="react-joyride-step-"]')
                            .forEach(function (el) { el.remove(); });
                    } catch (e) {}
                }
                dismissTour();
                var observer = new MutationObserver(function () { dismissTour(); });
                var attach = function () {
                    if (document.documentElement) {
                        observer.observe(document.documentElement, { childList: true, subtree: true });
                    } else {
                        setTimeout(attach, 50);
                    }
                };
                attach();
            })();
        """)

        added_names: List[str] = []
        for cookie_item in cookies:
            try:
                context.add_cookies([cookie_item])
                added_names.append(cookie_item["name"])
            except Exception as e_cookie:
                print(f"⚠️ [DevOps-Bot] Cookie accessoire ignoré ({cookie_item.get('name', '?')}) : {e_cookie}")

        if not added_names:
            context.close()
            browser.close()
            return None, None, None

        print(f"🔑 [DevOps-Bot] {len(added_names)}/{len(cookies)} cookies injectés ({', '.join(added_names[:15])}{'...' if len(added_names) > 15 else ''}).")

        page = context.new_page()
        page.set_default_timeout(45000)
        page.on("dialog", lambda dialog: dialog.accept())
        return browser, context, page

    def _warmup_session(self, page) -> None:
        """Pré-charge tiktok.com pour valider le contexte et fermer les bannières initiales."""
        home_url = "https://www.tiktok.com/?lang=fr"
        print(f"🌐 [DevOps-Bot] Initialisation session sur : {home_url}")
        try:
            page.goto(home_url, wait_until="domcontentloaded", timeout=45000)
            time.sleep(2.5)
            self._dismiss_popups(page)
        except Exception as e_home:
            print(f"⚠️ [DevOps-Bot] Pré-chargement page d'accueil ignoré ({e_home})")

    @staticmethod
    def _read_studio_tab_counts(page) -> Dict[str, Optional[int]]:
        """Extrait les compteurs d'onglets Publications et Brouillons sur TikTok Studio."""
        import re
        counts: Dict[str, Optional[int]] = {"publications": None, "drafts": None}
        try:
            text = page.inner_text("body") or ""
        except Exception:
            return counts

        pub_match = re.search(r"(?:Publications|Posts)\s*(\d+)", text, re.IGNORECASE)
        draft_match = re.search(r"(?:Brouillons|Drafts)\s*(\d+)", text, re.IGNORECASE)
        if pub_match:
            counts["publications"] = int(pub_match.group(1))
        if draft_match:
            counts["drafts"] = int(draft_match.group(1))
        return counts

    @staticmethod
    def _discover_draft_rows(page) -> List[Dict[str, Any]]:
        """
        Identifie les lignes de brouillons dans TikTok Studio (/content?tab=draft) et
        étiquette chaque bouton d'édition (icône Crayon / Modifier) avec data-autopilot-edit-idx.
        """
        try:
            rows = page.evaluate(r"""() => {
                document.querySelectorAll('[data-autopilot-edit-idx]').forEach(el => {
                    el.removeAttribute('data-autopilot-edit-idx');
                });

                const isVisible = (el) => {
                    if (!el) return false;
                    const r = el.getBoundingClientRect();
                    if (r.width <= 0 || r.height <= 0) return false;
                    const st = window.getComputedStyle(el);
                    return st.display !== 'none' && st.visibility !== 'hidden' && st.opacity !== '0';
                };

                const findEditTargetInRow = (rowEl) => {
                    const explicitSelectors = [
                        "button[data-e2e*='edit' i]",
                        "[role='button'][data-e2e*='edit' i]",
                        "[aria-label*='Modifier' i]",
                        "[aria-label*='Edit' i]",
                        "[aria-label*='Éditer' i]",
                        "[title*='Modifier' i]",
                        "[title*='Edit' i]",
                        "button[data-testid*='edit' i]",
                        "a[href*='tiktokstudio/upload']",
                        "a[href*='/upload']",
                    ];
                    for (const sel of explicitSelectors) {
                        const candidates = Array.from(rowEl.querySelectorAll(sel)).filter(isVisible);
                        if (candidates.length > 0) {
                            return { target: candidates[0], strategy: 'explicit:' + sel };
                        }
                    }

                    const textBtns = Array.from(rowEl.querySelectorAll("button, a, [role='button']")).filter(el => {
                        if (!isVisible(el)) return false;
                        const txt = (el.innerText || '').trim().toLowerCase();
                        return txt === 'modifier' || txt === 'edit' || txt === 'éditer';
                    });
                    if (textBtns.length > 0) {
                        return { target: textBtns[0], strategy: 'text' };
                    }

                    // Fallback géométrique : les icônes d'actions à droite [Crayon, Ciseaux, Corbeille]
                    const rowRect = rowEl.getBoundingClientRect();
                    const rawControls = Array.from(
                        rowEl.querySelectorAll("button, a, [role='button'], [tabindex='0'], span, div")
                    ).filter(el => {
                        if (!isVisible(el)) return false;
                        if (el.tagName === 'INPUT' || el.querySelector("input[type='checkbox']")) return false;
                        const tag = el.tagName;
                        const role = el.getAttribute('role') || '';
                        const hasSvg = !!el.querySelector('svg');
                        const isInteractiveTag = tag === 'BUTTON' || tag === 'A' || role === 'button';
                        const isSvgWrapper = hasSvg && window.getComputedStyle(el).cursor === 'pointer' && el.querySelectorAll('svg').length === 1;
                        if (!isInteractiveTag && !isSvgWrapper) return false;
                        const r = el.getBoundingClientRect();
                        if (r.width < 14 || r.width > 72 || r.height < 14 || r.height > 72) return false;
                        if (r.left < rowRect.left + rowRect.width * 0.40) return false;
                        return true;
                    });

                    // Garder uniquement les contrôles les plus internes (ou boutons/liens dédiés) sans doublons imbriqués
                    const deduped = rawControls.filter(el => {
                        return !rawControls.some(other => other !== el && el.contains(other) && (other.tagName === 'BUTTON' || other.tagName === 'A' || other.getAttribute('role') === 'button'));
                    }).filter(el => {
                        return !rawControls.some(other => other !== el && other.contains(el) && (other.tagName === 'BUTTON' || other.tagName === 'A' || other.getAttribute('role') === 'button'));
                    });

                    deduped.sort((a, b) => a.getBoundingClientRect().left - b.getBoundingClientRect().left);
                    if (deduped.length >= 2) {
                        return { target: deduped[0], strategy: 'right_cluster_first(' + deduped.length + ')' };
                    }
                    if (deduped.length === 1) {
                        return { target: deduped[0], strategy: 'single_action_icon' };
                    }
                    return null;
                };

                let candidateRows = [];
                const tableRows = Array.from(document.querySelectorAll("table tbody tr")).filter(isVisible);
                if (tableRows.length > 0) {
                    candidateRows = tableRows;
                } else {
                    const ariaRows = Array.from(document.querySelectorAll("[role='row']")).filter(r => {
                        if (!isVisible(r)) return false;
                        if (r.querySelector("th, [role='columnheader']")) return false;
                        const txt = (r.innerText || '').trim();
                        if (/^(Vidéo|Video)\s+(Actions|Créé)/i.test(txt)) return false;
                        return true;
                    });
                    if (ariaRows.length > 0) {
                        candidateRows = ariaRows;
                    } else {
                        // Recherche structurelle par conteneur répétitif contenant un SVG/bouton d'action et un aperçu
                        const allBlocks = Array.from(document.querySelectorAll("div, li")).filter(el => {
                            if (!isVisible(el)) return false;
                            const r = el.getBoundingClientRect();
                            if (r.width < 550 || r.height < 48 || r.height > 260) return false;
                            const btns = el.querySelectorAll("button, [role='button'], svg");
                            const hasMedia = !!el.querySelector("img, video");
                            return hasMedia && btns.length >= 2;
                        });
                        // Filtrer les conteneurs parents qui englobent plusieurs lignes
                        candidateRows = allBlocks.filter(el => !allBlocks.some(child => child !== el && el.contains(child)));
                    }
                }

                const results = [];
                let tagIdx = 0;
                for (const rowEl of candidateRows) {
                    const found = findEditTargetInRow(rowEl);
                    if (!found || !found.target) continue;
                    found.target.setAttribute('data-autopilot-edit-idx', String(tagIdx));
                    const sig = (rowEl.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 160);
                    results.push({
                        idx: tagIdx,
                        signature: sig,
                        strategy: found.strategy,
                    });
                    tagIdx += 1;
                }
                return results;
            }""")
            return rows or []
        except Exception as e_dom:
            print(f"⚠️ [DevOps-Bot] Inspection DOM brouillons échouée : {e_dom}")
            return []

    def upload(
        self,
        video_path: str,
        caption: str,
        mode: str = "draft"  # "draft" ou "public"
    ) -> Dict[str, Any]:
        """
        Exécute le cycle complet d'injection dans TikTok Studio.
        """
        cookies, err_res = self._validate_and_prepare_cookies()
        if err_res:
            return err_res

        abs_video_path = os.path.abspath(video_path)
        if not os.path.exists(abs_video_path):
            return {
                "status": "error",
                "error": f"Fichier vidéo introuvable : {abs_video_path}"
            }

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "status": "error",
                "error": "Playwright n'est pas installé. Exécutez 'pip install playwright && playwright install chromium'."
            }

        print("\n" + "=" * 60)
        print("🤖 [DevOps-Bot] Démarrage du robot d'envoi vers TikTok Studio...")
        print(f"• Fichier : {os.path.basename(abs_video_path)}")
        print(f"• Mode cible : {'Brouillon Studio 📱' if mode == 'draft' else 'Publication Directe 🚀'}")
        print("=" * 60)

        step_results: Dict[str, str] = {}

        with sync_playwright() as p:
            browser, context, page = self._launch_stealth_context(p, cookies)
            if not page:
                return {
                    "status": "auth_error",
                    "error": "Aucun cookie n'a pu être injecté dans le navigateur."
                }

            try:
                self._warmup_session(page)

                studio_url = "https://www.tiktok.com/tiktokstudio/upload?lang=fr"
                print(f"🌐 [DevOps-Bot] Navigation vers : {studio_url}")
                page.goto(studio_url, wait_until="domcontentloaded", timeout=60000)

                for _ in range(10):
                    if "login" in page.url.lower():
                        break
                    has_input = page.locator("input[type='file']").count() > 0 or any(
                        frame.locator("input[type='file']").count() > 0 for frame in page.frames
                    )
                    if has_input:
                        break
                    time.sleep(1)

                self._dismiss_popups(page)

                screenshot_1 = os.path.join(self.screenshots_dir, "01_tiktok_studio_opened.png")
                page.screenshot(path=screenshot_1, full_page=False)
                step_results["step1_screenshot"] = screenshot_1

                current_url = page.url
                if "login" in current_url.lower():
                    error_screen = os.path.join(self.screenshots_dir, "error_session_expired.png")
                    page.screenshot(path=error_screen)
                    remaining_names = sorted({c["name"] for c in context.cookies()})
                    has_session_after = "sessionid" in remaining_names or "sessionid_ss" in remaining_names
                    print(f"❌ [DevOps-Bot] Redirection vers page de connexion : {current_url}")
                    print(
                        f"🔎 [DevOps-Bot] Diagnostic post-redirection : sessionid actif={has_session_after} "
                        f"({len(remaining_names)} cookie(s) présent(s) : {', '.join(remaining_names[:15])})"
                    )
                    if not has_session_after:
                        print("⚠️ TikTok a invalidé le cookie côté serveur (session expirée, déconnectée ou révoquée).")
                    else:
                        print("⚠️ TikTok a demandé une reconnexion (cookies compagnons manquants ou contrôle sécurité IP/région — exportez TOUS les cookies via Cookie-Editor JSON).")
                    return {
                        "status": "auth_error",
                        "error": "Session TikTok invalide ou expirée. Veuillez mettre à jour TIKTOK_SESSION_ID dans les Secrets GitHub.",
                        "screenshot": error_screen,
                        "url": current_url
                    }

                print(f"✅ [DevOps-Bot] Accès à TikTok Studio confirmé (Page : '{page.title()}')")

                print("🔍 [DevOps-Bot] Recherche du champ de fichier vidéo...")
                file_input = None

                try:
                    page.locator("input[type='file']").first.wait_for(state="attached", timeout=10000)
                except Exception:
                    pass

                direct_inputs = page.locator("input[type='file']")
                if direct_inputs.count() > 0:
                    file_input = direct_inputs.first

                if not file_input:
                    for frame in page.frames:
                        frame_inputs = frame.locator("input[type='file']")
                        if frame_inputs.count() > 0:
                            file_input = frame_inputs.first
                            print("📦 [DevOps-Bot] Champ de fichier trouvé dans une sous-frame.")
                            break

                if not file_input:
                    error_input = os.path.join(self.screenshots_dir, "error_no_file_input.png")
                    page.screenshot(path=error_input)
                    print("❌ [DevOps-Bot] Aucun champ de sélection vidéo (input[type='file']) trouvé.")
                    return {
                        "status": "dom_error",
                        "error": "Impossible de localiser le champ de téléversement dans TikTok Studio.",
                        "screenshot": error_input
                    }

                print(f"📤 [DevOps-Bot] Injection du fichier vidéo : {os.path.basename(abs_video_path)}")
                file_input.set_input_files(abs_video_path)

                print("⏳ [DevOps-Bot] Téléversement en cours sur les serveurs TikTok...")
                upload_completed = False
                for wait_loop in range(30):
                    time.sleep(3)
                    self._dismiss_popups(page)
                    page_text = page.inner_text("body").lower()
                    btn_ready = False
                    if mode == "draft":
                        btn_probe, _ = self._find_visible_element(page, ["button[data-e2e='save_draft_button']"])
                    else:
                        btn_probe, _ = self._find_visible_element(page, ["button[data-e2e='post_video_button']", "button:text-is('Publier')", "button:text-is('Post')"])
                    if btn_probe is not None:
                        btn_ready = not self._is_button_disabled(btn_probe)
                    if (
                        btn_ready
                        or "téléchargé" in page_text
                        or "uploaded" in page_text
                        or "100%" in page_text
                        or "remplacer" in page_text
                        or "changer de vidéo" in page_text
                        or "change video" in page_text
                    ):
                        upload_completed = True
                        print(f"✅ [DevOps-Bot] Vidéo reçue par TikTok Studio en {((wait_loop + 1) * 3)}s !")
                        break

                screenshot_2 = os.path.join(self.screenshots_dir, "02_video_uploaded.png")
                page.screenshot(path=screenshot_2)
                step_results["step2_screenshot"] = screenshot_2

                print("✍️ [DevOps-Bot] Remplissage de la légende & hashtags...")
                self._dismiss_popups(page)
                caption_selectors = [
                    ".public-DraftEditor-content",
                    "div[contenteditable='true']",
                    "div[data-placeholder]",
                    "div[class*='editor']",
                    "textarea[placeholder*='description']",
                    "textarea"
                ]

                caption_field, _ = self._find_visible_element(page, caption_selectors)

                if caption_field:
                    try:
                        caption_field.scroll_into_view_if_needed()
                        caption_field.click()
                        time.sleep(0.4)
                        page.keyboard.press("ControlOrMeta+A")
                        page.keyboard.press("Backspace")
                        time.sleep(0.4)
                        page.keyboard.insert_text(caption[:2000])
                        time.sleep(0.4)
                        # Ferme le menu d'autocomplétion de hashtags (#...) avant le clic final
                        page.keyboard.press("Escape")
                        try:
                            caption_field.evaluate("el => el.blur()")
                        except Exception:
                            pass
                        print("✅ [DevOps-Bot] Légende insérée avec succès.")
                    except Exception as e_caption:
                        print(f"⚠️ Échec insertion directe clavier : {e_caption}")
                else:
                    print("⚠️ Champ de légende non détecté automatiquement, continuation vers la validation.")

                time.sleep(1.5)
                screenshot_3 = os.path.join(self.screenshots_dir, "03_caption_filled.png")
                page.screenshot(path=screenshot_3)
                step_results["step3_screenshot"] = screenshot_3

                target_action = "brouillon" if mode == "draft" else "publier"
                print(f"🎯 [DevOps-Bot] Recherche du bouton d'action : '{target_action.upper()}'...")
                self._dismiss_popups(page)

                if mode == "draft":
                    action_selectors = [
                        "button[data-e2e='save_draft_button']",
                        "button:has-text('Enregistrer les brouillons')",
                        "button:has-text('Enregistrer comme brouillon')",
                        "button:has-text('Sauvegarder en brouillon')",
                        "button:has-text('Enregistrer le brouillon')",
                        "button:has-text('Save draft')",
                        "button:has-text('Save as draft')",
                        "button:has-text('Brouillon')",
                        "button:has-text('Draft')"
                    ]
                else:
                    action_selectors = [
                        "button[data-e2e='post_video_button']",
                        "button:text-is('Publier')",
                        "button:text-is('Post')",
                        "button:has-text('Publier')",
                        "button:has-text('Post')"
                    ]

                action_button, matched_sel = self._find_visible_element(page, action_selectors)
                if action_button and matched_sel:
                    label_kind = "brouillon" if mode == "draft" else "publication"
                    print(f"🔘 [DevOps-Bot] Bouton {label_kind} repéré : '{matched_sel}'")

                action_clicked = False
                success_detected = False
                screenshot_4 = os.path.join(self.screenshots_dir, "04_action_clicked.png")
                if action_button:
                    action_clicked, success_detected = self._confirm_and_wait_publish(
                        page,
                        action_button,
                        mode=mode,
                        screenshot_clicked_path=screenshot_4,
                    )
                    step_results["step4_screenshot"] = screenshot_4
                    if action_clicked:
                        print("🎉 [DevOps-Bot] Clic validé ! Vérification du statut final...")
                    else:
                        print("⚠️ [DevOps-Bot] Le bouton est resté désactivé pendant l'attente.")
                else:
                    print("⚠️ Aucun bouton spécifique trouvé, capture d'état enregistrée.")

                if success_detected:
                    time.sleep(1.5)

                screenshot_final = os.path.join(self.screenshots_dir, "05_final_state.png")
                page.screenshot(path=screenshot_final)
                step_results["final_screenshot"] = screenshot_final

                print("\n" + "=" * 60)
                if success_detected:
                    dest_label = "Brouillons TikTok Studio" if mode == "draft" else "Fil Public TikTok"
                    print(f"🏆 [DevOps-Bot] SUCCÈS TOTAL : La vidéo est bien enregistrée dans {dest_label} !")
                elif action_clicked:
                    print("📸 [DevOps-Bot] Clic effectué. Consultez les captures d'écran pour confirmer l'état final.")
                else:
                    print("❌ [DevOps-Bot] Impossible de valider le bouton final dans TikTok Studio.")
                print(f"• Captures d'écran sauvegardées dans : '{self.screenshots_dir}'")
                print("=" * 60)

                final_status = "success" if success_detected else ("completed_with_screenshots" if action_clicked else "dom_error")
                return {
                    "status": final_status,
                    "mode": mode,
                    "upload_completed": upload_completed,
                    "action_clicked": action_clicked,
                    "success_detected": success_detected,
                    "final_url": page.url,
                    "screenshots": step_results
                }

            except Exception as e_run:
                err_screen = os.path.join(self.screenshots_dir, "error_runtime.png")
                try:
                    page.screenshot(path=err_screen)
                except Exception:
                    pass
                print(f"❌ [DevOps-Bot] Erreur pendant l'exécution navigateur : {e_run}")
                return {
                    "status": "error",
                    "error": str(e_run),
                    "screenshot": err_screen
                }
            finally:
                context.close()
                browser.close()

    def publish_all_drafts(
        self,
        max_count: int = 30,
        dry_run: bool = False,
        pause_seconds: float = 3.0,
    ) -> Dict[str, Any]:
        """
        Ouvre les Brouillons existants de TikTok Studio et les publie directement
        en mode public (Tout le monde / Maintenant).
        """
        cookies, err_res = self._validate_and_prepare_cookies()
        if err_res:
            return err_res

        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return {
                "status": "error",
                "error": "Playwright n'est pas installé. Exécutez 'pip install playwright && playwright install chromium'."
            }

        drafts_url = "https://www.tiktok.com/tiktokstudio/content?tab=draft&lang=fr"
        posts_url = "https://www.tiktok.com/tiktokstudio/content?lang=fr"
        os.makedirs(self.screenshots_dir, exist_ok=True)
        screenshots: Dict[str, str] = {}
        details: List[Dict[str, Any]] = []
        failed_signatures = set()
        published_count = 0
        failed_count = 0

        print("\n" + "=" * 60)
        print("🚀 [DevOps-Bot] Publication des Brouillons TikTok Studio en Public...")
        print(f"• Limite demandée : {max_count} | Mode dry-run : {dry_run}")
        print("=" * 60)

        with sync_playwright() as p:
            browser, context, page = self._launch_stealth_context(p, cookies)
            if not page:
                return {
                    "status": "auth_error",
                    "error": "Aucun cookie n'a pu être injecté dans le navigateur."
                }

            try:
                self._warmup_session(page)
                page.goto(drafts_url, wait_until="domcontentloaded", timeout=60000)

                for _ in range(12):
                    if "login" in page.url.lower():
                        break
                    rows_probe = self._discover_draft_rows(page)
                    counts_probe = self._read_studio_tab_counts(page)
                    if rows_probe or counts_probe["drafts"] == 0:
                        break
                    time.sleep(1.5)

                self._dismiss_popups(page)

                if "login" in page.url.lower():
                    err_screen = os.path.join(self.screenshots_dir, "drafts_auth_error.png")
                    page.screenshot(path=err_screen)
                    return {
                        "status": "auth_error",
                        "error": "Session TikTok invalide ou expirée lors de l'accès aux brouillons.",
                        "screenshot": err_screen,
                        "url": page.url
                    }

                before_counts = self._read_studio_tab_counts(page)
                before_screen = os.path.join(self.screenshots_dir, "drafts_before.png")
                page.screenshot(path=before_screen, full_page=False)
                screenshots["before"] = before_screen
                print(
                    f"📊 [DevOps-Bot] État initial — Publications : {before_counts['publications']} | "
                    f"Brouillons : {before_counts['drafts']}"
                )

                initial_rows = self._discover_draft_rows(page)
                if dry_run:
                    for r in initial_rows:
                        print(f"  • Brouillon détecté #{r['idx'] + 1} [{r['strategy']}] : {r['signature'][:90]}")
                    posts_info = {}
                    try:
                        page.goto(posts_url, wait_until="domcontentloaded", timeout=60000)
                        time.sleep(2.5)
                        self._dismiss_popups(page)
                        posts_counts = self._read_studio_tab_counts(page)
                        posts_screen = os.path.join(self.screenshots_dir, "posts_dry_run.png")
                        page.screenshot(path=posts_screen, full_page=False)
                        screenshots["posts_dry_run"] = posts_screen
                        posts_info["publications"] = posts_counts["publications"]
                        posts_info["body_preview"] = (page.inner_text("body") or "").replace("\n", " | ")[:400]
                        print(f"📊 [DevOps-Bot] Onglet Publications (dry-run) : {posts_info['body_preview']}")
                    except Exception as e_posts:
                        print(f"⚠️ [DevOps-Bot] Inspection Publications ignorée ({e_posts})")
                    return {
                        "status": "dry_run",
                        "publications_before": before_counts["publications"],
                        "drafts_before": before_counts["drafts"],
                        "rows_detected": len(initial_rows),
                        "rows": initial_rows,
                        "posts_info": posts_info,
                        "screenshots": screenshots,
                    }

                if not initial_rows and (before_counts["drafts"] or 0) > 0:
                    try:
                        dom_diag = page.evaluate(r"""() => ({
                            tr: document.querySelectorAll('table tbody tr').length,
                            roleRow: document.querySelectorAll("[role='row']").length,
                            buttons: document.querySelectorAll('button').length,
                            svgs: document.querySelectorAll('svg').length,
                            imgs: document.querySelectorAll('img, video').length,
                        })""")
                        print(f"🔎 [DevOps-Bot] Diagnostic DOM page brouillons : {dom_diag}")
                    except Exception:
                        pass
                    dom_err_screen = os.path.join(self.screenshots_dir, "drafts_dom_error.png")
                    page.screenshot(path=dom_err_screen, full_page=False)
                    screenshots["dom_error"] = dom_err_screen
                    return {
                        "status": "dom_error",
                        "error": "Des brouillons sont annoncés dans l'onglet mais aucun bouton d'édition n'a été détecté dans le DOM.",
                        "publications_before": before_counts["publications"],
                        "drafts_before": before_counts["drafts"],
                        "published_count": 0,
                        "screenshots": screenshots,
                    }

                pub_selectors = [
                    "button[data-e2e='post_video_button']",
                    "button:text-is('Publier')",
                    "button:text-is('Post')",
                    "button:has-text('Publier')",
                    "button:has-text('Post')",
                ]

                last_published_sig: Optional[str] = None
                for step_num in range(1, max_count + 1):
                    if "tab=draft" not in page.url.lower():
                        page.goto(drafts_url, wait_until="domcontentloaded", timeout=60000)

                    # Attente que la table se charge et que le brouillon tout juste publié disparaisse
                    rows: List[Dict[str, Any]] = []
                    for reload_wait in range(10):
                        self._dismiss_popups(page)
                        rows = self._discover_draft_rows(page)
                        counts_now = self._read_studio_tab_counts(page)
                        if counts_now["drafts"] == 0:
                            rows = []
                            break
                        if rows:
                            if last_published_sig and rows[0]["signature"] == last_published_sig and reload_wait < 4:
                                time.sleep(1.5)
                                if reload_wait == 2:
                                    page.reload(wait_until="domcontentloaded", timeout=45000)
                                continue
                            break
                        time.sleep(1.5)

                    target_row = next((r for r in rows if r["signature"] not in failed_signatures), None)
                    if target_row is None:
                        # Tentative de défilement si d'autres brouillons sont sous le pli et les premiers ont échoué
                        if rows:
                            try:
                                page.evaluate("window.scrollBy(0, 700)")
                                time.sleep(1.5)
                                rows = self._discover_draft_rows(page)
                                target_row = next((r for r in rows if r["signature"] not in failed_signatures), None)
                            except Exception:
                                pass
                        if target_row is None:
                            print("🏁 [DevOps-Bot] Plus aucun brouillon éligible dans la liste.")
                            break

                    sig = target_row["signature"]
                    print(f"\n🎬 [DevOps-Bot] Traitement brouillon #{step_num} ({target_row['strategy']}) : {sig[:85]}...")
                    edit_loc = page.locator(f"[data-autopilot-edit-idx='{target_row['idx']}']").first
                    pages_before = len(context.pages)
                    try:
                        edit_loc.scroll_into_view_if_needed()
                    except Exception:
                        pass
                    try:
                        edit_loc.click(timeout=5000)
                    except Exception:
                        edit_loc.click(force=True)

                    # Basculer si l'édition a ouvert un nouvel onglet
                    active_page = page
                    time.sleep(1.5)
                    if len(context.pages) > pages_before:
                        active_page = context.pages[-1]

                    # Attendre l'ouverture et l'hydratation complète du formulaire (apparition du bouton Publier)
                    pub_btn = None
                    pub_sel = None
                    for _ in range(20):
                        self._dismiss_popups(active_page)
                        pub_btn, pub_sel = self._find_visible_element(active_page, pub_selectors)
                        if pub_btn is not None:
                            break
                        time.sleep(1.5)

                    opened_shot = os.path.join(self.screenshots_dir, f"draft_{step_num:02d}_opened.png")
                    try:
                        active_page.screenshot(path=opened_shot)
                    except Exception:
                        pass

                    if pub_btn is None:
                        print(f"⚠️ [DevOps-Bot] Éditeur ou bouton Publier introuvable sur le brouillon #{step_num} (URL: {active_page.url}).")
                        failed_count += 1
                        failed_signatures.add(sig)
                        details.append({"step": step_num, "signature": sig, "status": "publish_button_missing", "opened_screenshot": opened_shot})
                        if active_page is not page:
                            try:
                                active_page.close()
                            except Exception:
                                pass
                        page.goto(drafts_url, wait_until="domcontentloaded", timeout=60000)
                        continue

                    print(f"🔘 [DevOps-Bot] Bouton publication détecté : '{pub_sel}'")
                    clicked_shot = os.path.join(self.screenshots_dir, f"draft_{step_num:02d}_after.png")
                    clicked, confirmed = self._confirm_and_wait_publish(
                        active_page,
                        pub_btn,
                        mode="public",
                        screenshot_clicked_path=clicked_shot,
                    )

                    if active_page is not page:
                        try:
                            active_page.close()
                        except Exception:
                            pass

                    if clicked and confirmed:
                        published_count += 1
                        last_published_sig = sig
                        print(f"✅ [DevOps-Bot] Brouillon #{step_num} publié sur TikTok ! (Total publiés : {published_count})")
                        details.append({
                            "step": step_num,
                            "signature": sig,
                            "status": "published",
                            "opened_screenshot": opened_shot,
                            "after_screenshot": clicked_shot,
                        })
                        time.sleep(pause_seconds)
                    else:
                        failed_count += 1
                        failed_signatures.add(sig)
                        print(f"⚠️ [DevOps-Bot] Brouillon #{step_num} non confirmé (clicked={clicked}, confirmed={confirmed}).")
                        details.append({
                            "step": step_num,
                            "signature": sig,
                            "status": "publish_unconfirmed",
                            "opened_screenshot": opened_shot,
                            "after_screenshot": clicked_shot,
                        })

                    page.goto(drafts_url, wait_until="domcontentloaded", timeout=60000)

                # Capture finale de l'onglet Brouillons puis de l'onglet Publications
                page.goto(drafts_url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(2.5)
                self._dismiss_popups(page)
                after_counts = self._read_studio_tab_counts(page)
                after_drafts_screen = os.path.join(self.screenshots_dir, "drafts_after.png")
                page.screenshot(path=after_drafts_screen, full_page=False)
                screenshots["drafts_after"] = after_drafts_screen

                try:
                    page.goto(posts_url, wait_until="domcontentloaded", timeout=60000)
                    time.sleep(2.5)
                    self._dismiss_popups(page)
                    posts_counts = self._read_studio_tab_counts(page)
                    if posts_counts["publications"] is not None:
                        after_counts["publications"] = posts_counts["publications"]
                    posts_screen = os.path.join(self.screenshots_dir, "posts_after.png")
                    page.screenshot(path=posts_screen, full_page=False)
                    screenshots["posts_after"] = posts_screen
                except Exception:
                    pass

                print("\n" + "=" * 60)
                print(f"🏆 [DevOps-Bot] Bilan Brouillons -> Public :")
                print(f"• Avant : Publications={before_counts['publications']} | Brouillons={before_counts['drafts']}")
                print(f"• Après : Publications={after_counts['publications']} | Brouillons={after_counts['drafts']}")
                print(f"• Publiés lors de cette session : {published_count} | Non confirmés/ignorés : {failed_count}")
                print("=" * 60)

                if published_count > 0:
                    final_status = "success" if failed_count == 0 else "partial_success"
                elif (before_counts["drafts"] == 0) or (not initial_rows and before_counts["drafts"] is None):
                    final_status = "empty"
                else:
                    final_status = "error"

                return {
                    "status": final_status,
                    "publications_before": before_counts["publications"],
                    "drafts_before": before_counts["drafts"],
                    "publications_after": after_counts["publications"],
                    "drafts_after": after_counts["drafts"],
                    "published_count": published_count,
                    "failed_count": failed_count,
                    "details": details,
                    "screenshots": screenshots,
                }
            except Exception as e_drafts:
                err_screen = os.path.join(self.screenshots_dir, "drafts_runtime_error.png")
                try:
                    page.screenshot(path=err_screen)
                except Exception:
                    pass
                print(f"❌ [DevOps-Bot] Erreur pendant la publication des brouillons : {e_drafts}")
                return {
                    "status": "error",
                    "error": str(e_drafts),
                    "published_count": published_count,
                    "failed_count": failed_count,
                    "details": details,
                    "screenshot": err_screen,
                    "screenshots": screenshots,
                }
            finally:
                context.close()
                browser.close()

