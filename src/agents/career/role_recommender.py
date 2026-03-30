import json
import os
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field, ValidationError

try:
    from langchain_core.output_parsers import PydanticOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_groq import ChatGroq

    _LLM_OK = True
except Exception:
    PydanticOutputParser = None  # type: ignore[assignment]
    ChatPromptTemplate = None  # type: ignore[assignment]
    ChatGroq = None  # type: ignore[assignment]
    _LLM_OK = False


class _RoleEvidence(BaseModel):
    signal: str = ""
    evidence: str = "non demontre"


class _RoleOut(BaseModel):
    role_title: str
    sector: str = "unknown"
    domain: str = "industrie"
    role_description: str = "Role industrie recommande."
    seniority: str = "IC"
    match_score: float = Field(default=0.0, ge=0.0, le=100.0)
    confidence: float = Field(default=0.2, ge=0.0, le=1.0)
    why_match: List[_RoleEvidence] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    next_actions: List[str] = Field(default_factory=list)


class _NoGoOut(BaseModel):
    role_title: str
    sector: str = "unknown"
    why_not_now: str = "Preuves insuffisantes."
    main_gaps: List[str] = Field(default_factory=list)
    confidence: float = Field(default=0.2, ge=0.0, le=1.0)


class _SuggestedOut(BaseModel):
    role_title: str
    domain: str = "industrie"
    description: str = "Role possible a explorer."


class _LLMBundle(BaseModel):
    top_immediate_fit: List[_RoleOut] = Field(default_factory=list)
    top_near_fit: List[_RoleOut] = Field(default_factory=list)
    no_go_roles: List[_NoGoOut] = Field(default_factory=list)
    suggested_roles: List[_SuggestedOut] = Field(default_factory=list)
    llm_summary: str = ""


class RoleRecommenderAgent:
    """Hybrid recommender: deterministic ranking + optional LLM expert overlay."""

    def __init__(self, catalog_path: str = "data/references/industry_roles_catalog.json", use_llm: Optional[bool] = None):
        self.catalog_path = catalog_path
        self.catalog = self._load_catalog()
        self.llm = None
        self.parser = None
        self.llm_enabled = False
        self.llm_status = "disabled"
        self._init_llm(use_llm)

    def _init_llm(self, use_llm: Optional[bool]) -> None:
        env_flag = str(os.getenv("CAREER_RECOMMENDER_USE_LLM", "1")).strip().lower()
        enable = env_flag not in {"0", "false", "no"} if use_llm is None else bool(use_llm)
        if not enable:
            self.llm_status = "disabled_by_config"
            return
        if not _LLM_OK:
            self.llm_status = "disabled_llm_stack_missing"
            return
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            self.llm_status = "disabled_missing_groq_key"
            return
        try:
            model = os.getenv("CAREER_LLM_MODEL", os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"))
            self.llm = ChatGroq(temperature=0.0, model_name=model, groq_api_key=api_key)
            self.parser = PydanticOutputParser(pydantic_object=_LLMBundle)
            self.llm_enabled = True
            self.llm_status = f"enabled:{model}"
        except Exception as exc:
            self.llm_status = f"disabled_init_error:{exc.__class__.__name__}"

    def _load_catalog(self) -> Dict[str, Any]:
        if os.path.exists(self.catalog_path):
            with open(self.catalog_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"version": "unknown", "roles": []}

    @staticmethod
    def _normalize(text: str) -> str:
        if not isinstance(text, str):
            return ""
        return re.sub(r"\s+", " ", text.strip().lower())

    @staticmethod
    def _clip(v: float, low: float, high: float) -> float:
        return max(low, min(v, high))

    def _find_evidence_snippet(self, cv_text: str, term: str) -> Optional[str]:
        if not cv_text or not term:
            return None
        m = re.search(re.escape(term), cv_text, flags=re.IGNORECASE)
        if not m:
            return None
        start = max(0, m.start() - 90)
        end = min(len(cv_text), m.end() + 90)
        return cv_text[start:end].replace("\n", " ").strip()

    def _match_terms(self, cv_text: str, terms: List[str]) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        seen: Set[str] = set()
        cv_norm = self._normalize(cv_text)
        for t in terms:
            term = str(t or "").strip()
            key = self._normalize(term)
            if not key or key in seen:
                continue
            snip = self._find_evidence_snippet(cv_text, term)
            if not snip:
                words = [w for w in re.findall(r"[a-z0-9\+\-]+", key) if len(w) > 2]
                if words and sum(1 for w in words if w in cv_norm) >= max(1, len(words) - 1):
                    snip = self._find_evidence_snippet(cv_text, words[0])
            if snip:
                out.append((term, snip))
                seen.add(key)
        return out

    def _skill_pool(self, tech_analysis: List[Dict[str, Any]]) -> List[str]:
        skills: List[str] = []
        for s in tech_analysis:
            if s.get("audit_status") == "VALIDATED" or s.get("status") == "INFERRED":
                name = str(s.get("skill_name", "")).strip()
                if name:
                    skills.append(name)
        return skills

    def _selected_sectors(self, preferences: Dict[str, Any]) -> Set[str]:
        return {self._normalize(s) for s in preferences.get("target_sectors", []) if isinstance(s, str) and s.strip()}

    def _domain_hint(self, preferences: Dict[str, Any]) -> str:
        return str(preferences.get("target_domain_text", "")).strip()

    def _action_plan(self, gaps: List[str], preferences: Dict[str, Any]) -> Dict[str, List[str]]:
        sectors = preferences.get("target_sectors", []) if isinstance(preferences, dict) else []
        sector_hint = ", ".join(sectors[:3]) if sectors else "vos secteurs cibles"
        return {
            "30_days": [
                "Refondre le CV au format industrie (impact et livrables).",
                f"Construire une shortlist de 20 postes dans {sector_hint}.",
            ],
            "60_days": [
                "Produire des preuves sur les gaps prioritaires (projets, KPIs, livrables).",
                "Simuler entretiens techniques et comportementaux.",
            ],
            "90_days": [
                "Candidater sur les roles immediate/near fit.",
                f"Gaps a reduire en priorite: {', '.join(gaps[:6]) if gaps else 'aucun gap critique'}.",
            ],
        }

    def _infer_families(self, cv_text: str, selected: Set[str]) -> List[Dict[str, str]]:
        families = [
            ("Scientifique developpement procedes", "Biotech / Bioproduction", "Conception et optimisation de procedes.", ["cell culture", "fermentation", "bioprocess"]),
            ("Data Scientist industriel", "Data / Analytics", "Modelisation pour decisions operationnelles.", ["python", "machine learning", "statistics"]),
            ("Ingenieur validation", "Pharma / Qualite", "Validation de procedes et equipements.", ["validation", "gmp", "iq", "oq", "pq"]),
            ("Specialiste affaires reglementaires", "Reglementaire", "Conformite et dossiers techniques.", ["regulatory", "fda", "ce", "iso 14971"]),
            ("Specialiste assurance qualite", "Qualite", "Pilotage qualite et amelioration continue.", ["quality assurance", "capa", "audit"]),
        ]
        norm = self._normalize(cv_text)
        out: List[Dict[str, str]] = []
        seen: Set[str] = set()
        for title, dom, desc, kws in families:
            hits = sum(1 for k in kws if self._normalize(k) in norm)
            if hits < 1:
                continue
            key = self._normalize(title)
            if key in seen:
                continue
            if selected and not any(sec in self._normalize(dom) for sec in selected) and hits < 2:
                continue
            out.append({"role_title": title, "domain": dom, "description": desc})
            seen.add(key)
        return out[:12]

    def _catalog_role(self, title: str) -> Dict[str, Any]:
        key = self._normalize(title)
        for role in self.catalog.get("roles", []):
            if self._normalize(role.get("role_title", "")) == key:
                return role
        return {}

    def _derive_domain_and_description(self, title: str, domain: str, description: str) -> Tuple[str, str]:
        cat = self._catalog_role(title)
        dom = str(domain or "").strip()
        desc = str(description or "").strip()

        is_default_domain = self._normalize(dom) in {"", "industrie", "industry"}
        is_default_desc = self._normalize(desc) in {
            "",
            "role possible a explorer.",
            "role industrie recommande.",
            "role industrie.",
            "role possible a explorer",
            "role industrie recommande",
        }

        if is_default_domain:
            if cat.get("sector"):
                dom = str(cat.get("sector"))
            elif " - " in title:
                dom = title.split(" - ", 1)[1].strip()
            else:
                dom = "industrie"

        if is_default_desc:
            if cat.get("description"):
                desc = str(cat.get("description"))
            else:
                must = [str(x).strip() for x in cat.get("must_have", [])[:3] if str(x).strip()]
                if must:
                    desc = f"Poste oriente {dom} centre sur {', '.join(must)}."
                else:
                    desc = f"Poste en {dom} adapte a un profil de transition vers l'industrie."

        return dom, desc

    def _complete_suggested_roles(
        self,
        seed_suggestions: List[Dict[str, str]],
        ranked_roles: List[Dict[str, Any]],
        selected: Set[str],
        min_items: int = 10,
    ) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        seen: Set[str] = set()
        catalog = self.catalog.get("roles", [])
        by_title = {self._normalize(r.get("role_title", "")): r for r in catalog if r.get("role_title")}

        def add_role(title: str, domain: str, description: str) -> None:
            key = self._normalize(title)
            if not key or key in seen:
                return
            dom, desc = self._derive_domain_and_description(title, domain, description)
            out.append({"role_title": title, "domain": dom, "description": desc})
            seen.add(key)

        for s in seed_suggestions:
            title = str(s.get("role_title", "")).strip()
            key = self._normalize(title)
            cat = by_title.get(key, {})
            sec = self._normalize(cat.get("sector", "")) if cat else ""
            if selected and sec and sec not in selected:
                continue
            add_role(title, str(s.get("domain", "industrie")), str(s.get("description", "Role possible a explorer.")))

        for r in ranked_roles:
            title = str(r.get("role_title", "")).strip()
            key = self._normalize(title)
            cat = by_title.get(key, {})
            sec = self._normalize(r.get("sector", cat.get("sector", "")))
            if selected and sec and sec not in selected:
                continue
            add_role(
                title,
                str(r.get("domain", r.get("sector", cat.get("sector", "industrie")))),
                str(r.get("role_description", cat.get("description", "Role possible a explorer."))),
            )
            if len(out) >= min_items:
                return out[:12]

        for cat in catalog:
            sec = self._normalize(cat.get("sector", ""))
            if selected and sec not in selected:
                continue
            add_role(
                str(cat.get("role_title", "Role industrie")),
                str(cat.get("sector", "industrie")),
                str(cat.get("description", "Role possible a explorer.")),
            )
            if len(out) >= min_items:
                break
        return out[:12]

    def _complete_suggested_open_world(
        self,
        seed_suggestions: List[Dict[str, str]],
        ranked_roles: List[Dict[str, Any]],
        min_items: int = 8,
    ) -> List[Dict[str, str]]:
        out: List[Dict[str, str]] = []
        seen: Set[str] = set()

        def add_role(title: str, domain: str, description: str) -> None:
            t = str(title or "").strip()
            key = self._normalize(t)
            if not key or key in seen:
                return
            d = str(domain or "").strip() or "industrie"
            desc = str(description or "").strip()
            if self._normalize(desc) in {
                "",
                "role possible a explorer.",
                "role possible a explorer",
                "role industrie recommande.",
                "role industrie recommande",
                "role industrie.",
            }:
                desc = f"Poste en {d} aligne avec les competences detectees dans le CV."
            out.append({"role_title": t, "domain": d, "description": desc})
            seen.add(key)

        for s in seed_suggestions:
            add_role(s.get("role_title", ""), s.get("domain", "industrie"), s.get("description", ""))
            if len(out) >= 12:
                return out[:12]

        for r in ranked_roles:
            add_role(
                r.get("role_title", ""),
                r.get("domain", r.get("sector", "industrie")),
                r.get("role_description", ""),
            )
            if len(out) >= max(min_items, 12):
                break

        return out[:12]

    def _deterministic(self, cv_text: str, tech_analysis: List[Dict[str, Any]], cv_global_analysis: Dict[str, Any], preferences_data: Dict[str, Any]) -> Dict[str, Any]:
        roles = self.catalog.get("roles", [])
        if not cv_text.strip() or not roles:
            return {
                "catalog_version": self.catalog.get("version", "unknown"),
                "methodology": "evidence_constrained_deterministic_v1",
                "top_immediate_fit": [],
                "top_near_fit": [],
                "no_go_roles": [],
                "suggested_roles": [],
                "action_plan_30_60_90": {"30_days": ["Ajouter un CV exploitable."], "60_days": [], "90_days": []},
                "global_note": "Aucune recommandation: CV vide ou catalogue indisponible.",
            }

        selected = self._selected_sectors(preferences_data)
        pool = [self._normalize(s) for s in self._skill_pool(tech_analysis)]
        scored: List[Dict[str, Any]] = []
        gaps_summary: List[str] = []
        cv_boost = float(cv_global_analysis.get("overall_score", 0.0)) * 1.2

        for role in roles:
            sector = self._normalize(role.get("sector", "unknown"))
            if selected and sector not in selected and sector != "cross_sector":
                continue
            must = role.get("must_have", [])
            nice = role.get("nice_to_have", [])
            trans = role.get("transferability_signals", [])
            red = role.get("red_flags", [])

            must_m = self._match_terms(cv_text, [*must, *pool])
            nice_m = self._match_terms(cv_text, nice)
            trans_m = self._match_terms(cv_text, trans)
            red_m = self._match_terms(cv_text, red)

            must_keys = {self._normalize(x[0]) for x in must_m}
            must_hits = sum(1 for t in must if self._normalize(t) in must_keys)
            must_ratio = must_hits / len(must) if must else 0.0
            nice_ratio = min(1.0, len(nice_m) / len(nice)) if nice else 0.0
            tr_ratio = min(1.0, len(trans_m) / len(trans)) if trans else 0.0
            red_hits = len(red_m)

            score = 100.0 * (0.55 * must_ratio + 0.20 * nice_ratio + 0.25 * tr_ratio) - (12.0 * red_hits) + cv_boost
            score = round(self._clip(score, 0.0, 100.0), 1)
            conf = 0.20 + 0.16 * must_hits + 0.06 * len(nice_m) + 0.07 * len(trans_m) - 0.10 * red_hits
            conf = round(self._clip(conf, 0.0, 1.0), 2)

            unmet = [m for m in must if self._normalize(m) not in must_keys]
            gaps_summary.extend(unmet[:2])
            why = [{"signal": t, "evidence": e} for t, e in (must_m + trans_m)[:5]] or [{"signal": "none", "evidence": "non demontre"}]
            actions = [f"Produire une preuve concrete sur '{g}'." for g in unmet[:3]]
            if conf < 0.45:
                actions.append("Confiance faible: renforcer les preuves avant candidature agressive.")

            scored.append(
                {
                    "role_title": role.get("role_title", "Unknown role"),
                    "sector": role.get("sector", "unknown"),
                    "domain": role.get("sector", "unknown"),
                    "role_description": role.get("description", "Role industrie."),
                    "seniority": role.get("seniority", "IC"),
                    "match_score": score,
                    "confidence": conf,
                    "why_match": why,
                    "gaps": unmet[:5],
                    "next_actions": actions[:5],
                    "evidence_count": len([x for x in why if self._normalize(x.get("evidence", "")) != "non demontre"]),
                }
            )

        scored.sort(key=lambda x: x["match_score"], reverse=True)
        immediate = [s for s in scored if s["match_score"] >= 60 and s["confidence"] >= 0.40 and s["evidence_count"] >= 1][:10]
        near = [s for s in scored if s not in immediate and s["match_score"] >= 25][:10]
        if not near:
            near = [s for s in scored if s not in immediate][:10]
        no_go = [
            {"role_title": s["role_title"], "sector": s["sector"], "why_not_now": "Gaps critiques ou preuves insuffisantes.", "main_gaps": s["gaps"][:3] or ["non demontre"], "confidence": s["confidence"]}
            for s in sorted(scored, key=lambda x: x["match_score"])[:5]
            if s["match_score"] < 25 and s["confidence"] < 0.30
        ]
        suggested_seed = self._infer_families(cv_text, selected)
        suggested = self._complete_suggested_roles(
            seed_suggestions=suggested_seed,
            ranked_roles=(immediate + near),
            selected=selected,
            min_items=10,
        )

        return {
            "catalog_version": self.catalog.get("version", "unknown"),
            "methodology": "evidence_constrained_deterministic_v1",
            "top_immediate_fit": immediate,
            "top_near_fit": near,
            "no_go_roles": no_go,
            "suggested_roles": suggested,
            "action_plan_30_60_90": self._action_plan(gaps_summary, preferences_data),
            "global_note": "Recommandations anti-hallucination basees sur preuves textuelles du CV.",
        }

    def _rules_open_world(
        self,
        cv_text: str,
        preferences_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not cv_text.strip():
            return {
                "top_immediate_fit": [],
                "top_near_fit": [],
                "no_go_roles": [],
                "suggested_roles": [],
                "llm_summary": "",
            }

        selected = self._selected_sectors(preferences_data)
        domain_hint = self._normalize(self._domain_hint(preferences_data))
        norm = self._normalize(cv_text)

        families = [
            {
                "role_title": "Ingenieur Systemes Embarques",
                "domain": "Systemes embarques",
                "description": "Conception firmware et integration hardware/software sur microcontroleurs.",
                "keywords": ["embedded", "firmware", "stm32", "esp32", "microcontroller", "freertos", "vhdl"],
            },
            {
                "role_title": "Ingenieur Firmware",
                "domain": "Firmware / Electronique",
                "description": "Developpement bas niveau en C/C++ pour produits electroniques.",
                "keywords": ["firmware", "c++", "c ", "stm32", "drivers", "rtos", "micro-ros"],
            },
            {
                "role_title": "Ingenieur Robotique",
                "domain": "Robotique",
                "description": "Developpement de controleurs robots, integration ROS2 et validation.",
                "keywords": ["robot", "robotique", "ros 2", "micro-ros", "gazebo", "pid", "state machine"],
            },
            {
                "role_title": "Ingenieur IoT",
                "domain": "IoT / Edge",
                "description": "Conception d'architectures IoT (MQTT, edge device, dashboard).",
                "keywords": ["iot", "mqtt", "http", "node-red", "wifi", "raspberry", "esp32"],
            },
            {
                "role_title": "Ingenieur Validation Electronique",
                "domain": "Validation / Tests",
                "description": "Verification fonctionnelle et validation de sous-systemes embarques.",
                "keywords": ["validation", "test", "integration", "debug", "simulation", "protocoles"],
            },
            {
                "role_title": "Ingenieur R&D Electronique",
                "domain": "R&D Electronique",
                "description": "Prototypage et developpement de systemes electroniques innovants.",
                "keywords": ["r&d", "electronics", "electronic", "prototype", "capteurs", "pixhawk"],
            },
            {
                "role_title": "Developpeur C++ Temps Reel",
                "domain": "Logiciel Industriel",
                "description": "Developpement applicatif et temps reel pour systemes critiques.",
                "keywords": ["c++", "real-time", "freertos", "linux", "bash", "performance"],
            },
            {
                "role_title": "Ingenieur Integration Systeme",
                "domain": "System Integration",
                "description": "Assemblage et integration de sous-systemes mecaniques/electroniques.",
                "keywords": ["integration", "montage", "sous-systemes", "communication", "uart", "i2c", "spi"],
            },
            {
                "role_title": "Ingenieur Industrialisation Produit Electronique",
                "domain": "Manufacturing / NPI",
                "description": "Preparation au passage prototype vers production industrielle.",
                "keywords": ["industrial", "production", "manufacturing", "quality", "process", "prototype"],
            },
            {
                "role_title": "Application Engineer (Embedded/Robotics)",
                "domain": "Field/Application Engineering",
                "description": "Support technique clients sur solutions embarquees et robotiques.",
                "keywords": ["application", "client", "technical", "robot", "embedded", "demonstration"],
            },
        ]

        scored: List[Dict[str, Any]] = []
        for fam in families:
            hits = sum(1 for kw in fam["keywords"] if self._normalize(kw) in norm)
            if hits <= 0:
                continue

            if selected:
                dom_norm = self._normalize(fam["domain"])
                if not any(sec in dom_norm for sec in selected) and hits < 2:
                    continue
            if domain_hint:
                dom_or_title = self._normalize(fam["domain"] + " " + fam["role_title"])
                if domain_hint not in dom_or_title and hits < 2:
                    continue

            evidence = self._match_terms(cv_text, fam["keywords"])[:4]
            if not evidence:
                continue

            score = round(self._clip(35.0 + hits * 10.0, 0.0, 95.0), 1)
            conf = round(self._clip(0.32 + hits * 0.09, 0.0, 0.9), 2)
            why = [{"signal": t, "evidence": e} for t, e in evidence]
            scored.append(
                {
                    "role_title": fam["role_title"],
                    "sector": fam["domain"],
                    "domain": fam["domain"],
                    "role_description": fam["description"],
                    "seniority": "Junior IC",
                    "match_score": score,
                    "confidence": conf,
                    "why_match": why,
                    "gaps": [],
                    "next_actions": ["Adapter le CV avec KPIs, livrables et resultats industriels."],
                    "evidence_count": len(why),
                }
            )

        scored.sort(key=lambda x: (x["match_score"], x["confidence"]), reverse=True)
        immediate = [s for s in scored if s["match_score"] >= 65 and s["confidence"] >= 0.45][:10]
        near = [s for s in scored if s not in immediate][:10]
        suggested = self._complete_suggested_open_world(
            seed_suggestions=[],
            ranked_roles=(immediate + near),
            min_items=6,
        )
        return {
            "top_immediate_fit": immediate,
            "top_near_fit": near,
            "no_go_roles": [],
            "suggested_roles": suggested,
            "llm_summary": "",
        }

    def _sanitize_json(self, text: str) -> str:
        payload = str(text or "").strip()
        if "```" in payload:
            m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", payload, re.DOTALL)
            payload = m.group(1) if m else payload.replace("```json", "").replace("```", "").strip()
        s, e = payload.find("{"), payload.rfind("}")
        return payload[s : e + 1] if s != -1 and e != -1 and e > s else payload

    def _evidence_supported(self, cv_text: str, evidence: str) -> bool:
        ev = self._normalize(evidence)
        if not ev or ev == "non demontre":
            return True
        cv = self._normalize(cv_text)
        if ev in cv:
            return True
        tokens = [t for t in re.findall(r"[a-z0-9\+\-]{3,}", ev) if len(t) >= 3]
        return sum(1 for t in tokens if t in cv) >= max(3, int(len(tokens) * 0.6)) if tokens else False

    def _llm_overlay(self, cv_text: str, tech_analysis: List[Dict[str, Any]], cv_global_analysis: Dict[str, Any], preferences_data: Dict[str, Any], base: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        if not self.llm_enabled or self.llm is None or self.parser is None:
            return None
        selected = self._selected_sectors(preferences_data)
        roles_ctx = []
        for r in self.catalog.get("roles", [])[:40]:
            sec = self._normalize(r.get("sector", "unknown"))
            if selected and sec not in selected and sec != "cross_sector":
                continue
            roles_ctx.append(
                f"- {r.get('role_title','Role')} | sector={r.get('sector','unknown')} | "
                f"must={', '.join(r.get('must_have', [])[:4])}"
            )
        skills_ctx = []
        for s in tech_analysis[:40]:
            if s.get("audit_status") == "VALIDATED" or s.get("status") == "INFERRED":
                name = str(s.get("skill_name", "")).strip()
                if name:
                    skills_ctx.append(f"- {name} | preuve={str(s.get('proof_excerpt','')).strip() or 'non demontre'}")

        prompt = """
Tu es un expert senior recrutement industrie (PhD/Postdoc).
Rend une sortie JSON stricte.
Interdiction absolue d'inventer: experiences, resultats, chiffres.
Si preuve absente: "non demontre".
Priorise le catalogue interne.

SECTEURS CIBLES: {selected}
CATALOGUE: {roles}
CV_GLOBAL: {cv_global}
HARD_SKILLS: {skills}
CV: {cv}

{fmt}
"""
        try:
            chain = ChatPromptTemplate.from_template(prompt) | self.llm
            raw = chain.invoke(
                {
                    "selected": ", ".join(sorted(selected)) if selected else "non specifie",
                    "roles": "\n".join(roles_ctx) if roles_ctx else "- aucun",
                    "cv_global": json.dumps(cv_global_analysis or {}, ensure_ascii=False),
                    "skills": "\n".join(skills_ctx) if skills_ctx else "- aucune",
                    "cv": cv_text[:14000],
                    "fmt": self.parser.get_format_instructions(),
                }
            )
            txt = getattr(raw, "content", str(raw))
            parsed = None
            try:
                parsed = self.parser.parse(txt)
                if not isinstance(parsed, _LLMBundle):
                    if hasattr(parsed, "model_dump"):
                        parsed = _LLMBundle.model_validate(parsed.model_dump())
                    else:
                        parsed = _LLMBundle.model_validate(parsed)
            except Exception:
                try:
                    parsed = _LLMBundle.model_validate(json.loads(self._sanitize_json(txt)))
                except (ValidationError, json.JSONDecodeError):
                    return None
            if parsed is None:
                return None
        except Exception:
            return None

        det_by_title = {self._normalize(r.get("role_title", "")): r for r in (base.get("top_immediate_fit", []) + base.get("top_near_fit", [])) if r.get("role_title")}
        merged_roles: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for item in list(parsed.top_immediate_fit) + list(parsed.top_near_fit):
            key = self._normalize(item.role_title)
            if not key or key in seen:
                continue
            seen.add(key)
            det = det_by_title.get(key, {})
            clean_why = []
            ev_count = 0
            unsupported = 0
            for ev in item.why_match[:6]:
                evidence = str(ev.evidence or "").strip() or "non demontre"
                if not self._evidence_supported(cv_text, evidence):
                    evidence = "non demontre"
                    unsupported += 1
                elif self._normalize(evidence) != "non demontre":
                    ev_count += 1
                clean_why.append({"signal": str(ev.signal or "signal"), "evidence": evidence})
            if not clean_why:
                clean_why = [{"signal": "none", "evidence": "non demontre"}]

            llm_conf = self._clip(float(item.confidence), 0.0, 1.0)
            det_conf = self._clip(float(det.get("confidence", llm_conf)), 0.0, 1.0)
            conf = round(self._clip(0.65 * llm_conf + 0.35 * det_conf - 0.08 * unsupported, 0.0, 1.0), 2)
            if ev_count == 0:
                conf = min(conf, 0.35)

            llm_score = self._clip(float(item.match_score), 0.0, 100.0)
            det_score = self._clip(float(det.get("match_score", llm_score)), 0.0, 100.0)
            score = round(self._clip(0.65 * det_score + 0.35 * llm_score, 0.0, 100.0), 1)
            if ev_count == 0:
                score = min(score, 45.0)

            merged_roles.append(
                {
                    "role_title": item.role_title,
                    "sector": item.sector or det.get("sector", "unknown"),
                    "domain": item.domain or det.get("domain", item.sector or "industrie"),
                    "role_description": item.role_description or det.get("role_description", "Role industrie recommande."),
                    "seniority": item.seniority or det.get("seniority", "IC"),
                    "match_score": score,
                    "confidence": conf,
                    "why_match": clean_why,
                    "gaps": [g for g in item.gaps[:5] if str(g).strip()],
                    "next_actions": [a for a in item.next_actions[:5] if str(a).strip()],
                    "evidence_count": ev_count,
                }
            )

        merged_roles.sort(key=lambda x: (x["match_score"], x["confidence"]), reverse=True)
        immediate = [r for r in merged_roles if r["match_score"] >= 60 and r["confidence"] >= 0.45 and r["evidence_count"] >= 1][:10]
        near = [r for r in merged_roles if r not in immediate and r["match_score"] >= 30][:10] or [r for r in merged_roles if r not in immediate][:10]
        no_go = [
            {
                "role_title": ng.role_title,
                "sector": ng.sector,
                "why_not_now": ng.why_not_now or "Preuves insuffisantes.",
                "main_gaps": ng.main_gaps[:4] or ["non demontre"],
                "confidence": round(self._clip(float(ng.confidence), 0.0, 1.0), 2),
            }
            for ng in parsed.no_go_roles[:10]
        ] or base.get("no_go_roles", [])[:10]
        suggested_seed = [
            {"role_title": s.role_title, "domain": s.domain, "description": s.description}
            for s in parsed.suggested_roles[:12]
            if str(s.role_title).strip()
        ]
        suggested = self._complete_suggested_roles(
            seed_suggestions=(suggested_seed or base.get("suggested_roles", [])),
            ranked_roles=(immediate + near + base.get("top_immediate_fit", []) + base.get("top_near_fit", [])),
            selected=selected,
            min_items=10,
        )

        return {
            "top_immediate_fit": immediate,
            "top_near_fit": near,
            "no_go_roles": no_go,
            "suggested_roles": suggested,
            "llm_summary": parsed.llm_summary,
        }

    def _llm_open_world(
        self,
        cv_text: str,
        cv_global_analysis: Dict[str, Any],
        preferences_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        if not self.llm_enabled or self.llm is None or self.parser is None:
            return None

        selected = self._selected_sectors(preferences_data)
        domain_hint = self._domain_hint(preferences_data)
        prompt = """
Tu es un expert recrutement industrie.
Objectif: recommander des postes REELS adaptes au CV, sans se limiter a un catalogue interne.
Contraintes anti-hallucination strictes:
- Interdiction d'inventer experiences/resultats.
- Chaque role doit contenir why_match avec evidence issue du CV.
- Si preuve absente: evidence="non demontre" et confidence faible.
- Eviter les roles hors contexte du CV.

PREFERENCES:
- secteurs cibles: {selected}
- domaine libre: {domain_hint}

CV_GLOBAL: {cv_global}
CV: {cv}

Rends un JSON strict conforme au schema.
{fmt}
"""
        try:
            chain = ChatPromptTemplate.from_template(prompt) | self.llm
            raw = chain.invoke(
                {
                    "selected": ", ".join(sorted(selected)) if selected else "non specifie",
                    "domain_hint": domain_hint or "non specifie",
                    "cv_global": json.dumps(cv_global_analysis or {}, ensure_ascii=False),
                    "cv": cv_text[:14000],
                    "fmt": self.parser.get_format_instructions(),
                }
            )
            txt = getattr(raw, "content", str(raw))
            try:
                parsed = self.parser.parse(txt)
                if not isinstance(parsed, _LLMBundle):
                    if hasattr(parsed, "model_dump"):
                        parsed = _LLMBundle.model_validate(parsed.model_dump())
                    else:
                        parsed = _LLMBundle.model_validate(parsed)
            except Exception:
                parsed = _LLMBundle.model_validate(json.loads(self._sanitize_json(txt)))
        except Exception:
            return None

        merged_roles: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for item in list(parsed.top_immediate_fit) + list(parsed.top_near_fit):
            key = self._normalize(item.role_title)
            if not key or key in seen:
                continue
            seen.add(key)

            clean_why = []
            ev_count = 0
            unsupported = 0
            for ev in item.why_match[:6]:
                evidence = str(ev.evidence or "").strip() or "non demontre"
                if not self._evidence_supported(cv_text, evidence):
                    evidence = "non demontre"
                    unsupported += 1
                elif self._normalize(evidence) != "non demontre":
                    ev_count += 1
                clean_why.append({"signal": str(ev.signal or "signal"), "evidence": evidence})
            if not clean_why:
                clean_why = [{"signal": "none", "evidence": "non demontre"}]

            conf = round(self._clip(float(item.confidence) - 0.08 * unsupported, 0.0, 1.0), 2)
            score = round(self._clip(float(item.match_score), 0.0, 100.0), 1)
            if ev_count == 0:
                conf = min(conf, 0.35)
                score = min(score, 45.0)

            merged_roles.append(
                {
                    "role_title": item.role_title,
                    "sector": item.sector or item.domain or "industrie",
                    "domain": item.domain or item.sector or "industrie",
                    "role_description": item.role_description or "Role industrie pertinent a explorer.",
                    "seniority": item.seniority or "IC",
                    "match_score": score,
                    "confidence": conf,
                    "why_match": clean_why,
                    "gaps": [g for g in item.gaps[:5] if str(g).strip()],
                    "next_actions": [a for a in item.next_actions[:5] if str(a).strip()],
                    "evidence_count": ev_count,
                }
            )

        merged_roles.sort(key=lambda x: (x["match_score"], x["confidence"]), reverse=True)
        immediate = [r for r in merged_roles if r["match_score"] >= 60 and r["confidence"] >= 0.45 and r["evidence_count"] >= 1][:10]
        near = [r for r in merged_roles if r not in immediate][:10]
        no_go = [
            {
                "role_title": ng.role_title,
                "sector": ng.sector,
                "why_not_now": ng.why_not_now or "Preuves insuffisantes.",
                "main_gaps": ng.main_gaps[:4] or ["non demontre"],
                "confidence": round(self._clip(float(ng.confidence), 0.0, 1.0), 2),
            }
            for ng in parsed.no_go_roles[:10]
        ]
        suggested_seed = [
            {"role_title": s.role_title, "domain": s.domain, "description": s.description}
            for s in parsed.suggested_roles[:12]
            if str(s.role_title).strip()
        ]
        suggested = self._complete_suggested_open_world(
            seed_suggestions=suggested_seed,
            ranked_roles=(immediate + near),
            min_items=8,
        )
        return {
            "top_immediate_fit": immediate,
            "top_near_fit": near,
            "no_go_roles": no_go,
            "suggested_roles": suggested,
            "llm_summary": parsed.llm_summary,
        }

    def analyze(
        self,
        cv_text: str,
        tech_analysis: Optional[List[Dict[str, Any]]] = None,
        cv_global_analysis: Optional[Dict[str, Any]] = None,
        preferences_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        tech_analysis = tech_analysis or []
        cv_global_analysis = cv_global_analysis or {}
        preferences_data = preferences_data or {}

        rec_mode = self._normalize(str(preferences_data.get("recommendation_mode", "")))
        use_open_world = rec_mode in {"open_world", "llm_open_world", "candidate_open_world"}

        if use_open_world:
            llm_ow = self._llm_open_world(cv_text, cv_global_analysis, preferences_data)
            if llm_ow:
                return {
                    "catalog_version": self.catalog.get("version", "unknown"),
                    "methodology": "open_world_llm_evidence_constrained_v1",
                    "engine_mode": "open_world_llm",
                    "top_immediate_fit": llm_ow.get("top_immediate_fit", []),
                    "top_near_fit": llm_ow.get("top_near_fit", []),
                    "no_go_roles": llm_ow.get("no_go_roles", []),
                    "suggested_roles": llm_ow.get("suggested_roles", []),
                    "action_plan_30_60_90": self._action_plan([], preferences_data),
                    "global_note": (
                        "Recommandations open-world (non limitees au catalogue), "
                        "avec preuves textuelles obligatoires. "
                        f"Mode LLM: {self.llm_status}. " + (llm_ow.get("llm_summary", "") or "")
                    ).strip(),
                }

            rules_ow = self._rules_open_world(cv_text, preferences_data)
            return {
                "catalog_version": self.catalog.get("version", "unknown"),
                "methodology": "open_world_rules_fallback_v1",
                "engine_mode": "open_world_rules_only",
                "top_immediate_fit": rules_ow.get("top_immediate_fit", []),
                "top_near_fit": rules_ow.get("top_near_fit", []),
                "no_go_roles": rules_ow.get("no_go_roles", []),
                "suggested_roles": rules_ow.get("suggested_roles", []),
                "action_plan_30_60_90": self._action_plan([], preferences_data),
                "global_note": (
                    "Mode open-world en fallback regles (LLM indisponible). "
                    "Suggestions basees uniquement sur signaux detectes dans le CV."
                ),
            }

        base = self._deterministic(cv_text, tech_analysis, cv_global_analysis, preferences_data)
        llm = self._llm_overlay(cv_text, tech_analysis, cv_global_analysis, preferences_data, base)
        if not llm:
            base["engine_mode"] = "deterministic_only"
            base["global_note"] = f"{base.get('global_note', '')} | Mode LLM: {self.llm_status}. Fallback deterministe actif."
            return base

        return {
            "catalog_version": self.catalog.get("version", "unknown"),
            "methodology": "hybrid_llm_evidence_constrained_v2",
            "engine_mode": "hybrid_llm_plus_rules",
            "top_immediate_fit": llm.get("top_immediate_fit", []),
            "top_near_fit": llm.get("top_near_fit", []),
            "no_go_roles": llm.get("no_go_roles", []),
            "suggested_roles": llm.get("suggested_roles", []),
            "action_plan_30_60_90": base.get("action_plan_30_60_90", {}),
            "global_note": (
                "Recommandations hybrides (LLM + regles), anti-hallucination, preuves CV obligatoires. "
                f"Mode LLM: {self.llm_status}. " + (llm.get("llm_summary", "") or "")
            ).strip(),
        }
