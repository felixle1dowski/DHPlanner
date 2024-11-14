from config import Config
from logger import Logger
from dhc_creation_pipeline_factory import DHCCreationPipelineFactory

config = Config()
logger = Logger()
Logger.info("Starting...")
pipeline = DHCCreationPipelineFactory().create_pipeline()
pipeline.start()
