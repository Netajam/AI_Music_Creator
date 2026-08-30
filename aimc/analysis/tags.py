"""Naming what plays inside `other`, by asking a tagger rather than a threshold.

`stems` splits a mix four ways and stops there: `other` is every harmonic
instrument that is neither the bass nor the voice, and Demucs has no vocabulary
to say which. This module supplies the vocabulary — AudioSet's, through the
Audio Spectrogram Transformer (`MIT/ast-finetuned-audioset-10-10-0.4593`,
87 M parameters, 350 MB), whose 527 labels include seventy-odd instruments and
fifty genres.

It is the third and last model in the analysis, and like the other two it is
asked for rather than run on anything's initiative.

Two readings, and they do not cost the same:

    instruments   from the `other` stem, so it needs the separation
    genres        from the mix, so it needs nothing at all

Both are computed inside `stems`' existing chunk loop, where the separated
`other` is already in hand: a second pass over the audio would double the only
expensive part for no reason.


Why the stem and not the mix
----------------------------
Measured on four tracks, 90 s each. Tagging the mix is not weak, it is dead:
the best instrument label on any of the four scored 0.027, and the umbrella
`Musical instrument` label sat between 0.004 and 0.048 while `Music` scored
0.71 to 0.92. The tagger plainly hears music and simply never fires an
instrument label on a full mix — AudioSet applied those labels mostly to clips
of one instrument, so a mix is out of the distribution they describe.

Separating first lifts that umbrella from 0.048 to 0.317 on the same audio.
That factor is what buys the second forward pass.


What it can and cannot hear
---------------------------
The four takes measured, best family score on the `other` stem:

    babylon-reggae-seed7    generated  reggae       keyboard        0.1483
    LYRICSON, Night and Day real       reggae/dub   bowed string    0.1638
    all-dayggering-seed7    generated  ragga jungle plucked string  0.0412
    Chase & Status, Baddadan real      jungle/DnB   (didgeridoo)    0.0575

The split is by genre and not by origin, which is worth stating plainly because
the opposite was expected: a *generated* reggae scored better than a *real*
commercial jungle track. ACE-Step's output is not the problem, and the worry
that it would be out of AudioSet's distribution is not what the numbers show.

What separates the two halves is what is left in `other` once the drums, the
bass and the voice are gone. Reggae leaves an organ and a skank; jungle leaves
break bleed and reverb tails, which name nothing. Read a silent verdict on a
breakbeat track as "there was nothing to name", not as "the track has no
instruments".


Why families, and why the top three
-----------------------------------
No individual label ever cleared 0.19 mean or 0.37 peak on any track measured,
so nothing here can support the panel flatly saying "guitar". What is readable
is not a score but an agreement: on the dub plate the tagger returned
`Pizzicato 0.18`, `Bowed string 0.16`, `Violin 0.15`, `Cello 0.08` and
`Double bass 0.05` — five labels describing one thing. On the ragga jungle it
returned `Mandolin 0.057`, `Accordion 0.042`, `Banjo 0.035`, `Violin 0.035` —
four labels contradicting each other at the same magnitude as some of the
first list. Same numbers, opposite meaning.

So a family scores as the mean of its three best labels, its own parent node
included. The mean of three is what makes the difference above legible: it
rewards a cluster and punishes a lone spike, which is exactly the failure seen
on Baddadan, where `Didgeridoo` alone reached 0.138 — comfortably the highest
single instrument label of any real track measured, and wrong. Averaged against
the two next labels in its family it falls to 0.051 and is correctly dropped.

`HEARD` sits at 0.10, in the gap between the two halves of the table above: the
highest family it rejects scores 0.0575 and the lowest it accepts 0.1483, a
factor of 2.6 with nothing measured in between. It is a round number in that
gap rather than a fitted one, because four tracks cannot justify a third digit.

A known false negative, recorded because it is the interesting one: on the
reggae take the skank guitar comes back as `plucked string` at 0.0501 — Guitar,
Plucked string instrument and Strum, three labels in agreement, pointing at an
instrument that is genuinely there. It is dropped anyway. A skank is a muted,
percussive chord, and Demucs leaves much of it in `drums` rather than in
`other`; what reaches the tagger is too little to clear a bar set where the
didgeridoo has to fall. Lowering `HEARD` to catch it would admit that
didgeridoo, which is the trade actually on offer here.

What this calibration does not cover: four tracks, two of them reggae, none
with a prominent solo instrument that is neither keys nor strings. Nothing here
has been shown to recognise a horn section or a saxophone; those families are
in the vocabulary and untested. And the gate is deliberately one-sided — it can
only ever suppress, so a family it does report is the weaker claim and a family
it stays silent about says as much about the residue in `other` as about the
track.
"""

from __future__ import annotations

from typing import Any

MODEL = "MIT/ast-finetuned-audioset-10-10-0.4593"

# The tagger's rate, and not a choice of ours: AST was trained on 16 kHz
# log-mel patches, and its feature extractor resamples nothing.
SR = 16000

# A family scores as the mean of its `SUPPORT` best labels. Three, because the
# clusters that turned out to be real ran four to five labels deep and the lone
# spikes ran one: three is the shortest window that tells those apart.
SUPPORT = 3
HEARD = 0.10

# A genre has no family to agree with it, so it stands on its own score and the
# bar is the same one. Reggae reached 0.218 on the generated take and 0.286 on
# the real dub plate; the jungle tracks' correct labels (`Drum and bass` 0.050,
# `Electronic music` 0.102) mostly sit under it, which is the honest outcome —
# the head is good on reggae and poor on bass music, and the threshold should
# not be lowered until it is not.
GENRE_HEARD = 0.10

# The AudioSet ontology, written as names rather than as the indices they
# resolve to. The indices are contiguous in this model and it would be shorter
# to slice a range, but a range says nothing about what it contains and would
# go quietly wrong against any other checkpoint. Resolved once, at load, and
# loudly: a name that no longer exists raises rather than scoring zero forever.
#
# Each family is (parent node, leaves). The parent is evidence like any other
# and takes part in the mean — `Keyboard (musical)` was the single strongest
# label on the reggae take, and dropping it for being a category would have
# thrown away the best number in the cluster.
FAMILY_LABELS: dict[str, tuple[str, tuple[str, ...]]] = {
    "plucked string": ("Plucked string instrument", (
        "Guitar", "Electric guitar", "Bass guitar", "Acoustic guitar",
        "Steel guitar, slide guitar", "Tapping (guitar technique)", "Strum",
        "Banjo", "Sitar", "Mandolin", "Zither", "Ukulele", "Harp")),
    "keyboard": ("Keyboard (musical)", (
        "Piano", "Electric piano", "Organ", "Electronic organ", "Hammond organ",
        "Synthesizer", "Sampler", "Harpsichord")),
    "bowed string": ("Bowed string instrument", (
        "String section", "Violin, fiddle", "Pizzicato", "Cello",
        "Double bass", "Orchestra")),
    "brass": ("Brass instrument", ("French horn", "Trumpet", "Trombone")),
    "wind": ("Wind instrument, woodwind instrument", (
        "Flute", "Saxophone", "Clarinet")),
    # No parent node in the ontology, and no musical family either — these are
    # the free-reed and one-off instruments that AudioSet lists flat. Grouped
    # so that they are subject to the same agreement rule as the rest rather
    # than escaping it as a set of lone spikes, which is precisely how
    # `Didgeridoo` scored 0.138 on a track with no didgeridoo in it.
    "other instrument": ("", (
        "Harmonica", "Accordion", "Bagpipes", "Didgeridoo", "Shofar",
        "Theremin", "Singing bowl", "Mallet percussion", "Marimba, xylophone",
        "Glockenspiel", "Vibraphone", "Steelpan", "Scratching (performance "
        "technique)")),
}

# Everything between `Pop music` and `Independent music` in the ontology. Listed
# rather than sliced, for the same reason as the families.
GENRE_LABELS: tuple[str, ...] = (
    "Pop music", "Hip hop music", "Beatboxing", "Rock music", "Heavy metal",
    "Punk rock", "Grunge", "Progressive rock", "Rock and roll",
    "Psychedelic rock", "Rhythm and blues", "Soul music", "Reggae", "Country",
    "Swing music", "Bluegrass", "Funk", "Folk music", "Middle Eastern music",
    "Jazz", "Disco", "Classical music", "Opera", "Electronic music",
    "House music", "Techno", "Dubstep", "Drum and bass", "Electronica",
    "Electronic dance music", "Ambient music", "Trance music",
    "Music of Latin America", "Salsa music", "Flamenco", "Blues",
    "Music for children", "New-age music", "Vocal music", "A capella",
    "Music of Africa", "Afrobeat", "Christian music", "Gospel music",
    "Music of Asia", "Carnatic music", "Music of Bollywood", "Ska",
    "Traditional music", "Independent music",
)

# The two umbrella labels, kept out of every family and reported on their own.
# They name no instrument, but `Musical instrument` going from 0.048 on a mix to
# 0.317 on the stem is the one number that says the separation did its job, and
# a reader who wants to check the claim above should not have to take it on
# trust.
UMBRELLA_LABELS = ("Music", "Musical instrument")


class Tagger:
    """The AST checkpoint and the index of the labels we care about.

    Held as an object because the label resolution is worth doing once, and
    because the caller loads this alongside Demucs and should be able to see
    exactly when the 350 MB arrives.
    """

    def __init__(self) -> None:
        from transformers import ASTFeatureExtractor, ASTForAudioClassification

        self.extractor = ASTFeatureExtractor.from_pretrained(MODEL)
        self.model = ASTForAudioClassification.from_pretrained(MODEL)
        self.model.eval()

        # id2label arrives as Any: transformers ships no types for it, and
        # the ints are what every lookup below indexes a numpy row with.
        by_name: dict[str, int] = {
            str(name): int(i) for i, name in self.model.config.id2label.items()}

        def index(name: str) -> int:
            if name not in by_name:
                raise KeyError(
                    f"{MODEL} has no label {name!r}: the ontology in "
                    f"aimc/analysis/tags.py does not match this checkpoint.")
            return by_name[name]

        self.families = {
            family: [index(n) for n in ((parent, *leaves) if parent else leaves)]
            for family, (parent, leaves) in FAMILY_LABELS.items()
        }
        self.genres = {name: index(name) for name in GENRE_LABELS}
        self.umbrella = {name: index(name) for name in UMBRELLA_LABELS}
        self.label = self.model.config.id2label

    def scores(self, mono: Any, rate: int) -> Any:
        """Scores over all 527 labels for one passage of mono audio.

        Sigmoid and not softmax: AST is trained multi-label with a per-label
        binary loss, and a passage is allowed to hold a guitar *and* an organ.
        A softmax here would make the labels compete for one budget and turn a
        rich arrangement into a poor one.
        """
        import torch
        import torchaudio.functional as functional

        if rate != SR:
            mono = functional.resample(mono, rate, SR)
        feats = self.extractor(mono.numpy(), sampling_rate=SR, return_tensors="pt")
        with torch.no_grad():
            return torch.sigmoid(self.model(**feats).logits[0]).numpy()


def summarise(tagger: Tagger, stem_scores: list[Any],
              mix_scores: list[Any]) -> dict[str, Any]:
    """Families heard in `other`, genres heard in the mix, and the numbers behind them.

    `stem_scores` and `mix_scores` are one array of 527 scores per chunk. They
    are averaged over the track rather than reported per chunk: a family holds
    for a section, not for a second, and the instrument that plays only in the
    bridge is below what four tracks of calibration can speak to.
    """
    import numpy as np

    if not stem_scores or not mix_scores:
        return {"error": "nothing tagged"}

    stem = np.array(stem_scores).mean(0)
    mix = np.array(mix_scores).mean(0)

    families: list[dict[str, Any]] = []
    for family, idx in tagger.families.items():
        best = sorted(idx, key=lambda i: -stem[i])[:SUPPORT]
        score = float(np.mean([stem[i] for i in best]))
        families.append({
            "family": family,
            "score": round(score, 4),
            "heard": score >= HEARD,
            # What the score is made of. A verdict from a threshold is worth
            # what the reader can check, which is the rule `stems` already
            # follows for its own.
            "labels": [{"label": tagger.label[i], "score": round(float(stem[i]), 4)}
                       for i in best],
        })
    families.sort(key=lambda f: -float(f["score"]))

    genres: list[dict[str, Any]] = [
        {"genre": name, "score": round(float(mix[i]), 4),
         "heard": float(mix[i]) >= GENRE_HEARD}
        for name, i in tagger.genres.items()]
    genres.sort(key=lambda g: -float(g["score"]))

    return {
        "tagger": MODEL,
        "families": families,
        "heard": [f["family"] for f in families if f["heard"]],
        "genres": genres[:8],
        "genres_heard": [g["genre"] for g in genres if g["heard"]],
        # The separation's receipt: `Musical instrument` on the mix against the
        # same label on the stem. If these two are close, the stem was not worth
        # separating and nothing below it should be believed.
        "umbrella": {name: {"mix": round(float(mix[i]), 4),
                            "stem": round(float(stem[i]), 4)}
                     for name, i in tagger.umbrella.items()},
    }
