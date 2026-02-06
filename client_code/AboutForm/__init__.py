from ._anvil_designer import AboutFormTemplate
from anvil import *
import anvil.users


class AboutForm(AboutFormTemplate):
  def __init__(self, **properties):
    self.init_components(**properties)

    # Header nav buttons
    if hasattr(self, "nav_panel"):
      self.nav_panel.clear()

      self.btn_about = Button(text="About", role="nav_btn", enabled=False)
      self.btn_game = Button(text="Game", role="nav_btn")

      self.btn_game.set_event_handler("click", self.go_game)
      self.btn_about.set_event_handler("click", lambda **e: open_form("AboutForm"))

      self.nav_panel.add_component(self.btn_about)
      self.nav_panel.add_component(self.btn_game)

    # Lock down navigation until logged in
    self._require_login()

  def _require_login(self):
    """
    Force the Anvil login popup until the user logs in.
    This prevents "free access" without a user account.
    """
    u = anvil.users.get_user()

    # Keep prompting until they actually log in
    while u is None:
      Notification("Please log in to continue.", style="warning").show()
      u = anvil.users.login_with_form()

    # At this point they are logged in
    Notification("Welcome!", style="success").show()

  def go_game(self, **e):
    # Because _require_login() ran, this will only happen when logged in.
    open_form("Form1")
