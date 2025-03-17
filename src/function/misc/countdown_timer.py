import logging
import time
import sys

class countdown_timer: 
    def __init__(self, seconds):
        self.seconds = seconds

        self.execute()
    
    def execute(self):
        logger = logging.getLogger("timer")
        while self.seconds:
            hours, remainder = divmod(self.seconds, 3600)
            mins, secs = divmod(remainder, 60)
            timer = f'{hours:02d}:{mins:02d}:{secs:02d}'
            sys.stdout.write(f"\rLe scan va reprendre dans {timer}")
            sys.stdout.flush()
            time.sleep(1)
            self.seconds -= 1
        logger.info("starting traitement")
