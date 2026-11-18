"""
tests/test_growth_bot.py - Comprehensive tests for Growth-Bot (GrowthOptimizer).
Covers:
- Tier 1: Feature coverage (8 prophetic hooks, AMEN CTA, Abidjan GMT slots, 10 hashtags, retention score).
- Tier 2: Boundary & corner cases (empty inputs, punctuation, casing, missing package keys).
- Tier 3: Summary sheet export and integration structure.
"""

import os
import pytest
from src.growth_optimizer import GrowthOptimizer

@pytest.fixture
def growth_optimizer():
    return GrowthOptimizer()

# ============================================================================
# TIER 1: FEATURE COVERAGE (Core Growth-Bot Capabilities)
# ============================================================================

class TestGrowthBotHooks:
    """Tests for the 8 prophetic hook banner variations in _generate_hook_banner."""

    def test_hook_prophetic_variation(self, growth_optimizer):
        """Keyword 'prophétie' or 'prophétique' triggers prophetic hook."""
        hook1 = growth_optimizer._generate_hook_banner("Voici une prophétie", "Dieu va te visiter")
        assert hook1 == "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️"

        hook2 = growth_optimizer._generate_hook_banner("", "C'est un appel prophétique pour ta maison")
        assert hook2 == "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️"

        hook3 = growth_optimizer._generate_hook_banner("", "Je viens annoncer la gloire de Dieu")
        assert hook3 == "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️"

    def test_hook_miracle_variation(self, growth_optimizer):
        """Keywords 'miracle', 'impossible', 'témoignage' trigger miracle hook."""
        hook = growth_optimizer._generate_hook_banner("Rien n'est impossible à Dieu", "Attends-toi à un miracle")
        assert hook == "LE MIRACLE QUE TU ATTENDS ARRIVE ⚡"

        hook_temoignage = growth_optimizer._generate_hook_banner("Voici un grand témoignage", "pour fortifier ta foi")
        assert hook_temoignage == "LE MIRACLE QUE TU ATTENDS ARRIVE ⚡"

    def test_hook_combat_variation(self, growth_optimizer):
        """Keywords 'combat', 'ennemi', 'délivrance', 'victoire' trigger combat hook."""
        hook = growth_optimizer._generate_hook_banner("Le combat spirituel fait rage", "Mais l'ennemi est vaincu")
        assert hook == "TA VICTOIRE EST PROCHE DÉCLARE-LE ⚔️"

        hook_delivrance = growth_optimizer._generate_hook_banner("C'est l'heure de ta délivrance", "selon Sa promesse")
        assert hook_delivrance == "TA VICTOIRE EST PROCHE DÉCLARE-LE ⚔️"

    def test_hook_prayer_variation(self, growth_optimizer):
        """Keywords 'prière', 'prier', 'demande' trigger prayer hook."""
        hook = growth_optimizer._generate_hook_banner("Entre dans la prière", "Prier sans cesse est notre force")
        assert hook == "FAIS CETTE PRIÈRE PUISSANTE 🙏"

        hook_demande = growth_optimizer._generate_hook_banner("Demande et tu recevras", "selon la volonté divine")
        assert hook_demande == "FAIS CETTE PRIÈRE PUISSANTE 🙏"

    def test_hook_trial_variation(self, growth_optimizer):
        """Keywords 'épreuve', 'douleur', 'pleurer', 'difficile' trigger trial hook."""
        hook = growth_optimizer._generate_hook_banner("Si tu traverses une épreuve", "et que la douleur est vive")
        assert hook == "POURQUOI CETTE ÉPREUVE DANS TA VIE ? 📖"

        hook_pleurer = growth_optimizer._generate_hook_banner("Tu as fini de pleurer", "le temps est difficile mais passera")
        assert hook_pleurer == "POURQUOI CETTE ÉPREUVE DANS TA VIE ? 📖"

    def test_hook_blessing_variation(self, growth_optimizer):
        """Keywords 'bénédiction', 'bénir', 'grâce', 'élévation' trigger blessing hook."""
        hook = growth_optimizer._generate_hook_banner("Une bénédiction divine descend", "La grâce et l'élévation sont à toi")
        assert hook == "CETTE PAROLE VA CHANGER TA VIE ✨"

    def test_hook_faith_variation(self, growth_optimizer):
        """Keywords 'foi', 'croire', 'douter' trigger faith hook."""
        hook = growth_optimizer._generate_hook_banner("Garde la foi en toutes circonstances", "Ne viens pas douter")
        assert hook == "NE DOUTE PLUS DE TA DESTINÉE 👑"

        hook_croire = growth_optimizer._generate_hook_banner("Il faut seulement croire", "au plan parfait")
        assert hook_croire == "NE DOUTE PLUS DE TA DESTINÉE 👑"

    def test_hook_default_fallback(self, growth_optimizer):
        """Text without specific trigger keywords falls back to default message."""
        hook = growth_optimizer._generate_hook_banner("Bonjour à tous mes frères et soeurs", "Regardons ce passage")
        assert hook == "DIEU A UN MESSAGE POUR TOI AUJOURD'HUI ✝️"


class TestGrowthBotCaptionsAndHashtags:
    """Tests for viral caption structure, AMEN CTA, hashtags and schedule."""

    def test_caption_structure_and_amen_cta(self, growth_optimizer):
        """Verifies multi-tier caption format and required AMEN call to action."""
        text = "Le Seigneur dit que ta saison de bénédiction est arrivée aujourd'hui."
        caption = growth_optimizer._generate_caption(text, "Prédication du Dimanche")

        assert caption.startswith("📖")
        assert "Écris 'AMEN' en commentaire pour sceller cette bénédiction 👇" in caption
        assert "Reçois cette parole dans ta vie et partage-la" in caption
        assert "Enregistre cette vidéo pour la réécouter" in caption

    def test_caption_word_truncation_rule(self, growth_optimizer):
        """Verifies summary truncates at 18 words with '...' when long, or uses full text when <= 18 words."""
        short_text = "Seigneur merci pour ta fidélité et ta grâce infinie."
        assert len(short_text.split()) <= 18
        short_caption = growth_optimizer._generate_caption(short_text, "Titre")
        assert f"📖 {short_text}" in short_caption
        assert not short_caption.startswith(f"📖 {short_text}...")

        long_words = [f"mot{i}" for i in range(25)]
        long_text = " ".join(long_words)
        long_caption = growth_optimizer._generate_caption(long_text, "Titre")
        expected_summary = " ".join(long_words[:18]) + "..."
        assert f"📖 {expected_summary}" in long_caption

    def test_select_hashtags_predication_pack(self, growth_optimizer):
        """Verifies default Predication pack uses Karl's exact 5 Christian hashtags."""
        tags = growth_optimizer._select_hashtags("Un enseignement sur la persévérance et l'évangile.")
        assert tags == [
            "#Predication",
            "#Evangile",
            "#JesusChrist",
            "#FoiEnDieu",
            "#ChristianTikTok",
        ]
        assert len(tags) == 5

    def test_select_hashtags_priere_and_gospel_packs(self, growth_optimizer):
        """Verifies Priere and Gospel packs are selected according to clip content."""
        tags_priere = growth_optimizer._select_hashtags("Fais cette prière puissante d'intercession et de délivrance.")
        assert tags_priere == [
            "#Priere",
            "#PriereDuJour",
            "#JesusChrist",
            "#FoiEnDieu",
            "#CotedIvoire",
        ]

        tags_gospel = growth_optimizer._select_hashtags("Un moment de louange et adoration gospel africain.")
        assert tags_gospel == [
            "#Gospel",
            "#MusiqueChretienne",
            "#Louange",
            "#JesusChrist",
            "#GospelAfricain",
        ]

    def test_retention_score_calculation(self, growth_optimizer):
        """Verifies retention formula min(92, int(70 + score * 1.4))."""
        pkg_low = growth_optimizer.generate_growth_package({"text": "Dieu", "score": 0}, "Titre")
        assert pkg_low["estimated_retention"] == "70%"

        pkg_mid = growth_optimizer.generate_growth_package({"text": "Dieu", "score": 10}, "Titre")
        assert pkg_mid["estimated_retention"] == "84%"

        pkg_high = growth_optimizer.generate_growth_package({"text": "Dieu", "score": 25}, "Titre")
        assert pkg_high["estimated_retention"] == "92%"  # Capped at 92

    def test_posting_slots_gmt_abidjan(self, growth_optimizer):
        """Verifies 4 Abidjan GMT schedule slots."""
        pkg = growth_optimizer.generate_growth_package({"text": "Prière matinale"}, "Titre")
        slots = pkg["recommended_schedule"]
        assert len(slots) == 4
        assert any("05h30 - 06h45 GMT" in s for s in slots)
        assert any("12h30 - 13h45 GMT" in s for s in slots)
        assert any("19h30 - 21h30 GMT" in s for s in slots)
        assert any("Dimanche" in s for s in slots)
        assert "Côte d'Ivoire (GMT / Abidjan)" in pkg["location_focus"]


# ============================================================================
# TIER 2: BOUNDARY & CORNER CASES
# ============================================================================

class TestGrowthBotCornerCases:
    """Boundary and adversarial edge cases for GrowthOptimizer."""

    def test_empty_and_whitespace_clip_info(self, growth_optimizer):
        """Handles completely empty clip_info dictionary without crashing."""
        pkg = growth_optimizer.generate_growth_package({}, "")
        assert pkg["hook_banner"] == "DIEU A UN MESSAGE POUR TOI AUJOURD'HUI ✝️"
        assert "📖" in pkg["caption"]
        assert len(pkg["hashtags"]) == 5
        assert pkg["hashtags"] == GrowthOptimizer.HASHTAG_PACKS["predication"]
        assert pkg["estimated_retention"] == "84%"  # Default score 10 in clip_info.get("score", 10)

    def test_special_characters_and_french_accents(self, growth_optimizer):
        """Handles French elisions, apostrophes, and mixed accents."""
        text = "L'ennemi a voulu détruire ta destinée, mais la délivrance est là !"
        pkg = growth_optimizer.generate_growth_package({"text": text, "first_sentence": text}, "Sujet")
        assert pkg["hook_banner"] == "TA VICTOIRE EST PROCHE DÉCLARE-LE ⚔️"

    def test_case_insensitivity_in_keyword_matching(self, growth_optimizer):
        """Keyword detection must be fully case-insensitive."""
        hook_upper = growth_optimizer._generate_hook_banner("VOICI UNE PROPHÉTIE MAJEURE", "")
        assert hook_upper == "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️"

        hook_mixed = growth_optimizer._generate_hook_banner("Un MiRaClE S'aCcOmPlIt", "")
        assert hook_mixed == "LE MIRACLE QUE TU ATTENDS ARRIVE ⚡"

    def test_export_summary_sheet_resilience(self, growth_optimizer, tmp_path):
        """
        Summary sheet export must succeed without raising KeyError,
        even if optional keys like karl_studio_link or schedule are missing or defaulted.
        """
        out_sheet = tmp_path / "test_sheet.txt"
        package = {
            "hook_banner": "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️",
            "full_post_text": "Légende complète avec #chretien",
            "recommended_schedule": ["Matin 06h00 GMT"],
            "estimated_retention": "88%",
            "cta": "Écris AMEN",
            "location_focus": "Côte d'Ivoire (GMT / Abidjan)"
            # Note: karl_studio_link omitted to test fallback resilience
        }
        growth_optimizer.export_summary_sheet(package, str(out_sheet))
        assert out_sheet.exists()
        content = out_sheet.read_text(encoding="utf-8")
        assert "ÉCOUTE CE MESSAGE PROPHÉTIQUE 🕊️" in content
        assert "FICHE STRATÉGIQUE PUBLICATION TIKTOK" in content
        assert "Côte d'Ivoire" in content

    def test_export_summary_sheet_with_karl_link(self, growth_optimizer, tmp_path):
        """Verifies summary sheet output when karl_studio_link is explicitly supplied."""
        out_sheet = tmp_path / "test_sheet_full.txt"
        package = growth_optimizer.generate_growth_package({"text": "Prière de foi", "score": 12}, "Culte")
        growth_optimizer.export_summary_sheet(package, str(out_sheet))
        assert out_sheet.exists()
        content = out_sheet.read_text(encoding="utf-8")
        assert "https://digrekarlito11-eng.github.io/karl-studio/" in content
