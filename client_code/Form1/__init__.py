"""
from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
from anvil.js import get_dom_node
import uuid


class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    # ----------------------------
    # Game state
    # ----------------------------
    self.board = [[[0.0, 0.0] for _ in range(7)] for _ in range(6)]
    self.player = 0
    self.game_over = False
    self.game_id = str(uuid.uuid4())
    self.loading = False

    # ----------------------------
    # Dropdown menu ABOVE board
    # ----------------------------
    self.selected_mode = "Player"
    self.model_dd = DropDown(
      items=["Player", "CNN", "Transformer"],
      selected_value="Player"
    )
    self.model_dd.role = "c4_model_dd"
    self.model_dd.set_event_handler("change", self.model_dd_change)

    if hasattr(self, "topbar_panel"):
      if hasattr(self.topbar_panel, "clear"):
        self.topbar_panel.clear()
      self.topbar_panel.add_component(self.model_dd)
    else:
      self.add_component(self.model_dd)

    # ----------------------------
    # Overlay buttons
    # ----------------------------
    self.overlay_panel.role = "c4_overlay"
    self.col_buttons = []
    self._build_overlay_buttons()

    # ----------------------------
    # Status + Loading + Restart UI (under board)
    # ----------------------------
    self.loading_lbl = Label(text="Loading…", role="c4_loading", visible=False)
    self.status_lbl = Label(text="", role="c4_status")

    # ✅ New behavior:
    # - Button is always enabled
    # - Shows "New Game" during play
    # - Switches to "Play again" after game ends
    self.restart_btn = Button(
      text="New Game",
      role="c4_restart_btn",
      enabled=True
    )
    self.restart_btn.set_event_handler("click", self.restart_game)

    if hasattr(self, "underboard_panel"):
      target = self.underboard_panel
    elif hasattr(self, "content_panel"):
      target = self.content_panel
    else:
      target = self

    if hasattr(target, "clear"):
      target.clear()

    target.add_component(self.loading_lbl)
    target.add_component(self.status_lbl)
    target.add_component(self.restart_btn)

    # Initial render
    self.render_board()
    self._update_status_ui()

  # ----------------------------
  # Dropdown handler
  # ----------------------------
  def model_dd_change(self, **e):
    # update mode
    self.selected_mode = self.model_dd.selected_value
  
    # ✅ start a fresh game whenever the mode changes
    self.restart_game()

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

  def _landing_row_for_col(self, col):
    for r in range(5, -1, -1):
      if self.board[r][col] == [0.0, 0.0]:
        return r
    return None

  def _update_ghost_positions(self):
    cell, gap, pad = 42, 8, 12
    for col, btn in enumerate(self.col_buttons):
      r = self._landing_row_for_col(col)
      dom = get_dom_node(btn)
      if r is None:
        dom.classList.add("c4-full")
        dom.style.removeProperty("--ghost-y")
      else:
        dom.classList.remove("c4-full")
        y = pad + r * (cell + gap) - 12
        dom.style.setProperty("--ghost-y", f"{y}px")

  def _sync_turn_classes(self):
    shell = self.dom_nodes.get("board_shell")
    if shell:
      shell.classList.toggle("player-red", self.player == 0)
      shell.classList.toggle("player-yellow", self.player == 1)

  def _sync_loading_class(self):
    shell = self.dom_nodes.get("board_shell")
    if shell:
      shell.classList.toggle("loading", self.loading)
      if self.loading:
        self.status_lbl.text = "Loading…"

  def _sync_game_over_class(self):
    shell = self.dom_nodes.get("board_shell")
    if shell:
      shell.classList.toggle("game-over", self.game_over)

  def _update_status_ui(self, winner=None, is_draw=False):
    # ✅ Button always works
    self.restart_btn.enabled = True

    if self.game_over:
      # After game ends, change button label
      self.restart_btn.text = "Play again"

      if is_draw:
        self.status_lbl.text = "Game over: Draw"
      elif winner == 0:
        self.status_lbl.text = "Game over: Red wins!"
      elif winner == 1:
        self.status_lbl.text = "Game over: Yellow wins!"
      else:
        self.status_lbl.text = "Game over"
      return

    # Game in progress: button says New Game
    self.restart_btn.text = "New Game"

    # If currently loading, show loading message and stop
    if self.loading:
      self.status_lbl.text = "Loading…"
      return

    # Turn text logic (your requested behavior)
    if self.player == 0:
      self.status_lbl.text = "Turn: Red"
    else:
      if self.selected_mode == "Player":
        self.status_lbl.text = "Turn: Yellow"
      else:
        self.status_lbl.text = f"Turn: {self.selected_mode}"

  # ----------------------------
  # Rendering
  # ----------------------------
  def render_board(self):
    self._sync_turn_classes()
    self._sync_loading_class()
    self._sync_game_over_class()

    def disc_class(cell):
      if cell[0] > 0.5: return "c4-disc c4-red"
      if cell[1] > 0.5: return "c4-disc c4-yellow"
      return "c4-disc"

    parts = ['<div class="c4-stage">', '<div class="c4-board">']
    for r in range(6):
      for c in range(7):
        parts.append(f'<div class="{disc_class(self.board[r][c])}"></div>')
    parts.append('</div></div>')

    self.dom_nodes["board_root"].innerHTML = "".join(parts)
    self._update_ghost_positions()

  # ----------------------------
  # Gameplay
  # ----------------------------

  def drop_piece(self, col):
    if self.game_over or self.loading:
      return
  
    prev_board = [[cell[:] for cell in row] for row in self.board]
  
    r = self._landing_row_for_col(col)
    if r is None:
      return
  
    # optimistic human move render (Red always starts, so this is fine)
    self.board[r][col] = [1.0, 0.0] if self.player == 0 else [0.0, 1.0]
    self.render_board()
  
    self.loading = True
    self._sync_loading_class()
    self._update_status_ui()
  
    try:
      # ✅ NEW BACKEND FUNCTION + NEW PARAMS
      resp = anvil.server.call(
        "receive_move",
        self.game_id,
        col,
        self.player,          # keep mismatch check working
        self.selected_mode    # mode = "Player" | "CNN" | "Transformer"
      )
    except Exception as e:
      self.board = prev_board
      self.render_board()
      Notification(str(e)).show()
      return
    finally:
      self.loading = False
      self._sync_loading_class()
  
    if not resp.get("ok"):
      self.board = prev_board
      self.render_board()
      Notification(resp.get("error", "Move rejected")).show()
      self._update_status_ui()
      return
  
    # ✅ authoritative state from backend (already includes AI move if mode != Player)
    self.board = resp["board"]
    self.player = resp.get("next_player", self.player)
    self.game_over = resp.get("game_over", False)
  
    self.render_board()
    self._update_status_ui(resp.get("winner"), resp.get("is_draw", False))
  
    # Optional: show what AI played
    ai_col = resp.get("ai_move")
    if ai_col is not None:
      Notification(f"{self.selected_mode} played column {ai_col + 1}").show()


  def restart_game(self, **e):
    self.game_id = str(uuid.uuid4())
    self.board = [[[0.0, 0.0] for _ in range(7)] for _ in range(6)]
    self.player = 0
    self.game_over = False
    self.loading = False
    self.render_board()
    self._update_status_ui()
#"""

from ._anvil_designer import Form1Template
from anvil import *
import anvil.server
from anvil.js import get_dom_node
import uuid


class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    # ----------------------------
    # Game state
    # ----------------------------
    self.board = [[[0.0, 0.0] for _ in range(7)] for _ in range(6)]
    self.player = 0
    self.game_over = False
    self.game_id = str(uuid.uuid4())
    self.loading = False

    # ----------------------------
    # Dropdown menu ABOVE board
    # ----------------------------
    self.selected_mode = "Player"
    self.model_dd = DropDown(
      items=["Player", "CNN", "Transformer"],
      selected_value="Player"
    )
    self.model_dd.role = "c4_model_dd"
    self.model_dd.set_event_handler("change", self.model_dd_change)

    if hasattr(self, "topbar_panel"):
      if hasattr(self.topbar_panel, "clear"):
        self.topbar_panel.clear()
      self.topbar_panel.add_component(self.model_dd)
    else:
      self.add_component(self.model_dd)

    # ----------------------------
    # Overlay buttons
    # ----------------------------
    self.overlay_panel.role = "c4_overlay"
    self.col_buttons = []
    self._build_overlay_buttons()

    # ----------------------------
    # Status + Loading + Restart UI
    # ----------------------------
    self.loading_lbl = Label(text="Loading…", role="c4_loading", visible=False)
    self.status_lbl = Label(text="", role="c4_status")

    self.restart_btn = Button(text="New Game", role="c4_restart_btn", enabled=True)
    self.restart_btn.set_event_handler("click", self.restart_game)

    if hasattr(self, "underboard_panel"):
      target = self.underboard_panel
    elif hasattr(self, "content_panel"):
      target = self.content_panel
    else:
      target = self

    if hasattr(target, "clear"):
      target.clear()

    target.add_component(self.loading_lbl)
    target.add_component(self.status_lbl)
    target.add_component(self.restart_btn)

    # Initial render
    self.render_board()
    self._update_status_ui()

  # ----------------------------
  # Mode helpers
  # ----------------------------
  def _is_ai_mode(self):
    return self.selected_mode in ("CNN", "Transformer")

  def _is_human_allowed_to_click(self):
    # Player mode: human controls both Red & Yellow (normal 2-player)
    if self.selected_mode == "Player":
      return True

    # AI mode: human is Red only; AI is Yellow
    return self.player == 0

  # ----------------------------
  # Dropdown handler
  # ----------------------------
  def model_dd_change(self, **e):
    self.selected_mode = self.model_dd.selected_value
    self.restart_game()

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

  def _landing_row_for_col(self, col):
    for r in range(5, -1, -1):
      if self.board[r][col] == [0.0, 0.0]:
        return r
    return None

  def _update_ghost_positions(self):
    cell, gap, pad = 42, 8, 12
    for col, btn in enumerate(self.col_buttons):
      r = self._landing_row_for_col(col)
      dom = get_dom_node(btn)
      if r is None:
        dom.classList.add("c4-full")
        dom.style.removeProperty("--ghost-y")
      else:
        dom.classList.remove("c4-full")
        y = pad + r * (cell + gap) - 12
        dom.style.setProperty("--ghost-y", f"{y}px")

  def _sync_turn_classes(self):
    shell = self.dom_nodes.get("board_shell")
    if shell:
      shell.classList.toggle("player-red", self.player == 0)
      shell.classList.toggle("player-yellow", self.player == 1)

  def _sync_loading_class(self):
    shell = self.dom_nodes.get("board_shell")
    if shell:
      shell.classList.toggle("loading", self.loading)
    self.loading_lbl.visible = self.loading

  def _sync_game_over_class(self):
    shell = self.dom_nodes.get("board_shell")
    if shell:
      shell.classList.toggle("game-over", self.game_over)

  def _sync_ai_turn_class(self):
    # Optional: lets CSS disable overlay during AI turn
    shell = self.dom_nodes.get("board_shell")
    if shell:
      shell.classList.toggle("ai-turn", self._is_ai_mode() and (self.player == 1) and (not self.game_over))

  def _update_status_ui(self, winner=None, is_draw=False):
    self.restart_btn.enabled = True

    if self.game_over:
      self.restart_btn.text = "Play again"
      if is_draw:
        self.status_lbl.text = "Game over: Draw"
      elif winner == 0:
        self.status_lbl.text = "Game over: Red wins!"
      elif winner == 1:
        self.status_lbl.text = "Game over: Yellow wins!"
      else:
        self.status_lbl.text = "Game over"
      return

    self.restart_btn.text = "New Game"

    if self.loading:
      self.status_lbl.text = "Loading…"
      return

    # Your requested behavior
    if self.player == 0:
      self.status_lbl.text = "Turn: Red"
    else:
      if self.selected_mode == "Player":
        self.status_lbl.text = "Turn: Yellow"
      else:
        self.status_lbl.text = f"Turn: {self.selected_mode}"

  # ----------------------------
  # Rendering
  # ----------------------------
  def render_board(self):
    self._sync_turn_classes()
    self._sync_loading_class()
    self._sync_game_over_class()
    self._sync_ai_turn_class()

    def disc_class(cell):
      if cell[0] > 0.5: return "c4-disc c4-red"
      if cell[1] > 0.5: return "c4-disc c4-yellow"
      return "c4-disc"

    parts = ['<div class="c4-stage">', '<div class="c4-board">']
    for r in range(6):
      for c in range(7):
        parts.append(f'<div class="{disc_class(self.board[r][c])}"></div>')
    parts.append('</div></div>')

    self.dom_nodes["board_root"].innerHTML = "".join(parts)
    self._update_ghost_positions()

  # ----------------------------
  # Gameplay
  # ----------------------------
  def drop_piece(self, col):
    if self.game_over or self.loading:
      return

    # ✅ Key rule: in AI modes, ignore clicks on Yellow's turn
    if not self._is_human_allowed_to_click():
      return

    prev_board = [[cell[:] for cell in row] for row in self.board]

    r = self._landing_row_for_col(col)
    if r is None:
      return

    # Optimistic local placement for the CURRENT player
    self.board[r][col] = [1.0, 0.0] if self.player == 0 else [0.0, 1.0]
    self.render_board()

    self.loading = True
    self._sync_loading_class()
    self._update_status_ui()

    try:
      resp = anvil.server.call(
        "receive_move",
        self.game_id,
        col,
        self.player,         # keeps backend "out-of-turn" guard useful
        self.selected_mode   # "Player" | "CNN" | "Transformer"
      )
    except Exception as e:
      self.board = prev_board
      self.loading = False
      self.render_board()
      self._update_status_ui()
      Notification(f"Backend error: {e}").show()
      return
    finally:
      self.loading = False
      self._sync_loading_class()

    if not resp.get("ok"):
      self.board = prev_board
      self.render_board()
      self._update_status_ui()
      Notification(resp.get("error", "Move rejected")).show()
      return

    # ✅ Authoritative state from backend
    self.board = resp["board"]
    self.player = resp.get("next_player", self.player)
    self.game_over = resp.get("game_over", False)

    self.render_board()
    self._update_status_ui(resp.get("winner"), resp.get("is_draw", False))

    # Helpful debug / visibility
    if resp.get("ai_error"):
      Notification(f"AI error: {resp['ai_error']}").show()

    ai_col = resp.get("ai_move")
    if ai_col is not None:
      Notification(f"{self.selected_mode} played column {ai_col + 1}").show()

  def restart_game(self, **e):
    self.game_id = str(uuid.uuid4())
    self.board = [[[0.0, 0.0] for _ in range(7)] for _ in range(6)]
    self.player = 0
    self.game_over = False
    self.loading = False
    self.render_board()
    self._update_status_ui()
