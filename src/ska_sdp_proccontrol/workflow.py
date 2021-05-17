"""
Temporary functions for reading and writing workflow definitions. They will be
replaced by methods in the transaction class in the configuration library.
"""

WORKFLOW_PREFIX = "workflow"


def workflow_path(type, id, version):
    return f"/{WORKFLOW_PREFIX}/{type}:{id}:{version}"


def create_workflow(txn, type, id, version, workflow):
    txn._create(workflow_path(type, id, version), workflow)


def get_workflow(txn, type, id, version):
    return txn._get(workflow_path(type, id, version))
