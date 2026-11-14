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

    def upload(
        self,
        video_path: str,
        caption: str,
        mode: str = "draft"  # "draft" ou "public"
    ) -> Dict[str, Any]:
        """
        Exécute le cycle complet d'injection dans TikTok Studio.
        """
        if not self.session_id:
            return {
                "status": "error",
                "error": "Aucun TIKTOK_SESSION_ID configuré. Impossible d'ouvrir la session TikTok Studio."
            }

        abs_video_path = os.path.abspath(video_path)
        if not os.path.exists(abs_video_path):
            return {
                "status": "error",
                "error": f"Fichier vidéo introuvable : {abs_video_path}"
            }

        # Validation préalable des cookies avant de lancer le navigateur
        cookies = self.parse_and_prepare_cookies(self.session_id)
        if not cookies:
            return {
                "status": "auth_error",
                "error": "Aucun cookie TikTok valide trouvé dans TIKTOK_SESSION_ID. Vérifiez que vous avez collé l'export JSON Cookie-Editor complet ou le cookie 'sessionid' (et non un lien web)."
            }

        parsed_names = {c["name"] for c in cookies}
        if "sessionid" not in parsed_names and "sessionid_ss" not in parsed_names:
            names_preview = ", ".join(sorted(parsed_names)[:10])
            print(f"❌ [DevOps-Bot] Cookie obligatoire 'sessionid' absent de l'export (cookies reçus : {names_preview}).")
            return {
                "status": "auth_error",
                "error": "Le cookie indispensable 'sessionid' est absent de TIKTOK_SESSION_ID. Connectez-vous à TikTok Studio puis exportez TOUS les cookies en JSON via Cookie-Editor."
            }

        companion_keys = [k for k in ("sid_tt", "uid_tt", "sid_guard", "tt_chain_token", "store-idc", "ttwid") if k in parsed_names]
        if not companion_keys:
            print("⚠️ [DevOps-Bot] Attention : Seul 'sessionid' a été fourni sans les cookies compagnons (sid_tt, sid_guard, tt_chain_token, store-idc). Si TikTok redirige vers /login, utilisez Cookie-Editor -> Export -> Export as JSON.")

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
            # 1. Lancement de Chromium avec configuration furtive (Stealth)
            browser = p.chromium.launch(
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

            # Aligner la version Chrome et la plateforme avec le véritable moteur Chromium pour éviter les discordances d'empreinte
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

            # Masquage du drapeau webdriver & suppression continue des guides React Joyride qui bloquent les clics
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

            # 2. Injection sécurisée des cookies (un par un pour qu'un cookie accessoire invalide ne bloque pas sessionid)
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
                return {
                    "status": "auth_error",
                    "error": "Aucun cookie n'a pu être injecté dans le navigateur."
                }

            print(f"🔑 [DevOps-Bot] {len(added_names)}/{len(cookies)} cookies injectés ({', '.join(added_names[:15])}{'...' if len(added_names) > 15 else ''}).")

            page = context.new_page()
            page.set_default_timeout(45000)
            page.on("dialog", lambda dialog: dialog.accept())

            try:
                # 3. Mise en confiance de session sur la page principale puis ouverture de TikTok Studio
                home_url = "https://www.tiktok.com/?lang=fr"
                print(f"🌐 [DevOps-Bot] Initialisation session sur : {home_url}")
                try:
                    page.goto(home_url, wait_until="domcontentloaded", timeout=45000)
                    time.sleep(2.5)
                    self._dismiss_popups(page)
                except Exception as e_home:
                    print(f"⚠️ [DevOps-Bot] Pré-chargement page d'accueil ignoré ({e_home})")

                studio_url = "https://www.tiktok.com/tiktokstudio/upload?lang=fr"
                print(f"🌐 [DevOps-Bot] Navigation vers : {studio_url}")
                page.goto(studio_url, wait_until="domcontentloaded", timeout=60000)

                # Attente dynamique : soit redirection login, soit apparition du champ upload
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

                # Vérification de connexion
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

                # 4. Recherche de la zone de dépôt (input file)
                print("🔍 [DevOps-Bot] Recherche du champ de fichier vidéo...")
                file_input = None

                # Attente brève au cas où le composant React finit de s'hydrater
                try:
                    page.locator("input[type='file']").first.wait_for(state="attached", timeout=10000)
                except Exception:
                    pass

                # Recherche dans le document principal
                direct_inputs = page.locator("input[type='file']")
                if direct_inputs.count() > 0:
                    file_input = direct_inputs.first

                # Recherche dans les éventuels iframes
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

                # 5. Dépôt de la vidéo MP4
                print(f"📤 [DevOps-Bot] Injection du fichier vidéo : {os.path.basename(abs_video_path)}")
                file_input.set_input_files(abs_video_path)

                # Attente du traitement / barre de progression
                print("⏳ [DevOps-Bot] Téléversement en cours sur les serveurs TikTok...")
                upload_completed = False
                for wait_loop in range(30):
                    time.sleep(3)
                    self._dismiss_popups(page)
                    page_text = page.inner_text("body").lower()
                    btn_ready = False
                    draft_probe = page.locator("button[data-e2e='save_draft_button']")
                    if mode == "draft" and draft_probe.count() > 0:
                        b = draft_probe.first
                        btn_ready = (
                            b.get_attribute("disabled") is None
                            and b.get_attribute("aria-disabled") != "true"
                            and b.get_attribute("data-disabled") != "true"
                        )
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

                # 6. Saisie de la légende et des hashtags
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

                caption_field = None
                for sel in caption_selectors:
                    try:
                        loc = page.locator(sel)
                        if loc.count() > 0 and loc.first.is_visible():
                            caption_field = loc.first
                            break
                    except Exception:
                        continue

                if caption_field:
                    try:
                        caption_field.scroll_into_view_if_needed()
                        caption_field.click()
                        time.sleep(0.4)
                        page.keyboard.press("ControlOrMeta+A")
                        page.keyboard.press("Backspace")
                        time.sleep(0.4)
                        # Insertion du texte sans déclencher de rechargement ni saut de ligne indésirable
                        page.keyboard.insert_text(caption[:2000])
                        print("✅ [DevOps-Bot] Légende insérée avec succès.")
                    except Exception as e_caption:
                        print(f"⚠️ Échec insertion directe clavier : {e_caption}")
                else:
                    print("⚠️ Champ de légende non détecté automatiquement, continuation vers la sauvegarde.")

                time.sleep(1.5)
                screenshot_3 = os.path.join(self.screenshots_dir, "03_caption_filled.png")
                page.screenshot(path=screenshot_3)
                step_results["step3_screenshot"] = screenshot_3

                # 7. Clic sur le bouton Enregistrer comme Brouillon (ou Publier)
                target_action = "brouillon" if mode == "draft" else "publier"
                print(f"🎯 [DevOps-Bot] Recherche du bouton d'action : '{target_action.upper()}'...")
                self._dismiss_popups(page)

                action_button = None
                if mode == "draft":
                    draft_selectors = [
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
                    for d_sel in draft_selectors:
                        try:
                            loc = page.locator(d_sel)
                            if loc.count() > 0 and loc.first.is_visible():
                                action_button = loc.first
                                print(f"🔘 [DevOps-Bot] Bouton brouillon repéré : '{d_sel}'")
                                break
                        except Exception:
                            continue
                else:
                    pub_selectors = [
                        "button[data-e2e='post_video_button']",
                        "button:has-text('Publier')",
                        "button:has-text('Post')"
                    ]
                    for p_sel in pub_selectors:
                        try:
                            loc = page.locator(p_sel)
                            if loc.count() > 0 and loc.first.is_visible():
                                action_button = loc.first
                                print(f"🔘 [DevOps-Bot] Bouton publication repéré : '{p_sel}'")
                                break
                        except Exception:
                            continue

                action_clicked = False
                if action_button:
                    # Attendre que le bouton devienne actif (TikTok désactive le bouton tant que la vidéo charge)
                    print("⏳ [DevOps-Bot] Attente de l'activation du bouton...")
                    for _attempt in range(30):
                        self._dismiss_popups(page)
                        is_disabled = (
                            action_button.get_attribute("disabled") is not None
                            or action_button.get_attribute("aria-disabled") == "true"
                            or action_button.get_attribute("data-disabled") == "true"
                            or "disabled" in (action_button.get_attribute("class") or "")
                        )
                        if not is_disabled:
                            print("⚡ [DevOps-Bot] Le bouton est ACTIF ! Clic en cours...")
                            action_button.scroll_into_view_if_needed()
                            try:
                                action_button.click(timeout=5000)
                            except Exception:
                                action_button.click(force=True)
                            action_clicked = True
                            time.sleep(2)
                            # Validation éventuelle de boîte de confirmation ("Continuer ?", "Save", "Post now", "Enregistrer")
                            confirm_selectors = [
                                "div[role='dialog'] button:has-text('Enregistrer')",
                                "div[role='dialog'] button:has-text('Save')",
                                "div[role='dialog'] button:has-text('Continuer')",
                                "div[role='dialog'] button:has-text('Continue')",
                                "button:has-text('Post now')",
                                "button:has-text('Publier maintenant')",
                            ]
                            for c_sel in confirm_selectors:
                                try:
                                    c_loc = page.locator(c_sel)
                                    if c_loc.count() > 0 and c_loc.first.is_visible():
                                        c_loc.first.click(timeout=2000)
                                        time.sleep(2)
                                        break
                                except Exception:
                                    pass
                            break
                        time.sleep(2)

                    screenshot_4 = os.path.join(self.screenshots_dir, "04_action_clicked.png")
                    page.screenshot(path=screenshot_4)
                    step_results["step4_screenshot"] = screenshot_4
                    if action_clicked:
                        print("🎉 [DevOps-Bot] Clic validé ! Vérification du statut final...")
                    else:
                        print("⚠️ [DevOps-Bot] Le bouton est resté désactivé pendant l'attente.")
                else:
                    print("⚠️ Aucun bouton spécifique trouvé, capture d'état enregistrée.")

                # Attente réelle de confirmation de sauvegarde / redirection
                success_detected = False
                if action_clicked:
                    for _ in range(8):
                        time.sleep(2)
                        current_after = page.url.lower()
                        body_text = page.inner_text("body").lower()
                        btn_gone = False
                        try:
                            btn_gone = (action_button is not None and not action_button.is_visible())
                        except Exception:
                            btn_gone = True
                        if (
                            "tiktokstudio/content" in current_after
                            or btn_gone
                            or "enregistré dans les brouillons" in body_text
                            or "enregistré" in body_text
                            or "saved to drafts" in body_text
                            or "saved" in body_text
                            or "your video has been uploaded" in body_text
                            or "gérer vos publications" in body_text
                            or "manage your posts" in body_text
                        ):
                            success_detected = True
                            break

                screenshot_final = os.path.join(self.screenshots_dir, "05_final_state.png")
                page.screenshot(path=screenshot_final)
                step_results["final_screenshot"] = screenshot_final

                print("\n" + "=" * 60)
                if success_detected:
                    dest_label = "Brouillons TikTok Studio" if mode == "draft" else "TikTok Studio"
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
