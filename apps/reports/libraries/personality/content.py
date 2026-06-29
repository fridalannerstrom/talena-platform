"""Localized personality-profile content used by Talena reports.

The indicator score bands follow the wording supplied by Talent Qode.
Only spelling, grammar and punctuation have been corrected.
Indicator low/high poles reuse the approved 1–2 and 9–10 texts.
"""


def _localized(sv, en):
    return {"sv": sv, "en": en}


def _indicator(
    *,
    label_sv,
    label_en,
    score_1_2,
    score_3,
    score_4_7,
    score_8,
    score_9_10,
):
    """Build one indicator entry without duplicating pole text."""
    return {
        "label_sv": label_sv,
        "label_en": label_en,
        "low_pole": score_1_2,
        "high_pole": score_9_10,
        "score_texts": {
            "1_2": score_1_2,
            "3": score_3,
            "4_7": score_4_7,
            "8": score_8,
            "9_10": score_9_10,
        },
    }


# Static full-trait pole wording from the Swedish and English profile reports.
# Trait summaries are still built dynamically from the three indicator score texts.
TRAIT_PROFILE_CONTENT = {
    "Cooperative": {
        "label_sv": "Samverkande",
        "label_en": "Cooperative",
        "low_pole": _localized(
            (
                "Föredrar att arbeta självständigt och säger ifrån vid "
                "meningsskiljaktigheter."
            ),
            (
                "Prefers to work independently and expresses themselves if they "
                "disagree with others."
            ),
        ),
        "high_pole": _localized(
            (
                "Tillmötesgående och gillar att samarbeta med andra. Är lyhörd "
                "gentemot andras behov."
            ),
            (
                "Agreeable and enjoys cooperating with others, sensitive to their "
                "needs."
            ),
        ),
    },
    "Empathy": {
        "label_sv": "Empati",
        "label_en": "Empathy",
        "low_pole": _localized(
            (
                "Kan ta tid på sig att vänja sig vid andra och ha förståelse för "
                "andras perspektiv."
            ),
            (
                "May take time to warm to others and tolerate different "
                "perspectives."
            ),
        ),
        "high_pole": _localized(
            (
                "Empatiserar lätt med andra. Gillar att lyssna och skapa goda "
                "relationer."
            ),
            (
                "Empathises easily with others, enjoys listening and building "
                "rapport."
            ),
        ),
    },
    "Supporting": {
        "label_sv": "Stödjande",
        "label_en": "Supporting",
        "low_pole": _localized(
            (
                "Har tydliga förväntningar på andra och låter dem utvecklas "
                "självständigt."
            ),
            (
                "Has clear expectations of others and lets them develop "
                "independently."
            ),
        ),
        "high_pole": _localized(
            "Stöttande och hjälper andra att utvecklas och växa.",
            "Supportive and helps others to develop and grow.",
        ),
    },
    "Connecting": {
        "label_sv": "Nätverkande",
        "label_en": "Connecting",
        "low_pole": _localized(
            (
                "Kommunicerar med en betrodd grupp. Kan känna sig obekväm med att "
                "skapa nya kontakter."
            ),
            (
                "Prefers to communicate with a smaller trusted group, may be "
                "uncomfortable initiating new contacts."
            ),
        ),
        "high_pole": _localized(
            (
                "Kommunicerar med en stor grupp människor. Tar gärna kontakt med "
                "andra."
            ),
            (
                "Communicates with a wide range of people, readily initiating "
                "contact with others."
            ),
        ),
    },
    "Dynamic": {
        "label_sv": "Driftighet",
        "label_en": "Dynamic",
        "low_pole": _localized(
            (
                "Föredrar att jobba i jämnt tempo och har ett försiktigt "
                "tillvägagångssätt."
            ),
            "Prefers to work at a steady pace and is cautious in approach.",
        ),
        "high_pole": _localized(
            "Driven och söker nya utmaningar. Fattar beslut snabbt.",
            "Driven and seeks out new challenges, makes decisions quickly.",
        ),
    },
    "Influential": {
        "label_sv": "Inflytelserik",
        "label_en": "Influential",
        "low_pole": _localized(
            (
                "Föredrar att följa instruktioner och undviker att tvinga över sina "
                "egna åsikter på andra."
            ),
            (
                "Prefers to follow instructions and avoids pushing their views on "
                "others."
            ),
        ),
        "high_pole": _localized(
            "Föredrar att ta ledningen och gillar att påverka andra.",
            "Prefers to take the lead and enjoys influencing others.",
        ),
    },
    "Goal-focused": {
        "label_sv": "Måldriven",
        "label_en": "Goal-focused",
        "low_pole": _localized(
            (
                "Undviker både konkurrens och att sätta upp mål. Föredrar att ta "
                "saker som de kommer."
            ),
            (
                "Avoids competition and setting specific goals, prefers to take "
                "things as they come."
            ),
        ),
        "high_pole": _localized(
            (
                "Motiveras av utmanande mål. Har god självdisciplin och är "
                "tävlingsinriktad."
            ),
            "Motivated by challenging goals, self-disciplined and competitive.",
        ),
    },
    "Structured": {
        "label_sv": "Strukturerad & disciplinerad",
        "label_en": "Structured",
        "low_pole": _localized(
            (
                "Har ett spontant tillvägagångssätt. Är mindre fokuserad på detaljer "
                "och tolererar små misstag."
            ),
            (
                "Takes a spontaneous approach, less focused on detail and accepts "
                "small mistakes."
            ),
        ),
        "high_pole": _localized(
            (
                "Planerar och strukturerar uppgifter, engagerad i att leverera och "
                "säkerställa noggrannhet."
            ),
            (
                "Conscientiously plans and organises tasks, committed to delivering "
                "and ensuring accuracy."
            ),
        ),
    },
    "Analytical": {
        "label_sv": "Analytisk",
        "label_en": "Analytical",
        "low_pole": _localized(
            (
                "Använder ett instinktivt tillvägagångssätt vid problemlösning. Är "
                "mindre intresserad av data och analys."
            ),
            (
                "Adopts an intuitive approach to solving problems, less interested "
                "in data or analysis."
            ),
        ),
        "high_pole": _localized(
            (
                "Använder ett analytiskt tillvägagångssätt för att utvärdera "
                "situationer. Använder data för att lösa problem."
            ),
            (
                "Adopts an analytical approach to evaluating situations, uses data "
                "to help solve problems."
            ),
        ),
    },
    "Complex Thinking": {
        "label_sv": "Konceptuell",
        "label_en": "Complex Thinking",
        "low_pole": _localized(
            (
                "Gillar ett praktiskt tillvägagångssätt som fokuserar på operativa "
                "detaljer. Undviker sannolikt komplexa problem."
            ),
            (
                "Enjoys taking a practical approach focused on operational details, "
                "likely to avoid complex problems."
            ),
        ),
        "high_pole": _localized(
            (
                "Gillar att jobba med komplexa situationer. Undersöker olika "
                "perspektiv och tekniker."
            ),
            (
                "Enjoys working with complex situations, exploring different "
                "perspectives and techniques."
            ),
        ),
    },
    "Creativity": {
        "label_sv": "Kreativitet",
        "label_en": "Creativity",
        "low_pole": _localized(
            (
                "Använder hellre beprövade tillvägagångssätt än att experimentera "
                "med nya tekniker."
            ),
            (
                "Prefers to use tried and tested approaches rather than experiment "
                "with new techniques."
            ),
        ),
        "high_pole": _localized(
            (
                "Har ett kreativt tillvägagångssätt. Gillar att vara innovativ och "
                "hitta nya lösningar på problem."
            ),
            (
                "Creative in approach, enjoys innovating and finding new solutions "
                "to problems."
            ),
        ),
    },
    "Adaptability": {
        "label_sv": "Anpassningsbarhet",
        "label_en": "Adaptability",
        "low_pole": _localized(
            (
                "Behöver tid för att anpassa sig till nya omständigheter. Har "
                "bestämda åsikter och föredrar en förutsägbar rutin."
            ),
            (
                "Takes time to adapt to new circumstances, has firm views and "
                "prefers a predictable routine."
            ),
        ),
        "high_pole": _localized(
            (
                "Anpassar sig lätt till nya situationer. Har ett flexibelt "
                "tillvägagångssätt och gillar variation."
            ),
            (
                "Adapts readily to new situations, taking a flexible approach and "
                "enjoying variety."
            ),
        ),
    },
    "Straightforward": {
        "label_sv": "Uppriktighet och regelstyrd",
        "label_en": "Straightforward",
        "low_pole": _localized(
            (
                "Ger gärna komplimanger till andra och kan tänka sig att kringgå "
                "regler för att få saker gjorda."
            ),
            (
                "Readily compliments others and avoids being direct, willing to "
                "bend rules when needed to get things done."
            ),
        ),
        "high_pole": _localized(
            (
                "Kommunicerar på ett rakt och ärligt sätt. Följer noggrant regler "
                "och riktlinjer."
            ),
            (
                "Communicates in a straightforward and candid manner, adhering "
                "closely to rules and guidelines."
            ),
        ),
    },
    "Status Avoidance": {
        "label_sv": "Prestigelöshet",
        "label_en": "Status Avoidance",
        "low_pole": _localized(
            "Gillar att hens status och egenskaper uppmärksammas av andra.",
            "Enjoys their status and qualities being recognised by others.",
        ),
        "high_pole": _localized(
            (
                "Undviker situationer där hens status eller unika egenskaper "
                "framhävs."
            ),
            "Avoids situations which highlight their status or uniqueness.",
        ),
    },
    "Modesty": {
        "label_sv": "Ödmjukhet",
        "label_en": "Modesty",
        "low_pole": _localized(
            (
                "Gillar att prata om sina egna framgångar och få andras "
                "uppmärksamhet."
            ),
            (
                "Enjoys talking about their successes and receiving attention from "
                "others."
            ),
        ),
        "high_pole": _localized(
            "Ödmjuk vid kontakt med andra. Undviker att stå i centrum.",
            (
                "Modest in their dealings with others, avoids being the centre of "
                "attention."
            ),
        ),
    },
    "Resilience": {
        "label_sv": "Tålighet",
        "label_en": "Resilience",
        "low_pole": _localized(
            (
                "Kan vara pessimistisk. Kan behöva viss tid att återhämta sig från "
                "motgångar och kritik."
            ),
            (
                "May be pessimistic and take some time to recover from setbacks or "
                "criticism."
            ),
        ),
        "high_pole": _localized(
            (
                "Svarar positivt på motgångar. Återhämtar sig snabbt från "
                "utmaningar och kritik."
            ),
            (
                "Responds positively to setbacks, quickly recovering from challenges "
                "or criticism."
            ),
        ),
    },
    "Emotional Control": {
        "label_sv": "Emotionell stabilitet",
        "label_en": "Emotional Control",
        "low_pole": _localized(
            "Visar sina känslor och blir ängslig vid påfrestningar.",
            (
                "Shows their feelings readily and experiences anxiety when under "
                "pressure."
            ),
        ),
        "high_pole": _localized(
            (
                "Behåller lugnet och har kontroll över sina känslor vid "
                "påfrestningar."
            ),
            "Stays composed and controls feelings under pressure.",
        ),
    },
    "Independence": {
        "label_sv": "Självständighet",
        "label_en": "Independence",
        "low_pole": _localized(
            "Föredrar att få råd och stöd från andra.",
            "Prefers to have support and advice from others.",
        ),
        "high_pole": _localized(
            (
                "Självständig och självgående. Behöver väldigt lite stöd från "
                "andra."
            ),
            (
                "Independent and self-reliant, needing little support from others."
            ),
        ),
    },
}


INDICATOR_PROFILE_CONTENT = {
    # Cooperative
    "Sensitivity": _indicator(
        label_sv="Känslighet",
        label_en="Sensitivity",
        score_1_2=_localized(
            "Låter inte andras känslor påverka hens handlingar och beslut.",
            (
                "Does not let other people's feelings influence their actions and "
                "decisions."
            )
        ),
        score_3=_localized(
            (
                "Är mindre benägen att låta andras känslor påverka hens handlingar och "
                "beslut."
            ),
            (
                "Is less inclined to let other people's feelings influence their "
                "actions and decisions."
            )
        ),
        score_4_7=_localized(
            (
                "Vid handlingar och beslut borde hen kunna göra en god avvägning mellan "
                "sina egna och andras känslor och behov."
            ),
            (
                "When acting and making decisions, they should be able to strike a good "
                "balance between being attentive to their own feelings and to the "
                "feelings and needs of others."
            )
        ),
        score_8=_localized(
            (
                "Är troligen lyhörd gentemot andras behov och känslor vid "
                "beslutsfattande och agerande."
            ),
            (
                "Is probably attentive to other people's needs and feelings when making "
                "decisions and taking action."
            )
        ),
        score_9_10=_localized(
            (
                "Är mycket lyhörd gentemot andras behov och känslor vid beslutsfattande "
                "och agerande."
            ),
            (
                "Is highly attentive to other people's needs and feelings when making "
                "decisions and taking action."
            )
        ),
    ),
    "Teamwork": _indicator(
        label_sv="Grupparbete",
        label_en="Teamwork",
        score_1_2=_localized(
            "Föredrar att arbeta på egen hand framför samarbete i grupp.",
            "Prefers working independently rather than cooperating in a group."
        ),
        score_3=_localized(
            "Trivs med att arbeta på egen hand, snarare än att samarbeta i grupp.",
            "Enjoys working independently rather than cooperating in a group."
        ),
        score_4_7=_localized(
            (
                "Är vanligtvis samarbetsvillig och bekväm med att jobba både "
                "självständigt och i team."
            ),
            (
                "Is generally cooperative and comfortable working both independently "
                "and as part of a team."
            )
        ),
        score_8=_localized(
            (
                "Trivs med att samarbeta med andra och jobba som del av ett team eller "
                "grupp."
            ),
            "Enjoys cooperating with others and working as part of a team or group."
        ),
        score_9_10=_localized(
            (
                "Föredrar att samarbeta med andra och jobba som del av ett team eller "
                "grupp."
            ),
            "Prefers cooperating with others and working as part of a team or group."
        ),
    ),
    "Agreeableness": _indicator(
        label_sv="Tillmötesgående",
        label_en="Agreeableness",
        score_1_2=_localized(
            (
                "Är bekväm med att uttrycka sina åsikter om hen inte håller med "
                "omgivningen."
            ),
            (
                "Is comfortable expressing their views when they disagree with those "
                "around them."
            )
        ),
        score_3=_localized(
            (
                "Kommer troligtvis att vara bekväm med att uttrycka sina åsikter om hen "
                "inte håller med omgivningen."
            ),
            (
                "Is likely to be comfortable expressing their views when they disagree "
                "with those around them."
            )
        ),
        score_4_7=_localized(
            (
                "Är samarbetsvillig men också bekväm med att uttrycka sin åsikt när det "
                "krävs."
            ),
            (
                "Is cooperative while also being comfortable expressing their view when "
                "required."
            )
        ),
        score_8=_localized(
            (
                "Är vänlig och tillmötesgående och kommer sannolikt lätt överens med "
                "andra."
            ),
            (
                "Is friendly and accommodating and is likely to get along easily with "
                "others."
            )
        ),
        score_9_10=_localized(
            (
                "Är vänlig och tillmötesgående och kommer utan ansträngning lätt "
                "överens med andra."
            ),
            "Is friendly and accommodating and gets along with others effortlessly."
        ),
    ),

    # Empathy
    "Tolerance": _indicator(
        label_sv="Tolerans",
        label_en="Tolerance",
        score_1_2=_localized(
            "Upplever det utmanande att vara tolerant när det gäller andras brister.",
            "Finds it challenging to be tolerant of other people's shortcomings."
        ),
        score_3=_localized(
            (
                "Ibland kan hen uppleva att det är utmanande att vara tolerant när det "
                "gäller andras brister."
            ),
            (
                "May sometimes find it challenging to be tolerant of other people's "
                "shortcomings."
            )
        ),
        score_4_7=_localized(
            "Är förmodligen ganska tolerant när det gäller andras brister.",
            "Is probably fairly tolerant of other people's shortcomings."
        ),
        score_8=_localized(
            (
                "Har sannolikt lätt för att förstå andras perspektiv och är tolerant "
                "mot andra människor."
            ),
            (
                "Is likely to find it easy to understand other people's perspectives "
                "and is tolerant of others."
            )
        ),
        score_9_10=_localized(
            (
                "Har lätt för att förstå andras perspektiv och är mycket tolerant mot "
                "andra människor."
            ),
            (
                "Finds it easy to understand other people's perspectives and is highly "
                "tolerant of others."
            )
        ),
    ),
    "Listening": _indicator(
        label_sv="Lyhördhet",
        label_en="Listening",
        score_1_2=_localized(
            (
                "Upplever det tröttsamt att lyssna när andra pratar om sina problem "
                "eller olika perspektiv."
            ),
            (
                "Finds it tiring to listen when others talk about their problems or "
                "different perspectives."
            )
        ),
        score_3=_localized(
            (
                "Kan ibland tycka att det är energikrävande att lyssna när andra pratar "
                "om sina problem eller olika perspektiv."
            ),
            (
                "May sometimes find it draining to listen when others talk about their "
                "problems or different perspectives."
            )
        ),
        score_4_7=_localized(
            "När det behövs lyssnar hen aktivt på andras perspektiv och problem.",
            (
                "Listens actively to other people's perspectives and problems when "
                "needed."
            )
        ),
        score_8=_localized(
            "Gillar att lyssna på andras perspektiv och problem.",
            "Enjoys listening to other people's perspectives and problems."
        ),
        score_9_10=_localized(
            "Tar sig aktivt tid för att lyssna på andras perspektiv och problem.",
            (
                "Actively makes time to listen to other people's perspectives and "
                "problems."
            )
        ),
    ),
    "Warmth": _indicator(
        label_sv="Värme",
        label_en="Warmth",
        score_1_2=_localized(
            (
                "Det är energikrävande att empatisera med andra, vilket gör att det tar "
                "längre tid för hen att öppna upp för andra och skapa djupa relationer."
            ),
            (
                "Finds empathising with others draining, which means it may take them "
                "longer to open up to others and form deep relationships."
            )
        ),
        score_3=_localized(
            (
                "Det kan vara energikrävande att empatisera med andra, vilket kan "
                "betyda att det tar längre tid för hen att öppna upp för andra och "
                "skapa djupa relationer."
            ),
            (
                "May find empathising with others draining, which may mean it takes "
                "them longer to open up to others and form deep relationships."
            )
        ),
        score_4_7=_localized(
            (
                "Har lika lätt som de flesta att skapa djupa relationer samt visar "
                "värme och öppenhet mot andra när det behövs."
            ),
            (
                "Finds it as easy as most people to form deep relationships and shows "
                "warmth and openness towards others when needed."
            )
        ),
        score_8=_localized(
            (
                "Visar sannolikt värme och öppenhet mot andra, och har troligtvis lätt "
                "för att skapa djupa relationer."
            ),
            (
                "Is likely to show warmth and openness towards others and probably "
                "finds it easy to form deep relationships."
            )
        ),
        score_9_10=_localized(
            (
                "Har mycket lätt för att visa värme och öppenhet mot andra, och det "
                "kommer naturligt att skapa djupa relationer med andra."
            ),
            (
                "Finds it very easy to show warmth and openness towards others, and "
                "forming deep relationships comes naturally."
            )
        ),
    ),

    # Supporting
    "Developing Others": _indicator(
        label_sv="Andras utveckling",
        label_en="Developing Others",
        score_1_2=_localized(
            (
                "Upplever det energikrävande att fokusera på andras utveckling, och "
                "låter därför andra utvecklas självständigt."
            ),
            (
                "Finds it draining to focus on other people's development and therefore "
                "lets others develop independently."
            )
        ),
        score_3=_localized(
            "Föredrar att låta andra utvecklas självständigt.",
            "Prefers to let others develop independently."
        ),
        score_4_7=_localized(
            "Bör känna sig bekväm med att hjälpa andra att utvecklas när det behövs.",
            "Should feel comfortable helping others develop when needed."
        ),
        score_8=_localized(
            (
                "Är sannolikt intresserad av att stötta andra och trivs troligtvis med "
                "att hjälpa andra att utvecklas."
            ),
            (
                "Is likely to be interested in supporting others and probably enjoys "
                "helping others develop."
            )
        ),
        score_9_10=_localized(
            (
                "Är genuint intresserad av att stötta andra och trivs med att hjälpa "
                "andra att utvecklas."
            ),
            (
                "Is genuinely interested in supporting others and enjoys helping others "
                "develop."
            )
        ),
    ),
    "Helpfulness": _indicator(
        label_sv="Hjälpsamhet",
        label_en="Helpfulness",
        score_1_2=_localized(
            "Lägger hellre tid på annat än på att stötta och hjälpa andra.",
            (
                "Prefers spending time on other things rather than supporting and "
                "helping others."
            )
        ),
        score_3=_localized(
            "Lägger troligtvis inte alltför mycket tid på att stötta andra.",
            "Probably does not spend a great deal of time supporting others."
        ),
        score_4_7=_localized(
            "Är förmodligen lika stöttande och hjälpsam mot andra som de flesta.",
            (
                "Is probably about as supportive and helpful towards others as most "
                "people."
            )
        ),
        score_8=_localized(
            (
                "Hjälper sannolikt andra och anstränger sig troligen för att uppfylla "
                "allas behov."
            ),
            (
                "Is likely to help others and probably makes an effort to meet "
                "everyone's needs."
            )
        ),
        score_9_10=_localized(
            "Hjälper andra och anstränger sig för att uppfylla allas behov.",
            "Helps others and makes an effort to meet everyone's needs."
        ),
    ),
    "Considerate": _indicator(
        label_sv="Omtänksam",
        label_en="Considerate",
        score_1_2=_localized(
            (
                "Fokuserar mer på sina egna uppgifter och blir inte distraherad av "
                "andra människors problem."
            ),
            (
                "Focuses more on their own tasks and is not distracted by other "
                "people's problems."
            )
        ),
        score_3=_localized(
            (
                "Fokuserar sannolikt mer på sina uppgifter och blir nog inte lätt "
                "distraherad av andra människors problem."
            ),
            (
                "Is likely to focus more on their own tasks and is probably not easily "
                "distracted by other people's problems."
            )
        ),
        score_4_7=_localized(
            (
                "Växlar förmodligen mellan att fokusera på sina egna uppgifter och att "
                "tänka på hur andra kan behöva hjälp och stöd."
            ),
            (
                "Probably alternates between focusing on their own tasks and "
                "considering how others may need help and support."
            )
        ),
        score_8=_localized(
            (
                "Lägger troligtvis tid på att fundera på hur andra kan bli stöttade och "
                "få hjälp på bästa sätt."
            ),
            (
                "Probably spends time considering how others can best be supported and "
                "helped."
            )
        ),
        score_9_10=_localized(
            (
                "Lägger mycket tid på att fundera på hur andra kan bli stöttade och få "
                "hjälp på bästa sätt."
            ),
            (
                "Spends a great deal of time considering how others can best be "
                "supported and helped."
            )
        ),
    ),

    # Connecting
    "Open Communication": _indicator(
        label_sv="Öppen kommunikation",
        label_en="Open Communication",
        score_1_2=_localized(
            "Hen är mer bekväm med att kommunicera med likasinnade personer.",
            "Is more comfortable communicating with like-minded people."
        ),
        score_3=_localized(
            "Hen föredrar förmodligen att kommunicera med likasinnade personer.",
            "Probably prefers communicating with like-minded people."
        ),
        score_4_7=_localized(
            (
                "Huruvida hen nätverkar med sin betrodda grupp och nya människor är "
                "sannolikt situationsbaserat."
            ),
            (
                "Whether they network within their trusted group or with new people is "
                "likely to depend on the situation."
            )
        ),
        score_8=_localized(
            (
                "Det kommer troligtvis naturligt för hen att kommunicera med olika "
                "typer av personer."
            ),
            (
                "Communicating with different types of people is likely to come "
                "naturally to them."
            )
        ),
        score_9_10=_localized(
            "Det är lätt för hen att kommunicera med många olika typer av personer.",
            "Finds it easy to communicate with many different types of people."
        ),
    ),
    "Building Networks": _indicator(
        label_sv="Skapa nätverk",
        label_en="Building Networks",
        score_1_2=_localized(
            (
                "Fokuserar främst på att vårda kontakten med en nära och betrodd grupp "
                "människor."
            ),
            (
                "Focuses mainly on maintaining contact with a close and trusted group "
                "of people."
            )
        ),
        score_3=_localized(
            (
                "Fokuserar troligen på att vårda kontakten med en nära och betrodd "
                "grupp människor, framför att utöka sitt nätverk."
            ),
            (
                "Is likely to focus on maintaining contact with a close and trusted "
                "group of people rather than expanding their network."
            )
        ),
        score_4_7=_localized(
            (
                "Vårdar troligen kontakten med en nära och betrodd grupp människor, och "
                "kan sannolikt nätverka strategiskt när det behövs."
            ),
            (
                "Is likely to maintain contact with a close and trusted group of people "
                "and can probably network strategically when needed."
            )
        ),
        score_8=_localized(
            (
                "Hen nätverkar sannolikt strategiskt och vårdar troligtvis dessa "
                "kontakter kontinuerligt."
            ),
            (
                "Is likely to network strategically and probably maintains these "
                "contacts continuously."
            )
        ),
        score_9_10=_localized(
            (
                "Det kommer naturligt för hen att nätverka strategiskt och att "
                "kontinuerligt vårda befintliga kontakter."
            ),
            (
                "Networking strategically and continuously maintaining existing "
                "contacts comes naturally to them."
            )
        ),
    ),
    "Initiating Contact": _indicator(
        label_sv="Ta kontakt",
        label_en="Initiating Contact",
        score_1_2=_localized(
            "Upplever det utmanande att ta kontakt med nya personer.",
            "Finds it challenging to make contact with new people."
        ),
        score_3=_localized(
            (
                "Känner sig troligtvis mindre bekväm med att ta kontakt med nya "
                "personer, men kan förmodligen göra det om det verkligen behövs."
            ),
            (
                "Is likely to feel less comfortable making contact with new people, but "
                "can probably do so when it is genuinely necessary."
            )
        ),
        score_4_7=_localized(
            (
                "Det är troligtvis situationsbaserat hur bekväm hen känner sig med att "
                "ta kontakt med nya personer."
            ),
            (
                "How comfortable they feel making contact with new people is likely to "
                "depend on the situation."
            )
        ),
        score_8=_localized(
            "Känner sig sannolikt bekväm med att ta kontakt med nya personer.",
            "Is likely to feel comfortable making contact with new people."
        ),
        score_9_10=_localized(
            "Att ta kontakt med nya personer kommer mycket naturligt.",
            "Making contact with new people comes very naturally."
        ),
    ),

    # Dynamic
    "Energetic": _indicator(
        label_sv="Energisk",
        label_en="Energetic",
        score_1_2=_localized(
            (
                "Föredrar ett lugnt tempo och upplever det energikrävande att ta på sig "
                "många uppgifter på en och samma gång."
            ),
            (
                "Prefers a calm pace and finds taking on many tasks at the same time "
                "draining."
            )
        ),
        score_3=_localized(
            (
                "Föredrar troligtvis ett lugnare tempo där det ges möjlighet att "
                "fokusera på en sak i taget."
            ),
            (
                "Probably prefers a calmer pace that allows them to focus on one thing "
                "at a time."
            )
        ),
        score_4_7=_localized(
            (
                "Föredrar troligtvis en balans mellan ett jämnare tempo och att aktivt "
                "söka nya uppgifter och utmaningar."
            ),
            (
                "Probably prefers a balance between a steady pace and actively seeking "
                "new tasks and challenges."
            )
        ),
        score_8=_localized(
            (
                "Trivs sannolikt i miljöer med högt tempo och söker troligen aktivt "
                "efter nya utmaningar och uppgifter att ta på sig."
            ),
            (
                "Is likely to thrive in fast-paced environments and probably actively "
                "seeks new challenges and tasks to take on."
            )
        ),
        score_9_10=_localized(
            (
                "Trivs i miljöer med högt tempo och söker aktivt efter nya utmaningar "
                "och uppgifter att ta på sig."
            ),
            (
                "Thrives in fast-paced environments and actively seeks new challenges "
                "and tasks to take on."
            )
        ),
    ),
    "Enthusiastic": _indicator(
        label_sv="Entusiastisk",
        label_en="Enthusiastic",
        score_1_2=_localized(
            (
                "Är mycket eftertänksam innan hen agerar och har en mer hänsynsfull "
                "inställning."
            ),
            "Is very thoughtful before acting and takes a more considerate approach."
        ),
        score_3=_localized(
            (
                "Är sannolikt eftertänksam innan hen agerar och har troligen en mer "
                "hänsynsfull inställning."
            ),
            (
                "Is likely to be thoughtful before acting and probably takes a more "
                "considerate approach."
            )
        ),
        score_4_7=_localized(
            (
                "Det är situationsberoende hur entusiastisk eller hänsynsfull hen är "
                "innan hen agerar."
            ),
            (
                "How enthusiastic or considerate they are before acting depends on the "
                "situation."
            )
        ),
        score_8=_localized(
            "Hen är sannolikt entusiastisk och snabb i att agera.",
            "Is likely to be enthusiastic and quick to act."
        ),
        score_9_10=_localized(
            "Hen är entusiastisk och snabb i att agera.",
            "Is enthusiastic and quick to act."
        ),
    ),
    "Risk Appetite": _indicator(
        label_sv="Riskaptit",
        label_en="Risk Appetite",
        score_1_2=_localized(
            (
                "Tar noga hänsyn till olika alternativ inför beslut och undviker risk "
                "om det inte är absolut nödvändigt."
            ),
            (
                "Carefully considers different options before making decisions and "
                "avoids risk unless it is absolutely necessary."
            )
        ),
        score_3=_localized(
            "Föredrar att ta hänsyn till olika alternativ inför beslut.",
            "Prefers to consider different options before making decisions."
        ),
        score_4_7=_localized(
            (
                "Gör en avvägning mellan att snabbt fatta beslut och att överväga olika "
                "alternativ inför mer avgörande beslut."
            ),
            (
                "Balances making decisions quickly with considering different options "
                "before more significant decisions."
            )
        ),
        score_8=_localized(
            (
                "Hen fattar förmodligen beslut snabbt utan att veta utfallet och är "
                "troligen bekväm med att ta risker."
            ),
            (
                "Probably makes decisions quickly without knowing the outcome and is "
                "likely to be comfortable taking risks."
            )
        ),
        score_9_10=_localized(
            "Hen fattar beslut snabbt utan att veta utfallet och tar gärna risker.",
            (
                "Makes decisions quickly without knowing the outcome and readily takes "
                "risks."
            )
        ),
    ),

    # Influential
    "Persuading": _indicator(
        label_sv="Övertygande",
        label_en="Persuading",
        score_1_2=_localized(
            (
                "Är obekväm med att behöva övertyga andra för att få dem att hålla med "
                "om sin åsikt eller perspektiv."
            ),
            (
                "Is uncomfortable having to persuade others to agree with their view or "
                "perspective."
            )
        ),
        score_3=_localized(
            (
                "Kan vara obekväm med att behöva övertyga andra för att få dem att "
                "hålla med om sin åsikt eller perspektiv."
            ),
            (
                "May be uncomfortable having to persuade others to agree with their "
                "view or perspective."
            )
        ),
        score_4_7=_localized(
            (
                "Det är situationsberoende hur bekväm personen är med att övertyga "
                "andra om sin åsikt eller perspektiv."
            ),
            (
                "How comfortable they are persuading others of their view or "
                "perspective depends on the situation."
            )
        ),
        score_8=_localized(
            (
                "Hen gillar troligen att övertyga andra och är sannolikt bekväm med att "
                "påverka andra."
            ),
            (
                "Probably enjoys persuading others and is likely to be comfortable "
                "influencing them."
            )
        ),
        score_9_10=_localized(
            (
                "Hen gillar att övertyga andra och är mycket bekväm med att påverka "
                "andra."
            ),
            "Enjoys persuading others and is very comfortable influencing them."
        ),
    ),
    "Desire to Lead": _indicator(
        label_sv="Viljan att leda andra",
        label_en="Desire to Lead",
        score_1_2=_localized(
            (
                "Föredrar att följa instruktioner istället för att ta ledningen i en "
                "grupp."
            ),
            "Prefers following instructions rather than taking the lead in a group."
        ),
        score_3=_localized(
            (
                "Föredrar sannolikt att följa instruktioner istället för att ta "
                "ledningen i en grupp."
            ),
            (
                "Is likely to prefer following instructions rather than taking the lead "
                "in a group."
            )
        ),
        score_4_7=_localized(
            (
                "Är bekväm med att ta ledningen i situationer där hen känner sig säker "
                "eller trygg."
            ),
            (
                "Is comfortable taking the lead in situations where they feel confident "
                "or secure."
            )
        ),
        score_8=_localized(
            (
                "Gillar sannolikt att ta befälet och är bekväm med att ta ledningen i "
                "de flesta situationer."
            ),
            (
                "Probably enjoys taking charge and is comfortable taking the lead in "
                "most situations."
            )
        ),
        score_9_10=_localized(
            "Föredrar att ta befälet och att leda andra.",
            "Prefers taking charge and leading others."
        ),
    ),
    "Assertive": _indicator(
        label_sv="Bestämd",
        label_en="Assertive",
        score_1_2=_localized(
            "Är obekväm med att framhäva sin åsikt eller sitt perspektiv.",
            "Is uncomfortable emphasising their view or perspective."
        ),
        score_3=_localized(
            (
                "Kommer troligen att vara mer obekväm med att framhäva sin åsikt, "
                "särskilt om man inte blivit ombedd att ge sitt perspektiv."
            ),
            (
                "Is likely to be more uncomfortable emphasising their view, "
                "particularly when they have not been asked to share their perspective."
            )
        ),
        score_4_7=_localized(
            (
                "Kan vara bekväm med att uttrycka sin åsikt, men anstränger sig "
                "förmodligen inte för att lägga fram åsikter som skiljer sig från "
                "andras."
            ),
            (
                "May be comfortable expressing their view, but probably does not make "
                "an effort to put forward views that differ from those of others."
            )
        ),
        score_8=_localized(
            (
                "Har sannolikt ett självsäkert och bestämt tillvägagångssätt, särskilt "
                "när det gäller att uttrycka sina åsikter."
            ),
            (
                "Is likely to take a confident and assertive approach, particularly "
                "when expressing their views."
            )
        ),
        score_9_10=_localized(
            (
                "Har ett självsäkert och bestämt tillvägagångssätt, särskilt när det "
                "gäller att uttrycka sina åsikter."
            ),
            (
                "Takes a confident and assertive approach, particularly when expressing "
                "their views."
            )
        ),
    ),

    # Goal-focused
    "Competitive": _indicator(
        label_sv="Tävlingsinriktad",
        label_en="Competitive",
        score_1_2=_localized(
            (
                "Ogillar att konkurrera med andra och undviker helst situationer som "
                "innefattar tävling."
            ),
            (
                "Dislikes competing with others and prefers to avoid situations "
                "involving competition."
            )
        ),
        score_3=_localized(
            (
                "Ogillar troligen att konkurrera med andra och är sannolikt "
                "ointresserad av situationer som innefattar tävling."
            ),
            (
                "Is likely to dislike competing with others and is probably "
                "uninterested in situations involving competition."
            )
        ),
        score_4_7=_localized(
            (
                "Kan vara bekväm med att konkurrera med andra och är intresserad av "
                "vissa tävlingssituationer."
            ),
            (
                "May be comfortable competing with others and finds some competitive "
                "situations interesting."
            )
        ),
        score_8=_localized(
            (
                "Har troligen en viss segervilja och trivs sannolikt i "
                "tävlingssammanhang."
            ),
            (
                "Probably has a degree of determination to win and is likely to thrive "
                "in competitive situations."
            )
        ),
        score_9_10=_localized(
            "Har en tydlig segervilja och trivs i tävlingssammanhang.",
            "Has a clear determination to win and thrives in competitive situations."
        ),
    ),
    "Challenge": _indicator(
        label_sv="Utmaning",
        label_en="Challenge",
        score_1_2=_localized(
            (
                "Föredrar att ta det som det kommer istället för att vara överdrivet "
                "angelägen om att uppnå särskilda mål."
            ),
            (
                "Prefers taking things as they come rather than being overly concerned "
                "with achieving specific goals."
            )
        ),
        score_3=_localized(
            (
                "Föredrar sannolikt att ta det som det kommer istället för att vara "
                "överdrivet angelägen om att uppnå särskilda mål."
            ),
            (
                "Is likely to prefer taking things as they come rather than being "
                "overly concerned with achieving specific goals."
            )
        ),
        score_4_7=_localized(
            (
                "Har förmågan att hitta en bra balans mellan att vilja uppnå mål och ta "
                "saker som de kommer."
            ),
            (
                "Is able to strike a good balance between wanting to achieve goals and "
                "taking things as they come."
            )
        ),
        score_8=_localized(
            (
                "Hen motiveras troligen av att lyckas och har sannolikt fokus på sina "
                "mål även när motgångar uppstår."
            ),
            (
                "Is probably motivated by succeeding and is likely to remain focused on "
                "their goals even when setbacks occur."
            )
        ),
        score_9_10=_localized(
            (
                "Hen motiveras av att lyckas och behåller därför fokus på sina mål även "
                "när motgångar uppstår."
            ),
            (
                "Is motivated by succeeding and therefore remains focused on their "
                "goals even when setbacks occur."
            )
        ),
    ),
    "Self-Discipline": _indicator(
        label_sv="Självdisciplin",
        label_en="Self-Discipline",
        score_1_2=_localized(
            (
                "Blir lätt distraherad från vad hen har för avsikt att uppnå, särskilt "
                "om intresse för målet saknas."
            ),
            (
                "Is easily distracted from what they intend to achieve, particularly "
                "when they lack interest in the goal."
            )
        ),
        score_3=_localized(
            (
                "Blir troligen lätt distraherad från vad hen har för avsikt att uppnå, "
                "särskilt om intresse för målet saknas."
            ),
            (
                "Is likely to be easily distracted from what they intend to achieve, "
                "particularly when they lack interest in the goal."
            )
        ),
        score_4_7=_localized(
            (
                "Kommer sannolikt att ha disciplin att uppnå ett begränsat antal "
                "prioriterade mål."
            ),
            (
                "Is likely to have the discipline to achieve a limited number of "
                "prioritised goals."
            )
        ),
        score_8=_localized(
            (
                "Blir sannolikt inte distraherad oavsett uppgift, utan är troligen "
                "disciplinerad när det kommer till att uppnå uppsatta mål."
            ),
            (
                "Is unlikely to be distracted regardless of the task and is probably "
                "disciplined when it comes to achieving set goals."
            )
        ),
        score_9_10=_localized(
            (
                "Blir inte distraherad oavsett uppgift, utan är disciplinerad när det "
                "kommer till att uppnå uppsatta mål."
            ),
            (
                "Is not distracted regardless of the task and is disciplined when it "
                "comes to achieving set goals."
            )
        ),
    ),

    # Structured
    "Planning and Organising": _indicator(
        label_sv="Planering och organisering",
        label_en="Planning and Organising",
        score_1_2=_localized(
            (
                "Föredrar ett flexibelt förhållningssätt framför att planera uppgifter "
                "i förväg."
            ),
            "Prefers a flexible approach rather than planning tasks in advance."
        ),
        score_3=_localized(
            (
                "Föredrar troligen ett mer flexibelt förhållningssätt framför att "
                "planera uppgifter i förväg."
            ),
            (
                "Is likely to prefer a more flexible approach rather than planning "
                "tasks in advance."
            )
        ),
        score_4_7=_localized(
            (
                "Gör en avvägning mellan att noga planera sina uppgifter och att ha ett "
                "flexibelt förhållningssätt."
            ),
            "Balances carefully planning their tasks with taking a flexible approach."
        ),
        score_8=_localized(
            (
                "Hen är sannolikt noggrann med att planera och strukturera sina "
                "uppgifter."
            ),
            "Is likely to plan and structure their tasks carefully."
        ),
        score_9_10=_localized(
            "Planerar och strukturerar sina uppgifter noggrant.",
            "Plans and structures their tasks carefully."
        ),
    ),
    "Attention to Detail": _indicator(
        label_sv="Känsla för detaljer",
        label_en="Attention to Detail",
        score_1_2=_localized(
            "Upplever det energikrävande att fokusera på detaljer.",
            "Finds focusing on details draining."
        ),
        score_3=_localized(
            "Upplever det sannolikt mer energikrävande att fokusera på detaljer.",
            "Is likely to find focusing on details more draining."
        ),
        score_4_7=_localized(
            (
                "Gör en avvägning mellan när det krävs att fokusera noggrant på "
                "detaljer och när det inte gör det."
            ),
            (
                "Balances situations that require careful attention to detail with "
                "those that do not."
            )
        ),
        score_8=_localized(
            (
                "Har sannolikt sinne för detaljer och föredrar att arbetet blir utfört "
                "med hög noggrannhet och kvalitet."
            ),
            (
                "Is likely to have an eye for detail and prefers work to be completed "
                "with a high level of accuracy and quality."
            )
        ),
        score_9_10=_localized(
            (
                "Har sinne för detaljer och ser till att arbetet blir utfört med hög "
                "noggrannhet och kvalitet."
            ),
            (
                "Has an eye for detail and ensures that work is completed with a high "
                "level of accuracy and quality."
            )
        ),
    ),
    "Keeping Promises": _indicator(
        label_sv="Hålla löften",
        label_en="Keeping Promises",
        score_1_2=_localized(
            "Är tolerant när det gäller mindre misstag eller ändringar i tidsplaner.",
            "Is tolerant of minor mistakes or changes to schedules."
        ),
        score_3=_localized(
            (
                "Är sannolikt tolerant när det gäller mindre misstag eller ändringar i "
                "tidsplaner."
            ),
            "Is likely to be tolerant of minor mistakes or changes to schedules."
        ),
        score_4_7=_localized(
            (
                "Försöker hålla det hen lovar när det är möjligt och kan godta mindre "
                "misstag eller förändringar i tidsplaner beroende på uppgiften."
            ),
            (
                "Tries to keep their promises when possible and may accept minor "
                "mistakes or changes to schedules depending on the task."
            )
        ),
        score_8=_localized(
            (
                "Anstränger sig sannolikt för att hålla det hen lovar och är mindre "
                "tolerant mot misstag och förändrade tidsplaner."
            ),
            (
                "Is likely to make an effort to keep their promises and is less "
                "tolerant of mistakes and changed schedules."
            )
        ),
        score_9_10=_localized(
            (
                "Gör sitt yttersta för att hålla det hen lovar och har låg tolerans mot "
                "misstag och förändrade tidsplaner."
            ),
            (
                "Does their utmost to keep their promises and has low tolerance for "
                "mistakes and changed schedules."
            )
        ),
    ),

    # Analytical
    "Data Focus": _indicator(
        label_sv="Datafokus",
        label_en="Data Focus",
        score_1_2=_localized(
            (
                "Är mindre intresserad av data och statistik och finner det "
                "energikrävande att ha stort fokus på detta."
            ),
            (
                "Is less interested in data and statistics and finds placing a strong "
                "focus on them draining."
            )
        ),
        score_3=_localized(
            (
                "Är sannolikt mindre intresserad av data och statistik och kan finna "
                "det energikrävande att ha stort fokus på detta."
            ),
            (
                "Is likely to be less interested in data and statistics and may find "
                "placing a strong focus on them draining."
            )
        ),
        score_4_7=_localized(
            (
                "Gör en avvägning mellan att använda ett intuitivt eller datadrivet "
                "tillvägagångssätt för att lösa problem."
            ),
            (
                "Balances using an intuitive and a data-driven approach to solving "
                "problems."
            )
        ),
        score_8=_localized(
            (
                "Har troligen ett datadrivet förhållningssätt, och ser sannolikt "
                "statistik och data som nyckeln till att lösa problem."
            ),
            (
                "Probably takes a data-driven approach and is likely to regard "
                "statistics and data as key to solving problems."
            )
        ),
        score_9_10=_localized(
            (
                "Har ett datadrivet förhållningssätt, och ser statistik och data som "
                "nyckeln till att lösa problem."
            ),
            (
                "Takes a data-driven approach and regards statistics and data as key to "
                "solving problems."
            )
        ),
    ),
    "Evaluating": _indicator(
        label_sv="Utvärderar",
        label_en="Evaluating",
        score_1_2=_localized(
            (
                "Är mindre intresserad av uppgifter som kräver kritisk utvärdering och "
                "granskning."
            ),
            "Is less interested in tasks that require critical evaluation and review."
        ),
        score_3=_localized(
            (
                "Är troligen mindre intresserad av uppgifter som kräver kritisk "
                "utvärdering och granskning."
            ),
            (
                "Is probably less interested in tasks that require critical evaluation "
                "and review."
            )
        ),
        score_4_7=_localized(
            (
                "Är relativt intresserad av att utvärdera situationer på ett kritiskt "
                "granskande sätt."
            ),
            (
                "Is relatively interested in evaluating situations in a critical and "
                "reviewing manner."
            )
        ),
        score_8=_localized(
            (
                "Föredrar sannolikt att utvärdera situationer på ett kritiskt "
                "granskande sätt."
            ),
            (
                "Is likely to prefer evaluating situations in a critical and reviewing "
                "manner."
            )
        ),
        score_9_10=_localized(
            "Föredrar att utvärdera situationer på ett kritiskt granskande sätt.",
            "Prefers evaluating situations in a critical and reviewing manner."
        ),
    ),
    "Analysing Problems": _indicator(
        label_sv="Problemanalys",
        label_en="Analysing Problems",
        score_1_2=_localized(
            (
                "Har ett mer intuitivt tillvägagångssätt för att lösa problem, snarare "
                "än att fokusera på statistik eller data."
            ),
            (
                "Takes a more intuitive approach to solving problems rather than "
                "focusing on statistics or data."
            )
        ),
        score_3=_localized(
            (
                "Har troligtvis ett mer intuitivt tillvägagångssätt för att lösa "
                "problem, snarare än att fokusera på statistik eller data."
            ),
            (
                "Is likely to take a more intuitive approach to solving problems rather "
                "than focusing on statistics or data."
            )
        ),
        score_4_7=_localized(
            (
                "Gör en avvägning mellan att använda ett intuitivt eller datadrivet "
                "tillvägagångssätt för att lösa problem."
            ),
            (
                "Balances using an intuitive and a data-driven approach to solving "
                "problems."
            )
        ),
        score_8=_localized(
            (
                "Använder sannolikt olika informationskällor och ett analytiskt "
                "tillvägagångssätt för att lösa problem."
            ),
            (
                "Is likely to use different sources of information and an analytical "
                "approach to solving problems."
            )
        ),
        score_9_10=_localized(
            (
                "Använder olika informationskällor och ett analytiskt tillvägagångssätt "
                "för att lösa problem."
            ),
            (
                "Uses different sources of information and an analytical approach to "
                "solving problems."
            )
        ),
    ),

    # Complex Thinking
    "Strategic Thinking": _indicator(
        label_sv="Strategiskt tänkande",
        label_en="Strategic Thinking",
        score_1_2=_localized(
            (
                "Föredrar att ha ett operativt fokus framför att arbeta med komplexa "
                "problem."
            ),
            (
                "Prefers having an operational focus rather than working with complex "
                "problems."
            )
        ),
        score_3=_localized(
            (
                "Föredrar sannolikt att ha ett operativt fokus framför att arbeta med "
                "komplexa problem."
            ),
            (
                "Is likely to prefer having an operational focus rather than working "
                "with complex problems."
            )
        ),
        score_4_7=_localized(
            (
                "Kan växla mellan att fokusera på komplexa problem och att fokusera på "
                "operativa detaljer beroende på situation."
            ),
            (
                "Can switch between focusing on complex problems and focusing on "
                "operational details depending on the situation."
            )
        ),
        score_8=_localized(
            "Denna individ gillar sannolikt att hitta lösningar på komplexa problem.",
            "Is likely to enjoy finding solutions to complex problems."
        ),
        score_9_10=_localized(
            "Denna individ gillar verkligen att hitta lösningar på komplexa problem.",
            "Genuinely enjoys finding solutions to complex problems."
        ),
    ),
    "Conceptual": _indicator(
        label_sv="Konceptuell",
        label_en="Conceptual",
        score_1_2=_localized(
            (
                "Föredrar att arbeta med praktiska detaljer i en situation, snarare än "
                "att utforska de konceptuella aspekterna."
            ),
            (
                "Prefers working with practical details in a situation rather than "
                "exploring its conceptual aspects."
            )
        ),
        score_3=_localized(
            (
                "Föredrar troligen att arbeta med praktiska detaljer i en situation, "
                "snarare än att utforska de konceptuella aspekterna."
            ),
            (
                "Is likely to prefer working with practical details in a situation "
                "rather than exploring its conceptual aspects."
            )
        ),
        score_4_7=_localized(
            (
                "Är bekväm med att utforska både konceptuella aspekter och operativa "
                "detaljer, beroende på situation."
            ),
            (
                "Is comfortable exploring both conceptual aspects and operational "
                "details, depending on the situation."
            )
        ),
        score_8=_localized(
            (
                "Gillar sannolikt ett konceptuellt tillvägagångssätt och "
                "helhetsperspektiv vid komplex problemlösning, snarare än att fokusera "
                "på operativa detaljer."
            ),
            (
                "Is likely to enjoy taking a conceptual approach and a broad "
                "perspective when solving complex problems rather than focusing on "
                "operational details."
            )
        ),
        score_9_10=_localized(
            (
                "Föredrar ett konceptuellt tillvägagångssätt och helhetsperspektiv vid "
                "komplex problemlösning, snarare än att fokusera på operativa detaljer."
            ),
            (
                "Prefers taking a conceptual approach and a broad perspective when "
                "solving complex problems rather than focusing on operational details."
            )
        ),
    ),
    "Curiosity": _indicator(
        label_sv="Nyfikenhet",
        label_en="Curiosity",
        score_1_2=_localized(
            (
                "Upplever det energikrävande att behöva lära sig om nya arbetssätt och "
                "metoder."
            ),
            "Finds having to learn about new ways of working and methods draining."
        ),
        score_3=_localized(
            (
                "Upplever det troligtvis energikrävande att behöva lära sig om nya "
                "arbetssätt och metoder."
            ),
            (
                "Is likely to find having to learn about new ways of working and "
                "methods draining."
            )
        ),
        score_4_7=_localized(
            (
                "Är relativt öppen och nyfiken på att lära sig nya arbetssätt och "
                "metoder."
            ),
            (
                "Is relatively open and curious about learning new ways of working and "
                "methods."
            )
        ),
        score_8=_localized(
            (
                "Är nyfiken och söker sannolikt upp möjligheter att lära sig om nya "
                "arbetssätt och metoder."
            ),
            (
                "Is curious and is likely to seek opportunities to learn about new ways "
                "of working and methods."
            )
        ),
        score_9_10=_localized(
            (
                "Är nyfiken och söker aktivt upp möjligheter att lära sig om nya "
                "arbetssätt och metoder."
            ),
            (
                "Is curious and actively seeks opportunities to learn about new ways of "
                "working and methods."
            )
        ),
    ),

    # Creativity
    "Innovating": _indicator(
        label_sv="Innovation",
        label_en="Innovating",
        score_1_2=_localized(
            (
                "Föredrar beprövade och bekanta metoder för att lösa problem, snarare "
                "än att utforska nya eller innovativa tillvägagångssätt."
            ),
            (
                "Prefers tried-and-tested and familiar methods for solving problems "
                "rather than exploring new or innovative approaches."
            )
        ),
        score_3=_localized(
            (
                "Föredrar troligen beprövade och bekanta metoder för att lösa problem, "
                "snarare än att utforska nya eller innovativa tillvägagångssätt."
            ),
            (
                "Is likely to prefer tried-and-tested and familiar methods for solving "
                "problems rather than exploring new or innovative approaches."
            )
        ),
        score_4_7=_localized(
            (
                "Har troligtvis en balans mellan att använda beprövade metoder och "
                "innovativa tillvägagångssätt vid problemlösning."
            ),
            (
                "Is likely to balance using tried-and-tested methods with innovative "
                "approaches to problem-solving."
            )
        ),
        score_8=_localized(
            (
                "Gillar sannolikt att hitta innovativa lösningar, och är troligen "
                "bekväm med att använda nya tillvägagångssätt vid problemlösning."
            ),
            (
                "Is likely to enjoy finding innovative solutions and is probably "
                "comfortable using new approaches to problem-solving."
            )
        ),
        score_9_10=_localized(
            (
                "Föredrar att hitta innovativa lösningar, framför att använda "
                "befintliga metoder, och är bekväm med att använda helt nya "
                "tillvägagångssätt vid problemlösning."
            ),
            (
                "Prefers finding innovative solutions rather than using existing "
                "methods and is comfortable using entirely new approaches to "
                "problem-solving."
            )
        ),
    ),
    "Generating Ideas": _indicator(
        label_sv="Idéskapande",
        label_en="Generating Ideas",
        score_1_2=_localized(
            (
                "Upplever det utmanande att komma på nya idéer eller lösningar, och "
                "undviker helst situationer som kräver idégenerering."
            ),
            (
                "Finds it challenging to come up with new ideas or solutions and "
                "prefers to avoid situations that require idea generation."
            )
        ),
        score_3=_localized(
            (
                "Kan sannolikt uppleva det utmanande att komma på nya idéer eller "
                "lösningar, och undviker troligen situationer som kräver idégenerering."
            ),
            (
                "May find it challenging to come up with new ideas or solutions and is "
                "likely to avoid situations that require idea generation."
            )
        ),
        score_4_7=_localized(
            (
                "Kan vara bekväm med att generera nya idéer eller lösningar, men söker "
                "sig nödvändigtvis inte aktivt till sådana situationer."
            ),
            (
                "May be comfortable generating new ideas or solutions but does not "
                "necessarily seek out such situations actively."
            )
        ),
        score_8=_localized(
            (
                "Gillar sannolikt att generera idéer och komma på kreativa lösningar "
                "till problem."
            ),
            (
                "Is likely to enjoy generating ideas and coming up with creative "
                "solutions to problems."
            )
        ),
        score_9_10=_localized(
            "Gillar att generera idéer och komma på kreativa lösningar till problem.",
            (
                "Enjoys generating ideas and coming up with creative solutions to "
                "problems."
            )
        ),
    ),
    "Experimenting": _indicator(
        label_sv="Experimentförmåga",
        label_en="Experimenting",
        score_1_2=_localized(
            (
                "Använder hellre beprövade och befintliga metoder, snarare än att "
                "experimentera med nya arbetssätt."
            ),
            (
                "Prefers using tried-and-tested and existing methods rather than "
                "experimenting with new ways of working."
            )
        ),
        score_3=_localized(
            (
                "Använder sannolikt hellre beprövade och befintliga metoder, snarare än "
                "att experimentera med nya arbetssätt."
            ),
            (
                "Is likely to prefer using tried-and-tested and existing methods rather "
                "than experimenting with new ways of working."
            )
        ),
        score_4_7=_localized(
            (
                "Är troligen lika bekväm med att använda befintliga metoder som att "
                "testa nya arbetssätt, beroende på situation."
            ),
            (
                "Is likely to be equally comfortable using existing methods and testing "
                "new ways of working, depending on the situation."
            )
        ),
        score_8=_localized(
            "Gillar troligen att experimentera och testa nya sätt att arbeta på.",
            "Is likely to enjoy experimenting and testing new ways of working."
        ),
        score_9_10=_localized(
            "Gillar att experimentera och testa nya sätt att arbeta på.",
            "Enjoys experimenting and testing new ways of working."
        ),
    ),

    # Adaptability
    "Adapting to Change": _indicator(
        label_sv="Förändringsanpassning",
        label_en="Adapting to Change",
        score_1_2=_localized(
            (
                "Upplever förändringar som utmanande och det kan ta tid att anpassa sig "
                "till nya situationer."
            ),
            "Finds change challenging and may take time to adapt to new situations."
        ),
        score_3=_localized(
            (
                "Upplever troligen förändringar som utmanande och det kan eventuellt ta "
                "tid att anpassa sig till nya situationer."
            ),
            (
                "Is likely to find change challenging and may possibly take time to "
                "adapt to new situations."
            )
        ),
        score_4_7=_localized(
            (
                "Anpassar sig till nya situationer och förändringar lika väl som de "
                "flesta andra."
            ),
            "Adapts to new situations and changes about as well as most people."
        ),
        score_8=_localized(
            (
                "Gillar sannolikt förändringar och anpassar sig troligen snabbare till "
                "nya situationer."
            ),
            (
                "Is likely to enjoy change and probably adapts more quickly to new "
                "situations."
            )
        ),
        score_9_10=_localized(
            "Gillar förändringar och anpassar sig snabbt till nya situationer.",
            "Enjoys change and adapts quickly to new situations."
        ),
    ),
    "Flexible": _indicator(
        label_sv="Flexibel",
        label_en="Flexible",
        score_1_2=_localized(
            (
                "Har en bestämd uppfattning och synsätt i de flesta situationer, och "
                "visar ointresse för andra perspektiv."
            ),
            (
                "Has a fixed view and approach in most situations and shows little "
                "interest in other perspectives."
            )
        ),
        score_3=_localized(
            (
                "Har sannolikt en bestämd uppfattning och synsätt i flera situationer, "
                "och kan troligen vara ointresserad av andra perspektiv."
            ),
            (
                "Is likely to have a fixed view and approach in several situations and "
                "may be uninterested in other perspectives."
            )
        ),
        score_4_7=_localized(
            (
                "Huruvida personen har ett öppet eller bestämt synsätt beror på "
                "situationen."
            ),
            "Whether they take an open or fixed approach depends on the situation."
        ),
        score_8=_localized(
            (
                "Har sannolikt ett flexibelt förhållningssätt vid nya situationer och "
                "ändrar förmodligen enkelt sitt synsätt vid ny information och "
                "perspektiv."
            ),
            (
                "Is likely to take a flexible approach in new situations and probably "
                "changes their view easily when presented with new information and "
                "perspectives."
            )
        ),
        score_9_10=_localized(
            (
                "Har ett flexibelt förhållningssätt vid nya situationer och ändrar "
                "enkelt sitt synsätt vid ny information och perspektiv."
            ),
            (
                "Takes a flexible approach in new situations and changes their view "
                "easily when presented with new information and perspectives."
            )
        ),
    ),
    "Variety": _indicator(
        label_sv="Variation",
        label_en="Variety",
        score_1_2=_localized(
            (
                "Föredrar ett förutsägbart och rutinmässigt arbetssätt, och kan uppleva "
                "oförutsägbarhet som energikrävande."
            ),
            (
                "Prefers a predictable and routine way of working and may find "
                "unpredictability draining."
            )
        ),
        score_3=_localized(
            (
                "Föredrar sannolikt ett mer förutsägbart och rutinmässigt arbetssätt, "
                "och kan troligen uppleva oförutsägbarhet som energikrävande."
            ),
            (
                "Is likely to prefer a more predictable and routine way of working and "
                "may find unpredictability draining."
            )
        ),
        score_4_7=_localized(
            (
                "Hen uppskattar troligen en balans mellan rutinartade arbetsuppgifter "
                "och variation."
            ),
            "Is likely to appreciate a balance between routine tasks and variety."
        ),
        score_8=_localized(
            (
                "Föredrar troligen variation och kan uppleva rutinmässiga uppgifter som "
                "energikrävande."
            ),
            "Is likely to prefer variety and may find routine tasks draining."
        ),
        score_9_10=_localized(
            (
                "Föredrar stor variation och upplever rutinmässiga uppgifter som "
                "energikrävande."
            ),
            "Prefers a high degree of variety and finds routine tasks draining."
        ),
    ),

    # Straightforward
    "Adhering to Rules": _indicator(
        label_sv="Regelefterlevnad",
        label_en="Adhering to Rules",
        score_1_2=_localized(
            (
                "Känner sig bekväm med att tumma på och bryta mot regler i rimlig "
                "utsträckning när det behövs för att få saker gjorda."
            ),
            (
                "Feels comfortable bending and breaking rules to a reasonable extent "
                "when needed to get things done."
            )
        ),
        score_3=_localized(
            (
                "Känner sig sannolikt bekväm med att tumma på och bryta mot regler i "
                "rimlig utsträckning när det behövs för att få saker gjorda."
            ),
            (
                "Is likely to feel comfortable bending and breaking rules to a "
                "reasonable extent when needed to get things done."
            )
        ),
        score_4_7=_localized(
            (
                "Har troligtvis en balans mellan att följa regler och riktlinjer, och "
                "att tumma på dessa i rimlig utsträckning."
            ),
            (
                "Is likely to balance following rules and guidelines with bending them "
                "to a reasonable extent."
            )
        ),
        score_8=_localized(
            (
                "Följer sannolikt regler och riktlinjer noggrant med minimalt "
                "ifrågasättande, och är troligen ovillig att tumma på dessa."
            ),
            (
                "Is likely to follow rules and guidelines carefully with minimal "
                "questioning and is probably unwilling to bend them."
            )
        ),
        score_9_10=_localized(
            (
                "Följer regler och riktlinjer mycket noggrant utan ifrågasättande och "
                "är ovillig att tumma på dessa oavsett omständigheterna."
            ),
            (
                "Follows rules and guidelines very carefully without questioning them "
                "and is unwilling to bend them regardless of the circumstances."
            )
        ),
    ),
    "Candid": _indicator(
        label_sv="Uppriktig",
        label_en="Candid",
        score_1_2=_localized(
            (
                "Föredrar att vara indirekt och mindre rättfram i sin kommunikation när "
                "hen framför sin åsikt."
            ),
            (
                "Prefers to communicate indirectly and less straightforwardly when "
                "expressing their opinion."
            )
        ),
        score_3=_localized(
            (
                "Är troligen mer indirekt och mindre rättfram i sin kommunikation när "
                "hen framför sin åsikt."
            ),
            (
                "Is likely to communicate more indirectly and less straightforwardly "
                "when expressing their opinion."
            )
        ),
        score_4_7=_localized(
            (
                "Huruvida personen är direkt eller indirekt i sin kommunikation kring "
                "sina åsikter beror på situationen."
            ),
            (
                "Whether they communicate directly or indirectly about their opinions "
                "depends on the situation."
            )
        ),
        score_8=_localized(
            (
                "Hen kommer sannolikt att vara direkt och rättfram i sin kommunikation, "
                "och rak med sina åsikter."
            ),
            (
                "Is likely to communicate directly and straightforwardly and to be "
                "candid about their opinions."
            )
        ),
        score_9_10=_localized(
            (
                "Oberoende av situation kommer hen att vara direkt och rättfram i sin "
                "kommunikation och rak med sina åsikter."
            ),
            (
                "Communicates directly and straightforwardly and is candid about their "
                "opinions regardless of the situation."
            )
        ),
    ),
    "Earnest": _indicator(
        label_sv="Äkta",
        label_en="Earnest",
        score_1_2=_localized(
            (
                "Är bekväm med att ge komplimanger eller visa uppskattning, även när "
                "det inte helt speglar den egna uppfattningen, om det hjälper att nå "
                "ett mål. Håller tillbaka sin egentliga åsikt om andra när det bedöms "
                "vara mer ändamålsenligt."
            ),
            (
                "Is comfortable giving compliments or showing appreciation even when it "
                "does not fully reflect their own view, if doing so helps them achieve "
                "a goal. Holds back their true opinion of others when this is "
                "considered more effective."
            )
        ),
        score_3=_localized(
            (
                "Är troligen bekväm med att ge komplimanger eller visa uppskattning, "
                "även när det inte helt speglar den egna uppfattningen, om det hjälper "
                "att nå ett mål. Håller sannolikt tillbaka sin egentliga åsikt om andra "
                "när det bedöms vara mer ändamålsenligt."
            ),
            (
                "Is likely to be comfortable giving compliments or showing appreciation "
                "even when it does not fully reflect their own view, if doing so helps "
                "them achieve a goal. Is likely to hold back their true opinion of "
                "others when this is considered more effective."
            )
        ),
        score_4_7=_localized(
            (
                "Anpassar troligen hur öppet hens uppfattning om andra kommer fram i "
                "olika situationer. Uttrycker uppskattning när den känns befogad, men "
                "kan också välja att hålla tillbaka eller nyansera sina åsikter när "
                "situationen kräver det."
            ),
            (
                "Is likely to adapt how openly their view of others is expressed in "
                "different situations. Expresses appreciation when it feels warranted, "
                "but may also choose to withhold or temper their opinions when the "
                "situation calls for it."
            )
        ),
        score_8=_localized(
            (
                "Har troligen en tydlig uppfattning om andra och kan ha svårt att "
                "uttrycka uppskattning om den inte känns genuint förankrad. Är "
                "förmodligen mer rak med sina åsikter och kan ha begränsat behov av att "
                "dölja vad hen faktiskt tycker."
            ),
            (
                "Is likely to have a clear view of others and may find it difficult to "
                "express appreciation unless it feels genuinely grounded. Is probably "
                "more candid about their opinions and may have limited need to conceal "
                "what they actually think."
            )
        ),
        score_9_10=_localized(
            (
                "Har en tydlig uppfattning om andra och kan ha svårt att uttrycka "
                "uppskattning om den inte känns genuint förankrad. Är rak med sina "
                "åsikter och kan ha begränsat behov av att dölja vad hen faktiskt "
                "tycker."
            ),
            (
                "Has a clear view of others and may find it difficult to express "
                "appreciation unless it feels genuinely grounded. Is candid about their "
                "opinions and may have limited need to conceal what they actually "
                "think."
            )
        ),
    ),

    # Status Avoidance
    "Egalitarian": _indicator(
        label_sv="Jämlik",
        label_en="Egalitarian",
        score_1_2=_localized(
            (
                "Förväntar sig att andra bekräftar hens status genom att visa respekt, "
                "och att hens roll i organisationen kommer med en viss särbehandling."
            ),
            (
                "Expects others to acknowledge their status by showing respect and "
                "expects their role in the organisation to come with a degree of "
                "special treatment."
            )
        ),
        score_3=_localized(
            (
                "Uppskattar att andra bekräftar hens status genom att visa respekt, och "
                "att hens roll i organisationen kommer med en viss särbehandling."
            ),
            (
                "Appreciates others acknowledging their status by showing respect and "
                "their role in the organisation coming with a degree of special "
                "treatment."
            )
        ),
        score_4_7=_localized(
            (
                "Gillar att få bekräftelse emellanåt för sin status, men kommer "
                "troligen inte anstränga sig för att få det."
            ),
            (
                "Likes receiving occasional acknowledgement of their status but is "
                "unlikely to make an effort to obtain it."
            )
        ),
        score_8=_localized(
            (
                "Föredrar att bli behandlad på samma sätt som andra oavsett hens roll, "
                "och kan därför undvika att framhäva sin status."
            ),
            (
                "Prefers to be treated in the same way as others regardless of their "
                "role and may therefore avoid emphasising their status."
            )
        ),
        score_9_10=_localized(
            (
                "Vill bli behandlad på samma sätt som andra oavsett hens roll, och "
                "undviker därför att framhäva sin status."
            ),
            (
                "Wants to be treated in the same way as others regardless of their role "
                "and therefore avoids emphasising their status."
            )
        ),
    ),
    "Collective": _indicator(
        label_sv="Kollektiv",
        label_en="Collective",
        score_1_2=_localized(
            (
                "Vill få uppmärksamhet och erkännande för sina unika egenskaper och "
                "färdigheter."
            ),
            "Wants attention and recognition for their unique qualities and skills."
        ),
        score_3=_localized(
            (
                "Önskar troligen få uppmärksamhet och erkännande för sina unika "
                "egenskaper och färdigheter."
            ),
            (
                "Is likely to want attention and recognition for their unique qualities "
                "and skills."
            )
        ),
        score_4_7=_localized(
            (
                "Kan uppskatta uppmärksamhet för sina egenskaper och färdigheter, men "
                "anstränger sig troligen inte aktivt för att få det."
            ),
            (
                "May appreciate attention for their qualities and skills, but is "
                "unlikely to make an active effort to obtain it."
            )
        ),
        score_8=_localized(
            (
                "Föredrar att smälta in i gruppen framför att få särskild uppmärksamhet "
                "och vill helst inte att andra ska känna att de måste visa hen "
                "uppskattning."
            ),
            (
                "Prefers blending into the group rather than receiving special "
                "attention and would rather others did not feel they had to show "
                "appreciation."
            )
        ),
        score_9_10=_localized(
            (
                "Smälter helst in i gruppen framför att få särskild uppmärksamhet och "
                "vill inte att andra ska känna att de måste visa hen uppskattning."
            ),
            (
                "Prefers blending into the group rather than receiving special "
                "attention and does not want others to feel they have to show "
                "appreciation."
            )
        ),
    ),
    "Avoiding Status": _indicator(
        label_sv="Undvika status",
        label_en="Avoiding Status",
        score_1_2=_localized(
            (
                "Förväntar sig att hens status och roll erkänns och bekräftas av andra "
                "och i organisationen."
            ),
            (
                "Expects their status and role to be recognised and acknowledged by "
                "others and within the organisation."
            )
        ),
        score_3=_localized(
            (
                "Är bekväm med att hens status och roll erkänns och bekräftas av andra "
                "och i organisationen."
            ),
            (
                "Is comfortable with their status and role being recognised and "
                "acknowledged by others and within the organisation."
            )
        ),
        score_4_7=_localized(
            (
                "Gillar att hens status erkänns av andra och i organisationen, men "
                "kommer troligen inte anstränga sig extra för att få det."
            ),
            (
                "Likes their status to be recognised by others and within the "
                "organisation but is unlikely to make an extra effort to obtain this."
            )
        ),
        score_8=_localized(
            (
                "Har litet behov av att hens status uppmärksammas och anser troligen "
                "att respekt ska förtjänas, inte att det kommer automatiskt med en "
                "titel."
            ),
            (
                "Has little need for their status to receive attention and is likely to "
                "believe that respect should be earned rather than automatically coming "
                "with a title."
            )
        ),
        score_9_10=_localized(
            (
                "Har inget behov av att hens status uppmärksammas och anser att respekt "
                "ska förtjänas, inte att det kommer automatiskt med en titel."
            ),
            (
                "Has no need for their status to receive attention and believes that "
                "respect should be earned rather than automatically coming with a "
                "title."
            )
        ),
    ),

    # Modesty
    "Humble": _indicator(
        label_sv="Ödmjuk",
        label_en="Humble",
        score_1_2=_localized(
            (
                "Kan uppleva det frustrerande om hens insats går obemärkt förbi och "
                "förväntar sig att andra visar uppskattning."
            ),
            (
                "May find it frustrating when their contribution goes unnoticed and "
                "expects others to show appreciation."
            )
        ),
        score_3=_localized(
            (
                "Kan sannolikt uppleva det frustrerande om hens insats går obemärkt "
                "förbi och förväntar sig förmodligen att andra visar uppskattning."
            ),
            (
                "Is likely to find it frustrating when their contribution goes "
                "unnoticed and probably expects others to show appreciation."
            )
        ),
        score_4_7=_localized(
            (
                "Anstränger sig inte nödvändigtvis för att få uppskattning, men känner "
                "sig inte obekväm med att få detta från andra."
            ),
            (
                "Does not necessarily make an effort to receive appreciation but is not "
                "uncomfortable receiving it from others."
            )
        ),
        score_8=_localized(
            (
                "Anser sig sannolikt inte vara bättre än någon annan och förväntar sig "
                "troligen inte heller uppskattning eller specialbehandling."
            ),
            (
                "Is likely not to consider themselves better than anyone else and "
                "probably does not expect appreciation or special treatment."
            )
        ),
        score_9_10=_localized(
            (
                "Anser sig inte vara bättre än någon annan och förväntar sig inte "
                "uppskattning eller specialbehandling."
            ),
            (
                "Does not consider themselves better than anyone else and does not "
                "expect appreciation or special treatment."
            )
        ),
    ),
    "Modest": _indicator(
        label_sv="Anspråkslös",
        label_en="Modest",
        score_1_2=_localized(
            (
                "Pratar gärna om sina framgångar och mår bra när hen får uppmärksamhet "
                "för sina prestationer."
            ),
            (
                "Readily talks about their successes and feels good when they receive "
                "attention for their achievements."
            )
        ),
        score_3=_localized(
            (
                "Är bekväm med att prata om sina framgångar och att få uppmärksamhet "
                "för sina prestationer."
            ),
            (
                "Is comfortable talking about their successes and receiving attention "
                "for their achievements."
            )
        ),
        score_4_7=_localized(
            (
                "Är relativt ödmjuk när det gäller sina framgångar och vad hen har "
                "uppnått."
            ),
            "Is relatively modest about their successes and what they have achieved."
        ),
        score_8=_localized(
            (
                "Undviker helst att prata om sina framgångar, och blir troligen obekväm "
                "när hen får uppmärksamhet för sina prestationer."
            ),
            (
                "Prefers to avoid talking about their successes and is likely to feel "
                "uncomfortable when they receive attention for their achievements."
            )
        ),
        score_9_10=_localized(
            (
                "Är blygsam och undviker att prata om sina framgångar, och är obekväm "
                "när hen får uppmärksamhet för sina prestationer."
            ),
            (
                "Is modest, avoids talking about their successes, and feels "
                "uncomfortable when they receive attention for their achievements."
            )
        ),
    ),
    "Avoiding Attention": _indicator(
        label_sv="Undvika uppmärksamhet",
        label_en="Avoiding Attention",
        score_1_2=_localized(
            (
                "Trivs med att stå i centrum och föredrar att få uppmärksamhet i "
                "gruppsammanhang, snarare än att vara en i mängden."
            ),
            (
                "Enjoys being the centre of attention and prefers receiving attention "
                "in group settings rather than being one among many."
            )
        ),
        score_3=_localized(
            (
                "Är bekväm med att stå i centrum och att få uppmärksamhet i "
                "gruppsammanhang, snarare än att vara en i mängden."
            ),
            (
                "Is comfortable being the centre of attention and receiving attention "
                "in group settings rather than being one among many."
            )
        ),
        score_4_7=_localized(
            "Är lika bekväm med att vara i centrum som att vara en i mängden.",
            (
                "Is equally comfortable being the centre of attention and being one "
                "among many."
            )
        ),
        score_8=_localized(
            (
                "Undviker helst att stå i centrum och håller sig hellre i bakgrunden, "
                "för att undgå uppmärksamhet."
            ),
            (
                "Prefers to avoid being the centre of attention and would rather stay "
                "in the background to avoid attention."
            )
        ),
        score_9_10=_localized(
            (
                "Undviker att stå i centrum och håller sig gärna i bakgrunden, för att "
                "undgå uppmärksamhet."
            ),
            (
                "Avoids being the centre of attention and readily stays in the "
                "background to avoid attention."
            )
        ),
    ),

    # Resilience
    "Tough Minded": _indicator(
        label_sv="Härdad",
        label_en="Tough Minded",
        score_1_2=_localized(
            "Känslig för kritik från andra och det kan ta tid att släppa det.",
            "Is sensitive to criticism from others and may take time to let it go."
        ),
        score_3=_localized(
            (
                "Är troligen känslig för kritik från andra och det kan troligtvis ta "
                "tid att släppa den."
            ),
            (
                "Is likely to be sensitive to criticism from others and may take time "
                "to let it go."
            )
        ),
        score_4_7=_localized(
            (
                "Huruvida kritik stannar kvar eller rinner av lättare är "
                "situationsberoende."
            ),
            (
                "Whether criticism lingers or is easier to let go depends on the "
                "situation."
            )
        ),
        score_8=_localized(
            (
                "Påverkas förmodligen inte så lätt av kritik och oroar sig troligen "
                "inte för hur andra uppfattar hen."
            ),
            (
                "Is probably not easily affected by criticism and is unlikely to worry "
                "about how others perceive them."
            )
        ),
        score_9_10=_localized(
            (
                "Påverkas inte så lätt av kritik och oroar sig inte för hur andra "
                "uppfattar hen."
            ),
            (
                "Is not easily affected by criticism and does not worry about how "
                "others perceive them."
            )
        ),
    ),
    "Recovering": _indicator(
        label_sv="Återhämtningsförmåga",
        label_en="Recovering",
        score_1_2=_localized(
            (
                "Kan ta tid att komma över misstag och kan ha svårigheter att gå vidare "
                "efter en motgång."
            ),
            (
                "May take time to get over mistakes and may find it difficult to move "
                "on after a setback."
            )
        ),
        score_3=_localized(
            (
                "Tar troligtvis något mer tid att komma över misstag och kan ha vissa "
                "svårigheter att gå vidare efter en motgång."
            ),
            (
                "Is likely to take somewhat longer to get over mistakes and may have "
                "some difficulty moving on after a setback."
            )
        ),
        score_4_7=_localized(
            (
                "Återhämtar sig lika snabbt från motgångar och bakslag som de flesta "
                "andra."
            ),
            "Recovers from adversity and setbacks about as quickly as most people."
        ),
        score_8=_localized(
            (
                "Svarar troligen väl på bakslag och motgångar, och går vidare utan att "
                "övertänka."
            ),
            (
                "Is likely to respond well to setbacks and adversity and moves on "
                "without overthinking."
            )
        ),
        score_9_10=_localized(
            (
                "Svarar väl på bakslag och motgångar, och går vidare snabbt utan att "
                "övertänka."
            ),
            (
                "Responds well to setbacks and adversity and moves on quickly without "
                "overthinking."
            )
        ),
    ),
    "Optimistic": _indicator(
        label_sv="Optimistisk",
        label_en="Optimistic",
        score_1_2=_localized(
            (
                "Har en pessimistisk syn när saker och ting går snett och oroar sig för "
                "tänkbara konsekvenser."
            ),
            (
                "Takes a pessimistic view when things go wrong and worries about "
                "possible consequences."
            )
        ),
        score_3=_localized(
            (
                "Kan ha en pessimistisk syn när saker och ting går snett och är benägen "
                "att oroa sig för tänkbara konsekvenser."
            ),
            (
                "May take a pessimistic view when things go wrong and is inclined to "
                "worry about possible consequences."
            )
        ),
        score_4_7=_localized(
            (
                "Kan ofta se positiva aspekter i utmanande situationer, men väger också "
                "in möjliga hinder och konsekvenser."
            ),
            (
                "Can often see positive aspects in challenging situations while also "
                "considering possible obstacles and consequences."
            )
        ),
        score_8=_localized(
            (
                "Är förmodligen optimistisk med fokus på de positiva aspekterna i de "
                "flesta situationer, snarare än att fokusera på hinder eller det "
                "negativa."
            ),
            (
                "Is probably optimistic and focuses on the positive aspects in most "
                "situations rather than on obstacles or negative aspects."
            )
        ),
        score_9_10=_localized(
            (
                "Optimistisk och väljer att fokusera på de positiva aspekterna vid "
                "utmanande situationer, snarare än att fokusera på hinder eller det "
                "negativa."
            ),
            (
                "Is optimistic and chooses to focus on the positive aspects in "
                "challenging situations rather than on obstacles or negative aspects."
            )
        ),
    ),

    # Emotional Control
    "Controlling Stress": _indicator(
        label_sv="Stresshantering",
        label_en="Controlling Stress",
        score_1_2=_localized(
            "Kan lätt visa känslor i påfrestande och utmanande situationer.",
            "May readily show emotion in stressful and challenging situations."
        ),
        score_3=_localized(
            "Tenderar att visa känslor i påfrestande och utmanande situationer.",
            "Tends to show emotion in stressful and challenging situations."
        ),
        score_4_7=_localized(
            (
                "Hen kan behärska sina känslor i påfrestande situationer lika bra som "
                "de flesta."
            ),
            (
                "Can control their emotions in stressful situations about as well as "
                "most people."
            )
        ),
        score_8=_localized(
            (
                "Har sannolikt god känsloreglering och kan troligen dölja negativa "
                "känslor under press."
            ),
            (
                "Is likely to regulate their emotions well and can probably conceal "
                "negative emotions under pressure."
            )
        ),
        score_9_10=_localized(
            "Har god känsloreglering och kan dölja negativa känslor under press.",
            (
                "Regulates their emotions well and can conceal negative emotions under "
                "pressure."
            )
        ),
    ),
    "Calm": _indicator(
        label_sv="Lugn",
        label_en="Calm",
        score_1_2=_localized(
            (
                "Kan oroa sig för situationer som känns utmanande och visar regelbundet "
                "sin ängslan för andra."
            ),
            (
                "May worry about situations that feel challenging and regularly shows "
                "anxiety to others."
            )
        ),
        score_3=_localized(
            (
                "Kan troligen oroa sig för situationer som känns utmanande och visar "
                "sin ängslan för andra."
            ),
            (
                "May be likely to worry about situations that feel challenging and "
                "shows anxiety to others."
            )
        ),
        score_4_7=_localized(
            (
                "Kan förmodligen hålla sig lugn i många situationer, men även uppvisa "
                "känslor i situationer som känns utmanande."
            ),
            (
                "Can probably remain calm in many situations but may also show emotion "
                "in situations that feel challenging."
            )
        ),
        score_8=_localized(
            (
                "Känner troligen inte oro så ofta och har en lugn framtoning i de "
                "flesta situationer."
            ),
            (
                "Is unlikely to feel worried very often and presents as calm in most "
                "situations."
            )
        ),
        score_9_10=_localized(
            (
                "Känner sällan oro och har en mycket lugn framtoning i de flesta "
                "situationer."
            ),
            "Rarely feels worried and presents as very calm in most situations."
        ),
    ),
    "Composed": _indicator(
        label_sv="Samlad",
        label_en="Composed",
        score_1_2=_localized(
            (
                "Vid mycket utmanande eller känslomässigt påfrestande situationer är "
                "självbehärskning svårare och därmed kan hen vara benägen att tappa "
                "fattningen."
            ),
            (
                "In highly challenging or emotionally stressful situations, "
                "self-control is more difficult and they may therefore be inclined to "
                "lose their composure."
            )
        ),
        score_3=_localized(
            (
                "Vid mycket utmanande eller känslomässigt påfrestande situationer kan "
                "självbehärskning vara svårare och därmed kan hen vara benägen att "
                "tappa fattningen."
            ),
            (
                "In highly challenging or emotionally stressful situations, "
                "self-control may be more difficult and they may therefore be inclined "
                "to lose their composure."
            )
        ),
        score_4_7=_localized(
            (
                "Har lika god självbehärskning som de flesta andra i känslomässigt "
                "påfrestande och utmanande situationer."
            ),
            (
                "Has about as much self-control as most people in emotionally stressful "
                "and challenging situations."
            )
        ),
        score_8=_localized(
            (
                "Har sannolikt självbehärskning, bibehåller troligen lugnet och håller "
                "sig samlad i utmanande och känslomässigt påfrestande situationer."
            ),
            (
                "Is likely to show self-control, probably remains calm, and stays "
                "composed in challenging and emotionally stressful situations."
            )
        ),
        score_9_10=_localized(
            (
                "Har god självbehärskning, bibehåller lugnet och håller sig samlad i "
                "utmanande och känslomässigt påfrestande situationer."
            ),
            (
                "Shows good self-control, remains calm, and stays composed in "
                "challenging and emotionally stressful situations."
            )
        ),
    ),

    # Independence
    "Self-Reliant": _indicator(
        label_sv="Självgående",
        label_en="Self-Reliant",
        score_1_2=_localized(
            "Föredrar att bli vägledd och att få mycket stöd från omgivningen.",
            (
                "Prefers to be guided and to receive a great deal of support from those "
                "around them."
            )
        ),
        score_3=_localized(
            "Gillar troligen att bli vägledd och att få stöd från omgivningen.",
            (
                "Probably likes to be guided and to receive support from those around "
                "them."
            )
        ),
        score_4_7=_localized(
            (
                "I vissa situationer kommer personen sannolikt att vara bekväm med att "
                "agera självgående, medan andra situationer kommer att kräva mer "
                "vägledning."
            ),
            (
                "Is likely to be comfortable acting independently in some situations, "
                "while other situations will require more guidance."
            )
        ),
        score_8=_localized(
            (
                "Är bekväm med att ta sig an uppgifter på egen hand och behöver "
                "sannolikt inte stöd och vägledning från andra."
            ),
            (
                "Is comfortable taking on tasks independently and is unlikely to need "
                "support and guidance from others."
            )
        ),
        score_9_10=_localized(
            (
                "Föredrar att ta sig an uppgifter på egen hand och är inte i behov av "
                "stöd och vägledning från andra."
            ),
            (
                "Prefers taking on tasks independently and does not need support and "
                "guidance from others."
            )
        ),
    ),
    "Self-Contained": _indicator(
        label_sv="Självständig",
        label_en="Self-Contained",
        score_1_2=_localized(
            (
                "Arbetar som allra bäst när de får emotionellt stöd och uppmuntran från "
                "andra, och delar gärna med sig av sina känslor öppet."
            ),
            (
                "Works best when they receive emotional support and encouragement from "
                "others and readily shares their feelings openly."
            )
        ),
        score_3=_localized(
            (
                "Arbetar troligen bättre när de får emotionellt stöd och uppmuntran "
                "från andra, och delar sannolikt med sig av sina känslor öppet."
            ),
            (
                "Is likely to work better when they receive emotional support and "
                "encouragement from others and is likely to share their feelings "
                "openly."
            )
        ),
        score_4_7=_localized(
            (
                "Kan troligen vara både självständig och söka stöd och uppmuntran från "
                "omgivningen, beroende på situation."
            ),
            (
                "Can probably be independent while also seeking support and "
                "encouragement from those around them, depending on the situation."
            )
        ),
        score_8=_localized(
            (
                "Föredrar troligen att arbeta självständigt och har sannolikt litet "
                "behov av emotionellt stöd och uppmuntran från omgivningen."
            ),
            (
                "Is likely to prefer working independently and probably has little need "
                "for emotional support and encouragement from those around them."
            )
        ),
        score_9_10=_localized(
            (
                "Föredrar att arbeta självständigt och har inte behov av emotionellt "
                "stöd och uppmuntran från omgivningen."
            ),
            (
                "Prefers working independently and does not need emotional support and "
                "encouragement from those around them."
            )
        ),
    ),
    "Thinking Independently": _indicator(
        label_sv="Tänker självständigt",
        label_en="Thinking Independently",
        score_1_2=_localized(
            (
                "Söker råd inför beslut och lägger stor vikt vid andras åsikter innan "
                "hen agerar."
            ),
            (
                "Seeks advice before making decisions and places great importance on "
                "other people's opinions before taking action."
            )
        ),
        score_3=_localized(
            (
                "Tenderar att fråga andra om råd inför beslut och lägger troligen vikt "
                "vid andras åsikter när de agerar."
            ),
            (
                "Tends to ask others for advice before making decisions and is likely "
                "to attach importance to their opinions when taking action."
            )
        ),
        score_4_7=_localized(
            (
                "Är relativt bekväm med att fatta beslut självständigt, men kan också "
                "söka råd inför mer avgörande beslut."
            ),
            (
                "Is relatively comfortable making decisions independently but may also "
                "seek advice before more significant decisions."
            )
        ),
        score_8=_localized(
            (
                "Föredrar sannolikt att fatta beslut självständigt utan att söka råd "
                "från andra, och är förmodligen bekväm med att fatta beslut utan att "
                "oroa sig för vad andra ska tycka."
            ),
            (
                "Is likely to prefer making decisions independently without seeking "
                "advice from others and is probably comfortable making decisions "
                "without worrying about what others will think."
            )
        ),
        score_9_10=_localized(
            (
                "Föredrar att fatta beslut självständigt utan att söka råd från andra "
                "och är bekväm med att fatta beslut utan att oroa sig för vad andra ska "
                "tycka."
            ),
            (
                "Prefers making decisions independently without seeking advice from "
                "others and is comfortable making decisions without worrying about what "
                "others will think."
            )
        ),
    ),

}