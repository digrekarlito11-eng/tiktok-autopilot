#!/usr/bin/env python3
"""
Sous-agent DevOps-Bot : Sonde de diagnostic "Story" sur TikTok Studio Web (lecture seule).

Objectif : vérifier si TikTok Studio (version navigateur) propose une option pour
partager une vidéo en Story — soit dans le formulaire d'import (section "Afficher plus"),
soit dans le menu "..." d'une publication existante.

AUCUNE publication n'est effectuée : la sonde n'appuie jamais sur "Publier".
"""

import os
import re
import sys
import json
import time
import argparse
from typing import Dict, Any, List

try:
    from .tiktok_studio_uploader import TikTokStudioUploader
except ImportError:
    from tiktok_studio_uploader import TikTokStudioUploader

STORY_PATTERN = re.compile(r"(stor(y|ies)|histoire|en story|partager.{0,20}story)", re.IGNORECASE)


def _story_lines(text: str) -> List[str]:
    lines = [ln.strip() for ln in (text or "").splitlines() if ln.strip()]
    return [ln[:200] for ln in lines if STORY_PATTERN.search(ln)][:40]


def run_probe(video_path: str, out_dir: str) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)
    uploader = TikTokStudioUploader(screenshots_dir=out_dir)
    cookies, err = uploader._validate_and_prepare_cookies()
    if err:
        return err

    from playwright.sync_api import sync_playwright

    report: Dict[str, Any] = {"status": "ok", "findings": {}}

    with sync_playwright() as p:
        browser, context, page = uploader._launch_stealth_context(p, cookies)
        if not page:
            return {"status": "auth_error", "error": "Aucun cookie injecté."}
        try:
            uploader._warmup_session(page)

            # 1) Onglet Publications : liste complète + menu "..." de la 1re publication
            page.goto("https://www.tiktok.com/tiktokstudio/content?lang=fr", wait_until="domcontentloaded", timeout=60000)
            time.sleep(5)
            uploader._dismiss_popups(page)
            page.screenshot(path=os.path.join(out_dir, "story_01_publications_full.png"), full_page=True)
            body = page.inner_text("body") or ""
            report["findings"]["publications_counts"] = uploader._read_studio_tab_counts(page)
            report["findings"]["publications_story_lines"] = _story_lines(body)

            more_clicked = False
            try:
                more_btns = page.locator("table tbody tr button, [role='row'] button")
                n = more_btns.count()
                # Le bouton "..." est le dernier bouton d'action de la première ligne
                first_row = page.locator("table tbody tr, [role='row']:has(img)").first
                row_btns = first_row.locator("button, [role='button']")
                rc = row_btns.count()
                if rc > 0:
                    row_btns.nth(rc - 1).click(timeout=5000)
                    more_clicked = True
                report["findings"]["row_buttons_detected"] = {"all": n, "first_row": rc}
                if not more_clicked:
                    # Repli : la liste Studio n'est pas un <table>. On vise l'icône "..."
                    # de la 1re ligne (colonne Actions) : élément cliquable le plus à droite
                    # sur la hauteur de la première vignette.
                    pos = page.evaluate(r"""() => {
                        const thumbs = Array.from(document.querySelectorAll('img')).filter(i => {
                            const r = i.getBoundingClientRect(); return r.width > 40 && r.height > 60 && r.left > 250 && r.top > 150;
                        });
                        if (!thumbs.length) return null;
                        const t = thumbs[0].getBoundingClientRect();
                        const cy = t.top + t.height / 2;
                        const cands = Array.from(document.querySelectorAll('button, [role=button], div, span, svg')).filter(e => {
                            const r = e.getBoundingClientRect();
                            return r.width > 10 && r.width < 60 && r.height > 10 && r.height < 60 && Math.abs((r.top + r.height/2) - cy) < 20;
                        });
                        if (!cands.length) return null;
                        cands.sort((a, b) => b.getBoundingClientRect().left - a.getBoundingClientRect().left);
                        const r = cands[0].getBoundingClientRect();
                        return {x: r.left + r.width / 2, y: r.top + r.height / 2};
                    }""")
                    report["findings"]["more_fallback_pos"] = pos
                    if pos:
                        page.mouse.click(pos["x"], pos["y"])
                        more_clicked = True
            except Exception as e_more:
                report["findings"]["more_menu_error"] = str(e_more)[:200]
            time.sleep(2)
            page.screenshot(path=os.path.join(out_dir, "story_02_more_menu.png"), full_page=False)
            if more_clicked:
                menu_text = page.inner_text("body") or ""
                before = set(l.strip() for l in body.splitlines() if l.strip())
                report["findings"]["more_menu_new_lines"] = [
                    l.strip() for l in menu_text.splitlines() if l.strip() and l.strip() not in before
                ][:40]
                report["findings"]["more_menu_story_lines"] = _story_lines(menu_text)
                try:
                    menu_items = page.evaluate(r"""() => Array.from(document.querySelectorAll(
                        "[role='menu'] *, [role='menuitem'], [data-floating-ui-portal] li, [data-floating-ui-portal] [role='option'], [data-floating-ui-portal] button"
                    )).map(e => (e.innerText || '').trim()).filter(t => t && t.length < 80)""")
                    report["findings"]["more_menu_items"] = sorted(set(menu_items or []))[:40]
                except Exception:
                    pass
            page.keyboard.press("Escape")

            # 2) Formulaire d'import : section "Afficher plus" (sans jamais publier)
            page.goto("https://www.tiktok.com/tiktokstudio/upload?lang=fr", wait_until="domcontentloaded", timeout=60000)
            page.locator("input[type='file']").first.wait_for(state="attached", timeout=30000)
            page.locator("input[type='file']").first.set_input_files(os.path.abspath(video_path))
            for _ in range(30):
                time.sleep(2)
                uploader._dismiss_popups(page)
                btn, _sel = uploader._find_visible_element(page, ["button[data-e2e='post_video_button']"])
                if btn is not None and not uploader._is_button_disabled(btn):
                    break
            expanded = False
            for sel in ["text=Afficher plus", "text=Show more", "button:has-text('Afficher plus')"]:
                try:
                    loc = page.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        loc.scroll_into_view_if_needed()
                        loc.click(timeout=4000)
                        expanded = True
                        break
                except Exception:
                    continue
            time.sleep(2)
            report["findings"]["upload_show_more_expanded"] = expanded
            page.screenshot(path=os.path.join(out_dir, "story_03_upload_settings_full.png"), full_page=True)
            upload_text = page.inner_text("body") or ""
            report["findings"]["upload_story_lines"] = _story_lines(upload_text)
            try:
                idx = upload_text.find("Paramètres")
                report["findings"]["upload_settings_text"] = upload_text[idx: idx + 1500] if idx >= 0 else upload_text[:1500]
            except Exception:
                pass
            # Ne jamais publier : on quitte simplement la page
        except Exception as e_run:
            report["status"] = "error"
            report["error"] = str(e_run)[:300]
            try:
                page.screenshot(path=os.path.join(out_dir, "story_error.png"))
            except Exception:
                pass
        finally:
            context.close()
            browser.close()

    with open(os.path.join(out_dir, "story_probe_report.json"), "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Sonde lecture seule des options Story de TikTok Studio Web.")
    parser.add_argument("--video", required=True, help="Vidéo de test (jamais publiée)")
    parser.add_argument("--out", default="output/story_probe", help="Dossier des captures")
    args = parser.parse_args()
    res = run_probe(args.video, args.out)
    if res.get("status") in ("auth_error", "error"):
        sys.exit(1)


if __name__ == "__main__":
    main()
