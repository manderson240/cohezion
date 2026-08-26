"""RSNA Knee Abnormality Detection Baseline Kernel."""
import os
import pandas as pd

def main():
    test_path = "/kaggle/input/rsna-knee-abnormality-detection/test.csv"
    sample_sub = "/kaggle/input/rsna-knee-abnormality-detection/sample_submission.csv"
    
    if os.path.exists(sample_sub):
        df = pd.read_csv(sample_sub)
    elif os.path.exists(test_path):
        test_df = pd.read_csv(test_path)
        cols = ["StudyInstanceUID","ACL","MCL","Medial Meniscus","Lateral Meniscus","Medial OA","Lateral OA","PF OA","Effusion","Synovitis","Baker's","Contusion","Fracture"]
        df = pd.DataFrame(columns=cols)
        df["StudyInstanceUID"] = test_df["StudyInstanceUID"].unique()
    else:
        df = pd.DataFrame()

    priors = {
        "ACL": 0.18, "MCL": 0.12, "Medial Meniscus": 0.31,
        "Lateral Meniscus": 0.19, "Medial OA": 0.28, "Lateral OA": 0.14,
        "PF OA": 0.22, "Effusion": 0.42, "Synovitis": 0.25,
        "Baker's": 0.08, "Contusion": 0.15, "Fracture": 0.05
    }
    
    for col, prob in priors.items():
        if col in df.columns:
            df[col] = prob
            
    df.to_csv("submission.csv", index=False)
    print("Saved submission.csv successfully!")

if __name__ == "__main__":
    main()
