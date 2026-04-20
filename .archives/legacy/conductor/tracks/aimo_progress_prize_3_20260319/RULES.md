# Official Competition Rules: AI Mathematical Olympiad - Progress Prize 3

**Sponsor**: XTX Investments Limited  
**Website**: [Kaggle AIMO Progress Prize 3](https://www.kaggle.com/competitions/ai-mathematical-olympiad-progress-prize-3)

## 1. Key Constraints & Mandates

### 1.1 Model Restrictions (Section 2.6.c)
- **Open-Weight Mandate**: Any LLM (AMLT) used at **runtime** must be at least **open-weight**.
    - *Permitted*: DeepSeek-R1, Llama 3, Mistral.
    - *Prohibited*: GPT-4, Claude 3.5, Gemini 1.5 Pro (if used at runtime).
- **Release Cutoff**: All runtime models must have been released prior to **15th March 2026**.
- **Commercial Usage**: Commercial models (like GPT-4) can be used **indirectly** for data generation/distillation, but NOT in the final submission pipeline.

### 1.2 Evaluation & Scoring (Section 1.5 & Evaluation Tab)
- **Penalized Accuracy**: Each submission is run **twice** on the private test set.
    - 1.0 point: Correct in both runs.
    - 0.5 points: Correct in one run.
    - 0.0 points: Incorrect in both.
- **Answer Format**: Non-negative integer between **0 and 99,999**.

### 1.3 Reproducibility & Licensing (Section 2.5 & 2.8)
- **License**: Winning submissions must be licensed under **CC-BY 4.0** or an **OSI-approved** open-source license (MIT, Apache 2.0).
- **Full Reproducibility**: The process from data collection to final weights must be fully documented and reproducible without "undue costs."

### 1.4 Submission Limits (Section 2.2)
- **Daily Limit**: 1 submission per day.
- **Final Selection**: 1 final submission for judging.

---

## 2. Prize Structure

- **1st Place**: $262,144
- **2nd Place**: $131,072
- **3rd Place**: $65,536
- **4th Place**: $32,768
- **5th Place**: $16,384
- **Overall Progress Prize**: **$1,589,248+** (Requires score of 47/50 on both public and private sets).
- **Additional Prizes**: Hard Problem Prize ($30k), Writeup Prizes (2x $15k).

---

## 3. Compliance Checklist for Swarm Development
- [ ] Ensure all models in the submission pipeline are open-weight.
- [ ] Verify model release dates are before March 15, 2026.
- [ ] Implement dual-run consistency checks in the local sandbox.
- [ ] Maintain a detailed audit log of all external data and tools used.
- [ ] Prepare for CC-BY 4.0 licensing of all custom code and datasets.
