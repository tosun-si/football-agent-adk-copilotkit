"""Slide-by-slide content for the DevLille / GCS France 2026 talk."""

SLIDES = [
    {
        "type": "title",
        "title": "Qui a marqué le plus de buts ?",
        "subtitle": "Construire un agent IA qui interroge des données en langage naturel",
        "footer": "Mazlum Tosun — DevLille / Google Cloud Summit France 2026",
        "notes": (
            "Présentation rapide. Pendant les 45 prochaines minutes, on va construire "
            "un agent qui répond à cette question — et bien d'autres — sans écrire une "
            "ligne de SQL. Cas d'usage : statistiques de la Coupe du monde 2022."
        ),
    },
    {
        "type": "image",
        "title": "La donnée brute",
        "image_path": "",  # placeholder: screenshot table BigQuery
        "image_placeholder": "Screenshot console BigQuery — table team_players_stat_raw",
        "caption": "qatar_fifa_world_cup.team_players_stat_raw — colonnes camelCase, beaucoup de STRING",
        "notes": (
            "Voilà ce qu'on a : stats de tous les joueurs de la Coupe du monde 2022. "
            "Et regardez les types — la plupart des colonnes numériques sont en STRING. "
            "Ça va devenir intéressant côté requêtes."
        ),
    },
    {
        "type": "bullets",
        "title": "Le besoin métier",
        "bullets": [
            "Data teams débordées par les requêtes ad-hoc",
            "Équipes non-tech veulent explorer sans Looker ni SQL",
            "Décisions plus rapides, moins d'allers-retours",
            "Démocratisation de la donnée interne",
        ],
        "notes": (
            "Chez les clients c'est toujours le même pattern : la data team passe son "
            "temps à écrire des SELECT pour les autres équipes. On peut faire mieux en "
            "donnant un accès direct via langage naturel."
        ),
    },
    {
        "type": "bullets",
        "title": "Pourquoi c'est dur sans agent",
        "bullets": [
            "Connaître le schéma exact (camelCase, types mixtes)",
            "SAFE_CAST partout pour les STRING numériques",
            "Règles métier complexes (performance rating, team style…)",
            "Joins, agrégations, fully-qualified tables",
            "Sans guidage, le LLM hallucine du SQL en boucle",
        ],
        "notes": (
            "Les LLMs hallucinent du SQL en boucle. Mauvais nom de colonne, mauvais cast, "
            "mauvaise table. Sans système d'instructions précis, c'est inutilisable. "
            "C'est exactement ce que l'agent va résoudre."
        ),
    },
    {
        "type": "image",
        "title": "La promesse",
        "image_path": "",
        "image_placeholder": "Capture chat : question NL → réponse + visualisation",
        "caption": "« Qui est le meilleur passeur d'Argentine ? » → SQL → résultat + viz",
        "notes": (
            "L'agent fait le pont entre la question floue de l'utilisateur et le SQL exact "
            "à exécuter sur BigQuery. C'est ça qu'on va construire dans les 40 prochaines "
            "minutes."
        ),
    },
    {
        "type": "image",
        "title": "Architecture — vue d'ensemble",
        "image_path": "diagrams/adk_gcp_football_stats_agent.png",
        "caption": "ADK Agent + MCP BigQuery + Cloud Run / Agent Engine",
        "notes": (
            "Trois briques : ADK pour l'agent, MCP pour parler à BigQuery sans réinventer "
            "la roue, GCP pour héberger. On va décortiquer chacune dans les slides suivantes."
        ),
    },
    {
        "type": "bullets",
        "title": "Pourquoi ADK ?",
        "bullets": [
            "Framework Google open-source pour agents LLM",
            "Model-agnostic — Gemini, Gemma, OpenAI, Anthropic",
            "Outils intégrés : sessions, tracing, déploiement Vertex",
            "Pythonic, peu de boilerplate",
            "adk web, adk api_server, adk deploy en CLI",
        ],
        "notes": (
            "ADK c'est l'équivalent LangChain de Google, mais beaucoup plus opinionated "
            "et intégré à l'écosystème Vertex AI. Si tu fais du GCP, c'est le choix "
            "logique pour démarrer."
        ),
    },
    {
        "type": "bullets",
        "title": "Pourquoi MCP ?",
        "bullets": [
            "Model Context Protocol — standard ouvert (Anthropic)",
            "Découplage agent ↔ data source",
            "BigQuery expose un serveur MCP natif via Cloud API Registry",
            "Zéro infra à maintenir côté MCP",
            "Marche aussi avec Postgres, MySQL, GitHub, Slack…",
        ],
        "notes": (
            "MCP c'est le USB-C des agents. BigQuery expose un serveur MCP managé via "
            "API Registry, donc zéro infra à maintenir. Et le pattern marche au-delà de "
            "BigQuery — c'est un standard, pas du Google-only."
        ),
    },
    {
        "type": "code",
        "title": "Le code de l'agent",
        "language": "python",
        "code": (
            "from google.adk.agents import LlmAgent\n"
            "from google.adk.integrations.api_registry import ApiRegistry\n"
            "\n"
            "def create_agent():\n"
            "    registry = ApiRegistry(PROJECT_ID, location=\"global\",\n"
            "                           header_provider=get_header)\n"
            "    mcp_server = f\"projects/{PROJECT_ID}/locations/global/\"\\\n"
            "                 f\"mcpServers/google-bigquery.googleapis.com-mcp\"\n"
            "    toolset = registry.get_toolset(mcp_server)\n"
            "\n"
            "    return LlmAgent(\n"
            "        model=\"gemini-2.5-flash\",\n"
            "        name=\"football_stats_agent\",\n"
            "        instruction=SYSTEM_INSTRUCTION,\n"
            "        tools=[toolset],\n"
            "    )"
        ),
        "notes": (
            "30 lignes de Python pour avoir un agent qui parle à BigQuery via MCP. ADK "
            "fait tout le gros du travail. La complexité est dans le SYSTEM_INSTRUCTION "
            "qu'on va voir juste après."
        ),
    },
    {
        "type": "code",
        "title": "Le system instruction — guider le modèle",
        "language": "text",
        "code": (
            "## Table Schema (team_players_stat_raw)\n"
            "Columns use camelCase naming:\n"
            "  nationality | STRING | Country/team name\n"
            "  goalsScored | STRING | Goals scored\n"
            "  assistsProvided | STRING | Assists provided\n"
            "  ...\n"
            "\n"
            "IMPORTANT: Many numeric columns are STRING.\n"
            "Use SAFE_CAST(goalsScored AS INT64) for sorting.\n"
            "\n"
            "## Business Rules\n"
            "1. Performance Rating (0-100):\n"
            "   ((Goals*20) + (Assists*10) + ...) / Matches\n"
            "2. Team Style: OFFENSIVE if Goals/Match > 2.0\n"
            "                & Possession > 55%"
        ),
        "notes": (
            "C'est ici qu'on guide le modèle : schéma précis, règles métier, contraintes "
            "de cast. Sans ça, hallucinations garanties — le LLM va inventer des noms de "
            "colonnes en snake_case et oublier les SAFE_CAST."
        ),
    },
    {
        "type": "code",
        "title": "uv comme package manager",
        "language": "bash",
        "code": (
            "# .envrc — auto activé par direnv\n"
            "if [ ! -d \".venv\" ]; then\n"
            "    uv venv\n"
            "fi\n"
            "export VIRTUAL_ENV=\"$(pwd)/.venv\"\n"
            "PATH_add \"$VIRTUAL_ENV/bin\"\n"
            "\n"
            "# Installer les deps (rapide, lockfile inclus)\n"
            "$ uv sync\n"
            "\n"
            "# Lancer l'agent en local\n"
            "$ uv run adk web"
        ),
        "notes": (
            "uv c'est le package manager Python qui a remplacé poetry chez moi. 10× plus "
            "rapide, lockfile inclus, marche avec direnv pour activer le venv "
            "automatiquement quand on entre dans le dossier."
        ),
    },
    {
        "type": "demo",
        "title": "Agent local + Docker Compose",
        "steps": [
            "uv run adk web → question NL → réponse",
            "docker buildx bake → 3 images en parallèle",
            "docker compose up → 3 services en local",
        ],
        "notes": (
            "Démo live : on lance l'agent avec adk web, on pose 2-3 questions. Puis on "
            "passe à compose pour montrer l'écosystème complet en local — agent + proxy "
            "+ webapp en une commande."
        ),
    },
    {
        "type": "bullets",
        "title": "Front Copilot Kit — pourquoi pas un simple chat ?",
        "bullets": [
            "Un chat texte = limité aux mots",
            "Copilot Kit : streaming agent → composants React",
            "Génération de UI à la volée (graphes, tableaux, cards)",
            "L'agent décide quand afficher quoi",
            "Expérience vraiment agentique, pas juste « chatbot »",
        ],
        "notes": (
            "Un chat texte c'est limité. Avec Copilot Kit, l'agent peut générer des "
            "composants React à la volée — y compris des graphes Recharts. La différence "
            "entre « assistant » et « vraie UI agentique »."
        ),
    },
    {
        "type": "demo",
        "title": "Question NL → graphe dynamique",
        "steps": [
            "« Top 5 buteurs d'Argentine » dans le chat",
            "Agent génère SQL + spec graphe",
            "Front rend un bar chart en streaming",
        ],
        "notes": (
            "Je pose une question, l'agent renvoie données + spec de graphe, le front "
            "rend ça en bar chart en streaming. C'est le moment wow du talk — montrer "
            "que l'agent ne renvoie pas juste du texte."
        ),
    },
    {
        "type": "image",
        "title": "Architecture cloud — pipeline CI/CD",
        "image_path": "diagrams/adk_gcp_football_stats_agent_cicd.png",
        "caption": "Cloud Build + Bake + Artifact Registry → 3 services Cloud Run",
        "notes": (
            "Trois services Cloud Run buildés en parallèle via Bake, cache registry "
            "mode=max pour des rebuilds rapides. Path parallèle violet : adk deploy "
            "agent_engine pour le path managed."
        ),
    },
    {
        "type": "code",
        "title": "Dockerfile multi-stage avec uv",
        "language": "dockerfile",
        "code": (
            "FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder\n"
            "ENV APP_DIR=/usr/local/src/app\n"
            "WORKDIR ${APP_DIR}\n"
            "COPY pyproject.toml uv.lock ./\n"
            "RUN --mount=type=cache,target=/root/.cache/uv \\\n"
            "    uv sync --frozen --no-dev --no-install-project\n"
            "COPY football_stats_agent/ ./football_stats_agent/\n"
            "\n"
            "FROM python:3.11-slim\n"
            "WORKDIR /agents\n"
            "COPY --from=builder ${APP_DIR}/.venv ${APP_DIR}/.venv\n"
            "COPY --from=builder ${APP_DIR}/football_stats_agent/ \\\n"
            "     ./football_stats_agent/\n"
            "ENV PATH=\"${APP_DIR}/.venv/bin:$PATH\"\n"
            "ENTRYPOINT [\"adk\"]\n"
            "CMD [\"api_server\", \"--host\", \"0.0.0.0\", \"--port\", \"8080\"]"
        ),
        "notes": (
            "Builder + runtime séparés. L'image finale ne contient que le .venv et le "
            "code de l'agent — pas les outils de build. Image plus petite, surface "
            "d'attaque plus faible, démarrage plus rapide."
        ),
    },
    {
        "type": "code",
        "title": "Cloud Build pipeline",
        "language": "yaml",
        "code": (
            "steps:\n"
            "  - name: 'gcr.io/cloud-builders/docker'\n"
            "    script: |\n"
            "      docker buildx create --use\n"
            "      docker buildx bake --push\n"
            "\n"
            "  - name: 'google-cloud-cli:slim'\n"
            "    script: |\n"
            "      gcloud run deploy football-stats-api ...\n"
            "      gcloud run deploy agent-engine-proxy ...\n"
            "      gcloud run deploy football-stats-webapp ..."
        ),
        "notes": (
            "Bake centralise les builds (HCL). Cache registry mode=max = rebuilds "
            "instantanés quand seul le code Python change, pas les deps. Trois services "
            "déployés en une seule pipeline."
        ),
    },
    {
        "type": "bullets",
        "title": "Agent Engine — l'alternative managed",
        "bullets": [
            "Managed Reasoning Engine sur Vertex AI",
            "Playground console intégré (test sans front)",
            "Path : adk deploy agent_engine",
            "Trade-off : moins de contrôle, plus de managed",
            "Bon choix pour démo aux PMs / business",
        ],
        "notes": (
            "Si tu veux du fully-managed avec un Playground gratuit pour tes product "
            "managers, Agent Engine c'est ça. Le pattern reste le même côté code — c'est "
            "juste un autre endroit où déployer."
        ),
    },
    {
        "type": "image",
        "title": "Agent en local pour la boucle de dev",
        "image_path": "/Users/mazlum/my-projects/blogarticles/football-agent-adk-gemma-dmr/diagrams/adk_gemma_docker_model_runner.png",
        "caption": "ADK + Docker Model Runner + Gemma 4 — repo : football-agent-adk-gemma-dmr",
        "notes": (
            "Pendant la phase de tuning du prompt, je tourne sur Gemma local via Docker "
            "Model Runner. Zéro coût, itération rapide. ADK est model-agnostic donc on "
            "swap juste le modèle. Trade-off : qualité ↓ mais OK pour valider la logique."
        ),
    },
    {
        "type": "bullets",
        "title": "System instructions modulaires + golden datasets",
        "bullets": [
            "Splitter le prompt en fichiers .md (schema, rules, examples)",
            "Charger dynamiquement à la création de l'agent",
            "Plus facile à differ, reviewer, faire évoluer",
            "Golden dataset = N questions + réponses attendues",
            "Rejouer à chaque PR → détecter les régressions tôt",
        ],
        "notes": (
            "Le prompt système, c'est du code critique. Modularisez-le, versionnez-le, "
            "testez-le contre un golden dataset. Sinon vous ne saurez jamais quand vous "
            "avez régressé après avoir ajouté une règle métier."
        ),
    },
    {
        "type": "bullets",
        "title": "Validation SQL avant exécution",
        "bullets": [
            "Hallucination = full table scan = incident coûteux",
            "Pattern : LLM génère → validation → exécution",
            "Validations : parse SQL, dry-run, quota max bytes",
            "Repo dédié : football-agent-adk-validated",
            "Couche obligatoire en prod",
        ],
        "notes": (
            "Un agent qui génère un SELECT * sur 50M de lignes en prod, c'est un "
            "incident. Une couche de validation entre génération et exécution = sécurité "
            "+ cost control. Le repo séparé montre le pattern complet."
        ),
    },
    {
        "type": "bullets",
        "title": "Production concerns",
        "bullets": [
            "Observabilité — Vertex AI tracing + Cloud Trace",
            "Cost control — quota max bytes, dry-run, alerting",
            "RBAC — Row-level / column-level security sur BQ",
            "Session storage — Cloud SQL via ADK SessionService",
            "Audit logging — qui a demandé quoi, quand",
        ],
        "notes": (
            "Ces sujets méritent chacun un talk dédié. Je vous les liste pour ne rien "
            "oublier quand vous passerez en prod. Chacun a son repo / sa doc dans "
            "l'écosystème ADK et GCP."
        ),
    },
    {
        "type": "takeaways",
        "title": "À retenir",
        "items": [
            ("ADK + MCP", "Découpler agent et data source. Pattern réutilisable hors GCP."),
            ("System instructions modulaires + golden datasets", "Dès le jour 1, pas en post-mortem."),
            ("Validation SQL avant exécution", "Sécurité + cost control non négociables."),
        ],
        "notes": (
            "Si vous ne retenez que 3 choses : ADK + MCP pour le découplage, instructions "
            "modulaires + golden datasets dès le début, et validation SQL avant exécution. "
            "Le reste, vous le construirez en passant en prod."
        ),
    },
    {
        "type": "title",
        "title": "Merci !",
        "subtitle": "Questions ?",
        "footer": "github.com/tosun-si  •  Mazlum Tosun  •  @mazlumtosun",
        "notes": (
            "Repo open-source, slides disponibles en ligne. Pour les questions : RAG vs "
            "MCP, coûts réels en prod, sécurité des données sensibles — je prends tout."
        ),
    },
]
