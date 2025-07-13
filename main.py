from flask import Flask, request, render_template
from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled
from youtube_transcript_api._errors import NoTranscriptFound
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from googletrans import Translator
import re

app = Flask(__name__)

# Extract video ID from URL
def extract_video_id(youtube_url):
    match = re.search(r"(?:v=|\/|v=)([0-9A-Za-z_-]{11})", youtube_url)
    if match:
        return match.group(1)
    return None

# Fetch transcript with fallback
def get_video_transcript(video_id):
    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try English first
        try:
            transcript = transcript_list.find_transcript(['en'])
        except NoTranscriptFound:
            # Try Hindi (auto-generated)
            transcript = transcript_list.find_generated_transcript(['hi'])

        fetched = transcript.fetch()
        text = " ".join([item.text for item in fetched if hasattr(item, 'text')])
        return text

    except Exception as e:
        print("Transcript Error:", e)
        return None


# Summarize text using LexRank
def summarize_text_with_lexrank(text, sentences_count=5):
    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = LexRankSummarizer()
    summary = summarizer(parser.document, sentences_count)
    return " ".join(str(sentence) for sentence in summary)

@app.route("/", methods=["GET", "POST"])
def index():
    summary = None
    translated_summary = None
    error = None
    selected_language = "en"

    if request.method == "POST":
        url = request.form.get("youtube_url", "").strip()
        selected_language = request.form.get("language", "en")

        if not url:
            error = "Please enter a YouTube link."
        else:
            video_id = extract_video_id(url)
            if not video_id:
                error = "Invalid YouTube URL."
            else:
                transcript = get_video_transcript(video_id)
                if transcript:
                    summary = summarize_text_with_lexrank(transcript)

                    if selected_language != "en":
                        try:
                            translator = Translator()
                            translated = translator.translate(summary, dest=selected_language)
                            translated_summary = translated.text
                        except Exception as e:
                            translated_summary = None
                            error = "Summary generated, but translation failed."
                else:
                    error = "Transcript not available for this video."

    return render_template(
        "index.html",
        summary=summary,
        translated_summary=translated_summary,
        error=error,
        selected_language=selected_language
    )

if __name__ == "__main__":
    app.run(debug=True)
