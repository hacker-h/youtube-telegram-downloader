from typing import Text
import telegram
from tqdm import tqdm
from datetime import datetime


class _TelegramIO():
    def __init__(self, token, chat_id, message_id):
        self.bot = telegram.Bot(token)
        self.chat_id = chat_id
        self.text = self.prev_text = '<< Init tg_tqdm bar >>'
        self.message_id = message_id
        print(self.message_id)

    def write(self, s):
        new_text = s.strip().replace('\r', '')
        if len(new_text) != 0:
            self.text = new_text

    def flush(self):
        if self.prev_text != self.text:
            self.bot.edit_message_text(self.text , self.chat_id, self.message_id)
            self.prev_text = self.text
            

def tg_tqdm(token, chat_id, message_id,
            desc=None, total=None, leave=True, ncols=None, mininterval=1.0, maxinterval=10.0,
            miniters=None, ascii=False, disable=False, unit='it',
            unit_scale=False, dynamic_ncols=False, smoothing=0.3,
            bar_format=None, initial=0, position=None, postfix=None,
            unit_divisor=1000, gui=False, **kwargs):
    """
    Decorate an iterable object, returning an iterator which acts exactly
    like the original iterable, but send to Telegram a dynamically updating
    progressbar every time a value is requested.
    
        Parameters
        ----------
        iterable  : iterable, required
            Iterable to decorate with a progressbar.
            Leave blank to manually manage the updates.
        token  : string, required
            Token of your telegram bot
            
        chat_id  : int, required
            Chat ID where information will be sent about the progress
            
        show_last_update  : bool, optional [default: True]
            Should I show the time-date of the last change in the progress bar?
            
        desc, total, leave, ncols, ... :
            Like in tqdm
            
    """
    tg_io = _TelegramIO(token, chat_id, message_id)
    return tqdm(desc=desc,
                total=total,
                leave=leave,
                file=tg_io,
                ncols=ncols,
                mininterval=mininterval,
                maxinterval=maxinterval,
                miniters=miniters,
                ascii=ascii,
                disable=disable,
                unit=unit,
                unit_scale=unit_scale,
                dynamic_ncols=dynamic_ncols,
                smoothing=smoothing,
                bar_format=bar_format,
                initial=initial,
                position=position,
                postfix=postfix,
                unit_divisor=unit_divisor,
                gui=gui,
                **kwargs)