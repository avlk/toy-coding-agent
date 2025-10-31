--- a/nqueens.py
+++ b/nqueens.py
@@ -1,5 +1,18 @@
 def is_safe(board, row, col, n):
-    # Check this row on left side
+    """
+    Checks if it's safe to place a queen at board[row][col].
+
+    Args:
+        board (list): The current state of the chessboard.
+        row (int): The row to check.
+        col (int): The column to check.
+        n (int): The size of the chessboard.
+
+    Returns:
+        bool: True if it's safe to place a queen, False otherwise.
+    """
     for i in range(col):
         if board[row][i] == 1:
             return False
@@ -18,6 +27,17 @@
     return True
 
 def solve_n_queens_util(board, col, n, solutions):
+    """
+    Recursive utility function to solve the N-Queens problem.
+
+    Args:
+        board (list): The current state of the chessboard.
+        col (int): The current column being considered.
+        n (int): The size of the chessboard.
+        solutions (list): A list to store all valid solutions.
+
+    Returns:
+        bool: True if a solution is found, False otherwise."""
     if col >= n:
         solution = []
         for i in range(n):
@@ -39,10 +59,31 @@
     return res
 
 def solve_n_queens(n):
+    """
+    Solves the N-Queens problem for a given board size.
+
+    Args:
+        n (int): The size of the chessboard (N x N).
+
+    Returns:
+        list: A list of all unique solutions, where each solution is represented
+              as a list of strings representing the chessboard.
+    """
+    if n <= 0:
+        return []
+    if n == 1:
+        return [["Q"]]
+    # For N=2 and N=3, there are no solutions. The algorithm will correctly return
+    # an empty list, but explicit checks could be added for clarity if desired.
+    # if n == 2 or n == 3:
+    #     return []
+
     board = [[0 for _ in range(n)] for _ in range(n)]
     solutions = []
     solve_n_queens_util(board, 0, n, solutions)
     return solutions
+
+
 
 if __name__ == '__main__':
     n = 8