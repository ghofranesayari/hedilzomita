import re
from typing import Dict, Any
from rapidfuzz import fuzz 

class PreferenceAgent:
    def __init__(self):
        self.FUZZY_THRESHOLD = 70 # Tolérance pour les fautes de frappe

    def _clean_text(self, text) -> str:
        """Filtre anti-bruit pour supprimer les listes (ex: '1. R&D' -> 'r&d')."""
        if text is None: return ""
        text = str(text).strip().lower()
        if text in ['nan', 'none', 'n/a', 'not applicable', 'not any', '']:
            return ""
        
        # Enlève les numérotations de listes au début ("1. ", "2) ")
        text = re.sub(r'^\d+[\.\)]\s*', '', text)
        # Enlève les caractères invisibles de fin de chaîne
        text = text.replace('\u200b', '').strip()
        
        return text

    def _extract_max_salary(self, text: str) -> float:
        """Trouve la valeur maximale demandée (Ex: '75K - 90K' -> 90000)."""
        clean = self._clean_text(text)
        if not clean: return 0.0
        
        # Convertit les 'k' en zéros (ex: 85k -> 85000)
        clean = re.sub(r'(\d+)\s*k\b', r'\g<1>000', clean)
        clean = clean.replace(',', '').replace('$', '').replace('cad', '')
        
        # Cherche tous les groupes de 4 chiffres ou plus
        numbers = [float(n) for n in re.findall(r'\d{4,}', clean)]
        
        return max(numbers) if numbers else 0.0

    def evaluate_feasibility(self, candidate_prefs: Dict[str, Any], job_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Évalue les préférences SANS pénaliser le salaire."""
        print(" Logistics Agent: Analyse Logistique (Salaire informatif, Score sur Rôle/Secteur)...")
        
        flags = []
        score = 10.0  # On commence à 10/10 sur la base professionnelle

        # --- 1. ALIGNEMENT DU RÔLE (Preferred Roles) ---
        job_title = job_metadata.get('title', '').lower()
        pref_roles = candidate_prefs.get('preferred_roles', [])
        if isinstance(pref_roles, str): pref_roles = [pref_roles] 
            
        valid_roles = [self._clean_text(r) for r in pref_roles if self._clean_text(r)]
        
        role_match = False
        for role in valid_roles:
            if fuzz.partial_ratio(role, job_title) >= self.FUZZY_THRESHOLD or role in job_title:
                role_match = True
                break
        
        if role_match:
            flags.append({"category": "ROLE", "status": "MATCH", "details": f"Le titre '{job_title.title()}' correspond aux aspirations du candidat."})
        else:
            flags.append({"category": "ROLE", "status": "MISMATCH", "details": f"Le candidat vise d'autres rôles (ex: {valid_roles[0].title() if valid_roles else 'Non spécifié'})."})
            score -= 5.0  #  PÉNALITÉ FATALE : -5.0 au lieu de -3.0

        # --- 2. ALIGNEMENT DU SECTEUR D'ACTIVITÉ (Fields of Activity) ---
        job_industry = job_metadata.get('industry', '').lower()
        cand_fields = candidate_prefs.get('fields_of_activity', [])
        if isinstance(cand_fields, str): cand_fields = [cand_fields]
            
        valid_fields = [self._clean_text(f) for f in cand_fields if self._clean_text(f)]
        
        industry_match = False
        if job_industry and valid_fields:
            for field in valid_fields:
                if fuzz.partial_ratio(field, job_industry) >= self.FUZZY_THRESHOLD or field in job_industry:
                    industry_match = True
                    break
                    
            if industry_match:
                flags.append({"category": "INDUSTRY", "status": "MATCH", "details": f"Secteur '{job_industry.title()}' aligné avec ses préférences."})
            else:
                flags.append({"category": "INDUSTRY", "status": "MISMATCH", "details": f"Le candidat préfère d'autres secteurs (ex: {valid_fields[0].title() if valid_fields else 'Non spécifié'})."})
                score -= 2.0

        # --- 3. SALAIRE (Informations PURES, 0 pénalité sur le score) ---
        cand_salary_raw = candidate_prefs.get('salary_expectations', '')
        cand_max_salary = self._extract_max_salary(cand_salary_raw)
        job_budget = job_metadata.get('salary_max', 0.0)

        if cand_max_salary > 0 and job_budget > 0:
            gap = (cand_max_salary - job_budget) / job_budget
            if gap <= 0:
                flags.append({"category": "SALARY", "status": "MATCH", "details": f"Demande ({cand_max_salary:,.0f}$) dans le budget ({job_budget:,.0f}$)"})
            elif gap <= 0.20:
                flags.append({"category": "SALARY", "status": "WARNING", "details": f"Demande ({cand_max_salary:,.0f}$) au-dessus du budget (+{int(gap*100)}%). Négociation possible."})
            else:
                flags.append({"category": "SALARY", "status": "MISMATCH", "details": f"Demande ({cand_max_salary:,.0f}$) hors budget (+{int(gap*100)}%)."})
        else:
            flags.append({"category": "SALARY", "status": "INFO", "details": f"Attentes du candidat : '{str(cand_salary_raw).strip()}'. À valider en entretien."})

        # --- 4. CIBLE ENTREPRISE (Le Bonus Sécurisé) ---
        target_companies = self._clean_text(candidate_prefs.get('target_companies', ''))
        company_name = job_metadata.get('company_name', '').lower()
        
        if company_name and len(company_name) > 2 and company_name in target_companies:
            if role_match: #  CONDITION STRICTE : Le bonus ne s'applique que s'il veut faire ce métier
                flags.append({"category": "COMPANY", "status": "BONUS", "details": f"Le candidat a explicitement ciblé {company_name.title()} ! Bonus accordé."})
                score += 2.0  
            else:
                flags.append({"category": "COMPANY", "status": "INFO", "details": f"Le candidat cible {company_name.title()}, mais le rôle métier ne l'intéresse pas. (Bonus refusé)."})

        # --- CALCUL FINAL ---
        final_score = max(0.0, min(10.0, score)) # Sécurité: Bloquer la note entre 0 et 10
        
        decision = "GO"
        if final_score <= 5.0: decision = "NO_GO" #  Seuil remonté : 5.0 est un échec
        elif final_score < 8.0: decision = "GO_WITH_NEGOTIATION"

        return {
            "flags": flags,
            "global_feasibility_score": final_score,
            "decision_recommendation": decision
        }