# CFP (FR) — Football Agent ADK + Copilot Kit

Notes réutilisables pour soumettre ce talk à des Call for Papers
francophones. Chaque section peut être copiée telle quelle dans le
formulaire de la conf.

---

## Titre

> Qui a marqué le plus de buts ? construire un agent IA qui interroge des données en langage naturel

---

## Abstract

Concevoir une application agentique de bout en bout reste un défi dès qu'il s'agit d'intégrer des données réelles et des règles métiers.

Dans ce talk, je présente un cas concret : un agent de statistiques sur la Coupe du monde de football ⚽, capable de répondre à des questions en langage naturel, de générer et exécuter des requêtes SQL, puis de restituer les résultats de manière compréhensible, accompagnés de graphiques générés dynamiquement dans une UI conversationnelle.

Nous verrons comment construire cet agent avec le framework Agent Development Kit (ADK), en combinant prompting et règles métiers pour produire des requêtes fiables. L'agent est connecté à BigQuery via le protocole MCP et déployé sur Google Cloud, avec différents modes d'exécution (Cloud Run et Agent Engine).

L'objectif est d'illustrer, à travers ce cas concret, une architecture agentique complète ainsi que les choix de conception et de déploiement nécessaires pour passer à la production. Même si cette implémentation s'appuie sur Google Cloud, les patterns présentés restent réutilisables avec d'autres infrastructures et sources de données exposées via MCP.

---

## Elevator pitch (court, format Twitter / résumé bref)

> Un agent IA qui répond en français à des questions sur la Coupe du Monde 2022, génère du SQL via MCP et dessine ses propres graphiques dans une UI conversationnelle. Démo end-to-end sur Google Cloud — mais les patterns (ADK, MCP, prompts modulaires, UI agentique) sont transposables à n'importe quelle infra.

---

## Public visé

Talk de niveau intermédiaire pour développeurs front / back / data, DevOps / SRE — et plus largement pour tout dev qui veut voir un vrai stack agentique au-delà du "hello world". Bases Python et curiosité pour les LLM suffisent — pas besoin d'avoir touché à ADK ni MCP avant.

---

## Takeaways

À la fin de la session, les participants repartiront avec :

1. **Un mental model clair** d'ADK et de comment il se positionne face aux autres frameworks (LangChain, LlamaIndex).
2. **Une compréhension pratique de MCP** : à quoi sert le protocole et ce qu'apporte un serveur MCP managé par le cloud provider.
3. **Deux chemins de déploiement** comparés en live (Cloud Run vs Agent Engine), avec leurs trade-offs réels (cold start, observabilité, coût, contrôle).
4. **Un pattern de prompts modulaires** : éclater le system prompt en `.md` par concern (rôle, schéma, workflow, règles métier, visualisation) pour que les non-devs puissent les relire et les éditer.
5. **Une recette de visualisation conversationnelle** : faire dessiner un agent LLM dans une UI React via Copilot Kit + Recharts, sans coder un parseur custom par type de question.
6. **Les vrais pièges prod** : env vars subtiles, IAM, exporters OpenTelemetry, choix d'extras `pyproject.toml` — toute la dette technique qu'un blog post idéalisé passe sous silence.

---

## Stack technique

- **Agent** : Google ADK 2.1 (`LlmAgent`, AgentRegistry, MCP toolset)
- **Modèle** : Gemini 2.5 Flash via Vertex AI
- **Données** : BigQuery (jeu de données Coupe du Monde 2022)
- **MCP** : serveur BigQuery MCP managé Google, découvert via Agent Registry
- **API agent** : `adk api_server` (FastAPI) déployé sur Cloud Run
- **Runtime managé** : Vertex AI Agent Engine (alias Agent Platform depuis le rebrand 2026)
- **Frontend conversationnel** : Next.js + Copilot Kit + Recharts pour les graphiques dynamiques
- **Packaging Python** : uv + Docker multi-stage + Docker Bake
- **CI/CD** : Cloud Build avec registry cache
- **Observabilité** : OpenTelemetry + Cloud Trace + onglet Trace d'Agent Platform

---

## Format

- **Durée** : 45 minutes
- **Découpage** : ~60% démo live + ~40% slides architecture
- **Architecture E2E** : la session déroule l'enchaînement complet, du dev local (Docker Compose qui orchestre l'agent ADK, le serveur MCP et la webapp Copilot Kit côte à côte) au déploiement serverless sur Google Cloud (Cloud Run + Agent Engine, pilotés par Cloud Build). Le passage local → prod illustre concrètement les choix de packaging Docker, le pipeline CI/CD et les différences de runtime entre les deux mondes.
- **Démos** : 3 questions sur le dataset (top buteurs, comparaison Mbappé vs Messi, joueurs de Lille face à Mbappé) qui font monter en complexité — bar chart simple, puis multi-séries, puis récit data avec twist local. Les démos tournent en local via Docker Compose (`adk web` + webapp Copilot Kit + MCP) ; la version prod déployée sur Cloud Run et le Playground Agent Platform sont montrés à la fin.

---

## Notes complémentaires pour l'organisation

- Le frontend embarqué dans ce repo est une UI **Next.js + Copilot Kit** qui rend les réponses de l'agent sous forme de **graphiques Recharts** (bar / pie / line, mono ou multi-séries) directement dans la conversation. C'est cette UI qui sert à montrer un agent "production-ready" et user-friendly, pas juste un chat technique. Pendant la démo, je m'appuie aussi sur l'UI fournie out-of-the-box par `adk web` (livrée par le framework ADK, pas codée dans le repo) pour montrer l'agent brut et son DAG d'exécution.
- L'agent est volontairement **en lecture seule sur BigQuery** au niveau IAM (rôles `bigquery.dataViewer` + `bigquery.jobUser`), ce qui sert d'exemple concret de défense en profondeur pendant la partie gouvernance.

---

## Références

- 📦 **Code source** : https://github.com/tosun-si/football-agent-adk-copilotkit
- 📝 **Article Medium détaillé** : https://medium.com/google-cloud/end-to-end-ai-agent-on-gcp-adk-bigquery-mcp-agent-engine-and-cloud-run-4843fec27c13
- 🎞️ **Slides (exemple, version DevLille)** : https://docs.google.com/presentation/d/19iBG2qq_2fFLu2J2NDfEkp0fsZD2Lzu9/edit?usp=sharing&ouid=107222582194830665741&rtpof=true&sd=true
- 🎨 **Diagrammes d'architecture** : dossier `diagrams/` du repo
