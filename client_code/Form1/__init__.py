from ._anvil_designer import Form1Template
from anvil import *
import anvil.tables as tables
import anvil.tables.query as q
from anvil.tables import app_tables
import anvil.users
import anvil.server
from anvil.js import get_dom_node
import uuid
import random


class Form1(Form1Template):
  def __init__(self, **properties):
    self.init_components(**properties)

    # ---------------------------------------------------------
    # FORCE LOGIN (Anvil built-in login popup)
    # - Returns user object if login succeeds
    # - Returns None if user cancels
    # ---------------------------------------------------------
    u = anvil.users.get_user()
    if u is None:
      u = anvil.users.login_with_form()
      if u is None:
        # user cancelled login -> go to About page (or just return)
        open_form("AboutForm")
        return

    # ---------------------------------------------------------
    # Header navigation (Buttons)
    # Requires:
    #   - HTML: <div anvil-slot="nav_panel"></div>
    #   - Designer: FlowPanel named nav_panel with HTML Slot "nav_panel"
    # ---------------------------------------------------------
    if hasattr(self, "nav_panel"):
      self.nav_panel.clear()

      btn_game = Button(text="Game", role="nav_btn", enabled=False)  # already on game
      btn_about = Button(text="About", role="nav_btn")

      btn_game.set_event_handler("click", lambda **e: open_form("Form1"))
      btn_about.set_event_handler("click", lambda **e: open_form("AboutForm"))

      self.nav_panel.add_component(btn_about)
      self.nav_panel.add_component(btn_game)

    # ----------------------------
    # Game state
    # ----------------------------
    self.board = [[[0.0, 0.0] for _ in range(7)] for _ in range(6)]
    self.player = 0
    self.game_over = False
    self.game_id = str(uuid.uuid4())
    self.loading = False

    self._drop_anim = None  # {"r": int, "c": int}

    # who goes first in AI modes: "Player" | "AI" | "Random"
    self.first_turn = "Player"
    self._resolved_first_turn = None  # resolved value for the current game (Player/AI)

    # which side AI controls in AI modes
    # 0 = Red, 1 = Yellow, None = Player mode
    self.ai_player = None

    # ----------------------------
    # Topbar dropdowns
    # ----------------------------
    self.selected_mode = "Player"

    self.model_dd = DropDown(items=["Player", "CNN", "Transformer"], selected_value="Player")
    self.model_dd.role = "c4_model_dd"
    self.model_dd.set_event_handler("change", self.model_dd_change)

    self.first_dd = DropDown(items=[], selected_value=None)
    self.first_dd.role = "c4_first_dd"
    self.first_dd.visible = False
    self.first_dd.set_event_handler("change", self.first_dd_change)

    if hasattr(self, "topbar_panel"):
      if hasattr(self.topbar_panel, "clear"):
        self.topbar_panel.clear()
      self.topbar_panel.add_component(self.model_dd)
      self.topbar_panel.add_component(self.first_dd)
    else:
      self.add_component(self.model_dd)
      self.add_component(self.first_dd)

    self._sync_first_dropdown()

    # ----------------------------
    # Overlay buttons
    # ----------------------------
    self.overlay_panel.role = "c4_overlay"
    self.col_buttons = []
    self._build_overlay_buttons()

    # ----------------------------
    # Status + Restart UI
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

    self.render_board()
    self._update_status_ui()

  # ----------------------------
  # Mode helpers
  # ----------------------------
  def _is_ai_mode(self):
    return self.selected_mode in ("CNN", "Transformer")

  def _compute_ai_player(self):
    """
    In AI modes:
      - If AI goes first -> AI must be Red (0)
      - If Player goes first -> AI is Yellow (1)
      - If Random -> randomly choose Player or AI once per new game
    """
    if not self._is_ai_mode():
      self._resolved_first_turn = None
      return None

    if self.first_turn == "Random":
      self._resolved_first_turn = random.choice(["Player", "AI"])
    else:
      self._resolved_first_turn = self.first_turn

    return 0 if self._resolved_first_turn == "AI" else 1

  def _is_human_allowed_to_click(self):
    # Player mode: human controls both
    if self.selected_mode == "Player":
      return True

    # AI mode: human can click only when it's NOT AI's turn
    return self.ai_player is not None and self.player != self.ai_player

  # ----------------------------
  # Dropdown handlers
  # ----------------------------
  def model_dd_change(self, **e):
    self.selected_mode = self.model_dd.selected_value
    self.first_turn = "Player"   # reset on mode change
    self._resolved_first_turn = None
    self._sync_first_dropdown()
    self.restart_game()

  def first_dd_change(self, **e):
    # now supports: Player / AI / Random
    self.first_turn = self.first_dd.selected_value
    self._resolved_first_turn = None
    self.restart_game()

  def _sync_first_dropdown(self):
    if not self._is_ai_mode():
      self.first_dd.visible = False
      return

    self.first_dd.visible = True
    ai_label = self.selected_mode

    self.first_dd.items = [
      ("Player goes first", "Player"),
      (f"{ai_label} goes first", "AI"),
      ("Random", "Random"),
    ]

    if self.first_turn not in ("Player", "AI", "Random"):
      self.first_turn = "Player"

    self.first_dd.selected_value = self.first_turn

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
    self.loading_lbl.visible = False

  def _sync_game_over_class(self):
    shell = self.dom_nodes.get("board_shell")
    if shell:
      shell.classList.toggle("game-over", self.game_over)

  def _sync_ai_turn_class(self):
    shell = self.dom_nodes.get("board_shell")
    if shell:
      is_ai_turn = (
        self._is_ai_mode()
        and (self.ai_player is not None)
        and (self.player == self.ai_player)
        and (not self.game_over)
      )
      shell.classList.toggle("ai-turn", is_ai_turn)

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
      return

    if self.selected_mode == "Player":
      self.status_lbl.text = "Turn: Red" if self.player == 0 else "Turn: Yellow"
      return

    if self.ai_player is None:
      self.status_lbl.text = "Turn"
      return

    ai_label = self.selected_mode
    human_color = "Red" if (1 - self.ai_player) == 0 else "Yellow"

    if self.player == self.ai_player:
      self.status_lbl.text = f"Turn: {ai_label}"
    else:
      self.status_lbl.text = f"Turn: Player ({human_color})"

  # ----------------------------
  # Rendering (holes + animation)
  # ----------------------------
  def render_board(self):
    self._sync_turn_classes()
    self._sync_loading_class()
    self._sync_game_over_class()
    self._sync_ai_turn_class()

    anim = self._drop_anim
    self._drop_anim = None

    cell, gap = 42, 8
    parts = ['<div class="c4-stage">', '<div class="c4-board">']

    for r in range(6):
      for c in range(7):
        cellv = self.board[r][c]

        disc_cls = None
        if cellv[0] > 0.5:
          disc_cls = "c4-disc c4-red"
        elif cellv[1] > 0.5:
          disc_cls = "c4-disc c4-yellow"

        disc_html = ""
        if disc_cls:
          if anim and anim["r"] == r and anim["c"] == c:
            fall_px = (r + 1) * (cell + gap)
            dur_ms = min(650, 220 + int(fall_px * 1.1))
            disc_html = (
              f'<div class="{disc_cls} c4-dropping" '
              f'style="--drop-from:{-fall_px}px;--drop-dur:{dur_ms}ms;"></div>'
            )
          else:
            disc_html = f'<div class="{disc_cls}"></div>'

        parts.append(
          f'<div class="c4-cell">'
          f'  <div class="c4-hole"></div>'
          f'  {disc_html}'
          f'</div>'
        )

    parts.append('</div></div>')
    self.dom_nodes["board_root"].innerHTML = "".join(parts)
    self._update_ghost_positions()

  # ----------------------------
  # AI first move
  # ----------------------------
  def _request_ai_opening_move(self):
    if self.game_over or self.loading or (not self._is_ai_mode()):
      return

    if self.ai_player is None or self.player != self.ai_player:
      return

    self.loading = True
    self._sync_loading_class()
    self._update_status_ui()

    try:
      resp = anvil.server.call(
        "receive_move",
        game_id=self.game_id,
        col=-1,
        player=None,
        mode=self.selected_mode,
        ai_player=self.ai_player
      )
    except Exception as e:
      self.loading = False
      self._sync_loading_class()
      Notification(f"Backend error during AI-first: {e}").show()
      return
    finally:
      self.loading = False
      self._sync_loading_class()

    if not resp.get("ok"):
      Notification(resp.get("error", "AI-first move rejected")).show()
      return

    new_board = resp["board"]
    ai_anim = None
    for rr in range(6):
      for cc in range(7):
        if self.board[rr][cc] == [0.0, 0.0] and new_board[rr][cc] != [0.0, 0.0]:
          ai_anim = {"r": rr, "c": cc}

    self.board = new_board
    self.player = resp.get("next_player", self.player)
    self.game_over = resp.get("game_over", False)

    if ai_anim:
      self._drop_anim = ai_anim

    self.render_board()
    self._update_status_ui(resp.get("winner"), resp.get("is_draw", False))

  # ----------------------------
  # Gameplay
  # ----------------------------
  def drop_piece(self, col):
    if self.game_over or self.loading:
      return
    if not self._is_human_allowed_to_click():
      return

    prev_board = [[cell[:] for cell in row] for row in self.board]
    r = self._landing_row_for_col(col)
    if r is None:
      return

    self._drop_anim = {"r": r, "c": col}

    self.board[r][col] = [1.0, 0.0] if self.player == 0 else [0.0, 1.0]
    self.render_board()

    self.loading = True
    self._sync_loading_class()
    self._update_status_ui()

    try:
      resp = anvil.server.call(
        "receive_move",
        game_id=self.game_id,
        col=col,
        player=self.player,
        mode=self.selected_mode,
        ai_player=self.ai_player
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

    new_board = resp["board"]

    ai_anim = None
    for rr in range(6):
      for cc in range(7):
        if self.board[rr][cc] == [0.0, 0.0] and new_board[rr][cc] != [0.0, 0.0]:
          ai_anim = {"r": rr, "c": cc}

    self.board = new_board
    self.player = resp.get("next_player", self.player)
    self.game_over = resp.get("game_over", False)

    if ai_anim:
      self._drop_anim = ai_anim

    self.render_board()
    self._update_status_ui(resp.get("winner"), resp.get("is_draw", False))

    if resp.get("ai_error"):
      Notification(f"AI error: {resp['ai_error']}").show()

    ai_col = resp.get("ai_move")
    if ai_col is not None:
      Notification(f"{self.selected_mode} played column {ai_col + 1}").show()

  def restart_game(self, **e):
    self.game_id = str(uuid.uuid4())
    self.board = [[[0.0, 0.0] for _ in range(7)] for _ in range(6)]
    self.game_over = False
    self.loading = False
    self._drop_anim = None

    self.ai_player = self._compute_ai_player()
    self.player = 0

    self.render_board()
    self._update_status_ui()

    if self._is_ai_mode() and self.first_turn == "Random" and self._resolved_first_turn in ("Player", "AI"):
      Notification(f"Random start: {self._resolved_first_turn} goes first").show()

    if self._is_ai_mode() and self.ai_player == 0:
      self._request_ai_opening_move()
