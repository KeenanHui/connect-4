from ._anvil_designer import Form1Template
from anvil import *

class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Example 6x7x2 tensor
    board = [[[0.0, 0.0] for _ in range(7)] for _ in range(6)]
    board[5][6] = [0.0, 1.0]  # example piece (yellow)

    self.set_board(board)

  def set_board(self, tensor_6x7x2):
    def disc_class(cell):
      a, b = cell[0], cell[1]
      if a > 0.5 and b < 0.5:
        return "c4-disc c4-red"
      if b > 0.5 and a < 0.5:
        return "c4-disc c4-yellow"
      return "c4-disc"

    # Flip if your tensor is bottom-up:
    rows = tensor_6x7x2  # or: list(reversed(tensor_6x7x2))

    parts = ['<div class="c4-board">']
    for r in range(6):
      for c in range(7):
        parts.append(f'<div class="{disc_class(rows[r][c])}"></div>')
    parts.append('</div>')

    # Write HTML into the named div
    self.dom_nodes["board_root"].innerHTML = "".join(parts)
