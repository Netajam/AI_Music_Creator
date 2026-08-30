"""Example — three songs, to show what a collection is.

A collection is the source; `night/build.py` is what turns it into the three
artefacts each song needs — a lyrics file, a preset, and a job in the queue —
refusing on the way anything that breaks a rule the recipe book already paid
for. Nothing here is special: copy this file, rename it, and edit.

    python3 night/build.py example     # write the files, queue what is new
    ./night/runner.sh                  # drain the queue, one process per take

The three below are deliberately unalike — a sung four-to-the-floor, a quiet
chanson, an instrumental — because a collection whose songs share a voice, a
structure and a negative produces ten costumes on one songwriter. That failure
is worth reading about before writing your own: see `docs/recipes.md`.

A song may also carry `"reference": "melange.wav"`, read from `refs/` in the
workspace, to be generated in the style of an existing track. No such file
ships here — `./grab` and `./blend-refs` are what make one.
"""

COLLECTION = {
    "order": 1,
    "title": "Example",
    "blurb": "Three songs that show the shape of a collection.",
}

SONGS = [
{
 "slug": "lache-tout", "title": "Lâche tout",
 "language": "fr", "era": "2019", "voice": "male, sung-spoken", "form": "two drops",
 "bpm": 126, "key": "D minor", "duration": 145, "seed": 1,
 "style": ("Energetic French electro-house with a hard techno edge, four-on-the-floor "
           "kick, driving sidechained bassline, dark minor-key synth hook, tense "
           "filtered build-ups releasing into a massive distorted sub-bass drop, "
           "sung-spoken French male vocal, big room festival energy"),
 "negative": ("acoustic, ballad, slow, orchestral, country, female lead vocals, "
              "lo-fi, muddy mix"),
 "lyrics": """[Intro]

[Verse]
On a fermé la ville à double tour
Les néons comptent les secondes
Personne ne rentre avant le jour
Personne ne dort quand ça gronde

[Build]
Et ça monte, et ça monte
Le sol tremble sous les pas
Trois, deux, un, plus rien ne compte

[Drop]
LÂCHE TOUT, LA NUIT NOUS APPARTIENT
LÂCHE TOUT, ON NE RENTRERA PAS

[Verse]
Les basses ouvrent le bitume
Les mains touchent le plafond
On a brûlé nos dernières brumes
Sur la dernière des chansons

[Build]
Et ça monte, et ça monte
Le sol tremble sous les pas
Trois, deux, un, plus rien ne compte

[Drop]
LÂCHE TOUT, LA NUIT NOUS APPARTIENT
LÂCHE TOUT, ON NE RENTRERA PAS

[Outro]
""",
},
{
 "slug": "chambre-douze", "title": "Chambre douze",
 "language": "fr", "era": "1974", "voice": "male, low and close", "form": "verse-chorus",
 "bpm": 78, "key": "A minor", "duration": 170, "seed": 1,
 "lm_temperature": 0.8,
 "style": ("Melancholic French chanson, fingerpicked nylon guitar, upright piano with "
           "the felt down, brushed drums entering late, a single cello holding long "
           "notes, low intimate male voice close to the microphone speaking more than "
           "singing, warm analogue room, spacious and unhurried"),
 "negative": ("electronic drums, synthesiser, distorted guitar, fast tempo, shouting, "
              "female lead vocals, reverb-heavy stadium production"),
 "lyrics": """[Intro]

[Verse]
La chambre douze donne sur la cour
Le radiateur parle la nuit
J'ai compté les taches du mur
Il en manquait une aujourd'hui

[Chorus]
Et je reste, et je reste
Le temps passe sans moi
La valise est prête
Depuis des mois, elle attend là

[Verse]
Le voisin joue toujours la même
Trois accords qu'il ne finit pas
J'ai fini par aimer ce thème
Comme on aime ce qu'on ne choisit pas

[Chorus]
Et je reste, et je reste
Le temps passe sans moi
La valise est prête
Depuis des mois, elle attend là

[Bridge]
Un jour la porte s'ouvrira
Sur un couloir, sur rien du tout

[Outro]
""",
},
{
 "slug": "dernier-metro", "title": "Dernier métro",
 "language": "en", "era": "1994 Berlin", "voice": "instrumental",
 "form": "one chord, eroding", "instrumental": True,
 "bpm": 120, "key": "F minor", "duration": 180, "seed": 1,
 "fade_out": 6,
 "style": ("Dub techno, one filtered chord stab soaked in tape delay repeating every "
           "two bars and slowly eroding, soft muffled four-to-the-floor kick, deep "
           "round sub bass, a wash of hiss and vinyl crackle, enormous reverb, almost "
           "nothing else, changing so slowly the change is barely audible, grey and "
           "submerged, instrumental with no voice"),
 "negative": ("vocals, singing, lyrics, melody, bright synths, busy arrangement, "
              "EDM drop, riser, guitar, orchestra, fast, cluttered mix"),
},
]
