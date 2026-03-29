# Official Data Description: AI Mathematical Olympiad - Progress Prize 3

## Data Description
The competition dataset consists of mathematical problems. Each problem is provided in LaTeX format.

## Files
- **test.csv:** The test set. It contains `id` and `problem` columns. The `problem` column contains the math problem in LaTeX.
- **sample_submission.csv:** A sample submission file in the correct format. It contains `id` and `answer` columns.
- **reference.csv:** (If provided) Contains reference problems with ground truth.

## Answer Format
- Every answer is a non-negative integer.
- For Progress Prize 3, the range is 0 to 99,999.

## Constraints
- This is a Code Competition. Your submission must be made through a Kaggle Notebook.
- The test set is hidden during the submission period. When you submit your notebook, it will be re-run against the full test set.
- **Internet Access**: Disabled during submission.
