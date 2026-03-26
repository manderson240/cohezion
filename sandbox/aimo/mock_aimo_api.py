import json
import os

import polars as pl


class AIMOCompetition:
    def __init__(self, problems_path):
        with open(problems_path) as f:
            self.problems = json.load(f)
        self.current_idx = 0
        self.results = []

    def iter_test(self):
        for idx, problem in enumerate(self.problems):
            self.current_idx = idx
            # Create Polars DataFrames to match official API structure
            test_df = pl.DataFrame([{"id": problem["id"], "problem": problem["problem"]}])
            sample_sub_df = pl.DataFrame([{"id": problem["id"], "answer": 0}])
            yield (test_df, sample_sub_df)

    def predict(self, sample_submission_df):
        problem = self.problems[self.current_idx]
        # In Polars, access is via column name and row index
        predicted_answer = sample_submission_df["answer"][0]
        correct = int(predicted_answer) == problem["answer"]
        self.results.append(
            {
                "id": problem["id"],
                "predicted": predicted_answer,
                "actual": problem["answer"],
                "correct": correct,
            }
        )
        print(
            f"[{problem['id']}] Prediction: {predicted_answer} | Actual: {problem['answer']} | Correct: {correct}"
        )

class MockEnv:
    def __init__(self, problems_path):
        self.competition = AIMOCompetition(problems_path)

    def iter_test(self):
        return self.competition.iter_test()

    def predict(self, answer_df):
        self.competition.predict(answer_df)

def make_env(problems_path=None):
    if problems_path is None:
        problems_path = os.path.join(os.path.dirname(__file__), "reference_problems.json")
    return MockEnv(problems_path)
