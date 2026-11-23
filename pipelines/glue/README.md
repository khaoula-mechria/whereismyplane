# pipelines/glue

Pas de job ETL Glue dans le déploiement de test : la préparation tourne dans l'étape SageMaker Processing `Prepare`, avec le code local testé ([ADR-0018](../../docs/05-decisions/adr/0018-aws-test-deployment-architecture.md), proposée). Glue sert de **catalogue** (base `aeropulse`, table `flights` avec projection de partitions, `infra/stacks/data_stack.py`).
