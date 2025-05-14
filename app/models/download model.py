from transformers import AutoTokenizer, AutoModelForSequenceClassification
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def download_model():
    model_name = "nur-dev/roberta-kaz-large"
    local_path = "roberta-kaz-large"
    
    try:
        # Create the directory if it doesn't exist
        os.makedirs(local_path, exist_ok=True)
        logger.info(f"Created directory: {local_path}")
        
        # Download tokenizer
        logger.info(f"Downloading tokenizer from {model_name}...")
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        tokenizer.save_pretrained(local_path)
        logger.info("Tokenizer downloaded and saved successfully")
        
        # Download model
        logger.info(f"Downloading model from {model_name}...")
        model = AutoModelForSequenceClassification.from_pretrained(model_name)
        model.save_pretrained(local_path)
        logger.info("Model downloaded and saved successfully")
        
        # Verify the download
        files = os.listdir(local_path)
        logger.info(f"Files downloaded to {local_path}:")
        for file in files:
            logger.info(f"- {file}")
            
        return True
        
    except Exception as e:
        logger.error(f"Error downloading model: {str(e)}")
        return False

if __name__ == "__main__":
    download_model()