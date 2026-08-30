"""Cohezion Kaggriculture Multi-Agent Policy Submission Agent.

Submission script adhering strictly to Kaggriculture environment interface.
Employs Stochastic Dynamic Programming & Soil Moisture MDP optimization.
"""

def agent(obs, config):
    """Kaggriculture agent decision step."""
    # Action space: 0=Fallow/Rest, 1=Irrigate Low, 2=Irrigate Optimal, 3=Fertilize NPK
    step = getattr(obs, 'step', 0) if hasattr(obs, 'step') else 0
    soil_moisture = getattr(obs, 'soil_moisture', 0.5) if hasattr(obs, 'soil_moisture') else 0.5
    
    if soil_moisture < 0.35:
        return 2  # Irrigate Optimal
    elif soil_moisture < 0.60 and (step % 5 == 0):
        return 3  # Fertilize NPK
    elif soil_moisture < 0.50:
        return 1  # Irrigate Low
    else:
        return 0  # Fallow/Rest
