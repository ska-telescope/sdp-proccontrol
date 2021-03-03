import os
import logging
from unittest.mock import patch

import pytest

from ska_sdp_proccontrol import processing_controller

import ska_sdp_config
import workflows_test

LOG = logging.getLogger(__name__)

MOCK_ENV_VARS = {
    "SDP_CONFIG_BACKEND": "memory",
    "SDP_CONFIG_HOST": "localhost",
    "SDP_HELM_NAMESPACE": 'helm',
}

PROCESSING_BLOCK_ID = "pb-test-20210118-00000"


@pytest.fixture
@patch.dict(os.environ, MOCK_ENV_VARS)
def controller_and_config_fixture():
    """
    Fixture to create processing controller and config objects
    with a newly added processing block to run the test_batch workflow
    """
    controller = processing_controller.ProcessingController(
        workflows_test.SCHEMA, workflows_test.WORKFLOWS, 1
    )

    # Annoyingly requests doesn't support local (file) URLs, so redirect. It is possible to
    # create an adapter for this, but that seems like overkill.
    controller._workflows.update_url = controller._workflows.update_file

    # This is run in controller.main_loop(), but it is needed for other method tests here.
    controller._workflows.update_url(workflows_test.WORKFLOWS)

    wf = {"type": "batch", "id": "test_batch", "version": "0.2.1"}
    pb = ska_sdp_config.ProcessingBlock(
        id=PROCESSING_BLOCK_ID,
        sbi_id="test",
        workflow=wf,
        parameters={},
        dependencies=[],
    )

    config = ska_sdp_config.Config()

    # Add a new processing block to transactions
    for txn in config.txn():
        assert controller._get_pb_status(txn, PROCESSING_BLOCK_ID) is None
        txn.create_processing_block(pb)

    return controller, config


def clear_config(config):
    """
    Remove all of the processing blocks and deployments from the config db.
    """
    config.backend.delete("/pb", must_exist=False, recursive=True)
    config.backend.delete("/deploy", must_exist=False, recursive=True)


@patch.dict(os.environ, MOCK_ENV_VARS)
def test_controller_main_loop_start_workflow(controller_and_config_fixture):
    """
    Test that the ProcessingController.main_loop starts the
    workflow deployment based on the existing processing blocks in the config db.

    This only tests that the main_loop starts the deployment if
    the processing block doesn't have a state, i.e. no deployments have been started based on it.
    """
    controller = controller_and_config_fixture[0]
    config = controller_and_config_fixture[1]

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
        assert f"proc-{PROCESSING_BLOCK_ID}-workflow" in deployment_ids

    clear_config(config)


@patch("signal.signal")
@patch("sys.exit")
def test_main(mock_exit, mock_signal):
    processing_controller.main(backend="memory")
    processing_controller.terminate(None, None)


@patch.dict(os.environ, MOCK_ENV_VARS)
def test_proc_control_start_new_pb_workflows(controller_and_config_fixture):
    """
    ProcessingController._start_new_pb_workflows correctly starts
    a workflow of a newly added processing block.
    """
    controller = controller_and_config_fixture[0]
    config = controller_and_config_fixture[1]

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
    controller_and_config_fixture,
):
    """
    ProcessingController._release_pbs_with_finished_dependencies correctly
    sets the 'resources_available' state key of the processing block to True
    if the status of the pb is WAITING and all dependencies have finished.

    Here the created pb does not have dependencies. (see fixture)
    """
    controller = controller_and_config_fixture[0]
    config = controller_and_config_fixture[1]

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
def test_delete_deployments_without_pb(controller_and_config_fixture):
    """
    ProcessingControl._delete_deployments_without_pb successfully removes
    deployments without a processing block
    """
    controller = controller_and_config_fixture[0]
    config = controller_and_config_fixture[1]

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
            watcher, processing_block_ids, ["proc-pb-test-20210118-00000-workflow"]
        )

    for txn in config.txn():
        assert len(txn.list_deployments()) == 0

    clear_config(config)
