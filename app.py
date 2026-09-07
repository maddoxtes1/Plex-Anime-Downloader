from app.sys import FolderConfig, universal_logger, LoggerConfig
from app.flask import flask_manager
from app.queue.manager import queues
from app.streaming import stream_manager

class App:
    def __init__(self):
        FolderConfig.init()
        LoggerConfig.init()
        self.logger = universal_logger("System", "sys.log")
    
    def run(self):
        queue_manager = queues()
        self.logger.info(msg="Queue manager initialized")
        
        flask_manager()
        self.logger.info(msg="Flask manager initialized")
        
        stream_manager(queue=queue_manager)
        self.logger.info(msg="Streaming manager initialized")



if __name__ == "__main__":
    app = App()
    app.run()