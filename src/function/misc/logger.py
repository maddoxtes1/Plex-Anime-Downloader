import logging
from datetime import datetime

def setup_logging(logs_path):
    log_filename = datetime.now().strftime('app_%Y-%m-%d_%H-%M-%S.log')
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s - %(name)s %(message)s', handlers=[logging.StreamHandler(), logging.FileHandler(f"{logs_path}/{log_filename}")])