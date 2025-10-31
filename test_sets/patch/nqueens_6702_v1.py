def is_safe(board, row, col, n):
    # Check this row on left side
    for i in range(col):
        if board[row][i] == 1:
            return False

    # Check upper diagonal on left side
    for i, j in zip(range(row, -1, -1), range(col, -1, -1)):
        if board[i][j] == 1:
            return False

    # Check lower diagonal on left side
    for i, j in zip(range(row, n, 1), range(col, -1, -1)):
        if board[i][j] == 1:
            return False

    return True

def solve_n_queens_util(board, col, n, solutions):
    if col >= n:
        solution = []
        for i in range(n):
            row_str = ""
            for j in range(n):
                if board[i][j] == 1:
                    row_str += "Q"
                else:
                    row_str += "."
            solution.append(row_str)
        solutions.append(solution)
        return True

    res = False
    for i in range(n):
        if is_safe(board, i, col, n):
            board[i][col] = 1
            res = solve_n_queens_util(board, col + 1, n, solutions) or res
            board[i][col] = 0  # Backtrack

    return res

def solve_n_queens(n):
    board = [[0 for _ in range(n)] for _ in range(n)]
    solutions = []
    solve_n_queens_util(board, 0, n, solutions)
    return solutions

if __name__ == '__main__':
    n = 8
    all_solutions = solve_n_queens(n)
    for i, solution in enumerate(all_solutions):
        print(f"Solution {i + 1}:")
        for row in solution:
            print(row)
        print("\n")