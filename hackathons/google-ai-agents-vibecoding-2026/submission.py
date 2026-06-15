def agent(observation, configuration):
    cols, rows, inarow = configuration.columns, configuration.rows, configuration.inarow
    board, mark = observation.board, observation.mark
    def drop_row(c, b):
        for r in range(rows - 1, -1, -1):
            if b[c + r * cols] == 0:
                return r
        return -1
    def wins(c, who):
        b = list(board); r = drop_row(c, b)
        if r < 0: return False
        b[c + r * cols] = who
        for dr, dc in ((0,1),(1,0),(1,1),(1,-1)):
            n = 1
            for s in (1,-1):
                rr, cc = r+dr*s, c+dc*s
                while 0<=rr<rows and 0<=cc<cols and b[cc+rr*cols]==who:
                    n+=1; rr+=dr*s; cc+=dc*s
            if n>=inarow: return True
        return False
    valid=[c for c in range(cols) if board[c]==0]
    for c in valid:
        if wins(c, mark): return c
    opp=3-mark
    for c in valid:
        if wins(c, opp): return c
    valid.sort(key=lambda c: abs(c-cols//2))
    return valid[0] if valid else 0
