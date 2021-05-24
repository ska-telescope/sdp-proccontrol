import os
import logging
from unittest.mock import patch

import pytest

import ska_sdp_config

from ska_sdp_proccontrol import processing_controller

LOG = logging.getLogger(__name__)

MOCK_ENV_VARS = {
    "SDP_CONFIG_BACKEND": "memory",
    "SDP_CONFIG_HOST": "localhost",
    "SDP_HELM_NAMESPACE": "helm",
}

PROCESSING_BLOCK_ID = "pb-test-20210118-00000"
DEPLOYMENT_ID = f"proc-{PROCESSING_BLOCK_ID}-workflow"
WORKFLOW_TYPE = "batch"
WORKFLOW_ID = "test_batch"
WORKFLOW_VERSION = "0.2.1"
WORKFLOW_IMAGE = "testregistry/workflow-test-batch:0.2.1"


@pytest.fixture
@patch.dict(os.environ, MOCK_ENV_VARS)
def config_and_controller_fixture():
    """
    Fixture to create config and processing controller objects with a workflow
    definition and processing block in the config DB.
    """
    config = ska_sdp_config.Config()
    controller = processing_controller.ProcessingController()

    # Workflow definition
    workflow = {"image": WORKFLOW_IMAGE}

    # Processing block
    pb = ska_sdp_config.ProcessingBlock(
        id=PROCESSING_BLOCK_ID,
        sbi_id="test",
        workflow={
            "type": WORKFLOW_TYPE,
            "id": WORKFLOW_ID,
            "version": WORKFLOW_VERSION,
        },
        parameters={},
        dependencies=[],
    )

    for txn in config.txn():
        txn.create_workflow(WORKFLOW_TYPE, WORKFLOW_ID, WORKFLOW_VERSION, workflow)
        txn.create_processing_block(pb)

    return config, controller


def clear_config(config):
    """
    Remove all of the workflow definitions, processing blocks and deployments
    from the config DB.
    """
    config.backend.delete("/workflow", must_exist=False, recursive=True)
    config.backend.delete("/pb", must_exist=False, recursive=True)
    config.backend.delete("/deploy", must_exist=False, recursive=True)


@patch.dict(os.environ, MOCK_ENV_VARS)
def test_controller_main_loop_start_workflow(config_and_controller_fixture):
    """
    Test that the ProcessingController.main_loop starts the
    workflow deployment based on the existing processing blocks in the config db.

    This only tests that the main_loop starts the deployment if
    the processing block doesn't have a state, i.e. no deployments have been started based on it.
    """
    config, controller = config_and_controller_fixture

    # Perform various actions on the processing block
    # In this case, it will start the workflow deployment
    # of the just entered processing block
    controller.main_loop()

    for txn in config.txn():
        assert controller._get_pb_status(txn, PROCESSING_BLOCK_ID) == "STARTING"
        deployment_ids = txn.list_deployments()

        LOG.info(deployment_ids)
        assert len(deployment_ids) == 1
        # deployment id generated in: ska_sdp_proccontrol.processing_controller.
        # ProcessingController._start_workflow, based on the pb_id
        assert DEPLOYMENT_ID in deployment_ids

        deployment = txn.get_deployment(DEPLOYMENT_ID)
        assert deployment.args["values"]["wf_image"] == WORKFLOW_IMAGE

    clear_config(config)


@patch("signal.signal")
@patch("sys.exit")
def test_main(mock_exit, mock_signal):
    processing_controller.main(backend="memory")
    processing_controller.terminate(None, None)


@patch.dict(os.environ, MOCK_ENV_VARS)
def test_proc_control_start_new_pb_workflows(config_and_controller_fixture):
    """
    ProcessingController._start_new_pb_workflows correctly starts
    a workflow of a newly added processing block.
    """
    config, controller = config_and_controller_fixture

    processing_block_ids = [PROCESSING_BLOCK_ID]
    for watcher in config.watcher():
        for txn in config.txn():
            assert controller._get_pb_status(txn, PROCESSING_BLOCK_ID) is None

        controller._start_new_pb_workflows(watcher, processing_block_ids)

        for txn in config.txn():
            assert controller._get_pb_status(txn, PROCESSING_BLOCK_ID) == "STARTING"

    clear_config(config)


@patch.dict(os.environ, MOCK_ENV_VARS)
def test_proc_control_release_pbs_with_finished_dependencies(
    config_and_controller_fixture,
):
    """
    ProcessingController._release_pbs_with_finished_dependencies correctly
    sets the 'resources_available' state key of the processing block to True
    if the status of the pb is WAITING and all dependencies have finished.

    Here the created pb does not have dependencies. (see fixture)
    """
    config, controller = config_and_controller_fixture

    processing_block_ids = [PROCESSING_BLOCK_ID]
    for watcher in config.watcher():
        # start a workflow
        controller._start_new_pb_workflows(watcher, processing_block_ids)

        # _release_pbs_with_finished_dependencies works on
        # processing blocks with the following state
        new_state = {"resources_available": False, "status": "WAITING"}
        for txn in config.txn():
            txn.update_processing_block_state(PROCESSING_BLOCK_ID, new_state)

        controller._release_pbs_with_finished_dependencies(
            watcher, processing_block_ids
        )

    expected_pb_state = {"resources_available": True, "status": "WAITING"}
    for txn in config.txn():
        assert txn.get_processing_block_state(PROCESSING_BLOCK_ID) == expected_pb_state

    clear_config(config)


@pytest.mark.skip("See TODO in test.")
@patch.dict(os.environ, MOCK_ENV_VARS)
def test_delete_deployments_without_pb(config_and_controller_fixture):
    """
    ProcessingControl._delete_deployments_without_pb successfully removes
    deployments without a processing block
    """
    config, controller = config_and_controller_fixture

    processing_block_ids = [PROCESSING_BLOCK_ID]
    for watcher in config.watcher():
        # start a workflow
        controller._start_new_pb_workflows(watcher, processing_block_ids)

    # remove the processing block, but leave the deployment
    config.backend.delete("/pb", must_exist=False, recursive=True)

    for watcher in config.watcher():
        for txn in config.txn():
            assert len(txn.list_deployments()) == 1

        # TODO: this doesn't work. MemoryBackend.list_keys fails to
        #  find the deployment even though it's there; problem with "tagging" with "depth"?
        controller._delete_deployments_without_pb(
            watcher, processing_block_ids, [DEPLOYMENT_ID]
        )

    for txn in config.txn():
        assert len(txn.list_deployments()) == 0

    clear_config(config)
