
import re
import pandas as pd
# import matplotlib.pyplot as plt
from wordcloud import WordCloud #, STOPWORDS
import nltk
nltk.download("punkt")
nltk.download("averaged_perceptron_tagger_eng")
nltk.download("punkt_tab")
nltk.download("stopwords")
nltk.download("wordnet")
nltk.download("omw-1.4")
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk import pos_tag
from nltk.corpus import wordnet
from nltk.stem import PorterStemmer, WordNetLemmatizer
import contractions
from textblob import TextBlob

# ── CONFIG ───────────────────────────────
CSV_PATH = "scraped_data/all_subreddits.csv"   # change if needed
TEXT_COLUMN = "title"
# ─────────────────────────────────────────


# Load CSV
df = pd.read_csv(CSV_PATH)

print("Loaded rows:", len(df))


# Keep only titles
texts = df[TEXT_COLUMN].dropna().astype(str)


# Combine all titles into one text
raw_text = " ".join(texts)

# Initialize NLP tools
stop_words = set(stopwords.words("english"))
stemmer = PorterStemmer()
lemmatizer = WordNetLemmatizer()

custom_stopwords = {
    "im", "ive", "dont", "doesnt", "didnt",
    "reddit", "post", "one", "would", "get"
}
stop_words.update(custom_stopwords)

# Cleaning function
def normalize_text(text: str) -> str:
    text = text.lower()                         # lowercase
    text = contractions.fix(text)               # expand contractions
    text = re.sub(r"http\S+", "", text)         # remove links
    return text

def remove_noise(text):
    """punctuation + numbers + noisy text"""
    text = re.sub(r"\d+", " ", text)            # remove numbers
    text = re.sub(r"[^a-z\s]", " ", text)       # remove punctuation/symbols
    text = re.sub(r"(.)\1{2,}", r"\1\1", text)  # remove repeated characters (coooool → cool)
    text = re.sub(r"\s+", " ", text).strip()    # remove extra spaces
    return text

def spelling_correction(text):
    """spelling correction (slow but optional)"""
    try:
        return str(TextBlob(text).correct())
    except:
        return text
    
def get_wordnet_pos(tag):
    """Convert NLTK POS tag → WordNet POS"""
    if tag.startswith('J'):
        return wordnet.ADJ
    elif tag.startswith('V'):
        return wordnet.VERB
    elif tag.startswith('N'):
        return wordnet.NOUN
    elif tag.startswith('R'):
        return wordnet.ADV
    return wordnet.NOUN

def preprocess(text):
    text = normalize_text(text)     # normalization
    text = remove_noise(text)       # cleaning symbols & noise
    tokens = word_tokenize(text)    # tokenization

    processed_tokens = []
    tagged_tokens = pos_tag(tokens)

    for word, tag in tagged_tokens:
    
        word = word.strip().lower()
    
        if (
            word in stop_words
            or len(word) == 1
            or not word.isalpha()
        ):
            continue
        
        # POS-aware lemmatization
        lemma = lemmatizer.lemmatize(word, get_wordnet_pos(tag))
    
        if len(lemma) == 1:
            continue
        
        processed_tokens.append(lemma)
    
    return processed_tokens


# Optional spelling correction (VERY slow for large datasets)
# raw_text = spelling_correction(raw_text)


# Apply preprocessing
tokens = preprocess(raw_text)

final_text = " ".join(tokens)

# Generate Word Cloud
wordcloud = WordCloud(
    width=1200,
    height=600,
    background_color="white",
    max_words=200,
    collocations=False
).generate(final_text)


# # Display
# plt.figure(figsize=(15, 7))
# plt.imshow(wordcloud, interpolation="bilinear")
# plt.axis("off")
# plt.title("Reddit Titles Word Cloud", fontsize=18)
# plt.show()

wordcloud.to_file("reddit_wordcloud.png")
print('✅ Word Cloud Created: "reddit_wordcloud.png"')