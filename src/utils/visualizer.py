import matplotlib.pyplot as plt
import numpy as np
from typing import Dict
import os

def generate_radar_chart(data: Dict[str, float], candidate_id: str, output_dir: str = "outputs/"):
    os.makedirs(output_dir, exist_ok=True)
    
    labels = list(data.keys())
    values = list(data.values())
    
    num_vars = len(labels)
    # Calcul des angles
    angles = np.linspace(0, 2 * np.pi, num_vars, endpoint=False).tolist()
    
    # Pour que le graphique soit un polygone fermé, on ajoute la première valeur à la fin
    values = np.concatenate((values, [values[0]]))
    angles += angles[:1]
    
    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))
    
    # Dessin du contour et remplissage
    ax.fill(angles, values, color='#1565c0', alpha=0.25)
    ax.plot(angles, values, color='#1565c0', linewidth=2)
    
    # Configuration des axes
    ax.set_ylim(0, 10) # L'échelle stricte de 0 à 10
    ax.set_yticklabels([]) # On cache les cercles de numéros pour faire plus épuré
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, fontsize=11, fontweight='bold', color='#37474f')
    
    plt.title(f"Diagnostic Opérationnel - {candidate_id}", size=16, color='#263238', y=1.1, fontweight='bold')
    
    output_path = os.path.join(output_dir, f"{candidate_id}_radar.png")
    plt.savefig(output_path, bbox_inches='tight', dpi=300) # dpi=300 pour un rapport HD
    plt.close()
    
    print(f"📊 Radar Chart généré HD : {output_path}")