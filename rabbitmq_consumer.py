"""
rabbitmq_consumer.py
────────────────────
Consomme "ats.scoring.queue" envoyée par Spring Boot (OffreRh).
Pour chaque message :
  1. Télécharge le CV depuis MinIO via l'URL fournie
  2. Fait le scoring CV ↔ Offre avec les modules ATS existants
  3. Publie le résultat dans "ats.result.queue" → Spring Boot
"""

import json
import os
import threading
import logging
import requests
import pika

logger = logging.getLogger(__name__)

# ── Configuration RabbitMQ ────────────────────────────────────────────────────
RABBITMQ_HOST     = os.getenv("RABBITMQ_HOST", "localhost")
RABBITMQ_PORT     = 5672
RABBITMQ_USER     = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASS     = os.getenv("RABBITMQ_PASS", "guest")
RABBITMQ_VHOST    = "/"

ATS_EXCHANGE        = "ats.exchange"
SCORING_QUEUE       = "ats.scoring.queue"
SCORING_ROUTING_KEY = "ats.scoring"
RESULT_QUEUE        = "ats.result.queue"
RESULT_ROUTING_KEY  = "ats.result"


def _get_connection() -> pika.BlockingConnection:
    credentials = pika.PlainCredentials(RABBITMQ_USER, RABBITMQ_PASS)
    params = pika.ConnectionParameters(
        host=RABBITMQ_HOST,
        port=RABBITMQ_PORT,
        virtual_host=RABBITMQ_VHOST,
        credentials=credentials,
        heartbeat=60,
        blocked_connection_timeout=300,
    )
    return pika.BlockingConnection(params)


def _declare_topology(channel):
    """Déclare exchange + queues (idempotent — sûr si Spring Boot a déjà déclaré)."""
    channel.exchange_declare(exchange=ATS_EXCHANGE, exchange_type="topic", durable=True)
    channel.queue_declare(queue=SCORING_QUEUE, durable=True)
    channel.queue_bind(queue=SCORING_QUEUE, exchange=ATS_EXCHANGE, routing_key=SCORING_ROUTING_KEY)
    channel.queue_declare(queue=RESULT_QUEUE, durable=True)
    channel.queue_bind(queue=RESULT_QUEUE, exchange=ATS_EXCHANGE, routing_key=RESULT_ROUTING_KEY)


def _download_cv_text(cv_url: str, parser) -> str:
    """Télécharge le PDF depuis MinIO et extrait le texte avec CVParser."""
    logger.info(f"[Consumer] Téléchargement CV : {cv_url}")
    response = requests.get(cv_url, timeout=30)
    response.raise_for_status()
    return parser.parse(response.content, cv_url.split("/")[-1])


def _publish_result(channel, result_payload: dict):
    """Publie le résultat de scoring dans ats.result.queue → Spring Boot."""
    channel.basic_publish(
        exchange=ATS_EXCHANGE,
        routing_key=RESULT_ROUTING_KEY,
        body=json.dumps(result_payload),
        properties=pika.BasicProperties(
            delivery_mode=2,
            content_type="application/json",
        ),
    )
    logger.info(f"[Consumer] Résultat publié → candidatureId={result_payload.get('candidatureId')}")


def _on_scoring_message(channel, method, properties, body, ats_modules: dict):
    """
    Callback déclenché pour chaque message reçu dans ats.scoring.queue.
    Utilise les modules ATS déjà initialisés dans main.py.
    """
    try:
        data = json.loads(body)
        logger.info(f"[Consumer] Message reçu — candidatureId={data.get('candidatureId')} "
                    f"offreId={data.get('offreId')}")

        parser      = ats_modules["parser"]
        job_parser  = ats_modules["job_parser"]
        scorer      = ats_modules["scorer"]
        store       = ats_modules["store"]
        hr_learner  = ats_modules["hr_learner"]
        retriever   = ats_modules["retriever"]

        # 1. Extraire le texte du CV
        cv_url  = data.get("cvUrl", "")
        cv_text = _download_cv_text(cv_url, parser)

        # 2. Parser l'offre
        offre_description = data.get("offreDescription", "")
        offre_titre       = data.get("offreTitre", "")
        offre_id_str      = str(data.get("offreId"))

        parsed_offer = job_parser.parse_text(offre_description)
        parsed_offer["job_offer_id"] = offre_id_str
        parsed_offer["title"]        = offre_titre

        if not store.get_offer(offre_id_str):
            store.save_offer(offre_id_str, parsed_offer)

        job_offer_text = job_parser.to_job_offer_text(parsed_offer)

        # 3. Contexte RAG
        rag_context = retriever.get_context(
            query=f"{cv_text} {offre_description}", k=5
        )

        # 4. Scoring
        result = scorer.calculate(
            cv_text=cv_text,
            job_offer=job_offer_text,
            rag_context=rag_context,
        )

        if len(hr_learner.feedback_history) > 0:
            result = hr_learner.apply_weights_to_score(result)

        candidat_email = data.get("candidatEmail", f"candidat_{data.get('candidatureId')}")

        store.save_score(
            candidate_id=candidat_email,
            job_offer_id=offre_id_str,
            score_result=result,
        )

        # 5. Publier le résultat vers Spring Boot
        result_payload = {
            "candidatureId":  data.get("candidatureId"),
            "candidatEmail":  candidat_email,
            "offreId":        data.get("offreId"),
            "finalScore":     result.get("final_score"),
            "grade":          result.get("grade"),
            "recommendation": result.get("recommendation"),
            "breakdown":      result.get("breakdown", {}),
            "hrAdjusted":     result.get("hr_adjusted", False),
        }
        _publish_result(channel, result_payload)

        # 6. Accusé de réception
        channel.basic_ack(delivery_tag=method.delivery_tag)
        logger.info(f"[Consumer] ✅ Scoring terminé — score={result.get('final_score')} grade={result.get('grade')}")

    except Exception as e:
        logger.error(f"[Consumer] ❌ Erreur : {e}", exc_info=True)
        channel.basic_nack(delivery_tag=method.delivery_tag, requeue=False)


def start_consumer(ats_modules: dict):
    """
    Démarre le consumer RabbitMQ dans un thread daemon.
    Appelé depuis main.py au startup de FastAPI.

    ats_modules = {
        "parser":     CVParser instance,
        "job_parser": JobOfferParser instance,
        "scorer":     FinalScorer instance,
        "store":      ScoreStore instance,
        "hr_learner": HRLearner instance,
        "retriever":  RAGRetriever instance,
    }
    """

    def _run():
        while True:
            try:
                logger.info("[Consumer] Connexion à RabbitMQ...")
                connection = _get_connection()
                channel    = connection.channel()

                _declare_topology(channel)
                channel.basic_qos(prefetch_count=1)

                channel.basic_consume(
                    queue=SCORING_QUEUE,
                    on_message_callback=lambda ch, method, props, body:
                        _on_scoring_message(ch, method, props, body, ats_modules),
                )

                logger.info(f"[Consumer] ✅ En écoute sur '{SCORING_QUEUE}'")
                channel.start_consuming()

            except pika.exceptions.AMQPConnectionError as e:
                logger.warning(f"[Consumer] Connexion perdue, reconnexion dans 5s... ({e})")
                import time; time.sleep(5)
            except Exception as e:
                logger.error(f"[Consumer] Erreur inattendue : {e}", exc_info=True)
                import time; time.sleep(5)

    thread = threading.Thread(target=_run, daemon=True, name="rabbitmq-consumer")
    thread.start()
    logger.info("[Consumer] Thread RabbitMQ démarré en arrière-plan")
