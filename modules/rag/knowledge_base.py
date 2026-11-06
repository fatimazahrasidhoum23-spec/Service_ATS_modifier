# modules/rag/knowledge_base.py

knowledge_documents = [

    # ══════════════════════════════════════
    # LANGAGES DE PROGRAMMATION
    # ══════════════════════════════════════
    "Python langage programmation backend Django Flask FastAPI pandas numpy scipy matplotlib seaborn scikit-learn tensorflow pytorch keras machine learning data science automation scripts",
    "Java langage programmation Spring Spring Boot Hibernate JPA Maven Gradle microservices enterprise backend API REST JEE Jakarta",
    "JavaScript TypeScript langage programmation frontend backend Node.js Express.js NestJS React Angular Vue webpack babel npm yarn",
    "C# dotnet ASP.NET Core Entity Framework LINQ WPF Xamarin Unity Microsoft Azure backend API REST",
    "PHP Laravel Symfony CodeIgniter WordPress Drupal Composer backend web développement",
    "C C++ Qt embedded systèmes temps réel performance bas niveau kernel drivers",
    "Swift iOS macOS développement mobile Apple Xcode UIKit SwiftUI",
    "Kotlin Android développement mobile JVM Spring Backend",
    "Go Golang backend microservices performance concurrence Docker Kubernetes cloud",
    "Rust systèmes performance sécurité mémoire backend WebAssembly",
    "Ruby Ruby on Rails backend web développement",
    "Scala Spark big data fonctionnel JVM",
    "R statistiques data science analyse données visualisation ggplot dplyr",

    # ══════════════════════════════════════
    # FRAMEWORKS WEB FRONTEND
    # ══════════════════════════════════════
    "React ReactJS React.js bibliothèque JavaScript frontend composants UI SPA hooks Redux Context API TypeScript Next.js",
    "Angular AngularJS framework TypeScript frontend SPA composants services RxJS NgRx Material CLI",
    "Vue VueJS Vue.js framework JavaScript frontend progressif Vuex Pinia Nuxt.js composants",
    "HTML5 CSS3 SASS SCSS Less frontend développement web responsive design Bootstrap Tailwind",
    "jQuery JavaScript bibliothèque DOM manipulation frontend legacy",

    # ══════════════════════════════════════
    # FRAMEWORKS BACKEND
    # ══════════════════════════════════════
    "FastAPI framework Python moderne REST API async await uvicorn pydantic OpenAPI Swagger microservices",
    "Django framework Python web ORM admin REST API DRF authentification PostgreSQL",
    "Flask framework Python micro web léger REST API Werkzeug Jinja2",
    "Spring Boot Java framework microservices REST API Hibernate JPA Security Maven",
    "Express.js Node.js framework JavaScript backend REST API middleware",
    "NestJS TypeScript framework Node.js backend modulaire REST API GraphQL",
    "Laravel PHP framework web ORM Eloquent MVC authentification REST API",
    "Symfony PHP framework web composants MVC REST API Doctrine",

    # ══════════════════════════════════════
    # BASES DE DONNÉES
    # ══════════════════════════════════════
    "PostgreSQL SGBD base données relationnelle SQL open source ACID transactions indexes performances",
    "MySQL MariaDB SGBD base données relationnelle SQL web applications performances",
    "Oracle SGBD base données relationnelle entreprise SQL PL/SQL performances",
    "SQL Server Microsoft SGBD base données relationnelle T-SQL entreprise",
    "MongoDB NoSQL base données documents JSON flexible scalable Atlas",
    "Redis cache mémoire base données clé-valeur pub/sub sessions performances temps réel",
    "Elasticsearch moteur recherche NoSQL full-text search analytics logs Kibana",
    "Cassandra NoSQL base données distribuée big data haute disponibilité",
    "SQLite base données légère embarquée mobile fichier",
    "Firebase Firestore Google base données temps réel NoSQL cloud mobile",
    "SQL requêtes jointures index transactions procédures stockées optimisation base données",

    # ══════════════════════════════════════
    # INTELLIGENCE ARTIFICIELLE ET ML
    # ══════════════════════════════════════
    "Machine Learning ML apprentissage automatique modèles prédictifs classification régression clustering scikit-learn",
    "Deep Learning apprentissage profond réseaux neurones CNN RNN LSTM Transformer TensorFlow PyTorch Keras",
    "NLP Natural Language Processing traitement langage naturel BERT GPT transformers spaCy NLTK text mining",
    "Computer Vision vision par ordinateur OpenCV détection objets reconnaissance images CNN YOLO",
    "Data Science science données analyse statistiques Python R pandas numpy matplotlib seaborn Jupyter",
    "MLOps déploiement modèles ML pipeline MLflow Kubeflow modèles production monitoring",
    "AI Intelligence Artificielle agents LLM LangChain RAG embeddings vectoriel ChromaDB",
    "Reinforcement Learning apprentissage renforcement agents récompenses Q-learning",
    "Feature Engineering préparation données normalisation encodage sélection features",
    "Modèles ML régression logistique SVM Random Forest XGBoost LightGBM réseaux neurones",

    # ══════════════════════════════════════
    # DEVOPS ET CLOUD
    # ══════════════════════════════════════
    "Docker conteneurisation images conteneurs Dockerfile docker-compose microservices déploiement",
    "Kubernetes K8s orchestration conteneurs pods services deployments cluster scalabilité",
    "CI/CD intégration continue déploiement continu pipeline automatisation tests Jenkins GitHub Actions GitLab CI",
    "AWS Amazon Web Services cloud EC2 S3 RDS Lambda ECS EKS CloudFormation infrastructure",
    "Azure Microsoft cloud services VMs containers AKS DevOps infrastructure",
    "GCP Google Cloud Platform Compute Engine Cloud Run Kubernetes Engine BigQuery",
    "Terraform Infrastructure as Code IaC cloud provisioning automatisation",
    "Ansible configuration management automatisation déploiement infrastructure",
    "Linux administration systèmes bash shell scripting Ubuntu CentOS RedHat",
    "Nginx Apache serveur web reverse proxy load balancer configuration",
    "Monitoring observabilité Prometheus Grafana ELK Stack logs métriques alertes",

    # ══════════════════════════════════════
    # ARCHITECTURE ET DESIGN
    # ══════════════════════════════════════
    "Microservices architecture distribuée services indépendants API Gateway événements scalabilité",
    "API REST RESTful HTTP endpoints JSON services web architecture stateless",
    "GraphQL API query language flexible typage fort mutations subscriptions",
    "Kafka RabbitMQ messaging broker événements asynchrones pub/sub streaming",
    "Architecture hexagonale Clean Architecture DDD Domain Driven Design patterns SOLID",
    "Design Patterns Singleton Factory Observer Strategy MVC MVP MVVM",
    "Sécurité JWT OAuth2 SSO authentification autorisation HTTPS chiffrement",

    # ══════════════════════════════════════
    # OUTILS DE DÉVELOPPEMENT
    # ══════════════════════════════════════
    "Git GitHub GitLab Bitbucket contrôle versions branches merge pull request code review",
    "VS Code Visual Studio IntelliJ PyCharm IDE éditeur développement plugins",
    "Jira Trello Asana gestion projet agile scrum kanban tickets sprints",
    "Postman Insomnia test API REST endpoints documentation",
    "Swagger OpenAPI documentation API spécification REST",

    # ══════════════════════════════════════
    # MÉTHODES ET SOFT SKILLS
    # ══════════════════════════════════════
    "Agile Scrum Sprint Kanban méthodes gestion projet itératif daily stand-up retrospective",
    "TDD Test Driven Development BDD tests unitaires intégration Pytest JUnit Jasmine",
    "Code review pair programming collaboration équipe bonnes pratiques",
    "Documentation technique rédaction spécifications API README",

    # ══════════════════════════════════════
    # NIVEAUX EXPÉRIENCE
    # ══════════════════════════════════════
    "Junior développeur débutant 0 1 2 ans expérience stage entry level formation récente",
    "Mid-level développeur confirmé 2 3 4 5 ans expérience autonome projets réalisés",
    "Senior développeur expert 5 6 7 8 10 ans expérience lead tech architecture décisions",
    "Tech Lead architecte solution référent technique équipe mentoring code review",

    # ══════════════════════════════════════
    # FORMATION ET DIPLÔMES
    # ══════════════════════════════════════
    "Bac+2 BTS DUT développement informatique réseaux systèmes",
    "Bac+3 Licence informatique génie logiciel systèmes réseaux",
    "Bac+4 Master 1 informatique développement logiciel",
    "Bac+5 Master ingénieur informatique génie logiciel systèmes distribués",
    "Doctorat PhD recherche informatique intelligence artificielle",
    "Bootcamp formation intensive développement web fullstack",
    "Certifications AWS Azure Google Cloud Kubernetes Docker professionnel",
]