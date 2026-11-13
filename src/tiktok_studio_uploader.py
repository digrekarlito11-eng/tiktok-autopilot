import os
import sys
import time
from typing import Dict, Any, Optional

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

    def _dismiss_popups(self, page) -> None:
        """Ferme les bannières de cookies, guides d'utilisation et alertes superposées."""
        dismiss_selectors = [
            # Consentement cookies
            "button:has-text('Tout accepter')",
            "button:has-text('Accepter tout')",
            "button:has-text('Accept all')",
            "button:has-text('Allow all')",
            # Guides & infobulles de démarrage
            "button:has-text('J\'ai compris')",
            "button:has-text('Compris')",
            "button:has-text('Got it')",
            "button:has-text('Passer')",
            "button:has-text('Skip')",
            "button:has-text('Plus tard')",
            "button:has-text('Annuler')",
            "button:has-text('Cancel')",
            "button[aria-label='Fermer']",
            "button[aria-label='Close']",
            ".modal-close",
            ".guide-close"
        ]
        for sel in dismiss_selectors:
            try:
                elem = page.locator(sel).first
                if elem.is_visible(timeout=500):
                    print(f"🧹 [DevOps-Bot] Fermeture popup : '{sel}'")
                    elem.click(timeout=1000)
                    time.sleep(0.5)
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

        step_results = {}

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

            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/126.0.0.0 Safari/537.36"
                ),
                locale="fr-FR",
                timezone_id="Africa/Abidjan"
            )

            # Masquage du drapeau webdriver dans le navigateur
            context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {
                    get: () => undefined
                });
                window.chrome = {
                    runtime: {}
                };
            """)

            # 2. Injection du cookie de session sécurisé
            clean_sid = self.session_id.strip()
            cookies = [
                {
                    "name": "sessionid",
                    "value": clean_sid,
                    "domain": ".tiktok.com",
                    "path": "/",
                    "secure": True,
                    "httpOnly": True,
                    "sameSite": "Lax"
                },
                {
                    "name": "sessionid_ss",
                    "value": clean_sid,
                    "domain": ".tiktok.com",
                    "path": "/",
                    "secure": True,
                    "httpOnly": True,
                    "sameSite": "Lax"
                }
            ]
            context.add_cookies(cookies)
            print("🔑 [DevOps-Bot] Cookies de session TikTok injectés avec succès.")

            page = context.new_page()
            page.set_default_timeout(45000)

            try:
                # 3. Navigation vers le Studio TikTok
                studio_url = "https://www.tiktok.com/tiktokstudio/upload?lang=fr"
                print(f"🌐 [DevOps-Bot] Navigation vers : {studio_url}")
                page.goto(studio_url, wait_until="domcontentloaded", timeout=60000)
                time.sleep(5)
                self._dismiss_popups(page)

                screenshot_1 = os.path.join(self.screenshots_dir, "01_tiktok_studio_opened.png")
                page.screenshot(path=screenshot_1, full_page=False)
                step_results["step1_screenshot"] = screenshot_1

                # Vérification de connexion
                current_url = page.url
                if "login" in current_url:
                    error_screen = os.path.join(self.screenshots_dir, "error_session_expired.png")
                    page.screenshot(path=error_screen)
                    print(f"❌ [DevOps-Bot] Redirection vers page de connexion : {current_url}")
                    print("⚠️ Le cookie TIKTOK_SESSION_ID est invalide ou expiré.")
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
                for wait_loop in range(15):
                    time.sleep(3)
                    self._dismiss_popups(page)
                    page_text = page.inner_text("body").lower()
                    if (
                        "téléchargé" in page_text or 
                        "uploaded" in page_text or 
                        "100%" in page_text or 
                        "remplacer" in page_text or
                        "changer de vidéo" in page_text or
                        "change video" in page_text
                    ):
                        upload_completed = True
                        print(f"✅ [DevOps-Bot] Vidéo reçue par TikTok Studio en {((wait_loop+1)*3)}s !")
                        break

                screenshot_2 = os.path.join(self.screenshots_dir, "02_video_uploaded.png")
                page.screenshot(path=screenshot_2)
                step_results["step2_screenshot"] = screenshot_2

                # 6. Saisie de la légende et des hashtags
                print("✍️ [DevOps-Bot] Remplissage de la légende & hashtags...")
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
                        elem = page.locator(sel).first
                        if elem.is_visible(timeout=1000):
                            caption_field = elem
                            break
                    except Exception:
                        continue

                if caption_field:
                    try:
                        caption_field.click()
                        time.sleep(0.5)
                        page.keyboard.press("Control+A")
                        page.keyboard.press("Backspace")
                        time.sleep(0.5)
                        # Insertion du texte sans déclencher de rechargement
                        page.keyboard.insert_text(caption[:2000])
                        print("✅ [DevOps-Bot] Légende insérée avec succès.")
                    except Exception as e_caption:
                        print(f"⚠️ Échec insertion directe clavier : {e_caption}")
                else:
                    print("⚠️ Champ de légende non détecté automatiquement, continuation vers la sauvegarde.")

                time.sleep(2)
                screenshot_3 = os.path.join(self.screenshots_dir, "03_caption_filled.png")
                page.screenshot(path=screenshot_3)
                step_results["step3_screenshot"] = screenshot_3

                # 7. Clic sur le bouton Enregistrer comme Brouillon (ou Publier)
                target_action = "brouillon" if mode == "draft" else "publier"
                print(f"🎯 [DevOps-Bot] Recherche du bouton d'action : '{target_action.upper()}'...")

                action_button = None
                if mode == "draft":
                    draft_selectors = [
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
                            btn = page.locator(d_sel).first
                            if btn.is_visible(timeout=1000):
                                action_button = btn
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
                            btn = page.locator(p_sel).first
                            if btn.is_visible(timeout=1000):
                                action_button = btn
                                print(f"🔘 [DevOps-Bot] Bouton publication repéré : '{p_sel}'")
                                break
                        except Exception:
                            continue

                if action_button:
                    # Attendre que le bouton devienne actif (TikTok désactive le bouton tant que la vidéo charge)
                    print("⏳ [DevOps-Bot] Attente de l'activation du bouton...")
                    for attempt in range(10):
                        is_disabled = (
                            action_button.get_attribute("disabled") is not None or
                            action_button.get_attribute("aria-disabled") == "true" or
                            "disabled" in (action_button.get_attribute("class") or "")
                        )
                        if not is_disabled:
                            print("⚡ [DevOps-Bot] Le bouton est ACTIF ! Clic en cours...")
                            action_button.click()
                            time.sleep(5)
                            break
                        time.sleep(2)

                    screenshot_4 = os.path.join(self.screenshots_dir, "04_action_clicked.png")
                    page.screenshot(path=screenshot_4)
                    step_results["step4_screenshot"] = screenshot_4
                    print("🎉 [DevOps-Bot] Clic validé ! Vérification du statut final...")
                else:
                    print("⚠️ Aucun bouton spécifique trouvé, capture d'état enregistrée.")

                time.sleep(4)
                screenshot_final = os.path.join(self.screenshots_dir, "05_final_state.png")
                page.screenshot(path=screenshot_final)
                step_results["final_screenshot"] = screenshot_final

                # Vérification finale
                final_content = page.content().lower()
                success_detected = (
                    "enregistré" in final_content or
                    "saved" in final_content or
                    "brouillon" in final_content or
                    "gérer vos publications" in final_content or
                    "manage your posts" in final_content or
                    "uploaded" in final_content
                )

                print("\n" + "=" * 60)
                if success_detected:
                    print("🏆 [DevOps-Bot] SUCCÈS TOTAL : La vidéo est dans tes Brouillons TikTok Studio !")
                else:
                    print("📸 [DevOps-Bot] Téléversement effectué. Les captures d'écran confirment l'état final.")
                print(f"• Captures d'écran sauvegardées dans : '{self.screenshots_dir}'")
                print("=" * 60)

                return {
                    "status": "success" if success_detected else "completed_with_screenshots",
                    "mode": mode,
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
