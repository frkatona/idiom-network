import csv
import re
from pathlib import Path

csv_path = Path("american_idioms_clean_list.csv")

# A comprehensive mapping of lowercase proper nouns to their correct casing
PROPER_NOUNS = {
    # Pronouns
    "i": "I", "i'm": "I'm", "i've": "I've", "i'd": "I'd", "i'll": "I'll",
    # Abbreviations
    "abc": "ABC", "abcs": "ABCs", "awol": "AWOL", "awols": "AWOLs", "qt": "QT", "zs": "Zs", "a-z": "A-Z", "usa": "USA",
    # Names
    "achilles": "Achilles", "adam": "Adam", "adams": "Adams", "brahms": "Brahms", "liszt": "Liszt", "charley": "Charley",
    "davy": "Davy", "dick": "Dick", "dicky": "Dicky", "harry": "Harry", "hoyle": "Hoyle", "jack": "Jack",
    "jones": "Jones", "joneses": "Joneses", "midas": "Midas", "nick": "Nick", "paul": "Paul",
    "pete": "Pete", "peter": "Peter", "riley": "Riley", "robin": "Robin", "robinson": "Robinson", "solomon": "Solomon",
    "thomas": "Thomas", "tom": "Tom", "sam": "Sam", "uncle": "Uncle", "hobson": "Hobson", "hobson's": "Hobson's",
    "goliath": "Goliath", "david": "David", "pandora": "Pandora", "pandora's": "Pandora's", "gordian": "Gordian",
    "damocles": "Damocles", "procrustean": "Procrustean", "pyrrhic": "Pyrrhic", "scylla": "Scylla", "charybdis": "Charybdis",
    "murphy's": "Murphy's", "newton's": "Newton's", "occam's": "Occam's", "nod": "Nod", "jekyll": "Jekyll", "hyde": "Hyde",
    "elvis": "Elvis", "george": "George", "gregory": "Gregory", "jimmy": "Jimmy", "khyber": "Khyber", "rosie": "Rosie",
    "shakespeare": "Shakespeare", "mrs": "Mrs", "york": "York", "peck": "Peck", "riddle": "Riddle",
    # Places / Nationalities
    "america": "America", "america's": "America's", "australian": "Australian", "britain": "Britain", "broadway": "Broadway",
    "danish": "Danish", "dutch": "Dutch", "english": "English", "french": "French", "greek": "Greek", "irish": "Irish",
    "mecca": "Mecca", "missouri": "Missouri", "newcastle": "Newcastle", "rome": "Rome", "rubicon": "Rubicon", "spain": "Spain",
    "waterloo": "Waterloo", "brighton": "Brighton", "brum": "Brum", "spanish": "Spanish", "german": "German",
    "scottish": "Scottish", "welsh": "Welsh", "roman": "Roman", "romans": "Romans", "bible": "Bible", "bibles": "Bibles",
    "biblical": "Biblical", "god": "God", "god's": "God's", "jesus": "Jesus", "christ": "Christ", "christ's": "Christ's",
    "babylon": "Babylon", "babel": "Babel", "eden": "Eden", "barnet": "Barnet", "china": "China", "cockney": "Cockney",
    "hollywood": "Hollywood", "pommy": "Pommy", "vatican": "Vatican",
    # Days & Months
    "sunday": "Sunday", "sundays": "Sundays", "monday": "Monday", "tuesday": "Tuesday", "wednesday": "Wednesday",
    "thursday": "Thursday", "friday": "Friday", "saturday": "Saturday", "january": "January", "february": "February",
    "june": "June", "july": "July", "august": "August",
    "september": "September", "october": "October", "november": "November", "december": "December",
}

# Context-dependent proper nouns that should ONLY remain capitalized if they were capitalized in the original text
CONTEXT_PROPER_NOUNS = {
    "new": "New", "year": "Year", "grand": "Grand", "central": "Central", "station": "Station", 
    "east": "East", "west": "West", "north": "North", "south": "South", "deep": "Deep", 
    "middle": "Middle", "old": "Old", "father": "Father", "time": "Time", "glory": "Glory",
    "maker": "Maker", "job": "Job", "march": "March", "may": "May"
}

# Overrides for structural/meta words that appeared capitalized in middle of phrases but should be lowercased
OVERRIDE_LOWERCASE = {"idioms", "phrase", "informal", "make", "that", "types"}

def clean_idiom_text(text: str) -> str:
    # Split text into word tokens and non-word separators
    tokens = re.split(r'(\b[a-zA-Z\'-]+\b)', text)
    cleaned = []
    
    # Extract only the word tokens to check ahead
    word_tokens = [t.lower() for t in tokens if re.match(r'^[a-zA-Z\'-]+$', t)]
    
    # We want to keep track of word index to differentiate first word from others
    word_idx = 0
    
    for token in tokens:
        if re.match(r'^[a-zA-Z\'-]+$', token):
            norm = token.lower()
            
            # 1. Structural overrides
            if norm in OVERRIDE_LOWERCASE:
                cleaned.append(norm)
            
            # 2. General Proper Nouns
            elif norm in PROPER_NOUNS:
                cleaned.append(PROPER_NOUNS[norm])
            
            # 3. Context-Dependent Proper Nouns
            elif norm in CONTEXT_PROPER_NOUNS:
                if word_idx == 0:
                    # If it's the first word of the phrase:
                    # Special case: "New York"
                    if norm == "new" and len(word_tokens) > 1 and word_tokens[1] == "york":
                        cleaned.append("New")
                    else:
                        cleaned.append(norm) # Lowercase first words like 'old', 'time', 'march'
                else:
                    # Mid-phrase context-dependent proper nouns (keep capitalized only if originally capitalized)
                    if token[0].isupper():
                        cleaned.append(CONTEXT_PROPER_NOUNS[norm])
                    else:
                        cleaned.append(norm)
            
            # 4. Single capitalized letters (like 'A' in 'an A for effort', 'Z' in 'A-Z')
            elif len(token) == 1 and token.isupper():
                if word_idx == 0:
                    cleaned.append(token.lower()) # Lowercase leading single letter articles like 'A'
                else:
                    cleaned.append(token) # Keep capitalized single letters in middle of sentence
            
            # 5. Regular Words
            else:
                cleaned.append(norm)
            
            word_idx += 1
        else:
            cleaned.append(token)
            
    return "".join(cleaned)

def main():
    if not csv_path.exists():
        print("CSV not found.")
        return

    rows = []
    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        for row in reader:
            cleaned_idiom = clean_idiom_text(row["idiom"]).replace("too May pies", "too many pies").replace("too may pies", "too many pies")
            cleaned_head = clean_idiom_text(row["raw_entry_head"]).replace("too May pies", "too many pies").replace("too may pies", "too many pies")
            cleaned_row = {
                "idiom": cleaned_idiom,
                "dict_page": row["dict_page"],
                "pdf_page": row["pdf_page"],
                "raw_entry_head": cleaned_head
            }
            rows.append(cleaned_row)

    # Write cleaned rows back
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    print(f"Successfully cleaned casing consistency on all {len(rows)} idioms.")

if __name__ == "__main__":
    main()
