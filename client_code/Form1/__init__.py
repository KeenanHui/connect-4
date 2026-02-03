from ._anvil_designer import Form1Template
from anvil import *
from anvil.js import get_dom_node  # ✅ supported way to style DOM

class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    self.board = [[[0.0, 0.0] for _ in range(7)] for _ in range(6)]
    self.player = 0

    self.overlay_panel.role = "c4_overlay"

    # keep references to buttons so we can update their ghost positions
    self.col_buttons = []

    self._build_overlay_buttons()
    self.render_board()

  def _make_drop_handler(self, col):
    def handler(**e):
      self.drop_piece(col)
    return handler

  def _build_overlay_buttons(self):
    self.overlay_panel.clear()
    self.col_buttons = []

    for col in range(7):
      btn = Button(text="", role="c4_col_btn")
      btn.set_event_handler("click", self._make_drop_handler(col))
      self.overlay_panel.add_component(btn)
      self.col_buttons.append(btn)

  def _landing_row_for_col(self, col: int):
    """
    Returns the row index (0=top..5=bottom) where a new piece would land.
    Returns None if the column is full.
    """
    for r in range(5, -1, -1):
      if self.board[r][col][0] == 0.0 and self.board[r][col][1] == 0.0:
        return r
    return None

  def _update_ghost_positions(self):
    """
    Sets a CSS variable --ghost-y on each column button so the CSS pseudo-element
    can appear at the correct landing row.
    """
    # Must match your CSS variables:
    cell = 42
    gap = 8
    pad = 12

    for col, btn in enumerate(self.col_buttons):
      r = self._landing_row_for_col(col)
      dom = get_dom_node(btn)

      if r is None:
        # Column full: hide ghost (optional)
        dom.classList.add("c4-full")
        dom.style.removeProperty("--ghost-y")
      else:
        dom.classList.remove("c4-full")
        GHOST_RAISE = 12
        y = pad + r * (cell + gap) - GHOST_RAISE

        #y = pad + r * (cell + gap)   # top position of that cell in px
        dom.style.setProperty("--ghost-y", f"{y}px")

  def _sync_turn_classes(self):
    shell = self.dom_nodes.get("board_shell")
    if shell is None:
      return
    shell.classList.remove("player-red", "player-yellow")
    shell.classList.add("player-red" if self.player == 0 else "player-yellow")

  def render_board(self):
    self._sync_turn_classes()
    def disc_class(cell):
      a, b = cell
      if a > 0.5: return "c4-disc c4-red"
      if b > 0.5: return "c4-disc c4-yellow"
      return "c4-disc"

    # Add a wrapper div that we can tag with the current player
    turn_class = "player-red" if self.player == 0 else "player-yellow"
  
    parts = [f'<div class="c4-stage {turn_class}">']
    parts.append('<div class="c4-board">')
    for r in range(6):
      for c in range(7):
        parts.append(f'<div class="{disc_class(self.board[r][c])}"></div>')
    parts.append('</div></div>')  # close c4-board + c4-stage
  
    self.dom_nodes["board_root"].innerHTML = "".join(parts)
    self._update_ghost_positions()

  def drop_piece(self, col: int):
    r = self._landing_row_for_col(col)
    if r is None:
      Notification("Column is full").show()
      return

    self.board[r][col] = [1.0, 0.0] if self.player == 0 else [0.0, 1.0]
    self.player = 1 - self.player
    self.render_board()

    