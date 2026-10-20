"""Génère artinq-commun.ttl : vocabulaire commun recommandé à partir des
rapprochements sémantiques entre les vocabulaires des étudiants.

Chaque terme commun liste ses sources (« Ex. <exercice> <terme> ») dans
skos:scopeNote ; les termes volontairement écartés sont listés dans
skos:editorialNote sur l'ontologie. La page index.html relit ces notes pour
afficher la couverture de chaque vocabulaire.

Usage : python3 generer_vocabulaire_commun.py
"""
from pathlib import Path

NS = "https://humanum-p8.fr/omk_artificialinquiries/onto/artinq#"

# (nom, label fr, label en, commentaire, sous-classe de, sources)
CLASSES = [
    # ── Personnes et exercices ──
    ("Participant", "Participant", "Participant",
     "Personne qui réalise un ou plusieurs exercices du vademecum.", None,
     "1 Participant; 2.a Utilisateur; 3.a Participant; 4 Participant; 5 Participant; 8 Partner; 11 Participant"),
    ("Exercice", "Exercice", "Exercise",
     "Exercice du vademecum Artificial Inquiries (numéro, bloc, consigne).", None,
     "1 Exercice; 6.c Exercice6c; 8 Exercise; 11 Exercice"),
    ("Question", "Question", "Question",
     "Question ou consigne d'un exercice à laquelle le participant répond.", None,
     "1 Question"),
    ("Passation", "Passation", "Session",
     "Séance au cours de laquelle un participant réalise un exercice, à une date et un moment donnés.", None,
     "1 Passation; 3.a SessionImpressions; 3.b Parcours"),
    ("Reponse", "Réponse", "Answer",
     "Réponse d'un participant à une question pendant une passation (classe abstraite).", None,
     "1 Reponse"),
    ("ReponseDessin", "Réponse dessin", "Drawing answer",
     "Réponse dessinée, composée de traits ; l'image est jointe en média.", "Reponse",
     "1 ReponseDessin"),
    ("ReponseTexte", "Réponse texte", "Text answer",
     "Réponse écrite à une question.", "Reponse",
     "1 ReponseTexte"),
    ("Trait", "Trait", "Stroke",
     "Trait d'un dessin : outil, couleur, épaisseur et points.", None,
     "1 Trait"),
    # ── Tâches ──
    ("Tache", "Tâche", "Task",
     "Tâche (professionnelle ou personnelle) décrite par le participant et éventuellement confiée à un LLM.", None,
     "2.a Tache; 2.b Task; 3.a TacheDeleguee; 6 Task; 6 CoreTask; 6.c Tache; 7.b Tache; 8 Task; 10.a Task"),
    ("CategorieTache", "Catégorie de tâche", "Task category",
     "Catégorie servant à classer des tâches ou des conversations (ex. BUSINESS, PLEASURE).", None,
     "3.b Categorie; 4 CategorieTache; 6 Category"),
    ("Role", "Rôle", "Role",
     "Rôle ou responsabilité attribué soit à l'IA, soit conservé par l'humain.", None,
     "2.b AIRole; 2.b HumanResponsibility"),
    # ── LLM, prompts, tests ──
    ("LLM", "Modèle de langage (LLM)", "Language model",
     "Modèle d'IA utilisé (ChatGPT, Claude, Mistral…).", None,
     "4 LLM; 5 LLM; 7.b ModeleIA; 8 Model; 10.a LLM"),
    ("Prompt", "Prompt", "Prompt",
     "Instruction donnée à un LLM pour réaliser une tâche.", None,
     "10.a Prompt"),
    ("Test", "Test", "Test",
     "Soumission d'un même prompt à un ou plusieurs LLM.", None,
     "7.b Test"),
    ("ReponseLLM", "Réponse d'un LLM", "LLM output",
     "Résultat produit par un LLM lors d'un test ou d'une tâche.", None,
     "7.b Reponse; 8 Response; 10.a Result"),
    ("CodeAnonyme", "Code d'anonymisation", "Blind code",
     "Code (ex. nom d'animal) qui masque l'identité d'un LLM pendant un test à l'aveugle.", None,
     "8 AnimalCode"),
    # ── Conversations ──
    ("Historique", "Historique de conversations", "Conversation history",
     "Ensemble des conversations d'un participant avec des LLM.", None,
     "3.b Historique"),
    ("Conversation", "Conversation", "Conversation",
     "Conversation entre un participant et un LLM.", None,
     "3.b Conversation; 5 Conversation"),
    ("ConversationMarquante", "Conversation marquante", "Memorable conversation",
     "Conversation qui a laissé une impression durable.", "Conversation",
     "3.a ConversationMarquante; 3.b ConversationMemorable; 4 ConversationMemorable"),
    ("Echange", "Échange", "Exchange",
     "Un message du participant et la réponse du LLM au sein d'une conversation.", None,
     "5 Interaction"),
    ("Emotion", "Émotion", "Emotion",
     "Émotion associée à une conversation (enthousiasme, frustration, surprise…).", None,
     "4 Emotion"),
    ("TypeImpact", "Type d'impact", "Impact type",
     "Nature de l'impact d'une conversation sur le participant.", None,
     "4 TypeImpact"),
    ("Terme", "Terme", "Term",
     "Mot de remplacement pour désigner un interlocuteur (humain ou LLM).", None,
     "5 Terme"),
    ("Substitution", "Substitution", "Substitution",
     "Tour de substitution attribuant de nouveaux rôles au participant et au LLM.", None,
     "5 Substitution"),
    # ── Évaluation ──
    ("Evaluation", "Évaluation", "Evaluation",
     "Jugement porté sur une tâche, un terme, une réponse ou une œuvre.", None,
     "5 EvaluationTerme; 6 TaskAssessment; 6.c Evaluation; 13 Evaluation"),
    ("Attente", "Attente envers le LLM", "LLM expectation",
     "Niveau de performance attendu et critères d'échec, de résultat acceptable et de réussite.", None,
     "6 LLMExpectation; 6.c Attentes"),
    ("NiveauPerformance", "Niveau de performance", "Performance level",
     "Échelle : TERRIBLE, PRETTY_BAD, GOOD_ENOUGH, EXCELLENT.", None,
     "6 ExpectationLevel"),
    ("Critere", "Critère", "Criterion",
     "Critère d'évaluation (fréquence, enjeux, expertise, effort, collaboration, tolérance à l'erreur, standardisation, fierté).", None,
     "13 Criterion; 6 ResultCriteria"),
    ("ScoreCritere", "Score de critère", "Criterion score",
     "Note de 1 à 5 attribuée à un critère dans une évaluation.", None,
     "13 CriterionScore"),
    # ── Réflexion et sources ──
    ("Reflexion", "Réflexion", "Reflection",
     "Texte de réflexion, de synthèse ou de justification rédigé par le participant.", None,
     "2.b Reflection; 3.b Fiche; 5 Reflexion; 11 Reflexion; 13 Justification"),
    ("Observation", "Observation", "Observation",
     "Observation datée sur l'usage des LLM (avant, pendant ou après).", None,
     "11 Observation"),
    ("Dimension", "Dimension", "Dimension",
     "Dimension d'analyse d'une réflexion.", None,
     "11 Dimension"),
    ("Exemple", "Exemple", "Example",
     "Exemple concret (extrait de conversation, lien) illustrant une observation.", None,
     "11 Exemple"),
    ("Document", "Document", "Document",
     "Ressource documentaire ou média associé (fichier, source, capture).", None,
     "8 Document; 11 Media; 13 DocumentaryResource"),
    ("OeuvreExemplaire", "Œuvre exemplaire", "Exemplary work",
     "Travail ou document professionnel choisi pour son exemplarité.", None,
     "13 ExemplaryWork"),
    ("De", "Dé", "Die",
     "Dé utilisé pour parcourir l'historique de manière aléatoire.", None,
     "3.b De"),
]

# (nom, label fr, label en, commentaire, domaine, range, équivalent externe, sources)
# domaine/range : nom de classe artinq, "xsd:…", ou None (= o:Resource)
PROPS = [
    # ── Propriétés génériques (alignées sur Dublin Core / FOAF) ──
    ("identifiant", "identifiant", "identifier", "Identifiant d'une ressource.", None, "xsd:string", "dcterms:identifier",
     "2.a idUtilisateur; 2.a idTache; 6.c taskId; 8 id; 8 taskId; 10.a taskId"),
    ("titre", "titre", "title", "Titre ou intitulé d'un exercice, d'une tâche, d'une conversation.", None, "xsd:string", "dcterms:title",
     "1 titre; 2.a nomTache; 2.b taskName; 3.b titre; 6.c titre; 8 title; 11 titreExercice"),
    ("nom", "nom", "name", "Nom d'une personne, d'un modèle, d'une catégorie ou d'un rôle.", None, "xsd:string", "foaf:name",
     "2.a nom; 2.b roleName; 2.b responsibilityName; 3.b nom; 4 name; 8 name; 10.a name"),
    ("description", "description", "description", "Description libre.", None, "xsd:string", "dcterms:description",
     "2.b explanation; 6.c description; 8 description"),
    ("type", "type", "type", "Type ou nature (valeur contrôlée, ex. DESSIN/TEXTE, EVOLUTION/CONSTANCE).", None, "xsd:string", "dcterms:type",
     "1 typeQuestion; 5 typeTerme; 8 type; 10.a type; 11 typeReflexion"),
    ("date", "date", "date", "Date (et heure) de saisie, de passation, de test ou d'évaluation.", None, "xsd:dateTime", "dcterms:date",
     "1 datePassation; 3.b date; 7.b dateTest; 11 dateSaisie; 11 dateObservation; 13 evaluationDate"),
    ("dateModification", "date de modification", "modified", "Date de dernière modification.", None, "xsd:dateTime", "dcterms:modified",
     "1 modifieeLe"),
    ("texte", "texte", "text", "Contenu textuel (réponse, impression, contenu d'une réponse de LLM).", None, "xsd:string", None,
     "1 texte; 3.a impression; 4 content; 7.b contenu; 8 content; 10.a content; 11 texte"),
    ("resume", "résumé", "summary", "Résumé ou synthèse.", None, "xsd:string", "dcterms:abstract",
     "2.b summary; 11 resume"),
    ("url", "URL", "URL", "Adresse web d'une conversation ou d'une référence.", None, "xsd:anyURI", None,
     "11 urlConversation; 13 referenceUrl"),
    ("numero", "numéro", "number", "Numéro d'un exercice ou d'un échange.", None, "xsd:string", None,
     "1 numero; 5 numero; 11 numero"),
    ("ordre", "ordre", "order", "Position dans une séquence (rang, tour, position).", None, "xsd:integer", None,
     "1 ordre; 3.a rang; 3.b position; 5 tour; 6 position"),
    ("statut", "statut", "status", "Statut (ex. simulation, succès, erreur).", None, "xsd:string", None,
     "7.b statut"),
    # ── Participant ──
    ("pseudo", "pseudo", "nickname", "Pseudo ou identifiant de connexion du participant.", "Participant", "xsd:string", "foaf:nick",
     "1 pseudo; 11 login"),
    ("compteGithub", "compte GitHub", "GitHub account", "Identifiant GitHub du participant.", "Participant", "xsd:string", "foaf:accountName",
     "5 compteGithub"),
    ("profession", "profession", "profession", "Métier ou profession du participant.", "Participant", "xsd:string", None,
     "3.a metier; 11 profession"),
    ("dateInscription", "date d'inscription", "registration date", "Date d'inscription du participant.", "Participant", "xsd:dateTime", None,
     "1 inscritLe"),
    ("utiliseLLM", "utilise le LLM", "uses LLM", "Relie un participant, une conversation, un test ou une tâche au LLM utilisé.", None, "LLM", None,
     "3.a llmPrincipal; 4 usesLLM; 5 avecLLM; 7.b utiliseModele; 8 tests; 10.a usesLLM; 11 llmUtilise"),
    ("frequence", "fréquence", "frequency", "Fréquence d'une tâche ou de l'usage d'un LLM.", None, "xsd:string", None,
     "2.a frequence; 2.b frequency; 3.a frequence"),
    ("dureeMinuteur", "durée du minuteur", "timer duration", "Durée du minuteur en secondes.", "Passation", "xsd:integer", None,
     "3.a dureeMinuteur"),
    ("partEchangesCourts", "part d'échanges courts", "share of short exchanges", "Pourcentage de conversations à une seule question-réponse.", "Passation", "xsd:decimal", None,
     "3.a partEchangesCourts"),
    ("partConversationsLongues", "part de conversations longues", "share of long conversations", "Pourcentage de conversations à plusieurs allers-retours.", "Passation", "xsd:decimal", None,
     "3.a partConversationsLongues"),
    ("partDialoguesEtendus", "part de dialogues étendus", "share of extended dialogues", "Pourcentage de conversations de plus d'une journée.", "Passation", "xsd:decimal", None,
     "3.a partDialoguesEtendus"),
    # ── Exercice, question, passation ──
    ("bloc", "bloc", "block", "Bloc du vademecum auquel appartient l'exercice.", "Exercice", "xsd:string", None,
     "1 bloc"),
    ("pageVademecum", "page du vademecum", "vademecum page", "Page de l'exercice dans le vademecum.", "Exercice", "xsd:string", None,
     "11 pageVademecum"),
    ("consigne", "consigne", "instructions", "Consigne d'un exercice ou d'une tâche.", None, "xsd:string", None,
     "1 consigne; 7.b instruction; 8 instructions"),
    ("aPourQuestion", "a pour question", "has question", "Relie un exercice à l'une de ses questions.", "Exercice", "Question", "dcterms:hasPart",
     "1 contientQuestion"),
    ("libelle", "libellé", "wording", "Texte d'une question ou d'un libellé.", None, "xsd:string", None,
     "1 libelle; 11 libelle; 11 question"),
    ("moment", "moment", "moment", "Moment de la passation (avant, pendant, après…).", None, "xsd:string", None,
     "1 moment; 11 periode"),
    ("realiseePar", "réalisée par", "carried out by", "Relie une passation, une conversation ou une réflexion au participant.", None, "Participant", "dcterms:creator",
     "1 realiseePar; 3.a aPourParticipant; 4 createdBy; 5 aParticipant"),
    ("porteSur", "porte sur", "is about exercise", "Relie une ressource à l'exercice concerné.", None, "Exercice", None,
     "1 porteSur; 11 hasExercice"),
    ("aPourReponse", "a pour réponse", "has answer", "Relie une passation à l'une de ses réponses.", "Passation", "Reponse", None,
     "1 contientReponse"),
    ("repondA", "répond à", "answers", "Relie une réponse à la question.", "Reponse", "Question", None,
     "1 repondA"),
    # ── Dessin ──
    ("aPourTrait", "a pour trait", "has stroke", "Relie une réponse dessin à l'un de ses traits.", "ReponseDessin", "Trait", None,
     "1 composeDe"),
    ("outil", "outil", "tool", "CRAYON, FEUTRE ou GOMME.", "Trait", "xsd:string", None, "1 outil"),
    ("couleur", "couleur", "colour", "Code hexadécimal de la couleur.", "Trait", "xsd:string", None, "1 couleur"),
    ("epaisseur", "épaisseur", "width", "Épaisseur en pixels.", "Trait", "xsd:decimal", None, "1 epaisseur"),
    ("points", "points", "points", "Points du trait en JSON : [[x, y], …].", "Trait", "xsd:string", None, "1 points"),
    # ── Tâche ──
    ("aPourTache", "a pour tâche", "has task", "Relie un participant, une passation, un exercice ou un test à une tâche.", None, "Tache", None,
     "2.a realise; 2.b managesTask; 3.a aPourTache; 6 selectsTask; 6.c hasTache; 7.b concerneTache; 8 contains; 8 provides; 8 executes"),
    ("aPourCategorie", "a pour catégorie", "has category", "Relie une tâche ou une conversation à sa catégorie.", None, "CategorieTache", None,
     "3.b categorie; 3.b appartientCategorie; 3.b categories; 3.b regroupeCategorie; 4 hasTaskCategory; 6 category"),
    ("pourcentage", "pourcentage", "percentage", "Part estimée (0-100) de la tâche dans l'usage du LLM.", "Tache", "xsd:decimal", None,
     "3.a pourcentage"),
    ("importance", "importance", "importance", "Importance de la tâche pour le participant.", "Tache", "xsd:string", None,
     "2.b importance"),
    ("appreciation", "appréciation", "appreciation", "Goût du participant pour la tâche.", "Tache", "xsd:string", None,
     "2.a appreciation"),
    ("tempsNecessaire", "temps nécessaire", "time required", "Temps nécessaire pour réaliser la tâche.", "Tache", "xsd:string", None,
     "2.a tempsNecessaire"),
    ("procrastination", "procrastination", "procrastination", "Tendance à repousser la tâche.", "Tache", "xsd:string", None,
     "2.a procrastination"),
    ("niveauExpertise", "niveau d'expertise", "expertise level", "Expertise nécessaire ou détenue pour la tâche.", "Tache", "xsd:string", None,
     "2.a niveauExpertise"),
    ("niveauAssistance", "niveau d'assistance", "assistance level", "Niveau d'assistance attendu de l'IA.", "Tache", "xsd:string", None,
     "2.b assistanceLevel"),
    ("delegation", "délégation envisagée", "delegation", "La tâche est-elle déléguée au LLM ?", "Tache", "xsd:boolean", None,
     "6 delegation"),
    ("confianceComplete", "confiance complète", "complete trust", "Niveau de confiance accordé au LLM pour la tâche.", "Tache", "xsd:string", None,
     "6 completeTrust; 6.c confidence"),
    ("hesitation", "hésitation à déléguer", "hesitation", "Le participant hésite-t-il à déléguer ?", "Tache", "xsd:boolean", None,
     "6 hesitation"),
    ("aPourRole", "a pour rôle", "has role", "Relie une tâche à un rôle confié à l'IA ou conservé par l'humain.", "Tache", "Role", None,
     "2.b usesAIRole; 2.b keepsHumanResponsibility"),
    ("attribueA", "attribué à", "assigned to", "IA ou HUMAIN.", "Role", "xsd:string", None, ""),
    # ── LLM, test, réponse ──
    ("version", "version", "version", "Version du LLM.", "LLM", "xsd:string", None,
     "4 version; 5 version; 7.b version; 11 version"),
    ("fournisseur", "fournisseur", "provider", "Éditeur du modèle (OpenAI, Anthropic, Mistral…).", "LLM", "xsd:string", None,
     "7.b fournisseur"),
    ("aPourPrompt", "a pour prompt", "has prompt", "Relie une tâche ou un test au prompt utilisé.", None, "Prompt", None,
     "7.b promptUtilise; 10.a hasPrompt"),
    ("modeTest", "mode de test", "test mode", "individuel ou simultané.", "Test", "xsd:string", None,
     "7.b mode"),
    ("produitReponse", "produit la réponse", "produces output", "Relie un test, une tâche ou un LLM à une réponse produite.", None, "ReponseLLM", None,
     "7.b reponseDeTest; 8 produces; 8 generates; 10.a producesResult"),
    ("produitePar", "produite par", "produced by", "Relie une réponse au LLM qui l'a produite.", "ReponseLLM", "LLM", None,
     "7.b produitePar"),
    ("codeAnonyme", "code d'anonymisation", "blind code", "Relie un LLM ou une réponse à son code d'anonymisation.", None, "CodeAnonyme", None,
     "8 animalCode; 8 assignsCode; 8 receives"),
    ("probleme", "problème rencontré", "problem", "Problème ou défi rencontré.", None, "xsd:string", None,
     "10.a problem; 13 problemChallenge"),
    ("cause", "cause", "cause", "Cause du problème.", None, "xsd:string", None, "10.a cause"),
    ("amelioration", "piste d'amélioration", "improvement", "Piste d'amélioration.", None, "xsd:string", None, "10.a improvement"),
    # ── Conversation ──
    ("aPourConversation", "a pour conversation", "has conversation", "Relie un historique, une passation, une fiche ou un échange à une conversation.", None, "Conversation", None,
     "3.a aPourConversationMarquante; 3.b conversations; 3.b memorables; 3.b gardeConversationMemorable; 5 dansConversation"),
    ("pourquoiMarquante", "pourquoi marquante", "why memorable", "Raison pour laquelle la conversation a marqué.", "ConversationMarquante", "xsd:string", None,
     "4 whyMemorable"),
    ("aPourEmotion", "a pour émotion", "has emotion", "Émotion associée à une conversation.", None, "Emotion", None,
     "3.a ressenti; 4 hasEmotion"),
    ("aPourTypeImpact", "a pour type d'impact", "has impact type", "Type d'impact d'une conversation.", None, "TypeImpact", None,
     "4 hasImpactType"),
    ("extraitUtilisateur", "extrait utilisateur", "user excerpt", "Extrait d'un message du participant.", None, "xsd:string", None,
     "5 extraitUser; 11 extraitConversation"),
    ("extraitLLM", "extrait LLM", "LLM excerpt", "Extrait de la réponse du LLM.", None, "xsd:string", None,
     "5 extraitLLM"),
    ("utiliseDe", "utilise le dé", "uses die", "Relie une passation au dé utilisé.", "Passation", "De", None, "3.b utiliseDe"),
    ("faces", "faces", "faces", "Nombre de faces du dé.", "De", "xsd:integer", None, "3.b faces"),
    ("parcourtHistorique", "parcourt l'historique", "browses history", "Relie une passation à l'historique parcouru.", "Passation", "Historique", None,
     "3.b parcourtHistorique"),
    ("occurrences", "occurrences", "occurrences", "Nombre d'occurrences d'une catégorie.", "CategorieTache", "xsd:integer", None,
     "3.b occurrences"),
    # ── Substitution de termes (Ex. 5) ──
    ("pourEchange", "pour l'échange", "for exchange", "Échange concerné par la substitution.", "Substitution", "Echange", None, "5 pourInteraction"),
    ("roleUtilisateur", "rôle utilisateur", "user role", "Terme qui remplace « moi / l'utilisateur ».", "Substitution", "Terme", None, "5 roleUser"),
    ("roleLLM", "rôle LLM", "LLM role", "Terme qui remplace « la machine / l'IA ».", "Substitution", "Terme", None, "5 roleLLM"),
    ("aRaffiner", "à raffiner", "to refine", "Faut-il un nouveau tour de substitution ?", "Substitution", "xsd:boolean", None, "5 aRaffiner"),
    ("estFinal", "tour final", "is final", "Ce tour donne-t-il les termes finaux ?", "Substitution", "xsd:boolean", None, "5 estFinal"),
    ("evalueTerme", "évalue le terme", "evaluates term", "Terme évalué.", "Evaluation", "Terme", None, "5 evalueTerme"),
    ("adequat", "adéquat", "adequate", "Le terme décrit-il bien l'interlocuteur ?", "Evaluation", "xsd:boolean", None, "5 adequat"),
    ("etrange", "étrange", "uncanny", "Le terme paraît-il étrange ?", "Evaluation", "xsd:boolean", None, "5 etrange"),
    ("correspondTon", "correspond au ton", "matches tone", "Le rôle correspond-il au ton de la réponse ?", "Evaluation", "xsd:boolean", None, "5 correspondTon"),
    # ── Évaluation et attentes ──
    ("aPourEvaluation", "a pour évaluation", "has evaluation", "Relie une ressource à son évaluation.", None, "Evaluation", None,
     "5 aEvaluation; 6 hasAssessment; 6.c hasEvaluation; 13 hasEvaluation"),
    ("note", "note", "rating", "Note ou score (ex. 1 à 5).", None, "xsd:decimal", None,
     "4 rating; 13 scoreValue"),
    ("evaluationPerformance", "évaluation de performance", "performance evaluation", "Appréciation de la performance du LLM.", None, "xsd:string", None,
     "4 performanceEvaluation; 5 evaluation"),
    ("justification", "justification", "justification", "Explication d'un choix ou d'une évaluation.", None, "xsd:string", None,
     "4 performanceExplanation; 5 justification; 6 reasoning; 13 scoreComment; 13 generalComment"),
    ("adequationTache", "adéquation de la tâche", "task fit", "La tâche convient-elle au test ?", "Evaluation", "xsd:string", None,
     "6 taskFit; 6.c taskFit"),
    ("pertinenceProfessionnelle", "pertinence professionnelle", "professional relevance", "Enjeu professionnel de la tâche.", "Evaluation", "xsd:string", None,
     "6 professionalRelevance; 6.c professionalRelevance"),
    ("consequencePersonnelle", "conséquence personnelle", "personal outcome", "Conséquence personnelle du résultat.", "Evaluation", "xsd:string", None,
     "6 personalOutcome; 6.c personalOutcome"),
    ("aPourAttente", "a pour attente", "has expectation", "Relie une tâche ou une évaluation aux attentes envers le LLM.", None, "Attente", None,
     "6 hasLLMExpectation; 6 hasResultCriteria; 6.c hasAttentes"),
    ("performanceAttendue", "performance attendue", "expected performance", "Niveau de performance attendu.", "Attente", "NiveauPerformance", None,
     "6 expectedPerformance; 6.c expectedPerformance"),
    ("critereEchec", "critère d'échec", "failure criterion", "Ce qui serait un échec.", "Attente", "xsd:string", None, "6 failure; 6.c failure"),
    ("critereAcceptable", "critère de résultat acceptable", "good-enough criterion", "Ce qui serait suffisant.", "Attente", "xsd:string", None, "6 goodEnough; 6.c goodEnough"),
    ("critereReussite", "critère de réussite", "success criterion", "Ce qui serait une réussite.", "Attente", "xsd:string", None, "6 success; 6.c success"),
    ("aPourCritere", "a pour critère", "has criterion", "Relie un score au critère évalué.", "ScoreCritere", "Critere", None, "13 hasCriterion"),
    # ── Réflexion, observation, documents ──
    ("aPourReflexion", "a pour réflexion", "has reflection", "Relie une ressource à une réflexion ou justification.", None, "Reflexion", None,
     "2.b generatesReflection; 11 hasReflexion; 13 hasJustification"),
    ("aPourObservation", "a pour observation", "has observation", "Relie une réflexion à une observation.", None, "Observation", None, "11 hasObservation"),
    ("aPourDimension", "a pour dimension", "has dimension", "Relie une réflexion à une dimension.", None, "Dimension", None, "11 hasDimension"),
    ("aPourExemple", "a pour exemple", "has example", "Relie une observation à un exemple.", None, "Exemple", None, "11 hasExemple"),
    ("aPourDocument", "a pour document", "has document", "Relie une ressource à un document ou média associé.", None, "Document", "dcterms:references",
     "8 mayRequire; 11 hasMedia; 13 hasDocumentaryResource"),
    # ── Œuvre exemplaire (Ex. 13) ──
    ("domaineProfessionnel", "domaine professionnel", "professional field", "Domaine professionnel concerné.", None, "xsd:string", None,
     "13 professionalDomain; 13 professionalField"),
    ("contributionPrincipale", "contribution principale", "primary contribution", "Apport principal de l'œuvre.", "OeuvreExemplaire", "xsd:string", None, "13 primaryContribution"),
    ("solutionDistinctive", "solution distinctive", "distinctive solution", "Solution qui distingue l'œuvre.", "OeuvreExemplaire", "xsd:string", None, "13 distinctiveSolution"),
    ("valeursProfessionnelles", "valeurs professionnelles", "professional values", "Valeurs ou standards incarnés.", "OeuvreExemplaire", "xsd:string", None, "13 professionalValues"),
    ("aspectAImiter", "aspect à imiter", "aspect to emulate", "Ce qui mérite d'être imité.", "OeuvreExemplaire", "xsd:string", None, "13 aspectToEmulate"),
]

# Termes étudiants volontairement non repris, avec la raison
NON_RETENUS = [
    ("2.b TaskManager", "entité technique de l'application, pas un concept du domaine"),
    ("11 fichier", "géré nativement par les médias Omeka"),
    ("11 typeMime", "géré nativement par les médias Omeka"),
    ("13 frequencyScore; 13 professionalStakesScore; 13 expertiseRequiredScore; 13 effortResourcesScore; "
     "13 collaborationScore; 13 errorToleranceScore; 13 standardisationScore; 13 professionalPrideScore",
     "remplacés par des instances de artinq:Critere notées via artinq:ScoreCritere"),
]

PREFIXES = {
    "artinq": NS,
    "dcterms": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "o": "http://omeka.org/s/vocabs/o#",
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "vs": "http://www.w3.org/2003/06/sw-vocab-status/ns#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
}


def lit(s, lang=None):
    s = s.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{s}"' + (f"@{lang}" if lang else "")


def ref(x):
    if x is None:
        return "o:Resource"
    return x if ":" in x else f"artinq:{x}"


def sources_note(src):
    items = [s.strip() for s in src.split(";") if s.strip()]
    return "Rapprochements : " + " ; ".join(f"Ex. {s}" for s in items) if items else None


def term(name, kind, fr, en, comment, extra, src):
    lines = [f"artinq:{name} a {kind} ;",
             f"    rdfs:label {lit(fr, 'fr')}, {lit(en, 'en')} ;",
             f"    rdfs:comment {lit(comment, 'fr')} ;"]
    lines += [f"    {p} {o} ;" for p, o in extra]
    note = sources_note(src)
    if note:
        lines.append(f"    skos:scopeNote {lit(note, 'fr')} ;")
    lines.append('    vs:term_status "testing" .')
    return "\n".join(lines)


def main():
    known = {c[0] for c in CLASSES}
    for p in PROPS:
        for r in (p[4], p[5]):
            assert r is None or ":" in r or r in known, f"{p[0]} : classe inconnue {r}"
    names = [c[0] for c in CLASSES] + [p[0] for p in PROPS]
    assert len(names) == len(set(names)), "nom en double"

    out = [f"@prefix {k}: <{v}> ." for k, v in PREFIXES.items()]
    out.append("")
    notes = [f"Non retenu : {' ; '.join('Ex. ' + s.strip() for s in src.split(';'))} — {why}"
             for src, why in NON_RETENUS]
    out.append(f"<{NS}> a owl:Ontology ;")
    out.append(f'    dcterms:title {lit("Artificial Inquiries — vocabulaire commun", "fr")} ;')
    out.append("    dcterms:description " + lit(
        "Vocabulaire commun recommandé, obtenu par rapprochement sémantique des classes et propriétés "
        "des vocabulaires produits pour les exercices du vademecum Artificial Inquiries. "
        "Chaque terme indique dans skos:scopeNote les termes d'origine qu'il remplace.", "fr") + " ;")
    out.append('    owl:versionInfo "1.0" ;')
    out += [f"    skos:editorialNote {lit(n, 'fr')} ;" for n in notes]
    out[-1] = out[-1][:-2] + " ."
    out.append("")

    out.append("# " + "─" * 60 + "\n# CLASSES\n# " + "─" * 60 + "\n")
    for name, fr, en, comment, sub, src in CLASSES:
        extra = [("rdfs:subClassOf", ref(sub))] if sub else []
        out.append(term(name, "rdfs:Class", fr, en, comment, extra, src) + "\n")

    out.append("# " + "─" * 60 + "\n# PROPRIÉTÉS\n# " + "─" * 60 + "\n")
    for name, fr, en, comment, dom, rng, equiv, src in PROPS:
        extra = [("rdfs:domain", ref(dom)), ("rdfs:range", ref(rng) if rng else "rdfs:Literal")]
        if equiv:
            extra.append(("rdfs:subPropertyOf", equiv))
        out.append(term(name, "rdf:Property", fr, en, comment, extra, src) + "\n")

    path = Path(__file__).with_name("artinq-commun.ttl")
    path.write_text("\n".join(out), encoding="utf-8")
    print(f"{path.name} : {len(CLASSES)} classes, {len(PROPS)} propriétés")


if __name__ == "__main__":
    main()
