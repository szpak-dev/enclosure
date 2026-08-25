from django.db import models


class GateSatisfactionModel(models.Model):
    identifier = models.UUIDField(primary_key=True)
    plan_run = models.ForeignKey("PlanRunModel", on_delete=models.CASCADE, related_name="gate_satisfactions")
    gate_id = models.CharField(max_length=255)
    satisfaction_key = models.CharField(max_length=300, unique=True)
    evidence = models.JSONField(default=dict)


class OperationExecutionModel(models.Model):
    identifier = models.UUIDField(primary_key=True)
    plan_run = models.ForeignKey("PlanRunModel", on_delete=models.CASCADE, related_name="operation_executions")
    operation_id = models.CharField(max_length=255)
    execution_key = models.CharField(max_length=300, unique=True)
    status = models.CharField(max_length=32, default="complete")
    output = models.JSONField(default=dict)


class PlanArtifactModel(models.Model):
    identifier = models.UUIDField(primary_key=True)
    plan_run = models.ForeignKey("PlanRunModel", on_delete=models.CASCADE, related_name="artifacts")
    artifact_id = models.CharField(max_length=255)
    artifact_key = models.CharField(max_length=300, unique=True)
    payload = models.JSONField(default=dict)


class PlanDefinitionModel(models.Model):
    identifier = models.UUIDField(primary_key=True)
    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField()
    publication_key = models.CharField(max_length=300, unique=True)
    start_stage_id = models.CharField(max_length=255)
    stages = models.JSONField(default=list)
    transitions = models.JSONField(default=list)
    gates = models.JSONField(default=list)
    operations = models.JSONField(default=list)
    artifacts = models.JSONField(default=list)


class PlanRunModel(models.Model):
    identifier = models.UUIDField(primary_key=True)
    definition = models.ForeignKey(PlanDefinitionModel, on_delete=models.PROTECT, related_name="runs")
    definition_version = models.PositiveIntegerField()
    current_stage_id = models.CharField(max_length=255)
    current_input = models.JSONField(default=dict)
    status = models.CharField(max_length=32)
    revision = models.PositiveIntegerField(default=0)


class StageSubmissionModel(models.Model):
    identifier = models.UUIDField(primary_key=True)
    plan_run = models.ForeignKey(PlanRunModel, on_delete=models.CASCADE, related_name="submissions")
    stage_id = models.CharField(max_length=255)
    payload = models.JSONField(default=dict)
