"""Composing a style string, with the facts to hand and the vocabulary checked.

`--style` is the strongest lever this project has and the easiest to get wrong.
The recipe book records what works; this domain is the other half of that — it
puts the two sources of truth in front of you while you write, rather than after
a seven-minute take has said you were wrong:

  * the **genre database** in `refs/waxonia/`, which knows what tempo a genre
    actually sits at, what year and city it came from, and what it descends
    from. A tempo taken from there is a fact rather than a guess;
  * the **model's own vocabulary**, `engine/acestep/genres_vocab.txt` — 178,571
    entries and not one artist name — which decides whether a term you typed is
    a term the model has ever seen.

It reads both and writes a preset. It does not generate anything, and it knows
nothing about audio: it is a writing desk, not an instrument.
"""
