import google.generativeai
import os
from dotenv import load_dotenv
load_dotenv()

#Module for Google Gemini
class GenAI:
    def __new__(cls):
        if not hasattr(cls, 'instance'):
            cls.instance = super(GenAI, cls).__new__(cls)
        return cls.instance

    prompt: str = ''
    #def __init__(self, prompt):
    #    super().__init__(prompt=prompt)

    GEMINI_TOKEN: str = os.getenv('GEMINI_TOKEN')

    google.generativeai.configure(api_key=GEMINI_TOKEN)

    def generate_response(self) -> str:
        prompt = self.prompt
        try:
            model = google.generativeai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return "Gemini Ai hasn't processed message"




# DEBUG, please, do not launch this script!
if __name__ == '__main__':
    message1: str = 'difference between helicopter and plane'
    GenAI.generate_response(message1)

