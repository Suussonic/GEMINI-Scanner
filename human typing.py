import time
import keyboard
import random
import string


def _build_neighbor_map():
    # QWERTY rows as strings to compute neighbors
    rows = [
        "`1234567890-=" ,
        "qwertyuiop[]\\",
        "asdfghjkl;'",
        "zxcvbnm,./"
    ]
    neigh = {}
    for r in rows:
        for i, ch in enumerate(r):
            s = set()
            # same row neighbors
            if i - 1 >= 0:
                s.add(r[i - 1])
            if i + 1 < len(r):
                s.add(r[i + 1])
            # neighbor from row above/below by approximate index
            for orow in rows:
                if r is orow:
                    continue
            neigh[ch] = ''.join(s)
    # include uppercase mapping
    full = {}
    for k, v in neigh.items():
        full[k] = v
        full[k.upper()] = v.upper()
    return full


NEIGHBORS = _build_neighbor_map()


def human_like_typing(text, base_delay=0.08, random_factor=0.04, typo_chance=0.12, long_pause_chance=0.02, long_pause_max=3.0, neighbor_chance=0.75):
    """Simulate more human-like typing.

    Features:
    - realistic typos using neighboring keys (insertion/replacement/transposition)
    - variable per-character speed with jitter
    - rare long pauses (thinking)
    - slightly longer pauses after punctuation

    :param text: text to type
    :param base_delay: average delay between chars
    :param random_factor: variation around base_delay
    :param typo_chance: chance to make a typo at any character
    :param long_pause_chance: chance to do a longer pause (thinking)
    :param long_pause_max: max seconds for long pause
    :param neighbor_chance: when making a typo, chance to use a physical-neighbor char
    """
    if not text:
        return

    prev_char = ''
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]

        # Rare long pause to simulate thinking (e.g., 1-3s)
        if random.random() < long_pause_chance:
            pause = random.uniform(1.0, long_pause_max)
            time.sleep(pause)

        # punctuation small extra pause
        if ch in '.!?;:,' and random.random() < 0.9:
            punct_pause = random.uniform(0.08, 0.35)
        else:
            punct_pause = 0

        made_typo = False
        # Decide whether to make a typo
        if random.random() < typo_chance and ch.isprintable() and ch != '\n':
            # Select typo type
            t = random.random()
            if t < 0.45 and prev_char:
                # transpose previous and current (swap)
                # simulate by deleting prev, typing current, then prev
                try:
                    keyboard.send('backspace')
                except Exception:
                    pass
                keyboard.write(ch)
                keyboard.write(prev_char)
                time.sleep(base_delay + random.uniform(-random_factor, random_factor))
                # then delete the extra prev and retype correctly
                keyboard.send('backspace')
                keyboard.send('backspace')
                keyboard.write(prev_char)
                keyboard.write(ch)
                made_typo = True
            else:
                # insert or replace with neighboring key
                use_neighbor = random.random() < neighbor_chance
                if use_neighbor and ch.lower() in NEIGHBORS and NEIGHBORS[ch.lower()]:
                    neighs = NEIGHBORS[ch.lower()]
                    typo_char = random.choice(neighs)
                    # preserve case
                    if ch.isupper():
                        typo_char = typo_char.upper()
                else:
                    typo_char = random.choice(string.punctuation + string.digits)

                # Either insert then backspace, or replace then correct
                if random.random() < 0.6:
                    # insert
                    keyboard.write(typo_char)
                    time.sleep(base_delay + random.uniform(-random_factor, random_factor))
                    keyboard.send('backspace')
                    time.sleep(base_delay + random.uniform(-random_factor, random_factor))
                else:
                    # replace then correct
                    keyboard.write(typo_char)
                    time.sleep(base_delay + random.uniform(-random_factor, random_factor))
                    keyboard.send('backspace')
                    time.sleep(base_delay + random.uniform(-random_factor, random_factor))
                made_typo = True

        # Type the intended character
        if ch == '\n':
            keyboard.send('enter')
        else:
            keyboard.write(ch)

        # compute delay: base +/- random; faster inside words sometimes
        delay = base_delay + random.uniform(-random_factor, random_factor)
        # If previous and current are both letters, sometimes speed up
        if prev_char.isalpha() and ch.isalpha() and random.random() < 0.15:
            delay *= random.uniform(0.6, 0.95)
        # Slightly longer after punctuation or if a typo was corrected
        if punct_pause:
            time.sleep(punct_pause)
        time.sleep(max(0.0, delay))

        prev_char = ch
        i += 1

    # small final pause
    time.sleep(random.uniform(0.05, 0.25))

def main():
    try:
        print("Preparing to read the file and simulate typing...")
        time.sleep(1.5)  # Delay to simulate preparation
        
        # Open the file with UTF-8 encoding
        with open("output.txt", "r", encoding="utf-8") as file:
            content = file.read()  # Read the entire content of output.txt
            print("Simulating human-like typing from output.txt...")
            time.sleep(2)  # Delay before starting to simulate typing
            human_like_typing(content, base_delay=0.1, random_factor=0.05, typo_chance=0.1)
    except FileNotFoundError:
        print("Error: output.txt file not found. Please create the file and add content to it.")
        time.sleep(1)
    except UnicodeDecodeError:
        print("Error: The file is not encoded in UTF-8. Please save the file with UTF-8 encoding.")
        time.sleep(1)

if __name__ == "__main__":
    main()
