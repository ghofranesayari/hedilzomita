import os
import re
from typing import Any, Dict, List, Literal, Optional

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq
from pydantic import BaseModel, Field


class CVRisk(BaseModel):
    title: str = Field(description="Risk label in French.")
    severity: Literal["HIGH", "MEDIUM", "LOW"] = Field(description="Risk severity.")
    evidence: str = Field(description="Exact quote from the CV or pitch.")
    why_it_hurts: str = Field(description="Why this hurts an industry application.")


class CVAdvice(BaseModel):
    priority: int = Field(ge=1, le=5)
    action: str = Field(description="Concrete change to apply in the CV.")
    rationale: str = Field(description="Why this change improves hiring signal.")
    example_rewrite: Optional[str] = Field(
        default=None,
        description="Suggested rewrite pattern, without inventing fake metrics.",
    )


class CVGlobalDiagnostic(BaseModel):
    profile_positioning: Literal["INDUSTRY_READY", "HYBRID", "ACADEMIC_BIASED"]
    confidence: float = Field(ge=0.0, le=1.0)
    industry_relevance: float = Field(ge=0.0, le=10.0)
    business_impact: float = Field(ge=0.0, le=10.0)
    transferability_narrative: float = Field(ge=0.0, le=10.0)
    brevity_focus: float = Field(ge=0.0, le=10.0)
    publication_calibration: float = Field(ge=0.0, le=10.0)
    evidence_quality: float = Field(ge=0.0, le=10.0)
    critical_risks: List[CVRisk] = Field(default_factory=list)
    priority_actions: List[CVAdvice] = Field(default_factory=list)
    expert_summary: str = Field(description="Executive summary in French.")


class IndustryCVAdvisorAgent:
    """Global CV advisor focused on PhD/Postdoc transitions to industry."""

    def __init__(self):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY manquante.")
        self.llm = ChatGroq(
            temperature=0.0,
            model_name=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
            groq_api_key=api_key,
        )
        self.parser = PydanticOutputParser(pydantic_object=CVGlobalDiagnostic)

    def _sanitize_json_output(self, text: str) -> str:
        text = text.strip()
        if "```" in text:
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
            text = match.group(1) if match else text.split("```")[1]
        start = text.find("{")
        end = text.rfind("}")
        return text[start : end + 1] if start != -1 and end != -1 else text

    def _count_publication_signals(self, cv_text: str) -> int:
        markers = [
            r"\bpublication",
            r"\bpublications",
            r"\bjournal",
            r"\bconference",
            r"\bdoi\b",
            r"\bet al\.",
            r"\bvol\.",
            r"\bpp\.",
        ]
        count = 0
        for marker in markers:
            count += len(re.findall(marker, cv_text, flags=re.IGNORECASE))
        return count

    def _count_impact_metrics(self, text: str) -> int:
        patterns = [
            r"\b\d+(?:[\.,]\d+)?\s?%",
            r"\b\d+(?:[\.,]\d+)?\s?(?:k|m|million|milliards?)\b",
            r"\b(?:ROI|KPI|co[uû]t|cost|d[ée]lai|lead time|yield|throughput)\b",
            r"\b\d+(?:[\.,]\d+)?\s?(?:jours?|months?|semaines?|heures?|hours?)\b",
        ]
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text, flags=re.IGNORECASE))
        return count

    def _extract_text_lines(self, text: str, min_len: int = 25, max_len: int = 220) -> List[str]:
        chunks = re.split(r"[\n\r]+", text or "")
        out: List[str] = []
        for chunk in chunks:
            line = re.sub(r"\s+", " ", str(chunk).strip(" -\t•")).strip()
            if min_len <= len(line) <= max_len:
                out.append(line)
        return out

    def _is_generic_text(self, text: str, min_len: int = 24) -> bool:
        t = str(text or "").strip().lower()
        if len(t) < min_len:
            return True
        generic_markers = [
            "n/a",
            "non demontre",
            "non démontré",
            "fallback",
            "role possible",
            "role industrie",
            "diagnostic non disponible",
            "erreur",
        ]
        return any(m in t for m in generic_markers)

    def _evidence_exists_in_source(self, evidence: str, source: str) -> bool:
        ev = re.sub(r"\s+", " ", str(evidence or "").strip().lower())
        src = re.sub(r"\s+", " ", str(source or "").strip().lower())
        if not ev or ev in {"non demontre", "n/a"}:
            return False
        if ev in src:
            return True
        tokens = [t for t in re.findall(r"[a-z0-9\+\-]{3,}", ev) if len(t) >= 3]
        if not tokens:
            return False
        overlap = sum(1 for t in tokens if t in src)
        return overlap >= max(3, int(len(tokens) * 0.6))

    def _tailor_output(
        self,
        output: Dict[str, Any],
        cv_text: str,
        pitch_text: str,
        hard_skills_context: str,
    ) -> Dict[str, Any]:
        source_text = f"{cv_text}\n{pitch_text}"
        lines = self._extract_text_lines(source_text)
        pub_lines = [l for l in lines if re.search(r"\b(publication|journal|conference|doi|et al)\b", l, flags=re.IGNORECASE)]
        impact_lines = [
            l
            for l in lines
            if re.search(
                r"(\b\d+(?:[\.,]\d+)?\s?%|\b(kpi|roi|yield|throughput|cost|co[uû]t|d[ée]lai)\b)",
                l,
                flags=re.IGNORECASE,
            )
        ]
        transfer_lines = [
            l
            for l in lines
            if re.search(
                r"\b(develop|designed|led|managed|implemented|optimized|validated|pilot|delivered|coordinated|responsable|dirig[ée])\b",
                l,
                flags=re.IGNORECASE,
            )
        ]

        ref_general = (transfer_lines or impact_lines or pub_lines or lines or ["Information CV a preciser."])[0]
        ref_publication = (pub_lines or [ref_general])[0]
        ref_impact = (impact_lines or [ref_general])[0]

        risks = output.get("critical_risks", []) or []
        normalized_risks: List[Dict[str, Any]] = []
        for risk in risks[:6]:
            title = str(risk.get("title", "Risque CV")).strip() or "Risque CV"
            severity = str(risk.get("severity", "MEDIUM")).upper()
            if severity not in {"HIGH", "MEDIUM", "LOW"}:
                severity = "MEDIUM"
            evidence = str(risk.get("evidence", "")).strip()
            why = str(risk.get("why_it_hurts", "")).strip()

            title_norm = title.lower()
            target_ref = ref_general
            if "publication" in title_norm or "academ" in title_norm:
                target_ref = ref_publication
            elif any(k in title_norm for k in ["impact", "metric", "kpi", "business", "resultat", "résultat"]):
                target_ref = ref_impact

            if self._is_generic_text(evidence) or not self._evidence_exists_in_source(evidence, source_text):
                evidence = target_ref
            if self._is_generic_text(why, min_len=28):
                if target_ref == ref_publication:
                    why = "Ce signal renforce une image academique et reduit la lisibilite de la valeur business pour un recruteur industrie."
                elif target_ref == ref_impact:
                    why = "Sans resultats mesurables relies au business, la credibilite de transition vers l'industrie baisse nettement."
                else:
                    why = "Le message n'explique pas assez clairement la valeur operationnelle livrable en contexte industriel."

            normalized_risks.append(
                {
                    "title": title,
                    "severity": severity,
                    "evidence": evidence,
                    "why_it_hurts": why,
                }
            )

        if not normalized_risks:
            normalized_risks = [
                {
                    "title": "Narratif trop academique",
                    "severity": "MEDIUM",
                    "evidence": ref_publication,
                    "why_it_hurts": "Le CV priorise des signaux académiques au lieu de la valeur opérationnelle attendue en industrie.",
                },
                {
                    "title": "Impact business insuffisamment quantifie",
                    "severity": "MEDIUM",
                    "evidence": ref_impact,
                    "why_it_hurts": "Le recruteur ne peut pas estimer la contribution concrete sans indicateurs mesurables.",
                },
            ]

        actions = output.get("priority_actions", []) or []
        normalized_actions: List[Dict[str, Any]] = []
        for idx, action in enumerate(actions[:6], start=1):
            a = str(action.get("action", "")).strip()
            r = str(action.get("rationale", "")).strip()
            ex = str(action.get("example_rewrite", "") or "").strip()
            p = int(action.get("priority", idx)) if str(action.get("priority", idx)).isdigit() else idx
            p = max(1, min(p, 5))

            if self._is_generic_text(a):
                a = "Reecrire un bloc d'experience avec resultat industriel explicite."
            if self._is_generic_text(r, min_len=20):
                r = f"Observation source: \"{ref_general}\". Cette formulation doit etre traduite en valeur operationnelle pour l'industrie."

            ref = ref_general
            a_norm = a.lower()
            if "publication" in a_norm:
                ref = ref_publication
            elif any(k in a_norm for k in ["impact", "kpi", "resultat", "metric", "business"]):
                ref = ref_impact

            if self._is_generic_text(ex, min_len=18):
                ex = (
                    f"Au lieu de \"{ref}\", ecrire une version orientee industrie: "
                    "\"Action realisee -> contexte industriel -> impact mesurable reel (sans inventer de chiffre)\"."
                )

            normalized_actions.append(
                {
                    "priority": p,
                    "action": a,
                    "rationale": r,
                    "example_rewrite": ex,
                }
            )

        if len(normalized_actions) < 3:
            missing = 3 - len(normalized_actions)
            candidates = [
                {
                    "priority": 1,
                    "action": "Calibrer la section publications pour un CV industrie.",
                    "rationale": f"Le CV contient des signaux publication dominants: \"{ref_publication}\".",
                    "example_rewrite": (
                        f"Conserver 2-4 publications pertinentes et remplacer le reste par des realisations impact: \"{ref_publication}\" -> \"Contribution industrielle + resultat\"."
                    ),
                },
                {
                    "priority": 2,
                    "action": "Ajouter des resultats mesurables par experience.",
                    "rationale": f"Ligne actuelle trop descriptive: \"{ref_impact}\".",
                    "example_rewrite": (
                        f"Reecrire \"{ref_impact}\" en format: action + livrable + indicateur concret (gain de temps, qualite, cout, rendement)."
                    ),
                },
                {
                    "priority": 3,
                    "action": "Expliciter le transfert recherche -> industrie.",
                    "rationale": "Le recruteur doit voir clairement comment les methodes de recherche deviennent valeur business.",
                    "example_rewrite": (
                        "Ajouter une phrase de transition par experience: methode scientifique -> decision/proces produit -> impact."
                    ),
                },
                {
                    "priority": 4,
                    "action": "Ancrer les hard skills dans des preuves de livraison.",
                    "rationale": f"Contexte hard skills actuel: {hard_skills_context[:160]}",
                    "example_rewrite": "Associer chaque competence critique a un livrable concret (prototype, validation, SOP, transfert).",
                },
            ]
            for cand in candidates:
                if missing <= 0:
                    break
                if not any(self._normalize(x.get("action", "")) == self._normalize(cand["action"]) for x in normalized_actions):
                    normalized_actions.append(cand)
                    missing -= 1

        normalized_actions = sorted(normalized_actions, key=lambda x: x.get("priority", 99))[:5]

        expert_summary = str(output.get("expert_summary", "")).strip()
        if self._is_generic_text(expert_summary, min_len=45):
            position = output.get("profile_positioning", "HYBRID")
            expert_summary = (
                f"Profil {position}: le CV montre des atouts techniques, mais la traduction en valeur industrielle reste partielle. "
                f"Preuve representative: \"{ref_general}\". Priorites: calibrer le narratif, quantifier l'impact, et lier chaque competence a un livrable concret."
            )

        output["critical_risks"] = normalized_risks
        output["priority_actions"] = normalized_actions
        output["expert_summary"] = expert_summary
        return output

    def _compute_guardrails(self, output: Dict[str, Any], cv_text: str, pitch_text: str) -> Dict[str, Any]:
        pub_signals = self._count_publication_signals(cv_text)
        impact_signals = self._count_impact_metrics(f"{cv_text}\n{pitch_text}")

        rubric_keys = [
            "industry_relevance",
            "business_impact",
            "transferability_narrative",
            "brevity_focus",
            "publication_calibration",
            "evidence_quality",
        ]
        rubric_values = [float(output.get(k, 0.0)) for k in rubric_keys]
        base = sum(rubric_values) / len(rubric_values) if rubric_values else 0.0

        penalty = 0.0
        if pub_signals >= 12:
            penalty += 1.2
        elif pub_signals >= 8:
            penalty += 0.8

        if impact_signals <= 2:
            penalty += 1.2
        elif impact_signals <= 5:
            penalty += 0.6

        final_score = max(0.0, min(round(base - penalty, 1), 10.0))

        output["cv_style_flags"] = {
            "high_publication_density": pub_signals >= 8,
            "low_business_metric_density": impact_signals <= 5,
            "publication_signal_count": pub_signals,
            "business_metric_signal_count": impact_signals,
        }
        output["overall_score"] = final_score
        return output

    def _fallback_output(self, cv_text: str, pitch_text: str) -> Dict[str, Any]:
        pub_signals = self._count_publication_signals(cv_text)
        impact_signals = self._count_impact_metrics(f"{cv_text}\n{pitch_text}")
        publication_score = 4.0 if pub_signals >= 8 else 6.5
        business_score = 3.0 if impact_signals <= 2 else 5.5
        base = (5.0 + business_score + 5.0 + 5.5 + publication_score + 4.5) / 6
        overall = max(0.0, min(round(base, 1), 10.0))
        return {
            "profile_positioning": "ACADEMIC_BIASED",
            "confidence": 0.4,
            "industry_relevance": 5.0,
            "business_impact": business_score,
            "transferability_narrative": 5.0,
            "brevity_focus": 5.5,
            "publication_calibration": publication_score,
            "evidence_quality": 4.5,
            "critical_risks": [
                {
                    "title": "Analyse CV incomplète (fallback)",
                    "severity": "MEDIUM",
                    "evidence": "Fallback système: parsing LLM indisponible.",
                    "why_it_hurts": "Le diagnostic est partiel et moins précis.",
                }
            ],
            "priority_actions": [
                {
                    "priority": 1,
                    "action": "Réduire la section publications à une sélection ciblée industrie.",
                    "rationale": "Un CV industrie doit prioriser impact, pas exhaustivité académique.",
                    "example_rewrite": "Publications sélectionnées: 3 articles pertinents au poste visé.",
                },
                {
                    "priority": 2,
                    "action": "Ajouter des résultats mesurables orientés business.",
                    "rationale": "Les recruteurs industrie jugent surtout l'effet concret et livrable.",
                    "example_rewrite": "Pilotage d'un protocole réduisant le délai expérimental de X%.",
                },
                {
                    "priority": 3,
                    "action": "Renforcer le pont recherche -> valeur industrielle.",
                    "rationale": "Le narratif de transférabilité est critique pour ce type de profil.",
                    "example_rewrite": "Méthode de recherche appliquée à un besoin production/qualité.",
                },
            ],
            "expert_summary": "Diagnostic généré en mode sécurisé suite à une erreur technique du conseiller CV.",
            "cv_style_flags": {
                "high_publication_density": pub_signals >= 8,
                "low_business_metric_density": impact_signals <= 5,
                "publication_signal_count": pub_signals,
                "business_metric_signal_count": impact_signals,
            },
            "overall_score": overall,
        }

    def analyze(
        self,
        cv_text: str,
        pitch_text: str,
        job_description: str,
        tech_analysis: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        tech_analysis = tech_analysis or []
        evidence_lines = []
        for skill in tech_analysis:
            if skill.get("audit_status") == "VALIDATED" or skill.get("status") == "INFERRED":
                excerpt = skill.get("proof_excerpt") or "Preuve implicite"
                evidence_lines.append(f"- {skill.get('skill_name', 'N/A')} | {excerpt}")
        hard_skills_context = "\n".join(evidence_lines[:30]) if evidence_lines else "Aucune preuve validée."

        prompt = """
        Tu es un Senior Industry CV Advisor ultra-rigoureux. Tu évalues des profils PhD/Postdoc qui visent l'industrie.
        Tu dois fournir une évaluation STRICTEMENT fondée sur les textes fournis, sans invention.

        RÈGLES OBLIGATOIRES:
        1. Interdiction d'inventer des expériences, métriques, résultats ou titres de poste.
        2. Tout risque doit contenir une preuve textuelle exacte dans `evidence`.
        3. `priority_actions` doit contenir 3 à 5 actions, ordonnées par priorité.
        4. Si la section publications est trop dominante, tu dois le signaler explicitement.
        5. Toujours écrire en FRANÇAIS professionnel.

        RUBRIC (0-10):
        - industry_relevance: adéquation du contenu aux attentes industrie.
        - business_impact: présence de résultats mesurables/impact opérationnel.
        - transferability_narrative: traduction recherche -> valeur industrielle.
        - brevity_focus: clarté, concision, priorisation des informations.
        - publication_calibration: calibration de la section publication pour un CV industrie.
        - evidence_quality: niveau de preuves concrètes et traçables.

        POSITIONNEMENT:
        - INDUSTRY_READY: CV majoritairement orienté valeur business/livraison.
        - HYBRID: mix académique/industrie avec signaux partiellement convaincants.
        - ACADEMIC_BIASED: CV surtout académique, faible conversion vers enjeux industrie.

        INPUTS:
        [JOB DESCRIPTION]
        {job_description}

        [CV TEXT]
        {cv_text}

        [PITCH TEXT]
        {pitch_text}

        [HARD SKILLS VALIDATED CONTEXT]
        {hard_skills_context}

        FORMAT JSON:
        {format_instructions}
        """

        try:
            chain = ChatPromptTemplate.from_template(prompt) | self.llm
            response = chain.invoke(
                {
                    "job_description": job_description[:4000],
                    "cv_text": cv_text[:9000],
                    "pitch_text": pitch_text[:3000],
                    "hard_skills_context": hard_skills_context[:3500],
                    "format_instructions": self.parser.get_format_instructions(),
                }
            )
            clean = self._sanitize_json_output(response.content)
            parsed = self.parser.parse(clean).model_dump()
            guarded = self._compute_guardrails(parsed, cv_text, pitch_text)
            return self._tailor_output(guarded, cv_text, pitch_text, hard_skills_context)
        except Exception as exc:
            print(f"CV Advisor Error: {exc}")
            fallback = self._fallback_output(cv_text, pitch_text)
            return self._tailor_output(fallback, cv_text, pitch_text, hard_skills_context)
