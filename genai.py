import google.generativeai

#Module for Google Gemini

#Can be changed
GEMINI_TOKEN: str = 'AIzaSyDJgAQw4HnfAtEyipO78cxDxJfU0DGyx9M'

google.generativeai.configure(api_key=GEMINI_TOKEN)

def generate_genai_response(message: str) -> str:
    try:
        model = google.generativeai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(message)
        return response.text
    except Exception as e:
        return "Gemini Ai hasn't processed message"

#DEBUG, please, do not launch this script!
if __name__ == '__main__':
    message1: str = 'difference between helicopter and plane'
    generate_genai_response(message1)