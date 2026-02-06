"""
from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
from anvil.js import get_dom_node  # ✅ supported way to style DOM
import uuid

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

    self.game_id = str(uuid.uuid4())

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
    #Returns the row index (0=top..5=bottom) where a new piece would land.
    #Returns None if the column is full.
    for r in range(5, -1, -1):
      if self.board[r][col][0] == 0.0 and self.board[r][col][1] == 0.0:
        return r
    return None

  def _update_ghost_positions(self):
    #Sets a CSS variable --ghost-y on each column button so the CSS pseudo-element
    #can appear at the correct landing row.
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
    try:
      resp = anvil.server.call("forward_move_to_lightsail", self.game_id, col, self.player)
    except Exception as e:
      Notification(f"Backend error: {e}").show()
      return
  
    if not resp.get("ok"):
      Notification(resp.get("error", "Move rejected")).show()
      return
  
    self.board = resp["board"]
    self.player = resp["next_player"]
    self.render_board()
  
    if resp.get("game_over"):
      if resp.get("winner") == 0:
        Notification("Red wins!").show()
      elif resp.get("winner") == 1:
        Notification("Yellow wins!").show()
      else:
        Notification("Draw!").show()
"""

"""
from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
from anvil.js import get_dom_node  # ✅ supported way to style DOM
import uuid


class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    # ----------------------------
    # Game state (UI mirrors backend)
    # ----------------------------
    self.board = [[[0.0, 0.0] for _ in range(7)] for _ in range(6)]
    self.player = 0
    self.game_over = False
    self.game_id = str(uuid.uuid4())

    # ----------------------------
    # Overlay buttons
    # ----------------------------
    self.overlay_panel.role = "c4_overlay"
    self.col_buttons = []
    self._build_overlay_buttons()

    # ----------------------------
    # Status + Restart UI (under board)
    # IMPORTANT: You must have a panel component on your form to add these to.
    # Replace `self.content_panel` with the actual panel on your form
    # (e.g., self.column_panel_1 / self.card_panel / self.main_panel).
    # ----------------------------
    self.status_lbl = Label(text="", role="c4_status")
    self.restart_btn = Button(text="Play again", role="c4_restart_btn", enabled=False)
    self.restart_btn.set_event_handler("click", self.restart_game)

    try:
      # ✅ change this to your real container/panel name if different
      self.content_panel.add_component(self.status_lbl)
      self.content_panel.add_component(self.restart_btn)
    except Exception:
      # Fallback: add to the form itself if no panel name matches
      # (Not ideal, but prevents crashes)
      self.add_component(self.status_lbl)
      self.add_component(self.restart_btn)

    # Initial render + status
    self.render_board()
    self._update_status_ui()

  # ----------------------------
  # UI helpers
  # ----------------------------
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
    #Returns the row index (0=top..5=bottom) where a new piece would land.
    #Returns None if the column is full.
    for r in range(5, -1, -1):
      if self.board[r][col][0] == 0.0 and self.board[r][col][1] == 0.0:
        return r
    return None

  def _update_ghost_positions(self):
    #Sets a CSS variable --ghost-y on each column button so the CSS pseudo-element
    #can appear at the correct landing row.
    cell = 42
    gap = 8
    pad = 12

    for col, btn in enumerate(self.col_buttons):
      r = self._landing_row_for_col(col)
      dom = get_dom_node(btn)

      if r is None:
        dom.classList.add("c4-full")
        dom.style.removeProperty("--ghost-y")
      else:
        dom.classList.remove("c4-full")
        GHOST_RAISE = 12
        y = pad + r * (cell + gap) - GHOST_RAISE
        dom.style.setProperty("--ghost-y", f"{y}px")

  def _sync_turn_classes(self):
    shell = self.dom_nodes.get("board_shell")
    if shell is None:
      return
    shell.classList.remove("player-red", "player-yellow")
    shell.classList.add("player-red" if self.player == 0 else "player-yellow")

  def _update_status_ui(self, winner=None, is_draw=False):
    #Updates the label text and enables/disables the restart button.
    if self.game_over:
      if is_draw:
        self.status_lbl.text = "Game over: Draw"
      elif winner == 0:
        self.status_lbl.text = "Game over: Red wins!"
      elif winner == 1:
        self.status_lbl.text = "Game over: Yellow wins!"
      else:
        self.status_lbl.text = "Game over"
      self.restart_btn.enabled = True
    else:
      self.status_lbl.text = "Turn: Red" if self.player == 0 else "Turn: Yellow"
      self.restart_btn.enabled = False

  # ----------------------------
  # Rendering
  # ----------------------------
  def render_board(self):
    self._sync_turn_classes()

    def disc_class(cell):
      a, b = cell
      if a > 0.5: return "c4-disc c4-red"
      if b > 0.5: return "c4-disc c4-yellow"
      return "c4-disc"

    turn_class = "player-red" if self.player == 0 else "player-yellow"

    parts = [f'<div class="c4-stage {turn_class}">']
    parts.append('<div class="c4-board">')
    for r in range(6):
      for c in range(7):
        parts.append(f'<div class="{disc_class(self.board[r][c])}"></div>')
    parts.append('</div></div>')

    self.dom_nodes["board_root"].innerHTML = "".join(parts)
    self._update_ghost_positions()

  # ----------------------------
  # Gameplay
  # ----------------------------
  def drop_piece(self, col: int):
    # Ignore clicks after game ends
    if self.game_over:
      return

    try:
      resp = anvil.server.call("forward_move_to_lightsail", self.game_id, col, self.player)
    except Exception as e:
      Notification(f"Backend error: {e}").show()
      return

    if not resp.get("ok"):
      Notification(resp.get("error", "Move rejected")).show()
      return

    # Backend returns authoritative board + next player + end state
    self.board = resp["board"]
    self.player = resp.get("next_player", self.player)
    self.game_over = resp.get("game_over", False)

    self.render_board()

    if self.game_over:
      self._update_status_ui(winner=resp.get("winner"), is_draw=resp.get("is_draw", False))
    else:
      self._update_status_ui()

  def restart_game(self, **e):
    # Start a fresh game by using a new game_id (backend in-memory store keyed by game_id)
    self.game_id = str(uuid.uuid4())
    self.board = [[[0.0, 0.0] for _ in range(7)] for _ in range(6)]
    self.player = 0
    self.game_over = False
    self.render_board()
    self._update_status_ui()
#"""


from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
from anvil.js import get_dom_node  # ✅ supported way to style DOM
import uuid


class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    # ----------------------------
    # Game state (UI mirrors backend)
    # ----------------------------
    self.board = [[[0.0, 0.0] for _ in range(7)] for _ in range(6)]
    self.player = 0
    self.game_over = False
    self.game_id = str(uuid.uuid4())

    # ----------------------------
    # Overlay buttons
    # ----------------------------
    self.overlay_panel.role = "c4_overlay"
    self.col_buttons = []
    self._build_overlay_buttons()

    # ----------------------------
    # Status + Restart UI (under board)
    # ----------------------------
    self.status_lbl = Label(text="", role="c4_status")
    self.restart_btn = Button(text="Play again", role="c4_restart_btn", enabled=False)
    self.restart_btn.set_event_handler("click", self.restart_game)
    self.loading = False


    # ✅ Prefer a Designer panel named `underboard_panel` (slot under the board),
    # otherwise fall back to content_panel, otherwise fall back to the form.
    target = None
    if hasattr(self, "underboard_panel"):
      target = self.underboard_panel
    elif hasattr(self, "content_panel"):
      target = self.content_panel
    else:
      target = self

    try:
      # If it's a panel, clear it so it doesn't stack duplicates on reload
      if hasattr(target, "clear"):
        target.clear()

      target.add_component(self.status_lbl)
      target.add_component(self.restart_btn)
    except Exception:
      # last resort
      self.add_component(self.status_lbl)
      self.add_component(self.restart_btn)

    # Initial render + status
    self.render_board()
    self._update_status_ui()

  # ----------------------------
  # UI helpers
  # ----------------------------
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
    # Returns the row index (0=top..5=bottom) where a new piece would land.
    # Returns None if the column is full.
    for r in range(5, -1, -1):
      if self.board[r][col][0] == 0.0 and self.board[r][col][1] == 0.0:
        return r
    return None

  def _update_ghost_positions(self):
    # Sets a CSS variable --ghost-y on each column button so the CSS pseudo-element
    # can appear at the correct landing row.
    cell = 42
    gap = 8
    pad = 12

    for col, btn in enumerate(self.col_buttons):
      r = self._landing_row_for_col(col)
      dom = get_dom_node(btn)

      if r is None:
        dom.classList.add("c4-full")
        dom.style.removeProperty("--ghost-y")
      else:
        dom.classList.remove("c4-full")
        GHOST_RAISE = 12
        y = pad + r * (cell + gap) - GHOST_RAISE
        dom.style.setProperty("--ghost-y", f"{y}px")

  def _sync_turn_classes(self):
    shell = self.dom_nodes.get("board_shell")
    if shell is None:
      return
    shell.classList.remove("player-red", "player-yellow")
    shell.classList.add("player-red" if self.player == 0 else "player-yellow")

  def _sync_loading_class(self):
    shell = self.dom_nodes.get("board_shell")
    if shell is None:
      return
    if self.loading:
      shell.classList.add("loading")
    else:
      shell.classList.remove("loading")

  def _sync_game_over_class(self):
    shell = self.dom_nodes.get("board_shell")
    if shell is None:
      return
    if self.game_over:
      shell.classList.add("game-over")
    else:
      shell.classList.remove("game-over")

  def _update_status_ui(self, winner=None, is_draw=False):
    # Updates the label text and enables/disables the restart button.
    if self.game_over:
      if is_draw:
        self.status_lbl.text = "Game over: Draw"
      elif winner == 0:
        self.status_lbl.text = "Game over: Red wins!"
      elif winner == 1:
        self.status_lbl.text = "Game over: Yellow wins!"
      else:
        self.status_lbl.text = "Game over"
      self.restart_btn.enabled = True
    else:
      self.status_lbl.text = "Turn: Red" if self.player == 0 else "Turn: Yellow"
      self.restart_btn.enabled = False

  # ----------------------------
  # Rendering
  # ----------------------------
  def render_board(self):
    self._sync_turn_classes()
    self._sync_loading_class()
    self._sync_game_over_class()

    def disc_class(cell):
      a, b = cell
      if a > 0.5: return "c4-disc c4-red"
      if b > 0.5: return "c4-disc c4-yellow"
      return "c4-disc"

    turn_class = "player-red" if self.player == 0 else "player-yellow"

    parts = [f'<div class="c4-stage {turn_class}">']
    parts.append('<div class="c4-board">')
    for r in range(6):
      for c in range(7):
        parts.append(f'<div class="{disc_class(self.board[r][c])}"></div>')
    parts.append('</div></div>')

    self.dom_nodes["board_root"].innerHTML = "".join(parts)
    self._update_ghost_positions()

  # ----------------------------
  # Gameplay
  # ----------------------------
  def drop_piece(self, col: int):
  # Ignore clicks after game ends or while waiting for backend
    if self.game_over or getattr(self, "loading", False):
      return
    # place the piece locally
    prev_board = [[cell[:] for cell in row] for row in self.board]  # deep copy (6x7x2)
  
    r = self._landing_row_for_col(col)
    if r is None:
      return  # column full, ignore
  
    # place current player's disc locally
    if self.player == 0:
      self.board[r][col] = [1.0, 0.0]  # red
    else:
      self.board[r][col] = [0.0, 1.0]  # yellow
  
    # show it immediately
    self.render_board()
  
    # start loading (disables ghost/hover + clicks via CSS)
    self.loading = True
    self._sync_loading_class()
  
    # ask backend to validate + return authoritative state
    try:
      resp = anvil.server.call("forward_move_to_lightsail", self.game_id, col, self.player)
    except Exception as e:
      # revert local optimistic move on error
      self.board = prev_board
      self.render_board()
      Notification(f"Backend error: {e}").show()
      return
    finally:
      self.loading = False
      self._sync_loading_class()
  
    if not resp.get("ok"):
      # revert local optimistic move if rejected
      self.board = prev_board
      self.render_board()
      Notification(resp.get("error", "Move rejected")).show()
      return
  
    # Backend returns authoritative board + next player + end state
    self.board = resp["board"]
    self.player = resp.get("next_player", self.player)
    self.game_over = resp.get("game_over", False)
  
    # Re-render authoritative board (in case backend differs)
    self.render_board()
  
    if self.game_over:
      self._update_status_ui(winner=resp.get("winner"), is_draw=resp.get("is_draw", False))
    else:
      self._update_status_ui()



  def restart_game(self, **e):
    # Start a fresh game by using a new game_id (backend in-memory store keyed by game_id)
    self.game_id = str(uuid.uuid4())
    self.board = [[[0.0, 0.0] for _ in range(7)] for _ in range(6)]
    self.player = 0
    self.game_over = False
    self.render_board()
    self._update_status_ui()
