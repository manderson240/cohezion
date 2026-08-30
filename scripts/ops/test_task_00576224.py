import numpy as np

# Train 0: input = [[7, 9], [4, 3]]
# Output row 0: 7 9 7 9 7 9  (tile arr x 3)
# Output row 1: 4 3 4 3 4 3  (tile arr x 3)
# Output row 2: 9 7 9 7 9 7  (flipud + rot / fliplr of arr)
# Output row 3: 3 4 3 4 3 4
# Let's check:
arr = np.array([[7, 9], [4, 3]])
# Row 0,1 is arr
# Row 2,3 is [[9, 7], [3, 4]] which is np.fliplr(arr)
# Row 4,5 is arr
def solve(grid):
    a = np.array(grid)
    f = np.fliplr(a)
    block_row_0 = np.hstack([a, a, a])
    block_row_1 = np.hstack([f, f, f])
    block_row_2 = np.hstack([a, a, a])
    return np.vstack([block_row_0, block_row_1, block_row_2]).tolist()

train_0 = {"input": [[7, 9], [4, 3]], "output": [[7, 9, 7, 9, 7, 9], [4, 3, 4, 3, 4, 3], [9, 7, 9, 7, 9, 7], [3, 4, 3, 4, 3, 4], [7, 9, 7, 9, 7, 9], [4, 3, 4, 3, 4, 3]]}
pred = solve(train_0["input"])
print("Matches Train 0 with fliplr alternating row:", pred == train_0["output"])
