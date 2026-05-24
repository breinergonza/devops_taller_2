#!/usr/bin/env python3
"""
Script de automatización para configurar alertas de New Relic.
Utiliza la API de NerdGraph (GraphQL) para crear una política de alertas
y las 5 condiciones descritas en el documento de Entrega 4.
"""
import os
import sys
import json
from pathlib import Path

# Cargar dotenv para soporte local si existe
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / '.env.local'
    if env_path.exists():
        load_dotenv(env_path)
    else:
        # Intentar con .env regular
        env_path = Path(__file__).resolve().parent.parent / '.env'
        if env_path.exists():
            load_dotenv(env_path)
except ImportError:
    pass

try:
    import requests
except ImportError:
    print("Error: Se requiere la libreria 'requests'. Instálala ejecutando: pip install requests")
    sys.exit(1)


def get_env_var(name, default=None, required=True):
    val = os.environ.get(name, default)
    if required and not val:
        print(f"Error: La variable de entorno '{name}' es requerida.")
        sys.exit(1)
    return val


# Cargar configuraciones de variables de entorno
API_KEY = get_env_var("NEW_RELIC_API_KEY")
ACCOUNT_ID = int(get_env_var("NEW_RELIC_ACCOUNT_ID"))
REGION = get_env_var("NEW_RELIC_REGION", default="US", required=False).upper()
APP_NAME = get_env_var("NEW_RELIC_APP_NAME", default="devops-taller-4-flask (production)", required=False)

# Endpoint de NerdGraph segun la region
GRAPHQL_URL = "https://api.eu.newrelic.com/graphql" if REGION == "EU" else "https://api.newrelic.com/graphql"

HEADERS = {
    "Content-Type": "application/json",
    "API-Key": API_KEY
}


def run_query(query, variables=None):
    """Ejecuta una consulta o mutacion en NerdGraph."""
    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    response = requests.post(GRAPHQL_URL, json=payload, headers=HEADERS)
    if response.status_code != 200:
        print(f"Error de red/servidor ({response.status_code}): {response.text}")
        sys.exit(1)

    result = response.json()
    if "errors" in result:
        print("Errores devueltos por la API de New Relic:")
        print(json.dumps(result["errors"], indent=2))
        return None

    return result["data"]


def get_or_create_policy(policy_name):
    """Busca o crea una politica de alerta con el nombre especificado."""
    print(f"Buscando politica de alertas: '{policy_name}'...")
    
    # Query para buscar politicas existentes
    search_query = """
    query($accountId: Int!) {
      actor {
        account(id: $accountId) {
          alerts {
            policiesSearch(searchCriteria: {nameLike: "%s"}) {
              policies {
                id
                name
              }
            }
          }
        }
      }
    }
    """ % policy_name

    res = run_query(search_query, {"accountId": ACCOUNT_ID})
    if res:
        policies = res["actor"]["account"]["alerts"]["policiesSearch"]["policies"]
        for p in policies:
            if p["name"] == policy_name:
                print(f"Politica encontrada. ID: {p['id']}")
                return int(p["id"])

    print(f"Politica no encontrada. Creando nueva politica '{policy_name}'...")
    create_mutation = """
    mutation($accountId: Int!, $name: String!) {
      alertsCreatePolicy(accountId: $accountId, policy: {name: $name, incidentPreference: PER_POLICY}) {
        id
        name
      }
    }
    """
    res = run_query(create_mutation, {"accountId": ACCOUNT_ID, "name": policy_name})
    if res and res.get("alertsCreatePolicy"):
        policy_id = int(res["alertsCreatePolicy"]["id"])
        print(f"Politica creada exitosamente. ID: {policy_id}")
        return policy_id
    
    print("Error al crear la politica.")
    sys.exit(1)


def delete_existing_condition_if_exists(policy_id, condition_name):
    """Busca y elimina una condicion existente con el mismo nombre para evitar duplicados."""
    list_query = """
    query($accountId: Int!, $policyId: Float!) {
      actor {
        account(id: $accountId) {
          alerts {
            nrqlConditionsSearch(searchCriteria: {policyId: $policyId}) {
              nrqlConditions {
                id
                name
              }
            }
          }
        }
      }
    }
    """
    res = run_query(list_query, {"accountId": ACCOUNT_ID, "policyId": float(policy_id)})
    if not res:
        return

    conditions = res["actor"]["account"]["alerts"]["nrqlConditionsSearch"]["nrqlConditions"]
    for cond in conditions:
        if cond["name"] == condition_name:
            print(f"Condicion duplicada detectada: '{condition_name}' (ID: {cond['id']}). Eliminando para recrear...")
            delete_mutation = """
            mutation($accountId: Int!, $id: ID!) {
              alertsConditionDelete(accountId: $accountId, id: $id) {
                id
              }
            }
            """
            run_query(delete_mutation, {"accountId": ACCOUNT_ID, "id": cond["id"]})
            print(f"Condicion {cond['id']} eliminada.")


def create_nrql_condition(policy_id, name, query, threshold, operator, duration_sec, description=""):
    """Crea una condicion de alerta NRQL estatica bajo la politica especificada."""
    print(f"Configurando condicion: '{name}'...")
    delete_existing_condition_if_exists(policy_id, name)

    mutation = """
    mutation(
      $accountId: Int!,
      $policyId: Float!,
      $name: String!,
      $query: String!,
      $threshold: Float!,
      $operator: AlertsNrqlConditionTermsOperator!,
      $duration: Int!,
      $description: String
    ) {
      alertsNrqlConditionStaticCreate(
        accountId: $accountId,
        policyId: $policyId,
        condition: {
          enabled: true,
          name: $name,
          description: $description,
          nrql: {
            query: $query
          },
          signal: {
            aggregationDelay: 120,
            aggregationMethod: EVENT_FLOW,
            aggregationWindow: 60,
            fillOption: NONE
          },
          terms: [
            {
              operator: $operator,
              priority: CRITICAL,
              threshold: $threshold,
              thresholdDuration: $duration,
              thresholdOccurrences: ALL
            }
          ]
        }
      ) {
        id
        name
      }
    }
    """

    variables = {
      "accountId": ACCOUNT_ID,
      "policyId": float(policy_id),
      "name": name,
      "query": query,
      "threshold": float(threshold),
      "operator": operator,
      "duration": int(duration_sec),
      "description": description
    }

    res = run_query(mutation, variables)
    if res and res.get("alertsNrqlConditionStaticCreate"):
        print(f"Condicion '{name}' creada con exito. ID: {res['alertsNrqlConditionStaticCreate']['id']}")
    else:
        print(f"Error al crear la condicion '{name}'")


def main():
    print("====================================================")
    print("  NEW RELIC ALERTS AUTOMATION SETUP SCRIPT")
    print("====================================================")
    print(f"Account ID : {ACCOUNT_ID}")
    print(f"Region     : {REGION}")
    print(f"App Name   : {APP_NAME}")
    print("----------------------------------------------------")

    policy_name = "devops-taller-4-alerts"
    policy_id = get_or_create_policy(policy_name)

    # 1. Error Rate > 5% por 5 minutos
    create_nrql_condition(
        policy_id=policy_id,
        name="High Error Rate (> 5%)",
        query=f"SELECT percentage(count(*), WHERE error IS true) FROM Transaction WHERE appName = '{APP_NAME}'",
        threshold=5.0,
        operator="ABOVE",
        duration_sec=300,
        description="Falla si la tasa de error del microservicio supera el 5% sostenidamente durante 5 minutos."
    )

    # 2. Apdex < 0.8 por 5 minutos
    create_nrql_condition(
        policy_id=policy_id,
        name="Low Apdex Satisfaction (< 0.8)",
        query=f"SELECT apdex(duration, t: 0.5) FROM Transaction WHERE appName = '{APP_NAME}'",
        threshold=0.8,
        operator="BELOW",
        duration_sec=300,
        description="Falla si el nivel de satisfaccion Apdex (umbral T=0.5s) cae por debajo de 0.8 por 5 minutos."
    )

    # 3. Web response time p95 > 1 s por 5 minutos
    create_nrql_condition(
        policy_id=policy_id,
        name="Slow Response Time p95 (> 1s)",
        query=f"SELECT percentile(duration, 95) FROM Transaction WHERE appName = '{APP_NAME}'",
        threshold=1.0,
        operator="ABOVE",
        duration_sec=300,
        description="Falla si el tiempo de respuesta p95 de transacciones web supera 1 segundo por 5 minutos."
    )

    # 4. Database response time p95 > 500 ms por 5 minutos
    create_nrql_condition(
        policy_id=policy_id,
        name="Slow Database Queries p95 (> 500ms)",
        query=f"SELECT percentile(databaseDuration, 95) FROM Transaction WHERE appName = '{APP_NAME}'",
        threshold=0.5,
        operator="ABOVE",
        duration_sec=300,
        description="Falla si el tiempo p95 consumido en consultas a base de datos PostgreSQL supera 500 ms por 5 minutos."
    )

    # 5. Container down / service unhealthy (Falta de transacciones / Loss of Signal)
    create_nrql_condition(
        policy_id=policy_id,
        name="Container or Service Down (No Transactions)",
        query=f"SELECT count(*) FROM Transaction WHERE appName = '{APP_NAME}'",
        threshold=1.0,
        operator="BELOW",
        duration_sec=300,
        description="Falla si no se registran transacciones web en el microservicio en 5 minutos (posible contenedor caido)."
    )

    print("----------------------------------------------------")
    print("¡Configuracion de alertas completada exitosamente!")
    print("====================================================")


if __name__ == "__main__":
    main()
