from enthought.traits.api import Str
from traitsui.api import Item, View, Handler
from traitsui.menu import OKButton

class GenericPopupMessage(Handler):
    message = Str
    traits_view = View(Item('message', style = 'readonly', show_label = False),
                       buttons = [OKButton], kind = 'modal')
